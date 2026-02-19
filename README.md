# UKFinGreatAssets (CIX Investment Platform) 🚀

**An MVP solution for the "Inclusive AI Loan Reallocation Engine" challenge by GFA Exchange.** *Built at the UK Finnovator Birmingham 2026 Hackathon.*

---

## 📖 Overview

UKFinGreatAssets is an automated, AI-driven sandbox and investment pipeline platform designed to help SME lenders identify, benchmark, and responsibly reallocate lending exposure. 

Addressing the core challenge of capital misallocation and static risk models in the SME lending space (specifically sub-£5m revenue businesses), our platform ingests lender investment theses, analyzes anonymized SME financial data, and utilizes a mathematical optimization engine to construct ideal "investment bundles". The goal is to improve financial inclusion outcomes, increase capital efficiency, and manage portfolio risk.

## ✨ Key Features

* **AI-Powered Thesis Ingestion:** Automatically parses investment thesis PDFs to extract budget constraints, KPIs, and desired sectoral weights.
* **Portfolio Optimization Engine:** Uses a formal linear programming (LP) formulation to construct an optimal investment bundle from available marketplace deals.
* **Smart Risk & Sector Rebalancing:** The algorithm explicitly minimizes sectoral misalignment (diluting over-exposed focus sectors) while applying a capital-weighted penalty for riskier investments (calculated via debt service, liquidity, and solvency ratios).
* **Interactive Dashboard:** A Flask-based web UI featuring:
  * **Portfolio View:** Track current holdings, ROI, and sectoral/geographic breakdowns.
  * **Insights:** Upload new investment theses and view AI-extracted metrics.
  * **Marketplace:** View and purchase LP-recommended deal allocations.
  * **Exchange:** Live transaction feed.

## 🧮 The Mathematics: Investment Bundle LP

Our reallocation engine relies on a rigorous linear program to trade off sectoral misalignment against credit risk. 
* **Objective:** Minimize absolute GBP deviation from target sectoral allocations, plus a risk penalty.
* **Risk Aggregation:** Each candidate investment is scored using three standard metrics: Debt Service Coverage Ratio ($r_1$), Liquidity Ratio ($r_2$), and Solvency Ratio ($r_3$). 
* **Penalty:** The risk penalty is directly proportional to the capital deployed and inversely proportional to the aggregate risk score ($R_j = r_1 + r_2 + r_3$).

## 📸 Screenshots

![IMG_1403](https://github.com/user-attachments/assets/caebf7a6-5d06-4c16-838c-4df364186034)
![IMG_1405](https://github.com/user-attachments/assets/d2ac03e4-0ca2-460b-bf88-17e00ec3ea94)
![IMG_1407](https://github.com/user-attachments/assets/15c9c797-c270-45e9-aa84-b3235fb5339e)
![IMG_1408](https://github.com/user-attachments/assets/36e7cca9-a7c3-4cbd-a2ed-273e74b9a07e)
![IMG_1409](https://github.com/user-attachments/assets/3c587e10-1349-498a-9900-821f33754ac8)

## ⚙️ Project Structure

```
UKFinGreatAssets/
├── CIX Post functional/
│   ├── app.py                 # Flask web application & API endpoints
│   ├── main_pipeline.py       # Orchestrates end-to-end PDF parsing to LP optimization
│   ├── stage1.py              # PDF parsing & thesis extraction logic
│   ├── stage2.py              # CSV loading and linear programming solver
│   ├── results.json           # Output of the pipeline for the frontend
│   ├── templates/             # HTML templates for the UI
│   ├── static/                # CSS and JS assets
│   └── UKFIN_combined...csv   # Anonymized/Synthetic SME dataset
└── README.md

```

## 🚀 Getting Started

### Prerequisites

* Python 3.13+
* **[TODO: Add other dependencies like Flask, PuLP, PyPDF2, etc., once confirmed by teammate]**

### Installation

1. Clone the repository:
```bash
git clone [https://github.com/oligreenhalgh/ukfingreatassets.git](https://github.com/oligreenhalgh/ukfingreatassets.git)
cd ukfingreatassets/"CIX Post functional"

```


2. Install dependencies:
```bash
# [TODO: Add specific installation command once tech stack is confirmed, e.g., pip install -r requirements.txt]

```


3. **[TODO: Add any specific environment variable setup steps here if needed, such as LLM API keys]**
4. Run the Web Application:
```bash
python app.py

```


The application will be available at `http://localhost:5000`.

### CLI Usage

You can also run the core pipeline directly from the command line without the web interface:

```bash
python main_pipeline.py path/to/thesis.pdf --csv path/to/dataset.csv -o results.json

```

## 👥 Team

* Oliver Greenhalgh - [@oligreenhalgh](https://www.google.com/search?q=https://github.com/oligreenhalgh)
* Finn Holroyd - [@madebyfinn](https://www.google.com/search?q=https://github.com/madebyfinn)
* Lanz Sarmiento - [@LSaanrzmiento](https://www.google.com/search?q=https://github.com/LSaanrzmiento)
* Emily Merritt - [@EmilyEsther1311](https://www.google.com/search?q=https://github.com/EmilyEsther1311)

---

*Developed for UK Finnovator Birmingham 2026. Data used within the platform is synthetic/anonymized in compliance with privacy standards.*
