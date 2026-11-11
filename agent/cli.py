"""
Unified Command Line Interface for Sim Companies Agent
"""

import sys
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from .constants import (
    C_RESET, C_BOLD, C_GREEN, C_YELLOW, C_CYAN, C_RED, C_BLUE, C_MAGENTA, C_DIM,
    DEFAULT_COMPANY_ID, DEFAULT_OLLAMA_MODEL, OFFICIAL_NAMES, SEASONAL_ITEM_IDS, RETAIL_STORES,
    STORE_HOURLY_WAGES
)
from .client import SimCompaniesClient
from .advisor import StrategicAdvisor

def format_quality(q):
    """Format quality integer into star display."""
    if q == 0:
        return "Q0"
    elif q == 1:
        return "Q1 ★"
    elif q == 2:
        return "Q2 ★★"
    elif q == 3:
        return "Q3 ★★★"
    elif q == 4:
        return "Q4 ★★★★"
    else:
        return f"Q{q} {q}★"

def check_order_book_spread(client, realm_id, resource_id, quality=0):
    """Fetch live order book to analyze instant flip spread for exact quality."""
    orders = client.fetch_order_book(realm_id, resource_id)
    if not orders or not isinstance(orders, list):
        return None

    q_orders = [o for o in orders if o.get("quality") == quality]
    if len(q_orders) < 2:
        return None

    cheapest = q_orders[0]
    p_buy = cheapest.get("price", 0)
    qty_available = cheapest.get("quantity", 0)

    idx_5 = min(4, len(q_orders) - 1)
    idx_10 = min(9, len(q_orders) - 1)
    p_5th = q_orders[idx_5].get("price", p_buy)
    p_10th = q_orders[idx_10].get("price", p_buy)

    return {
        "p_buy": p_buy,
        "qty_available": qty_available,
        "quality": quality,
        "seller": cheapest.get("seller", {}).get("company", "Unknown"),
        "seller_id": cheapest.get("seller", {}).get("id"),
        "p_5th": p_5th,
        "p_10th": p_10th,
        "spread_5th_net": ((p_5th * 0.96) - p_buy) / p_buy * 100 if p_buy > 0 else 0,
        "spread_10th_net": ((p_10th * 0.96) - p_buy) / p_buy * 100 if p_buy > 0 else 0
    }

def fetch_resource_candlesticks(client, realm_id, rid, prices_by_q, target_quality=None, max_q=4):
    """Worker function to fetch resource candlestick data concurrently."""
    url = f"https://api.simcotools.com/v1/realms/{realm_id}/market/resources/{rid}"
    r_info = client.fetch_json(url)
    if not r_info or "resource" not in r_info:
        return []

    summaries = r_info["resource"].get("summariesByQuality", [])
    results = []

    for q_summary in summaries:
        q = q_summary.get("quality", 0)
        if target_quality is not None and q != target_quality:
            continue
        if q > max_q:
            continue

        p_buy = prices_by_q.get((rid, q))
        if not p_buy or p_buy <= 0:
            continue

        candlestick = q_summary.get("lastDayCandlestick") or {}
        high_24h = candlestick.get("high", p_buy)
        low_24h = candlestick.get("low", p_buy)
        vwap_24h = candlestick.get("vwap", p_buy)
        volume_24h = candlestick.get("volume", 0)

        recent_closes = [c["closePrice"] for c in q_summary.get("latestClosePrices", []) if "closePrice" in c]
        recent_high = max(recent_closes) if recent_closes else high_24h

        results.append({
            "rid": rid,
            "quality": q,
            "p_buy": p_buy,
            "high_24h": high_24h,
            "low_24h": low_24h,
            "vwap": vwap_24h,
            "volume": volume_24h,
            "recent_high": recent_high
        })

    return results

