"""
AI Strategic Advisor & Decision Engine for Sim Companies
=========================================================
Synthesizes live company telemetry, order-book depth, and retail economics
into prioritized executive action plans. Supports both deterministic mathematical
reasoning and local LLM generative advisory (via Ollama qwen2.5:3b / gemma4:e4b).
"""

import json
import urllib.request
import urllib.error
from .constants import (
    C_RESET, C_BOLD, C_GREEN, C_YELLOW, C_CYAN, C_RED, C_BLUE, C_MAGENTA, C_DIM,
    OLLAMA_API_URL, DEFAULT_OLLAMA_MODEL, OFFICIAL_NAMES, SEASONAL_ITEM_IDS, RETAIL_STORES
)

SYSTEM_PROMPT = """You are the Senior Chief Strategy Officer (CSO) and Algorithmic Trading Advisor for a Sim Companies tycoon company.
Your goal is to maximize company valuation, return on capital (ROI), and continuous cash flow velocity.

Rules of Sim Companies you MUST follow:
1. Exchange trades incur a 4% seller market fee. Direct contracts have 0% market fee.
2. Retail sales have 0% market fee and deliver high gross margins (+50% to +350%).
3. Retail units sell at a steady speed (units/hour) determined by store level and market saturation.
4. Higher quality (stars ★) increases retail selling speed and customer satisfaction.
5. Inactive seasonal goods (Easter, Summer, Halloween, Christmas) cannot be retailed or produced outside active event dates.
6. Cash management: Keep at least 15-20% cash buffer for wages and admin overhead; allocate the rest to high-velocity retail inventory.
7. TIME & TURNOVER VELOCITY (CRITICAL):
   - Always calculate and factor in the TIME TAKEN to sell inventory: Time (hours) = Quantity / (Units/hr * Building Level).
   - Never recommend buying a batch that takes longer than 24-36 hours to liquidate if it locks up more than 50% of the player's capital.
   - Always contrast "Markup % (ROI)" against "Hourly Cash Flow ($/hour)" and "Turnover Speed":
     * Fast-turnover goods (e.g. Oranges @ 90u/hr, Apples @ 110u/hr) liquidate cash in 1-3 hours, allowing the player to reinvest and compound profits multiple times per day.
     * High-margin goods (e.g. Underwear @ 25u/hr) give immense % ROI (+350%) but liquidate slower (~4 hours per 100 units per level).
   - In your answer, always state:
     a) Exact time (hours and minutes) required to liquidate the recommended batch.
     b) Profit velocity ($ per hour and $ per day).
     c) When the working capital will be unlocked for reinvestment.

Respond concisely, with actionable numbers, exact item names, prices, sellout durations, and clear steps. Avoid generic fluff.
"""

