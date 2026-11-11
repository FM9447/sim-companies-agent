# Sim Companies Autonomous Strategy & Arbitrage Agent (AGENT_GUIDE.md)

> **Authoritative Technical Documentation & Onboarding Manual for Human Developers and Future AI Agents.**
> Everything required to maintain, execute, extend, and deploy the Sim Companies Trading & Retail Agent.

---

## 1. System Overview & Core Philosophy

The **Sim Companies Agent (`sim-company-agent`)** is a hybrid **Mathematical Decision Engine + Local Generative AI Advisor** built for the online economic simulation game *Sim Companies* (Realm 0: Magnates & Realm 1: Entrepreneurs).

### The Hybrid Design Philosophy:
1. **Deterministic Core (0% Hallucination):** Financial calculations (ROI, wholesale vs retail spreads, order-book depth, inventory liquidation, labor overhead) are computed mathematically via deterministic Python algorithms in under `0.5s`.
2. **Local AI Strategic Reasoning (Ollama):** When qualitative business advice, natural language Q&A, or strategic action plans are requested, the agent feeds live telemetry into an offline local LLM (`qwen2.5:3b` or `gemma4:e4b` via `http://localhost:11434`), delivering strategic intelligence without cloud API costs or data leakage.
3. **Zero-Ban Anti-Cheat Compliance:** The agent strictly performs **read-only** market scanning and company telemetry analysis. It never automates purchase clicks (`POST /api/v2/market-order/take/`), avoiding client-side bot detection (`X-Prot`, DOM telemetry) and ensuring **100% account safety**.

---

## 2. Codebase Architecture & File Structure

```
/media/fm9447/D/GAMES/sim-companies/
├── AGENT_GUIDE.md             # This comprehensive onboarding & technical guide
├── market_scanner.py          # Global executable entrypoint (symlinked to /home/fm9447/.local/bin/sim-company-agent)
└── agent/
    ├── __init__.py            # Package exports
    ├── constants.py           # In-game resource names (1-155), seasonal IDs, retail store maps, ANSI styling
    ├── client.py              # API client (session extraction, SQLite cookie parser, resilient cache fallback)
    ├── advisor.py             # Deterministic strategy planner + Ollama LLM reasoning engine
    └── cli.py                 # Unified CLI with subcommands (advise, ask, contracts, scan, stores)
```

---

## 3. Reverse-Engineered API Specifications

### A. Sim Companies Endpoints (`https://www.simcompanies.com`)

| Endpoint | Method | Auth Required | Purpose |
| :--- | :---: | :---: | :--- |
| `/api/v3/companies/auth-data/` | `GET` | Yes (`sessionid`) | Live cash balance, company ID, level, realm ID, PA alerts |
| `/api/v3/companies/{companyId}/` | `GET` | No (Public) | Company level, rating, active infrastructure & buildings list |
| `/api/v3/resources/{companyId}/` | `GET` | Yes (`sessionid`) | Live warehouse inventory: quantity, quality, cost basis |
| `/api/v3/market/{realm}/{resourceId}/` | `GET` | No (Public) | Live market order book: all active listings, sellers, quality, quantity |
| `/api/v4/{realm}/resources-retail-info/`| `GET` | No (Public) | Daily retail average prices, saturation index, sales volume |
| `/api/v2/constants/resources/` | `GET` | No (Public) | Base resource metadata: icons, units sold/hr, decay rates |
| `/api/v2/constants/buildings/` | `GET` | No (Public) | Building costs, build times, salary modifiers, categories |

#### Authentication & Session Harvesting:
- Sim Companies Electron client stores cookies in an unencrypted SQLite DB:
  `~/.config/Sim Companies/Partitions/simcompanies/Cookies`
- The session token is stored under `name = 'sessionid'`.
- **Resilient Fallback:** If the session cookie expires, `agent/client.py` falls back to the public company endpoint `/api/v3/companies/5960839/` combined with cached state in `~/.sim-company-cache.json`.

---

### B. SimcoTools Caching API (`https://api.simcotools.com`)

| Endpoint | Method | Rate Limits | Purpose |
| :--- | :---: | :---: | :--- |
| `/v1/realms/{realm}/market/prices` | `GET` | Medium | Bulk price index for all resources across Q0 to Q12 |
| `/v1/realms/{realm}/market/resources/{id}` | `GET` | Strict (0.02s delay) | 24h candlestick: open, high, low, close, volume, VWAP |
| `/v1/realms/{realm}/resources` | `GET` | Strict | Verified English names, production formulas, wages |

*Notice: To prevent `HTTP 429 Too Many Requests`, `agent/client.py` caches price payloads to `~/.sim-prices-cache.json`.*

---

## 4. Economic Game Formulas & Mathematics

### A. Exchange Arbitrage (The 4% Seller Fee)
When selling goods on the exchange, Sim Companies automatically deducts a **4.0% market fee**:
$$\text{Net Revenue} = P_{\text{sell}} \times (1 - 0.04) = 0.96 \times P_{\text{sell}}$$
$$\text{Net ROI \%} = \frac{(P_{\text{sell}} \times 0.96) - P_{\text{buy}}}{P_{\text{buy}}} \times 100\%$$

To achieve a minimum net profit of $\ge 2.0\%$:
$$P_{\text{sell}} \ge \frac{1.02}{0.96} \times P_{\text{buy}} \approx 1.0625 \times P_{\text{buy}} \implies \text{Required Gross Spread} \ge +6.25\%$$

