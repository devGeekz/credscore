# CredScore
### MoMo-Based Credit Intelligence Infrastructure for the "Missing Middle"

---

## 1. Executive Summary

**CredScore** is a B2B financial infrastructure platform that converts a micro-merchant's informal Mobile Money (MoMo) transaction history into a standardized, lender-ready digital cash-flow statement and credit profile.

Rather than competing as a direct-to-consumer lending app in a crowded market, CredScore positions itself as the neutral **"picks and shovels" intelligence layer** underneath the digital credit ecosystem. It solves the acute data-blindness that banks, microfinance institutions (MFIs), and fintech lenders face when underwriting unbanked and underbanked micro, small, and medium enterprises (MSMEs) — delivered as a **web application + REST API + WhatsApp intake channel**, with zero app download required from merchants.

```
                  ┌─────────────────────────────────────┐
                  │            DATA SOURCES             │
                  │   MoMo (Wedge) ➔ Bank ➔ POS ➔ APIs  │
                  └──────────────────┬──────────────────┘
                                     │
                                     ▼
                  ┌─────────────────────────────────────┐
                  │           CREDSCORE LAYER           │
                  │   Ingestion ➔ Parsing ➔ Analytics   │
                  └──────────────────┬──────────────────┘
                                     │
                                     ▼
                  ┌─────────────────────────────────────┐
                  │        FINANCIAL INSTITUTIONS       │
                  │   MFIs ➔ Fintech Lenders ➔ Banks    │
                  └─────────────────────────────────────┘
```

---

## 2. The Problem: The "Missing Middle" Credit Gap

Millions of market traders, shop owners, and small service providers generate consistent, provable daily revenue. Because they operate almost entirely on Mobile Money wallets rather than formal bank accounts, they remain financially "invisible" to formal credit systems.

Traditional lenders evaluate MSME applicants using legacy criteria that structurally exclude this segment:

| Legacy Criterion | Why It Fails Micro-Merchants |
|---|---|
| Physical collateral (land, vehicles) | Most micro-merchants don't own qualifying assets |
| Audited financial statements | Rarely exist for informal businesses |
| Traditional bank statements | Business activity happens on MoMo, not in a bank account |
| Credit bureau records | Only capture *negative* signals (past defaults) — not real-time repayment capacity |

The result: lenders either reject these applicants outright or price the unknown risk with predatory interest rates, while the merchant's actual financial truth — a steady, verifiable stream of MoMo transactions — sits unused.

---

## 3. The Solution & Strategic Wedge

### Mobile Money as the Trojan Horse

Building a unified credit-scoring API across every financial channel on day one is a massive, unfundable undertaking. CredScore uses a deliberate **wedge strategy**, entering through the single hardest, highest-value problem and expanding laterally once trusted.

- **Phase 1 — The MoMo Wedge:** Solve unstructured Mobile Money statement parsing and scoring, the segment no one else is serving well.
- **Phase 2 — The Multi-Channel Ledger:** Once embedded in a lender's loan-origination workflow, expand to ingest traditional bank statements, POS terminal feeds (e.g., Hubtel), and payment gateway APIs (e.g., Paystack, Flutterwave).
- **Phase 3 — Predictive Intelligence:** Move from historical reporting to predictive analytics — flagging cash-flow crunches *before* a merchant defaults.

### Core Value Proposition

With explicit, OTP-verified merchant consent, CredScore converts raw, unstructured MoMo logs into a clean financial ledger detailing:

- Verified business revenue (separated from personal transfers)
- Revenue consistency and volatility
- Estimated operating expenses (COGS)
- Average daily wallet balance
- A risk-adjusted suggested credit limit

---

## 4. Product Ecosystem: Web App + API + WhatsApp

