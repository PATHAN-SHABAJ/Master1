# 🤖 Flipkart Multi-Agent Monitoring System

A modular, enterprise-grade multi-agent architecture for tracking Flipkart products, detecting price drops & specification changes in real time, and updating a companion showcase web portal.

---

## 📁 Directory Structure

```text
D:\compare\flipcart\
│
├── agents\
│   ├── __init__.py          # Exports all agent classes
│   ├── discovery_agent.py   # Searches Flipkart for product links
│   ├── category_agent.py    # Crawls category pages with pagination
│   ├── product_agent.py     # Deep extraction (price, MRP, specs, highlights)
│   ├── change_agent.py      # Field-level diffing & change detection
│   └── update_agent.py      # Dispatches updates to the destination website API
│
├── website\
│   ├── __init__.py          # Website module
│   └── test_website.py      # Phone Finder test portal and HTTP REST API
│
├── core\
│   ├── __init__.py          # Core package
│   ├── config.py            # Central configurations, endpoints, timings
│   ├── browser.py           # Async Playwright manager with context lifecycle
│   └── api.py               # HTTP client for posting updates with retries
│
├── main.py                  # Master agent orchestrator loop
├── requirements.txt         # Project dependencies
└── README.md                # Documentation & usage guide
```

---

## ⚡ Architecture & Roles

| Component | Class | Responsibility |
|---|---|---|
| **Discovery Agent** | `DiscoveryAgent` | Performs searches on Flipkart to find new product URLs |
| **Category Agent** | `CategoryAgent` | Crawls category listings and handles pagination |
| **Product Agent** | `ProductAgent` | Parses product pages for Title, Price, MRP, Discount, Ratings, Brand, RAM, Storage, Seller, Highlights, and Offers |
| **Change Agent** | `ChangeAgent` | Compares product snapshots and flags field modifications |
| **Update Agent** | `UpdateAgent` | Sends verified product data to the local portal API |
| **Browser Manager** | `BrowserManager` | Handles Playwright Chromium lifecycle, viewport, and anti-bot headers |
| **API Client** | `ApiClient` | Robust HTTP communication with error recovery |
| **Test Website** | `HTTPServer` | Interactive Phone Finder storefront with live search and product modals |

---

## 🚀 Getting Started

### 1. Install Dependencies

```powershell
pip install -r requirements.txt
playwright install chromium
```

### 2. Run the Test Website

Start the mock storefront on `http://127.0.0.1:8000`:

```powershell
python website/test_website.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser to view available products and search.

### 3. Run the Monitoring Agents

In another terminal window:

```powershell
python main.py
```

The system will:
1. Launch the Playwright browser.
2. Navigate to configured products in `core/config.py`.
3. Extract live data, highlights, and pricing.
4. Detect differences against the previous state.
5. Push updates directly to the test website.
6. Sleep for the configured interval before repeating the cycle.
