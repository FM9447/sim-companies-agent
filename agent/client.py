"""
Sim Companies & SimcoTools API Client with Session & Cache Handling
"""

import os
import time
import json
import sqlite3
import urllib.request
import urllib.error
import gzip
try:
    import browser_cookie3
except Exception:
    browser_cookie3 = None

from .constants import (
    COOKIE_DB_PATH,
    CACHE_FILE_PATH,
    PRICES_CACHE_FILE,
    DEFAULT_COMPANY_ID,
    USER_AGENT,
    OFFICIAL_NAMES,
    SEASONAL_ITEM_IDS,
)

class SimCompaniesClient:
    def __init__(self, company_id=DEFAULT_COMPANY_ID):
        self.company_id = company_id
        # Load cookies from Electron DB and browser (Brave) if available
        self.session_cookie = self._extract_session_cookie()
        self.browser_cookies = self._load_browser_cookies()
        # Prefer browser session cookie if present
        if self.browser_cookies.get('sessionid'):
            self.session_cookie = self.browser_cookies['sessionid']
        # Store full cookie header string for reuse
        self.cookie_header = self._build_cookie_header()
        # Attempt to ensure Cloudflare challenge cookies are present
        try:
            self.refresh_cloudflare_cookies()
        except Exception as e:
            print('Warning: could not refresh Cloudflare cookies on init:', e)

    def _extract_session_cookie(self):
        """Extract `sessionid` cookie from the Electron app's SQLite DB.
        Returns the sessionid string if found, otherwise ``None``.
        """
        if not os.path.exists(COOKIE_DB_PATH):
            return None
        try:
            conn = sqlite3.connect(COOKIE_DB_PATH)
            cur = conn.cursor()
            # The Electron app stores cookies in the `cookies` table with name/value columns.
            cur.execute("SELECT value FROM cookies WHERE name='sessionid' LIMIT 1")
            row = cur.fetchone()
            conn.close()
            if row:
                return row[0]
        except Exception:
            pass
        return None

    def _load_browser_cookies(self):
        """Load cookies from Brave and Chrome using browser_cookie3.
        Returns a dict of cookie name to value for any Sim Companies related cookies.
        """
        cookies = {}
        if not browser_cookie3:
            return cookies
        # Try Brave first
        try:
            for c in browser_cookie3.brave():
                if 'simcompanies.com' in c.domain:
                    cookies[c.name] = c.value
        except Exception:
            pass
        # Try Chrome as fallback / additional source
        try:
            for c in browser_cookie3.chrome():
                if 'simcompanies.com' in c.domain:
                    cookies[c.name] = c.value
        except Exception:
            pass
        return cookies

    def _build_cookie_header(self):
        """Construct cookie header string from available cookies."""
        parts = []
        if self.session_cookie:
            parts.append(f"sessionid={self.session_cookie}")
        if self.browser_cookies.get('cf_clearance'):
            parts.append(f"cf_clearance={self.browser_cookies['cf_clearance']}")
        return "; ".join(parts) if parts else ""

    def refresh_cloudflare_cookies(self):
        """Refresh Cloudflare challenge cookies using browser_cookie3.
        Loads cookies from the Brave/Chrome browser profile and updates internal state.
        """
        # Reload cookies from the browser if possible.
        self.browser_cookies = self._load_browser_cookies()
        self.cookie_header = self._build_cookie_header()

    def fetch_json(self, url, timeout=10, retries=2):
        """Fetch JSON data from API endpoint with retry logic.
        Includes automatic Cloudflare challenge handling by refreshing cookies via Playwright.
        """
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "X-Requested-With": "XMLHttpRequest",
            "Connection": "keep-alive",
        }
        if "simcompanies.com" in url:
            headers["Referer"] = "https://www.simcompanies.com/"
        if self.cookie_header:
            headers["Cookie"] = self.cookie_header

        for attempt in range(retries + 1):
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    raw_data = resp.read()
                    if resp.headers.get('Content-Encoding') == 'gzip':
                        raw_data = gzip.decompress(raw_data)
                    raw = raw_data.decode("utf-8", errors="ignore")
                    return json.loads(raw)
            except urllib.error.HTTPError as e:
                # Do not spam terminal on 429 rate limits or 404s
                if e.code not in (404, 429):
                    try:
                        err_body = e.read().decode('utf-8', errors='ignore')
                    except Exception:
                        err_body = ''
                    print(f'HTTPError {e.code} for {url}:')
                    print(err_body[:500])
                    if e.code == 403 and ('cf_chl' in err_body or 'Cloudflare' in err_body):
                        try:
                            self.refresh_cloudflare_cookies()
                            self.cookie_header = self._build_cookie_header()
                            headers["Cookie"] = self.cookie_header
                        except Exception as e2:
                            print('Failed to refresh Cloudflare cookies:', e2)
                        continue
            except Exception:
                pass
            if attempt < retries:
                time.sleep(0.5)
        return None

    def get_company_data(self):
        """Fetch active company stats, cash balance, warehouse stock, and buildings.

        Uses the working API endpoints discovered from the game's JS bundle:
        - /api/v3/companies/{id}/  → public info (name, level, realm, buildings)
        - /api/v2/companies/{id}/balance-sheet/ → live cash balance (requires session cookie)
        - /api/v3/resources/{id}/  → warehouse inventory
        The old /api/v2/companies/me/ endpoint no longer exists on the server.
        """
        cached = self.load_cached_company()
        cid = cached.get("company_id", self.company_id)

        # 1. Public company info + buildings via v3 (always available)
        pub_data = self.fetch_json(f"https://www.simcompanies.com/api/v3/companies/{cid}/")
        if pub_data and isinstance(pub_data, dict):
            if "companyPublicInfo" in pub_data:
                c_pub = pub_data["companyPublicInfo"]
                cached["company_name"] = c_pub.get("company", cached.get("company_name"))
                cached["level"] = c_pub.get("level", cached.get("level", 10))
                cached["realm_id"] = c_pub.get("realmId", cached.get("realm_id", 0))
            if "infrastructure" in pub_data:
                b_list = pub_data["infrastructure"].get("buildings", [])
                cached["buildings"] = [
                    {"name": b.get("name"), "size": b.get("size", 1), "category": b.get("category", "")}
                    for b in b_list
                ]

        # 2. Live cash balance from /api/v2/companies/me/cashflow/recent/
        if self.session_cookie:
            cf_data = self.fetch_json("https://www.simcompanies.com/api/v2/companies/me/cashflow/recent/")
            if cf_data and isinstance(cf_data, dict) and cf_data.get("money") is not None:
                cached["money"] = float(cf_data["money"])
            else:
                # Fallback to balance-sheet
                balance = self.fetch_json(f"https://www.simcompanies.com/api/v2/companies/{cid}/balance-sheet/")
                if balance and isinstance(balance, dict) and "cash" in balance:
                    cash = float(balance.get("cash", 0.0))
                    reserved = float(balance.get("cashReservedForOrders", 0.0))
                    cached["money"] = cash + reserved

            # 3. Warehouse resources
            res_data = self.fetch_json(f"https://www.simcompanies.com/api/v3/resources/{cid}/")
            if res_data and isinstance(res_data, list):
                cached["warehouse"] = [
                    {"kind": r.get("kind"), "amount": r.get("amount", 0), "quality": r.get("quality", 0)}
                    for r in res_data
                ]

        self.save_cached_company(cached)
        return cached

    def load_cached_company(self):
        """Load cached company state."""
        if os.path.exists(CACHE_FILE_PATH):
            try:
                with open(CACHE_FILE_PATH, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "company_id": self.company_id,
            "company_name": "Asura Pvt",
            "money": 20140.0,
            "realm_id": 0,
            "level": 10,
            "buildings": [
                {"name": "Fashion store", "size": 1},
                {"name": "Farm", "size": 3},
                {"name": "Grocery store", "size": 1},
                {"name": "Grocery store", "size": 1},
                {"name": "Forest nursery", "size": 3}
            ],
            "warehouse": [
                {"kind": 1, "amount": 4000, "quality": 0},
                {"kind": 2, "amount": 8400, "quality": 0},
                {"kind": 101, "amount": 4, "quality": 0},
                {"kind": 102, "amount": 55, "quality": 0},
                {"kind": 108, "amount": 16, "quality": 0},
                {"kind": 111, "amount": 1, "quality": 0}
            ]
        }

    def save_cached_company(self, data):
        """Save latest company state to disk cache."""
        try:
            with open(CACHE_FILE_PATH, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def fetch_prices(self, realm_id=0):
        """Fetch market prices with disk caching fallback."""
        url = f"https://api.simcotools.com/v1/realms/{realm_id}/market/prices"
        data = self.fetch_json(url, timeout=12, retries=2)
        if data and "prices" in data:
            try:
                with open(PRICES_CACHE_FILE, "w") as f:
                    json.dump({"time": time.time(), "data": data}, f)
            except Exception:
                pass
            return data

        if os.path.exists(PRICES_CACHE_FILE):
            try:
                with open(PRICES_CACHE_FILE, "r") as f:
                    cached = json.load(f)
                    return cached.get("data")
            except Exception:
                pass

        return None

    def fetch_retail_data(self, realm_id=0):
        """Fetch retail information and average selling prices."""
        retail_list = self.fetch_json(f"https://www.simcompanies.com/api/v4/{realm_id}/resources-retail-info/")
        retail_map = {}
        if retail_list and isinstance(retail_list, list):
            for item in retail_list:
                rid = item.get("dbLetter")
                avg_price = item.get("averagePrice")
                saturation = item.get("saturation")
                if rid is not None and avg_price is not None:
                    if 0 < avg_price < 500000.0:
                        retail_map[rid] = {
                            "averagePrice": avg_price,
                            "saturation": saturation
                        }
        return retail_map

    def fetch_resource_definitions(self):
        """Fetch resource constants and metadata."""
        res_data = self.fetch_json("https://www.simcompanies.com/api/v2/constants/resources/")
        if not res_data:
            return {}

        names = {}
        for k, v in res_data.items():
            rid = int(k)
            name = OFFICIAL_NAMES.get(rid)
            if not name:
                img = v.get("image", "")
                name = img.split("/")[-1].replace(".png", "").replace("-", " ").title() if img else f"Resource {rid}"

            names[rid] = {
                "name": name,
                "producedAt": v.get("producedAt"),
                "unitsSoldAnHour": v.get("unitsSoldAnHour", 0.0),
                "is_seasonal": (rid in SEASONAL_ITEM_IDS or bool(v.get("retailSeason") or v.get("productionSeason")))
            }
        return names

    def fetch_order_book(self, realm_id, resource_id):
        """Fetch live market order book for a resource."""
        return self.fetch_json(f"https://www.simcompanies.com/api/v3/market/{realm_id}/{resource_id}/")