CredScore ships as three tightly integrated surfaces. No native mobile app is required for either the merchant or the lender.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           CREDSCORE ECOSYSTEM                            │
├──────────────────────────┬────────────────────────┬──────────────────────┤
│   1. MERCHANT INTAKE     │   2. INTELLIGENCE API  │  3. LENDER DASHBOARD │
│  (WhatsApp Bot / Web)    │     (Python Core)      │   (Web Application)  │
│  - USSD instructions     │  - PDF/CSV parser      │  - Underwriter portal│
│  - Statement ingestion   │  - Pattern-match engine│  - PDF report export │
│  - OTP consent capture   │  - Risk scoring model  │  - Webhook triggers  │
└──────────────────────────┴────────────────────────┴──────────────────────┘
```

### 4.1 Merchant Consent & Ingestion Flow (WhatsApp Bot + Web Link)

- **Trigger:** A merchant applies for a loan at a partnered MFI or fintech lender and receives a secure CredScore web link or an automated WhatsApp message.
- **Flow:** The WhatsApp bot (or web page) walks the merchant through requesting their official 3–6 month electronic MoMo statement directly from their telco via USSD (e.g., `*170#` for MTN Ghana), then either:
  - forwarding it to a dedicated ingestion address (`statements@credscore.com`), or
  - uploading the PDF/CSV directly through the WhatsApp bot or web form.
- **Consent:** Every ingestion event is gated by a timestamped OTP or signed consent checkbox, creating a verifiable chain of custody.

### 4.2 Core Intelligence Engine (API Layer)

- Receives the raw PDF/CSV statement.
- Cleans and normalizes messy transaction text.
- Runs pattern-matching heuristics to separate genuine business revenue from personal transfers and internal sweeps.
- Outputs a structured JSON payload — delivered to the lender's system within seconds via REST API or webhook.

### 4.3 B2B Lender Dashboard (Web Application)

- Used by credit officers and underwriters at MFIs, banks, and fintech lenders.
- A loan officer uploads (or receives, via webhook) an applicant's parsed MoMo report and instantly sees:
  - Cash-flow graphs
  - A financial health tag (Strong / Moderate / High Risk)
  - Debt-service coverage ratio
  - A downloadable, lender-branded credit memo (PDF)

---

## 5. Data Ingestion Strategy: Bypassing the Telco Monopoly

Telcos guard MoMo API access closely to protect their own proprietary credit products (e.g., MTN Qwikloan). CredScore bypasses this monopoly through a phased, fully legal data-acquisition pipeline built on the user's data portability rights.

| Phase | Channel | Mechanism | Status |
|---|---|---|---|
| **Phase 1 (MVP)** | USSD / Email & WhatsApp Upload | Merchant requests their statement via telco USSD, then forwards or uploads it to CredScore | 100% legal today — no telco API access required |
| **Phase 2** | Payment Gateway Integration | OAuth connections to merchant aggregator accounts (Hubtel, Paystack, Flutterwave) | High feasibility — captures formal digital payment flows |
| **Phase 3** | Direct Telco Integration | Enterprise Data Sharing Agreements (DSAs) negotiated once volume and trust are established | Long-term, once traction is proven |

---

## 6. Pattern Recognition & Scoring Model

The core IP of CredScore is distinguishing **true business revenue** from personal P2P transfers and internal wallet sweeps.

Raw MoMo logs contain unformatted strings, e.g. `"Transfer received from KWAME MENSAH Reference: lunch"`. The normalization pipeline runs three stages:

1. **Text Tokenization & Category Matching** — maps counterparty names, till numbers, and reference fields against a dictionary of known commercial entities and merchant IDs.
2. **Velocity & Frequency Heuristics** —
   - *Personal signal:* a single large transfer on a fixed monthly date (salary/remittance pattern).
   - *Business signal:* many smaller, similarly-sized inflows clustered during standard business hours (8 AM–6 PM).
3. **Net Cash-Flow & Liquidity Calculation** — tracks the running daily balance to distinguish merchants who retain working capital from those who immediately cash out (a liquidity red flag).

### Key Underwriting Metrics

| Indicator | What It Measures | Underwriting Signal |
|---|---|---|
| Net Verified Revenue | Inflows minus sweeps, refunds, personal transfers | Baseline debt-service capacity |
| Cash-Flow Consistency | Day-to-day fluctuation of inflows | Business stability |
| Average Daily Balance (ADB) | Lowest 30-day rolling wallet balance | Operational liquidity cushion |
| Expense Ratio (Est. COGS) | Frequency/volume of outbound supplier transfers | Profit margin estimate |
| Counterparty Concentration | Share of revenue from top 3 payers | Client/buyer dependency risk |

