# Sim Companies Agent & Multi-Quality Market Intelligence 🏢🚀

An advanced algorithmic market scanner, retail return-on-capital optimizer, and autonomous executive advisor for **[Sim Companies](https://www.simcompanies.com/)**.

Equipped with direct real-time telemetry extraction, Cloudflare clearance bypass handling, multi-quality exchange arbitrage detection (Q0–Q4), order book depth inspection, and local Ollama LLM integration.

---

## 🌟 Key Features

1. **Live Company Telemetry Extraction**
   - Automatically reads the authenticated session cookie directly from the Electron app database or Chromium-based browsers (Brave/Chrome).
   - Retrieves real-time cash balance (`/api/v2/companies/me/cashflow/recent/`), level, realm status, warehouse liquidation value, and active infrastructure.

2. **Time-Horizon Retail Optimization (`/hr`, `/2hr`, `/8hr`, `/24hr`)**
   - Ranks all retail store sectors (Fashion, Grocery, Hardware, Electronics, Gas, Car, Aerospace).
   - Projects realistic net profits across configurable operating cycles:
     - **`/hr`**: Hourly throughput rate per store level.
     - **`/2hr`**: Short turnaround retail runs.
     - **`/8hr`**: Standard overnight / work shifts.
     - **`/24hr`**: Full-day liquidation throughput.
   - Calculates turnover velocity (`Time/100u`) and return-on-capital (% markup).

3. **Multi-Quality Exchange Arbitrage Scanner (Q0–Q4 ★★★★)**
   - Simultaneously scans market order books for all active commodities on your realm.
   - Detects pricing inefficiencies between buy-now price and 24h peak/VWAP.
   - Flags **★MISPRICED (STEALS)** where higher-quality commodities (Q1–Q4) are listed below base Q0 market value.
   - Net ROI formula accounts for the mandatory 4% exchange market fee:
     $$\text{Net ROI} = \frac{(\text{Target Price} \times 0.96) - \text{Buy Price}}{\text{Buy Price}} \times 100$$

4. **Order Book Depth Analysis**
   - Verifies whether Listing #1 can be bought and immediately relisted into Listings #5 and #10 for instant arbitrage turnaround.

5. **Direct Contract Sourcing Intelligence**
   - Discovers top active market producers for any raw material or retail good.
   - Generates customized direct contract negotiation messages (saving the buyer 3% and the producer the 4% exchange tax).

6. **Local LLM Autonomous Business Advisor (Ollama)**
   - Connects to local offline models (e.g. `qwen2.5:3b`, `llama3.2`) to evaluate financial health, facility optimization, and capital allocation.

---

## 📊 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/FM9447/sim-companies-agent.git
cd sim-companies-agent

# Install dependencies (Python 3.10+)
pip install requests browser-cookie3
```

*(Optional: Install Electron client dependencies if running the standalone desktop wrapper)*
```bash
npm install
npm start
```

---

## 💻 CLI Usage & Commands

The agent executable is configured as `sim-company-agent` or run directly via `python3 -m agent.cli`.

### 1. Default Market & Retail Scan
Scans multi-quality arbitrage opportunities and ranks retail stores against your live liquid cash:
```bash
sim-company-agent
```

### 2. Time-Horizon Retail Showcase (`--only-retail`)
Shows cash flow over time across `/hr`, `/2hr`, `/8hr`, and `/24hr`:
```bash
sim-company-agent --only-retail
```

### 3. Deep Order Book Check (`--depth`)
Inspects listing spreads against the 5th and 10th depth tiers:
```bash
sim-company-agent --depth --min-roi 3.0
```

### 4. Direct Contract Negotiation (`contracts`)
Finds top producers and builds a ready-to-send contract proposal:
```bash
sim-company-agent contracts underwear
sim-company-agent contracts apples
```

### 5. Strategic AI Advice (`advise`)
Generates rule-based executive priorities or full local LLM synthesis:
```bash
sim-company-agent advise
sim-company-agent advise --llm --model qwen2.5:3b
```

---

## 📈 Architecture Overview

```
sim-companies-agent/
├── agent/
│   ├── __init__.py           # Package initializer
│   ├── cli.py                # Command-line interface & terminal formatting
│   ├── client.py             # Sim Companies HTTP Client & session resolver
│   ├── constants.py          # Resource definitions, IDs, store maps, ANSI styling
│   └── strategy.py           # Strategic heuristic evaluation & LLM prompt builder
├── scripts/                  # Helper installation and launcher scripts
├── main.js                   # Electron desktop application entrypoint
├── Makefile                  # Build and desktop integration targets
├── README.md                 # Project documentation
└── package.json              # Electron packaging configuration
```

---

## ⚖️ License

Distributed under the MIT License. See `LICENSE` for more information.