class StrategicAdvisor:
    def __init__(self, client, model=DEFAULT_OLLAMA_MODEL):
        self.client = client
        self.model = model

    def build_telemetry_snapshot(self):
        """Assemble a complete structured telemetry snapshot of the player's business."""
        comp = self.client.get_company_data()
        prices_raw = self.client.fetch_prices(comp.get("realm_id", 0))
        retail_map = self.client.fetch_retail_data(comp.get("realm_id", 0))
        res_meta = self.client.fetch_resource_definitions()

        prices_by_rq = {}
        if prices_raw and "prices" in prices_raw:
            for p in prices_raw["prices"]:
                prices_by_rq[(p["resourceId"], p["quality"])] = p["price"]

        cash = comp.get("money", 0.0)
        buildings = comp.get("buildings", [])
        warehouse = comp.get("warehouse", [])

        # Warehouse valuation
        wh_val = 0.0
        wh_net = 0.0
        wh_items = []
        for w in warehouse:
            rid = w["kind"]
            q = w["quality"]
            qty = w["amount"]
            p = prices_by_rq.get((rid, q), prices_by_rq.get((rid, 0), 0.0))
            gross = qty * p
            net = gross * 0.96
            wh_val += gross
            wh_net += net
            wh_items.append({
                "rid": rid,
                "name": OFFICIAL_NAMES.get(rid, f"Item {rid}"),
                "qty": qty,
                "quality": q,
                "unit_price": p,
                "gross_val": gross,
                "net_val": net
            })

        # Retail analysis for active goods
        retail_opps = []
        for sname, sinfo in RETAIL_STORES.items():
            for rid in sinfo["items"]:
                p_buy = prices_by_rq.get((rid, 0))
                r_info = retail_map.get(rid)
                if not p_buy or not r_info:
                    continue
                p_ret = r_info["averagePrice"]
                if p_ret <= 0 or p_buy <= 0:
                    continue
                markup = ((p_ret - p_buy) / p_buy) * 100
                speed = res_meta.get(rid, {}).get("unitsSoldAnHour", 0.0)
                profit_unit = p_ret - p_buy
                profit_hr = speed * profit_unit
                retail_opps.append({
                    "store": sname,
                    "rid": rid,
                    "name": OFFICIAL_NAMES.get(rid, f"Item {rid}"),
                    "buy": p_buy,
                    "retail": p_ret,
                    "markup": markup,
                    "profit_unit": profit_unit,
                    "speed": speed,
                    "profit_hr": profit_hr,
                    "affordable": int(cash // p_buy) if cash >= p_buy else 0
                })

        retail_opps.sort(key=lambda x: x["markup"], reverse=True)

        return {
            "company": comp,
            "cash": cash,
            "buildings": buildings,
            "warehouse_items": wh_items,
            "warehouse_total_gross": wh_val,
            "warehouse_total_net": wh_net,
            "retail_opportunities": retail_opps,
            "prices_by_rq": prices_by_rq
        }

    def generate_action_plan(self):
        """Deterministic mathematical strategic action plan."""
        data = self.build_telemetry_snapshot()
        cash = data["cash"]
        comp = data["company"]
        buildings = comp.get("buildings", [])

        # Categorize current player facilities
        facility_counts = {}
        for b in buildings:
            facility_counts[b["name"]] = facility_counts.get(b["name"], 0) + b.get("size", 1)

        has_fashion = "Fashion store" in facility_counts
        has_grocery = "Grocery store" in facility_counts
        has_farm = "Farm" in facility_counts

        # Strategic Action Items
        actions = []

        def format_time(hours):
            if hours <= 0:
                return "0m"
            h = int(hours)
            m = int(round((hours - h) * 60))
            if h > 0 and m > 0:
                return f"{h}h {m:02d}m"
            elif h > 0:
                return f"{h}h"
            else:
                return f"{m}m"

        # Action 1: Fashion Store Retail
        if has_fashion:
            fashion_lvl = facility_counts.get("Fashion store", 1)
            underwear_opp = next((r for r in data["retail_opportunities"] if r["rid"] == 60), None)
            if underwear_opp:
                speed_effective = underwear_opp["speed"] * fashion_lvl
                budget = min(cash * 0.40, 8000.0)
                units = int(budget // underwear_opp["buy"])
                expected_rev = units * underwear_opp["retail"]
                expected_profit = expected_rev - (units * underwear_opp["buy"])
                duration_hrs = (units / speed_effective) if speed_effective > 0 else 0
                time_str = format_time(duration_hrs)
                profit_hr = speed_effective * underwear_opp["profit_unit"]

                existing_wh = next((w for w in data["warehouse_items"] if w["rid"] == 60), None)
                existing_note = None
                if existing_wh:
                    ex_hours = existing_wh["qty"] / speed_effective if speed_effective > 0 else 0
                    existing_note = f"Warehouse stock: {existing_wh['qty']:,} units (Q{existing_wh['quality']}) = {format_time(ex_hours)} of sales queued."

                actions.append({
                    "title": "Stock Fashion Store with Underwear",
                    "priority": "HIGH",
                    "store": f"Fashion Store (Level {fashion_lvl})",
                    "item": "Underwear",
                    "buy_price": underwear_opp["buy"],
                    "sell_price": underwear_opp["retail"],
                    "markup": underwear_opp["markup"],
                    "units": units,
                    "speed": speed_effective,
                    "duration_hrs": duration_hrs,
                    "time_str": time_str,
                    "profit_hr": profit_hr,
                    "existing_note": existing_note,
                    "capital_required": units * underwear_opp["buy"],
                    "expected_revenue": expected_rev,
                    "net_profit": expected_profit,
                    "instructions": f"Buy {units:,} units of Underwear @ ~${underwear_opp['buy']:.2f}. Takes {time_str} to sell out at {speed_effective:.1f} u/hr, yielding +${expected_profit:,.2f} profit (+${profit_hr:,.2f}/hr)."
                })

        # Action 2: Grocery Store Retail
        if has_grocery:
            grocery_lvl = facility_counts.get("Grocery store", 1)
            grocery_items = [r for r in data["retail_opportunities"] if r["store"] == "Grocery store"]
            top_grocery = grocery_items[:2] if grocery_items else []
            for item in top_grocery:
                speed_effective = item["speed"] * grocery_lvl
                budget = min(cash * 0.25, 4000.0)
                units = int(budget // item["buy"])
                if units > 0:
                    expected_rev = units * item["retail"]
                    expected_profit = expected_rev - (units * item["buy"])
                    duration_hrs = (units / speed_effective) if speed_effective > 0 else 0
                    time_str = format_time(duration_hrs)
                    profit_hr = speed_effective * item["profit_unit"]

                    actions.append({
                        "title": f"Stock Grocery Stores with {item['name']}",
                        "priority": "HIGH",
                        "store": f"Grocery Store (Level {grocery_lvl})",
                        "item": item["name"],
                        "buy_price": item["buy"],
                        "sell_price": item["retail"],
                        "markup": item["markup"],
                        "units": units,
                        "speed": speed_effective,
                        "duration_hrs": duration_hrs,
                        "time_str": time_str,
                        "profit_hr": profit_hr,
                        "existing_note": None,
                        "capital_required": units * item["buy"],
                        "expected_revenue": expected_rev,
                        "net_profit": expected_profit,
                        "instructions": f"Stock {units:,} units of {item['name']} @ ${item['buy']:.2f}. Takes {time_str} to sell out at {speed_effective:.1f} u/hr (+${profit_hr:,.2f}/hr, +{item['markup']:.1f}% ROI)."
                    })

        # Action 3: Farm Production Synergy
        if has_farm:
            actions.append({
                "title": "Align Farm Production to Feed Grocery Stores",
                "priority": "MEDIUM",
                "store": "Farm (Size 3)",
                "item": "Apples / Oranges",
                "buy_price": 0.0,
                "sell_price": 6.24,
                "markup": 450.0,
                "units": 0,
                "capital_required": 0.0,
                "expected_revenue": 0.0,
                "net_profit": 0.0,
                "instructions": "Grow Apples and Oranges on your Farm using stored Water. Production cost is ~$1.00/unit, retailing for $5.40-$6.24 in your Grocery Stores (+450% pure profit)."
            })

        # Action 4: Warehouse Surplus Liquidation
        wh_actions = []
        for w in data["warehouse_items"]:
            if w["rid"] == 111 and w["qty"] >= 1:  # Construction units
                wh_actions.append(f"Sell {w['qty']}x Construction Units (+${w['net_val']:,.2f} net cash)")
            elif w["rid"] == 2 and w["qty"] > 4000:  # Excess water
                excess = w["qty"] - 3000
                wh_actions.append(f"Sell {excess:,} surplus Water (+${excess * w['unit_price'] * 0.96:,.2f} net cash)")

        return {
            "telemetry": data,
            "facility_counts": facility_counts,
            "actions": actions,
            "wh_actions": wh_actions
        }

    def print_executive_briefing(self):
        """Format and print the executive action plan to the terminal."""
        plan = self.generate_action_plan()
        data = plan["telemetry"]
        comp = data["company"]
        cash = data["cash"]

        print(f"\n{C_BOLD}{C_CYAN}========================================================================================{C_RESET}")
        print(f"{C_BOLD}{C_CYAN}                  SIM COMPANIES AI EXECUTIVE STRATEGY BRIEFING                           {C_RESET}")
        print(f"{C_BOLD}{C_CYAN}========================================================================================{C_RESET}\n")

        print(f" {C_BOLD}Company:{C_RESET} {C_GREEN}{comp['company_name']}{C_RESET} (Lvl {comp['level']}, Realm {comp.get('realm_id', 0)})")
        print(f" {C_BOLD}Working Capital:{C_RESET} {C_YELLOW}${cash:,.2f}{C_RESET}  |  {C_BOLD}Warehouse Liquidation Value:{C_RESET} {C_GREEN}${data['warehouse_total_net']:,.2f}{C_RESET}")
        facilities_str = ", ".join([f"{k} (x{v})" for k, v in plan["facility_counts"].items()])
        print(f" {C_BOLD}Operating Facilities:{C_RESET} {facilities_str}\n")

        print(f"{C_BOLD}{C_YELLOW}--- PRIORITIZED IMMEDIATE ACTION ITEMS ---{C_RESET}")
        for i, a in enumerate(plan["actions"], 1):
            color = C_GREEN if a["priority"] == "HIGH" else C_CYAN
            print(f" {C_BOLD}#{i}. [{a['priority']}] {a['title']}{C_RESET}")
            print(f"    ↳ Target: {color}{a['store']}{C_RESET} | Inventory: {a['item']}")
            if a["capital_required"] > 0:
                print(f"    ↳ Allocate: {C_YELLOW}${a['capital_required']:,.2f}{C_RESET} ({a['units']:,} units @ ${a['buy_price']:.2f})")
                print(f"    ↳ Time to Sell Out: {C_BOLD}{a.get('time_str', 'N/A')}{C_RESET} (Throughput: {a.get('speed', 0):.1f} units/hr)")
                print(f"    ↳ Projected Revenue: ${a['expected_revenue']:,.2f} | {C_GREEN}Net Profit: +${a['net_profit']:,.2f} (+{a['markup']:.1f}% ROI){C_RESET}")
                print(f"    ↳ Profit Velocity: {C_CYAN}+${a.get('profit_hr', 0):,.2f}/hr{C_RESET} (+${a.get('profit_hr', 0)*24:,.2f}/day)")
                if a.get("existing_note"):
                    print(f"    ↳ {C_DIM}Note: {a['existing_note']}{C_RESET}")
            print(f"    ↳ Action: {a['instructions']}\n")

        if plan["wh_actions"]:
            print(f"{C_BOLD}{C_BLUE}--- CAPITAL UNLOCK RECOMMENDATIONS ---{C_RESET}")
            for act in plan["wh_actions"]:
                print(f" • {act}")
            print(f" {C_DIM}* Liquidating idle construction units & excess water immediately injects liquid cash into active retail.{C_RESET}\n")

        # Expansion Roadmap
        print(f"{C_BOLD}{C_MAGENTA}--- STRATEGIC EXPANSION ROADMAP ---{C_RESET}")
        if cash < 50000:
            print(f" • {C_BOLD}Phase 1 ($20k - $50k):{C_RESET} Reinvest 100% of retail cash into Underwear (Fashion Store) and Oranges/Apples (Grocery Stores).")
            print(f" • {C_BOLD}Phase 2 ($50k - $100k):{C_RESET} Upgrade Fashion Store to Level 2/3 to double retail throughput, or add Hardware Store for Bricks (+192% margin).")
        else:
            print(f" • {C_BOLD}Phase 2 ($100k+):{C_RESET} Expand into Electronics Store (Tablets +66% markup) or Car Dealership for high-ticket capital deployment.")
        print(f"\n{C_CYAN}========================================================================================{C_RESET}\n")

    def ask_llm(self, question):
        """Pass full company context and mathematical telemetry to local Ollama LLM."""
        plan = self.generate_action_plan()
        data = plan["telemetry"]
        comp = data["company"]

        top_retail_summary = "\n".join([
            f"- {r['name']} ({r['store']}): Wholesale ${r['buy']:.2f}, Retail Avg ${r['retail']:.2f}, Markup +{r['markup']:.1f}%, Speed {r['speed']:.1f} units/hr/lvl, Est. Profit +${r['profit_hr']:.2f}/hr (Time for 100 units: {100/r['speed']:.1f}h, Full Cash Batch {r['affordable']:,} units: {r['affordable']/r['speed']:.1f}h)"
            for r in data["retail_opportunities"][:10]
        ])

        context = f"""COMPANY FINANCIAL SNAPSHOT:
- Company Name: {comp['company_name']}
- Level: {comp['level']}
- Cash on Hand: ${data['cash']:,.2f}
- Warehouse Liquidation Value: ${data['warehouse_total_net']:,.2f}
- Facilities Owned: {json.dumps(plan['facility_counts'])}

TOP ACTIVE RETAIL COMMODITIES (WITH TIME DURATION & HOURLY VELOCITY):
{top_retail_summary}

MATHEMATICAL RECOMMENDED ACTIONS:
{json.dumps([a['instructions'] for a in plan['actions']], indent=2)}
"""

        prompt = f"""{context}

USER QUESTION:
"{question}"

Provide a direct, strategic, highly actionable answer based strictly on the financial numbers and game mechanics above:"""

        print(f"{C_DIM}[*] Consulting local strategic AI model ({self.model})...{C_RESET}\n")
        payload = {
            "model": self.model,
            "system": SYSTEM_PROMPT,
            "prompt": prompt,
            "stream": False
        }

        try:
            req = urllib.request.Request(
                f"{OLLAMA_API_URL}/api/generate",
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload).encode("utf-8")
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                response_text = result.get("response", "").strip()
                print(f"{C_BOLD}{C_GREEN}AI Strategic Advisory:{C_RESET}\n")
                print(response_text)
                print()
                return response_text
        except Exception as e:
            print(f"{C_YELLOW}[!] Could not reach local Ollama server ({e}). Falling back to algorithmic plan.{C_RESET}\n")
            self.print_executive_briefing()
            return None