**Revenue Consistency Score** (conceptual formula):

```
Revenue Consistency Score = f( Monthly Active Days, σ(daily revenue) / μ(daily revenue), Counterparty Diversity )
```

---

## 7. Technical Architecture & Stack

```
                          ┌─────────────────────────┐
                          │   Merchant Inputs /     │
                          │  WhatsApp / Web Upload  │
                          └────────────┬────────────┘
                                       │
                                       ▼
 ┌───────────────────────────────────────────────────────────────────────────┐
 │                            FASTAPI CORE ENGINE                            │
 │                                                                           │
 │   ┌───────────────────────┐   ┌───────────────────────┐   ┌───────────┐   │
 │   │  PDF Parsing Layer    │   │  Normalization Engine │   │ Scoring   │   │
 │   │ (pdfplumber / PyPDF)  │ ➔ │  (Pandas / NumPy)     │ ➔ │ Model     │   │
 │   └───────────────────────┘   └───────────────────────┘   └─────┬─────┘   │
 └─────────────────────────────────────────────────────────────────┼─────────┘
                                                                   │
                                       ┌───────────────────────────┴───────────┐
                                       ▼                                       ▼
                          ┌─────────────────────────┐             ┌─────────────────────────┐
                          │    REST API / JSON      │             │  PostgreSQL Database    │
                          │  (Lender Systems)        │             │ (Anonymized Data Lake)  │
                          └─────────────────────────┘             └─────────────────────────┘
```

| Layer | Component | Technology | Why |
|---|---|---|---|
| Core Engine | API & processing | **Python (FastAPI)** | Async performance, native fit for data-science tooling |
| Data Parsing | Statement extraction | **pdfplumber / PyPDF2 / Tesseract OCR** | High-accuracy table extraction, OCR fallback for scanned statements |
| Data Cleaning | Analytics & heuristics | **Pandas / NumPy** | Fast tabular manipulation and time-series aggregation |
| Database | Storage | **PostgreSQL** | Relational integrity + JSONB for flexible statement storage |
| Merchant Channel | Intake | **WhatsApp Business API (Twilio / Meta Cloud API)** | Zero-download, ubiquitous merchant channel |
| Lender Dashboard | Frontend | **React.js + Tailwind CSS** | Clean, responsive enterprise financial UI |
| Infrastructure | Hosting | **AWS (ECS/Lambda + RDS) or GCP** | Serverless-friendly, handles async PDF-parsing spikes |
| Auth & API Keys | Security | **OAuth2 / API key management** | Enterprise-grade lender integrations |

---

## 8. Suggested Project Structure

```
credscore/
├── apps/
│   ├── api/                     # FastAPI core service
│   │   ├── main.py
│   │   ├── routers/
│   │   │   ├── ingestion.py     # statement upload / email intake endpoints
│   │   │   ├── scoring.py       # scoring + report generation endpoints
│   │   │   └── webhooks.py      # lender-facing webhook dispatch
│   │   ├── parsing/
│   │   │   ├── pdf_extractor.py
│   │   │   └── ocr_fallback.py
│   │   ├── engine/
│   │   │   ├── normalizer.py    # text tokenization / counterparty matching
│   │   │   ├── heuristics.py    # velocity & frequency rules
│   │   │   └── scoring_model.py
│   │   ├── models/               # SQLAlchemy / Pydantic schemas
│   │   └── tests/
│   │
│   ├── dashboard/                # React + Tailwind lender web app
│   │   ├── src/
│   │   │   ├── components/
│   │   │   ├── pages/
│   │   │   └── services/api.ts
│   │   └── public/
│   │
│   └── whatsapp-bot/              # Merchant intake channel
│       ├── bot.py
│       ├── flows/
│       │   ├── ussd_instructions.py
│       │   ├── otp_consent.py
│       │   └── upload_handler.py
│       └── tests/
│
├── infra/
│   ├── docker-compose.yml
│   ├── terraform/                 # AWS/GCP infrastructure as code
│   └── ci-cd/
│
├── docs/
│   ├── api-reference.md
│   ├── data-privacy-policy.md
│   └── architecture.md
│
└── README.md
```