### B. Retail Store Profit & Cash Velocity
Retail completely bypasses the 4% market fee (0% fee):
$$\text{Retail Markup \%} = \frac{P_{\text{retail}} - P_{\text{buy}}}{P_{\text{buy}}} \times 100\%$$
$$\text{Hourly Cash Flow} = \text{unitsSoldAnHour} \times (P_{\text{retail}} - P_{\text{buy}})$$

### C. Building Labor Overhead
Hourly wages depend on the building's `salaryModifier`:
- **Grocery Store (`G`):** `0.4x` (Cheapest labor in the game)
- **Hardware Store (`d`):** `0.5x`
- **Electronics Store (`C`):** `0.5x`
- **Fashion Store (`H`):** `0.9x`
- **Gas Station (`A`):** `1.0x`
- **Car Dealership (`2`):** `1.1x` (Highest wages)
- **Aerospace Sales (`B`):** `1.7x`

---

## 5. Active Retail Stores Map

```python
RETAIL_STORES = {
    "Grocery Store": [3, 4, 5, 7, 8, 9, 119, 121, 122, 123, 124, 125, 126, 127, 140],
    "Fashion Store": [60, 61, 62, 63, 64, 65, 70, 71],
    "Electronics Store": [24, 25, 26, 27, 28],
    "Gas Station": [11, 12],
    "Car Dealership": [53, 54, 55, 56, 57],
    "Hardware Store": [102, 103, 108, 109, 110],
    "Aerospace Sales Office": [91, 94, 95, 96, 97, 98, 99]
}
```

### C. Retail Turnover Speed & Liquidation Time:
$$\text{Effective Retail Speed} = \text{Base Units/Hour} \times \text{Building Level}$$
$$\text{Time to Liquidate (Hours)} = \frac{\text{Batch Quantity}}{\text{Effective Retail Speed}}$$
$$\text{Hourly Profit Velocity} = \text{Effective Retail Speed} \times (\text{Retail Price} - \text{Wholesale Cost})$$
$$\text{Daily Profit Potential} = \text{Hourly Profit Velocity} \times 24\text{ hours}$$

- **Fast Turnover (< 2 hours):** Apples (110u/hr), Oranges (90u/hr), Eggs (340u/hr). Unlocks working capital fast, compounding profits 8–12 times per day.
- **High Margin, Slower Turnover (4–12 hours):** Underwear (25u/hr), Gloves (20u/hr). Delivers massive +350% returns, but locks capital for longer cycles.

---

### Inactive Seasonal Items (Filtered by Default):
The following items **do not exist** in normal stores outside seasonal real-world event dates:
- `155`: Cream egg (Easter)
- `151`: Chocolate bunny (Easter)
- `152`: Baklava / Ramadan sweets (Ramadan)
- `153`, `154`: Chocolate & Apple icecream (Summer)
- `146`, `147`, `148`, `149`: Pumpkin, Jack-o'-lantern, Witch costume, Pumpkin soup (Halloween)
- `67`, `144`, `150`: Christmas crackers, Christmas ornament, Christmas tree (Xmas)

---

## 6. Local LLM Architecture & Prompt Engineering

The agent interfaces with the local Ollama daemon (`http://localhost:11434`):
- **Default Model:** `qwen2.5:3b` (installed locally, 1.9 GB, instant 3-5s inference).
- **Secondary Model:** `gemma4:e4b` (installed locally, 6.6 GB).

### Context Injection Architecture:
The agent dynamically builds a factual business context before dispatching to the LLM:
```
COMPANY FINANCIAL SNAPSHOT:
- Company Name: Asura Pvt
- Level: 10
- Cash on Hand: $20,140.00
- Warehouse Liquidation Value: $3,455.51
- Facilities Owned: {"Fashion store": 1, "Farm": 3, "Grocery store": 2, "Forest nursery": 3}

TOP ACTIVE RETAIL COMMODITIES RIGHT NOW:
- Underwear (Fashion Store): Buy $6.90, Retail $31.38, Markup +354.8%, Profit/hr $612.1
- Oranges (Grocery Store): Buy $2.30, Retail $6.24, Markup +171.1%, Profit/hr $336.3
...
```

---

## 7. CLI Command Reference for Daily Use

```bash
# 1. Executive AI Strategy Briefing (Deterministic Action Plan)
sim-company-agent advise

# 2. Executive Strategy with Local Generative AI Commentary
sim-company-agent advise --llm

# 3. Direct Conversational Business Consultation
sim-company-agent ask "Should I upgrade my Fashion Store or build another Grocery Store?"

# 4. Direct Contract Sourcing Intelligence
sim-company-agent contracts underwear
sim-company-agent contracts apples

# 5. Top Retail Profit Showcase (All Store Types)
sim-company-agent --top-retail

# 6. Detailed Store Breakdown
sim-company-agent --store fashion
sim-company-agent --store grocery
sim-company-agent --stores

# 7. Multi-Quality Exchange Arbitrage Scanner
sim-company-agent
sim-company-agent --depth --quality 1

# 8. Continuous Background Monitoring Watcher
sim-company-agent --watch --interval 180
```

---

## 8. Guide for Future Agents (How to Extend)

When a new AI agent takes over this codebase:
1. **Never write purchases to the API:** Automating `POST` buy orders will trigger `X-Prot` detection and ban the player. All purchasing advice must remain advisory.
2. **Adding New Store Types or Resources:** Modify `agent/constants.py` under `OFFICIAL_NAMES` and `RETAIL_STORES`.
3. **Changing LLM Models:** Set environment variable `export SIM_COMPANY_MODEL="gemma4:e4b"` or pass `--model gemma4:e4b` to `advise` or `ask`.
4. **Updating Session:** If the user logs in from a new machine, verify `/home/fm9447/.config/Sim Companies/Partitions/simcompanies/Cookies` is present.