def compute_all_stores_analysis(prices_by_rq, res_meta, retail_map, cash, include_seasonal=False):
    """Calculate retail profitability metrics across every store type."""
    store_results = {}
    all_retail_items = []

    for store_name, s_info in RETAIL_STORES.items():
        candidate_rids = list(s_info["items"])
        if include_seasonal:
            candidate_rids.extend(s_info.get("seasonal", []))

        items_data = []
        for rid in candidate_rids:
            if not include_seasonal and rid in SEASONAL_ITEM_IDS:
                continue

            p_buy = prices_by_rq.get((rid, 0))
            r_data = retail_map.get(rid)
            if not p_buy or not r_data:
                continue

            p_retail = r_data["averagePrice"]
            if p_retail <= 0 or p_buy <= 0:
                continue

            markup = ((p_retail - p_buy) / p_buy) * 100
            profit_unit = p_retail - p_buy
            speed = res_meta.get(rid, {}).get("unitsSoldAnHour", 0.0)
            gross_hourly = speed * profit_unit
            wage_hourly = STORE_HOURLY_WAGES.get(store_name, 0.0)
            net_hourly = gross_hourly - wage_hourly
            affordable_units = int(cash // p_buy) if cash >= p_buy else 0
            name = res_meta.get(rid, {}).get("name", f"Resource {rid}")

            item_obj = {
                "store": store_name,
                "rid": rid,
                "name": name,
                "buy": p_buy,
                "retail": p_retail,
                "markup": markup,
                "profit_unit": profit_unit,
                "speed": speed,
                "wage_hourly": wage_hourly,
                "profit_hourly": net_hourly,
                "gross_hourly": gross_hourly,
                "affordable": affordable_units
            }
            items_data.append(item_obj)
            all_retail_items.append(item_obj)

        items_data.sort(key=lambda x: x["markup"], reverse=True)
        store_results[store_name] = items_data

    return store_results, all_retail_items

def print_top_retail_leaderboard(all_retail_items, store_results, cash):
    """Print the dedicated showcase ranking the most profitable active retail opportunities."""
    print(f"\n{C_BOLD}{C_MAGENTA}========================================================================================{C_RESET}")
    print(f"{C_BOLD}{C_MAGENTA}         MOST PROFITABLE ACTIVE RETAIL OPPORTUNITIES (ACROSS ALL STORE TYPES)            {C_RESET}")
    print(f"{C_BOLD}{C_MAGENTA}========================================================================================{C_RESET}\n")

    top_by_margin = sorted(all_retail_items, key=lambda x: x["markup"], reverse=True)
    print(f"{C_BOLD}{C_GREEN}Top 10 Retail Items by Return on Capital (Highest % Markup):{C_RESET}")
    print(f"{'Item':<18} | {'Store Type':<18} | {'Wholesale':<10} | {'Retail Avg':<11} | {'Profit/Unit':<12} | {'Markup %':<10} | {'Speed/hr':<9} | {'Hourly $/hr'}")
    print("-" * 108)
    for it in top_by_margin[:10]:
        print(f"{C_BOLD}{it['name']:<18}{C_RESET} | {it['store']:<18} | ${it['buy']:<9.2f} | ${it['retail']:<10.2f} | ${it['profit_unit']:<11.2f} | {C_GREEN}+{it['markup']:6.1f}%{C_RESET}   | {it['speed']:<9.1f} | +${it['profit_hourly']:<9.2f}")
    print("-" * 108)
    print(f"{C_DIM}* Markup % gives return on capital; Speed/hr shows how fast each unit sells per building level.{C_RESET}\n")

    top_by_hourly = sorted(all_retail_items, key=lambda x: x["profit_hourly"], reverse=True)
    print(f"{C_BOLD}{C_CYAN}Top 10 Retail Items by True Net Profit After Worker Wages (/2hr, /8hr, /24hr):{C_RESET}")
    print(f"{'Item':<18} | {'Store Type':<16} | {'Speed/hr':<8} | {'Wage $/h':<9} | {'Net $/hr':<11} | {'/2hr':<11} | {'/8hr':<11} | {'/24hr':<12}")
    print("-" * 115)
    for it in top_by_hourly[:10]:
        p_hr = it['profit_hourly']
        p_2hr = p_hr * 2.0
        p_8hr = p_hr * 8.0
        p_24hr = p_hr * 24.0
        color = C_GREEN if p_hr > 0 else C_RED
        print(f"{C_BOLD}{it['name']:<18}{C_RESET} | {it['store']:<16} | {it['speed']:<8.1f} | -${it['wage_hourly']:<7.2f} | {color}+${p_hr:<9.2f}{C_RESET} | +${p_2hr:<9.2f} | +${p_8hr:<9.2f} | {C_GREEN}+${p_24hr:<10.2f}{C_RESET}")
    print("-" * 115)
    print(f"{C_DIM}* Net $/hr strictly deducts building worker wages per level (Realm 0 base: $345/h * store salaryModifier).{C_RESET}\n")

    print(f"{C_BOLD}{C_YELLOW}Retail Store Power Ranking (Which Store is Best to Build?):{C_RESET}")
    print(f"{'Rank':<6} | {'Store Type':<24} | {'Avg Markup':<13} | {'Top Margin Item':<22} | {'Peak Hourly Item'}")
    print("-" * 96)
    
    store_summary = []
    for sname, items in store_results.items():
        if not items:
            continue
        avg_markup = sum(i["markup"] for i in items) / len(items)
        best_margin_item = max(items, key=lambda x: x["markup"])
        best_hourly_item = max(items, key=lambda x: x["profit_hourly"])
        store_summary.append({
            "name": sname,
            "avg_markup": avg_markup,
            "best_margin": best_margin_item,
            "best_hourly": best_hourly_item
        })

    store_summary.sort(key=lambda x: x["avg_markup"], reverse=True)
    for rank, s in enumerate(store_summary, 1):
        m_str = f"+{s['avg_markup']:.1f}%"
        margin_item_str = f"{s['best_margin']['name']} (+{s['best_margin']['markup']:.0f}%)"
        hourly_item_str = f"{s['best_hourly']['name']} (+${s['best_hourly']['profit_hourly']:.0f}/hr)"
        print(f" #{rank:<4} | {C_BOLD}{s['name']:<24}{C_RESET} | {C_GREEN}{m_str:<13}{C_RESET} | {margin_item_str:<22} | {hourly_item_str}")
    print("-" * 96)
    print(f"{C_DIM}* Fashion Store and Hardware Store offer the highest return on capital for small to mid balances.{C_RESET}\n")

def print_all_stores_tables(store_results, filter_store=None):
    """Print full detailed tables for all retail store types or a specific store."""
    for sname, items in store_results.items():
        if filter_store and filter_store.lower() not in sname.lower():
            continue

        desc = RETAIL_STORES[sname]["desc"]
        print(f"\n{C_BOLD}{C_BLUE}--- {sname.upper()} ({desc}) ---{C_RESET}")
        print(f"{'Retail Item':<18} | {'Wholesale':<10} | {'Retail Avg':<11} | {'Markup %':<11} | {'Profit/Unit':<12} | {'Units/hr':<9} | {'$/hr':<10} | {'/2hr':<10} | {'/24hr':<11}")
        print("-" * 114)
        if not items:
            print(f" {C_YELLOW}No active retail price data available.{C_RESET}")
        else:
            for it in items:
                color = C_GREEN if it['markup'] >= 50.0 else (C_YELLOW if it['markup'] >= 20.0 else C_RESET)
                p_hr = it['profit_hourly']
                p_2hr = p_hr * 2.0
                p_24hr = p_hr * 24.0
                print(f"{C_BOLD}{it['name']:<18}{C_RESET} | ${it['buy']:<9.2f} | ${it['retail']:<10.2f} | {color}+{it['markup']:6.1f}%{C_RESET}    | ${it['profit_unit']:<11.2f} | {it['speed']:<9.1f} | {color}+${p_hr:<8.2f}{C_RESET} | +${p_2hr:<8.2f} | {C_GREEN}+${p_24hr:<9.2f}{C_RESET}")
        print("-" * 114)

def find_contract_producers(client, query_item):
    """Search active producers for a target item on the exchange and output contract templates."""
    res_meta = client.fetch_resource_definitions()
    
    # Resolve item ID
    target_rid = None
    target_name = None
    for rid, info in res_meta.items():
        if query_item.lower() in info["name"].lower():
            target_rid = rid
            target_name = info["name"]
            break

    if not target_rid:
        print(f"{C_RED}[!] Could not find active resource matching '{query_item}'.{C_RESET}")
        return

    print(f"\n{C_BOLD}{C_CYAN}--- CONTRACT SOURCING INTELLIGENCE: {target_name.upper()} ---{C_RESET}")
    print(f"{C_DIM}Scanning live exchange order book for top active producers...{C_RESET}\n")

    orders = client.fetch_order_book(0, target_rid)
    if not orders:
        print(f"{C_YELLOW}No live market listings found for {target_name}.{C_RESET}\n")
        return

    print(f"{'Rank':<6} | {'Company':<24} | {'Company ID':<12} | {'Qty in Stock':<14} | {'Price':<8} | {'Quality'}")
    print("-" * 80)
    producers = []
    seen_companies = set()

    for o in orders:
        seller = o.get("seller", {})
        cname = seller.get("company", "Unknown")
        cid = seller.get("id")
        if cname in seen_companies:
            continue
        seen_companies.add(cname)
        qty = o.get("quantity", 0)
        price = o.get("price", 0.0)
        q = o.get("quality", 0)
        producers.append({
            "company": cname,
            "id": cid,
            "qty": qty,
            "price": price,
            "quality": q
        })
        if len(producers) >= 6:
            break

    for rank, p in enumerate(producers, 1):
        q_str = format_quality(p["quality"])
        print(f" #{rank:<4} | {C_BOLD}{p['company']:<24}{C_RESET} | {p['id']:<12} | {p['qty']:<14,d} | ${p['price']:<7.2f} | {C_YELLOW}{q_str}{C_RESET}")
    print("-" * 80)

    if producers:
        top_p = producers[0]
        rec_contract_price = round(top_p["price"] * 0.97, 2)
        print(f"\n{C_BOLD}{C_GREEN}Recommended Direct Contract Negotiation Template:{C_RESET}")
        print(f"{C_YELLOW}\"Hi {top_p['company']}! Looking to buy ~800-1,000 units of {target_name} on direct contract at ${rec_contract_price:.2f}. Can you send me a contract?\"{C_RESET}")
        print(f"{C_DIM}* Saves you 3% on wholesale cost, and saves them the 4% market exchange fee.{C_RESET}\n")

def run_scan(min_roi=2.0, check_depth=False, custom_cash=None, target_quality=None, max_quality=4, show_all_stores=False, filter_store=None, only_top_retail=False, include_seasonal=False):
    """Main scanning routine."""
    client = SimCompaniesClient()
    advisor = StrategicAdvisor(client)

    print(f"\n{C_BOLD}{C_CYAN}========================================================================================{C_RESET}")
    print(f"{C_BOLD}{C_CYAN}               SIM COMPANIES MULTI-QUALITY ARBITRAGE SCANNER (sim-company-agent)        {C_RESET}")
    print(f"{C_BOLD}{C_CYAN}========================================================================================{C_RESET}\n")

    comp_info = client.get_company_data()
    cash = custom_cash if custom_cash is not None else comp_info["money"]

    print(f" {C_BOLD}Company:{C_RESET} {C_GREEN}{comp_info['company_name']}{C_RESET} (ID: {comp_info['company_id']}, Realm: {comp_info['realm_id']}, Lvl: {comp_info['level']})")
    print(f" {C_BOLD}Live Cash Balance:{C_RESET} {C_YELLOW}${cash:,.2f}{C_RESET}")
    
    buildings_str = ", ".join([f"{b['name']} (x{b['size']})" for b in comp_info["buildings"]])
    print(f" {C_BOLD}Active Facilities:{C_RESET} {buildings_str if buildings_str else 'None'}\n")

    res_meta = client.fetch_resource_definitions()
    realm_id = comp_info.get("realm_id", 0)

    price_data = client.fetch_prices(realm_id)
    if not price_data or "prices" not in price_data:
        print(f"{C_RED}[-] Failed to load live price data from SimcoTools.{C_RESET}")
        return

    prices_by_rq = {}
    for p in price_data["prices"]:
        prices_by_rq[(p["resourceId"], p["quality"])] = p["price"]

    retail_map = client.fetch_retail_data(realm_id)
    store_results, all_retail_items = compute_all_stores_analysis(prices_by_rq, res_meta, retail_map, cash, include_seasonal)

    if only_top_retail:
        print_top_retail_leaderboard(all_retail_items, store_results, cash)
        return

    if show_all_stores or filter_store:
        print_top_retail_leaderboard(all_retail_items, store_results, cash)
        print_all_stores_tables(store_results, filter_store)
        return

    # Warehouse Liquidation Table
    if comp_info and comp_info["warehouse"]:
        print(f"{C_BOLD}{C_BLUE}--- WAREHOUSE LIQUIDATION ANALYSIS (With Quality / Stars ★) ---{C_RESET}")
        print(f"{'Item':<20} | {'Quality':<8} | {'Quantity':<10} | {'Current Mkt':<12} | {'Gross Value':<12} | {'Net Cash (after 4%)'}")
        print("-" * 96)
        total_gross = 0.0
        total_net = 0.0
        for w in comp_info["warehouse"]:
            rid = w["kind"]
            q = w["quality"]
            q_str = format_quality(q)
            name = res_meta.get(rid, {}).get("name", f"Resource {rid}")
            qty = w["amount"]
            mkt_price = prices_by_rq.get((rid, q), prices_by_rq.get((rid, 0), 0.0))
            gross = qty * mkt_price
            net = gross * 0.96
            total_gross += gross
            total_net += net
            print(f"{name:<20} | {C_YELLOW}{q_str:<8}{C_RESET} | {qty:<10,d} | ${mkt_price:<11.3f} | ${gross:<11.2f} | {C_GREEN}${net:<10.2f}{C_RESET}")
        print("-" * 96)
        print(f"{C_BOLD}Total Warehouse Market Value:{C_RESET} ${total_gross:,.2f}  |  {C_BOLD}Net Liquidation Cash:{C_RESET} {C_GREEN}${total_net:,.2f}{C_RESET}")
        print(f"{C_DIM}* Selling surplus materials frees up extra capital to fund larger arbitrage flips.{C_RESET}\n")

    # Multi-Quality Exchange Arbitrage Table
    q_scope_desc = f"Quality: {format_quality(target_quality)}" if target_quality is not None else f"Qualities: Q0 through Q{max_quality} ★"
    print(f"{C_BOLD}{C_BLUE}--- MULTI-QUALITY ARBITRAGE SCAN ({q_scope_desc} | Net ROI >= +{min_roi:.1f}%) ---{C_RESET}")
    print(f"{C_DIM}Formula: Net ROI = ((Target Price * 0.96) - Buy Price) / Buy Price >= +{min_roi:.1f}% (Gross Spread >= +{((min_roi/100 + 1)/0.96 - 1)*100:.2f}%){C_RESET}")
    print(f"{C_DIM}Scanning active commodities on Realm {realm_id}...{C_RESET}", end="", flush=True)

    affordable_rids = set()
    for (rid, q), price in prices_by_rq.items():
        if not include_seasonal and rid in SEASONAL_ITEM_IDS:
            continue
        if target_quality is not None and q != target_quality:
            continue
        if q <= max_quality and 0 < price <= cash:
            affordable_rids.add(rid)

    candidates = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(fetch_resource_candlesticks, client, realm_id, rid, prices_by_rq, target_quality, max_quality): rid for rid in affordable_rids}
        for future in as_completed(futures):
            items = future.result()
            for res in items:
                rid = res["rid"]
                if not include_seasonal and rid in SEASONAL_ITEM_IDS:
                    continue

                p_buy = res["p_buy"]
                high_24h = res["high_24h"]
                target_price = high_24h

                gross_spread = ((target_price - p_buy) / p_buy) * 100
                net_roi = ((target_price * 0.96) - p_buy) / p_buy * 100

                if net_roi >= min_roi:
                    q = res["quality"]
                    name = res_meta.get(rid, {}).get("name", f"Resource {rid}")
                    max_units = int(cash // p_buy)
                    net_profit_total = max_units * ((target_price * 0.96) - p_buy)
                    
                    p_q0 = prices_by_rq.get((rid, 0))
                    is_steal = (q > 0 and p_q0 and p_buy <= p_q0)

                    candidates.append({
                        "id": rid,
                        "quality": q,
                        "name": name,
                        "buy_price": p_buy,
                        "target_price": target_price,
                        "vwap": res["vwap"],
                        "recent_high": res["recent_high"],
                        "volume": res["volume"],
                        "gross_spread": gross_spread,
                        "net_roi": net_roi,
                        "max_units": max_units,
                        "net_profit_total": net_profit_total,
                        "is_steal": is_steal
                    })

    print(f" {C_GREEN}Done! ({len(candidates)} active opportunities found across qualities){C_RESET}\n")

    candidates.sort(key=lambda x: x["net_roi"], reverse=True)

    if not candidates:
        print(f" {C_YELLOW}No items currently found meeting >= +{min_roi:.1f}% net profit threshold.{C_RESET}\n")
    else:
        print(f"{'Item':<18} | {'Quality':<8} | {'Buy Now':<9} | {'Sell Target':<11} | {'Gross Spread':<13} | {'Net ROI %':<11} | {'Affordable':<11} | {'Est. Net Profit'}")
        print("-" * 106)
        for c in candidates[:15]:
            q_str = format_quality(c["quality"])
            steal_badge = f"{C_MAGENTA}★MISPRICED{C_RESET}" if c["is_steal"] else ""
            print(f"{C_BOLD}{c['name']:<18}{C_RESET} | {C_YELLOW}{q_str:<8}{C_RESET} | ${c['buy_price']:<8.3f} | ${c['target_price']:<10.3f} | +{c['gross_spread']:6.2f}%      | {C_GREEN}+{c['net_roi']:6.2f}%{C_RESET}    | {c['max_units']:<11,d} | {C_GREEN}+${c['net_profit_total']:<10.2f}{C_RESET} {steal_badge}")
        print("-" * 106)
        print(f"{C_DIM}* Est. Net Profit assumes purchasing maximum affordable units with current ${cash:,.2f} cash.{C_RESET}\n")

    # Order Book Depth
    if check_depth and candidates:
        print(f"{C_BOLD}{C_BLUE}--- LIVE ORDER BOOK DEPTH CHECK (Instant Relisting Potential by Quality) ---{C_RESET}")
        print(f"{C_DIM}Checks if Listing #1 of that exact quality is priced far below Listing #5 and #10 on the live order book.{C_RESET}\n")
        checked_pairs = set()
        count = 0
        for c in candidates:
            if (c["id"], c["quality"]) in checked_pairs:
                continue
            checked_pairs.add((c["id"], c["quality"]))
            depth = check_order_book_spread(client, realm_id, c["id"], c["quality"])
            if depth:
                count += 1
                q_str = format_quality(c["quality"])
                print(f" • {C_BOLD}{c['name']} ({q_str}){C_RESET}: Listing #1 has {depth['qty_available']:,} units @ ${depth['p_buy']:.3f} (Seller: {depth['seller']})")
                color_5th = C_GREEN if depth['spread_5th_net'] >= min_roi else C_YELLOW
                color_10th = C_GREEN if depth['spread_10th_net'] >= min_roi else C_YELLOW
                print(f"   ↳ vs 5th listing:  ${depth['p_5th']:.3f} -> Net ROI: {color_5th}+{depth['spread_5th_net']:.2f}%{C_RESET}")
                print(f"   ↳ vs 10th listing: ${depth['p_10th']:.3f} -> Net ROI: {color_10th}+{depth['spread_10th_net']:.2f}%{C_RESET}\n")
            if count >= 6:
                break

    # Top Retail Highlights
    print_top_retail_leaderboard(all_retail_items, store_results, cash)
    print(f"{C_DIM}Tip: Run 'sim-company-agent advise' for prioritized action recommendations.{C_RESET}")
    print(f"{C_CYAN}========================================================================================{C_RESET}\n")

def main():
    parser = argparse.ArgumentParser(description="Sim Companies Multi-Quality Market & AI Agent (sim-company-agent)")
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Agent command to execute")

    # 1. advise subcommand
    advise_p = subparsers.add_parser("advise", help="Generate prioritized executive business strategy action plan")
    advise_p.add_argument("--llm", action="store_true", help="Synthesize strategy with local Ollama AI model")
    advise_p.add_argument("--model", type=str, default=DEFAULT_OLLAMA_MODEL, help="Ollama model name (default: qwen2.5:3b)")

    # 2. ask subcommand
    ask_p = subparsers.add_parser("ask", help="Ask the AI agent a direct strategic question using live company telemetry")
    ask_p.add_argument("question", type=str, help="Question to ask the AI agent")
    ask_p.add_argument("--model", type=str, default=DEFAULT_OLLAMA_MODEL, help="Ollama model name (default: qwen2.5:3b)")

    # 3. contracts subcommand
    contract_p = subparsers.add_parser("contracts", help="Find active producers and generate direct contract negotiation templates")
    contract_p.add_argument("item", type=str, help="Item name to search producers for (e.g. underwear, apples, diesel)")

    # Default scanner flags
    parser.add_argument("--watch", action="store_true", help="Run continuously in watch mode")
    parser.add_argument("--interval", type=int, default=180, help="Interval between scans in watch mode (seconds, default: 180s = 3 mins)")
    parser.add_argument("--min-roi", type=float, default=2.0, help="Minimum net ROI percentage after 4%% fee (default: 2.0)")
    parser.add_argument("--quality", "-q", type=int, default=None, help="Filter for a specific quality level (e.g. 0, 1, 2, 3)")
    parser.add_argument("--max-q", type=int, default=4, help="Maximum quality level to scan (default: 4 = Q4 ★★★★)")
    parser.add_argument("--depth", action="store_true", help="Inspect live order book depth for top candidates")
    parser.add_argument("--cash", type=float, default=None, help="Override cash balance for calculation")
    parser.add_argument("--stores", action="store_true", help="Display full profitability tables for all 7 retail store types")
    parser.add_argument("--store", type=str, default=None, help="Filter by specific store name (e.g. grocery, fashion, electronics, cars, gas, hardware)")
    parser.add_argument("--top-retail", action="store_true", help="Display only the all-stores retail profit leaderboards")
    parser.add_argument("--seasonal", action="store_true", help="Include inactive seasonal event items")
    args = parser.parse_args()

    client = SimCompaniesClient()

    if args.command == "advise":
        advisor = StrategicAdvisor(client, model=args.model)
        if args.llm:
            advisor.ask_llm("Analyze my full company situation and provide a prioritized 3-step action plan for immediate profit and long-term expansion.")
        else:
            advisor.print_executive_briefing()
        return

    if args.command == "ask":
        advisor = StrategicAdvisor(client, model=args.model)
        advisor.ask_llm(args.question)
        return

    if args.command == "contracts":
        find_contract_producers(client, args.item)
        return

    # Watch mode
    if args.watch:
        print(f"{C_BOLD}{C_GREEN}[*] Starting Watch Mode (Scanning every {args.interval} seconds / {args.interval/60:.1f} minutes)... Press Ctrl+C to stop.{C_RESET}\n")
        try:
            while True:
                run_scan(min_roi=args.min_roi, check_depth=args.depth, custom_cash=args.cash, target_quality=args.quality, max_quality=args.max_q, show_all_stores=args.stores, filter_store=args.store, only_top_retail=args.top_retail, include_seasonal=args.seasonal)
                print(f"{C_DIM}Next scan in {args.interval} seconds ({time.strftime('%H:%M:%S', time.localtime(time.time() + args.interval))})...{C_RESET}\n")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print(f"\n{C_YELLOW}[*] Watch mode stopped by user.{C_RESET}")
    else:
        run_scan(min_roi=args.min_roi, check_depth=args.depth, custom_cash=args.cash, target_quality=args.quality, max_quality=args.max_q, show_all_stores=args.stores, filter_store=args.store, only_top_retail=args.top_retail, include_seasonal=args.seasonal)

if __name__ == "__main__":
    main()