---

## 9. Business Model & Unit Economics

CredScore runs a hybrid B2B model aligned with lender loan-origination volume:

1. **API Pay-Per-Query:** Lenders pay a micro-fee (≈ GH¢5.00–GH¢15.00) per statement parsed and scored via the API.
2. **SaaS Platform Subscription:** Tiered monthly fees for institutions using the web dashboard for manual, human-in-the-loop underwriting.
3. **Origination Revenue Share (future):** A small percentage fee on loans successfully originated using CredScore-verified data.

---

## 10. Regulatory Compliance & Market Tailwinds

Market timing is strong due to recent regulatory shifts in West Africa:

- **Bank of Ghana (BoG) Digital Credit Directive:** Mandates rigorous consumer protection, prohibits aggressive collection practices, and requires lenders to prove a borrower's actual repayment capacity before issuing a loan. CredScore supplies exactly the verified cash-flow data lenders need to demonstrate compliance.
- **Data Protection Commission (DPC) Compliance:** Because CredScore only ingests statements the merchant initiates via USSD/OTP consent, it operates fully within DPC guidelines on user consent.
- **PII Anonymization:** Personally identifiable information is decoupled from raw transaction records used in model training/improvement.

---

## 11. Execution Roadmap

### Phase 0 — Hackathon MVP (48 Hours)

**Day 1 — The Engine (Backend)**
- Build the FastAPI backend skeleton.
- Build a `pdfplumber`-based script that ingests a sample 3-month MTN MoMo PDF and converts it into a clean Pandas dataframe.
- Write a heuristic filter: isolate "Deposits/Transfers In," ignore transfers under GH¢10, and calculate an "Estimated Monthly Revenue."

**Day 2 — The Interface (Frontend + Bot)**
- Build the React.js lender dashboard with a file-upload component.
- Display the parsed JSON as visual metrics: daily revenue line chart, CredScore, and a suggested credit limit.
- Stub a WhatsApp intake flow (even a simple scripted demo) showing the merchant-side experience.

**The Pitch Hook:** Side-by-side comparison — a traditional lender's blank credit file on the left, versus the CredScore dashboard showing verified monthly MoMo revenue extracted from a previously "invisible" merchant on the right.

### Phase 1 — Months 1–3: Pilot Validation
- Harden the parsing engine against real-world statement formats (multiple telcos, PDF/CSV variance).
- Secure 2–3 pilot partnerships with digital MFIs in Ghana.
- Validate scoring outputs against historical default data from pilot partners.
- Formalize OTP-based consent and data-retention policy with legal review.

### Phase 2 — Months 4–6: Channel Expansion
- Launch the production WhatsApp Business API bot for merchant statement submission.
- Publish developer API documentation for automated loan-origination integrations.
- Add webhook support so lender systems receive scores in real time.

### Phase 3 — Months 7–12: Multi-Channel Data Utility
- Integrate payment gateway/POS feeds (Hubtel, Paystack, Flutterwave) via OAuth.
- Expand ingestion to support formal bank statements.
- Begin conversations toward direct telco Data Sharing Agreements.
- Explore predictive analytics (early cash-flow-crunch alerts) as a premium tier.

---

## 12. Key Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Telco pushback on statement-forwarding workaround | Operate strictly within user data-portability rights; pursue formal DSAs as volume grows |
| PDF/CSV format variance across telcos | Build a modular parser with per-telco templates + OCR fallback |
| Lender trust in a new scoring methodology | Validate against historical default data during pilots; offer transparent, explainable scoring breakdowns |
| Data privacy concerns | OTP/consent-gated ingestion, PII anonymization, DPC-aligned policies |
| Merchant adoption friction | Zero-app-download design via WhatsApp and web link only |
