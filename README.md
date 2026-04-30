# Port Talbot · Decision Framework

> An enterprise decision intelligence tool for the Tata Steel UK EAF Transformation programme. Built for leadership teams who need to make high-stakes decisions under time pressure, uncertainty, and competing stakeholder priorities.

---

## What this is

The Port Talbot Decision Framework is a browser-based decision support system for the £1.25 billion EAF (Electric Arc Furnace) transformation at Tata Steel UK's Port Talbot site. It models how five senior leaders think about five live programme decisions — computing recommendations, scoring options, and surfacing conflicts between personas.

**It is not a presentation deck.** Every score, recommendation, and conflict insight is computed live from a mathematical engine every time you open it. Change a KPI value and the entire matrix updates. Switch scenarios and all 80 cells recompute.

---

## Quick start (2 minutes)

**Option A — No server needed (matrix only, no AI chat)**

1. Download `port_talbot_decision_framework.html`
2. Open it in Chrome or Edge
3. The matrix, engine, charts, and conflict view all work immediately

**Option B — With AI chat (Groq, free)**

1. Download `port_talbot_decision_framework.html` and `launch.py` into the same folder
2. Run:
   ```bash
   python3 launch.py     # Mac / Linux
   python launch.py      # Windows
   ```
3. Your browser opens at `http://localhost:8080/port_talbot_decision_framework.html`
4. Get a free Groq API key at [console.groq.com](https://console.groq.com) — no credit card
5. Enter the key in the banner that appears — it saves in your browser

**Option C — Full backend server**

See [Backend Setup](#backend-setup) below.

---

## The scenario

**October 2026.** The Port Talbot EAF is under construction. Tenova (the primary EAF contractor) has submitted Variation Order VO-112: a £31.4 million claim plus an 11-week programme extension.

- **£16.5M agreed** — Factor 3: fume treatment plant redesign (legitimate scope change)
- **£14.9M disputed** — Factor 1: steel price inflation (£8.7M) + Factor 2: labour scarcity (£6.2M)
- **21-day window** — pay or withhold; Tenova has a contractual suspension right

Five senior leaders each have different perspectives on what to do. The system models their decision-making across four emotional states and surfaces where they agree, where they conflict, and why.

The system also includes four additional programme scenarios:

| Scenario | Decision |
|---|---|
| National Grid Delay | Grid can't energise EAF until Q1 2028 — accept / litigate / accelerate |
| BMW AHSS Commitment | BMW needs grade commitment now; LMF validation not ready until 2028 |
| IJmuiden Transfer Price | £79M slab import overshoot — renegotiate / early grant draw / cut volume |
| EAF Staffing Crisis | 47% of 400 EAF operators trained with 20 months to commissioning |

---

## The five personas

| ID | Name | Role | Primary concern |
|---|---|---|---|
| P1 | Rajesh Nair | CEO, Tata Steel UK | 2027 commissioning date, grant covenant, group accountability |
| P3 | Owen Griffiths | Project Director | Schedule, contractor cooperation, site safety |
| P4 | Sian Morgan | CFO | £500M grant covenant, capital discipline, transition cash flow |
| P2 | Chris Jaques | CHRO | EAF operator staffing, union relations, legal compliance |
| P10 | Priya Mehta | Commercial Director | BMW/JLR offtake, AHSS grade commitment, green steel premium |

Each persona has four business perspectives (their Y-axis responsibilities) and is evaluated across four emotional states (X-axis).

---

## The decision engine

The core of the system is a **Multi-Criteria Decision Analysis (MCDA) engine** that computes recommendations mathematically. No answers are hardcoded. Change a number, the recommendation changes.

### How it works

**Step 1 — Base weights (role DNA)**

Each persona has fixed base weights reflecting what their role fundamentally prioritises:

```
Dimensions: [Schedule, Financial, Political, Commercial]

P1 CEO:              [0.30, 0.20, 0.30, 0.20]  — equal schedule + political
P3 Project Director: [0.45, 0.20, 0.10, 0.25]  — schedule dominates
P4 CFO:              [0.15, 0.45, 0.25, 0.15]  — financial dominates
P2 CHRO:             [0.20, 0.15, 0.45, 0.20]  — political/people dominates
P10 Commercial Dir:  [0.15, 0.20, 0.15, 0.50]  — commercial dominates
```

**Step 2 — Emotion multipliers**

Each emotional state amplifies or dampens dimensions. Applied to base weights, then renormalised:

```
cautious:   [0.90, 1.40, 1.10, 0.70]  — financial + political up, commercial down
strategic:  [0.70, 0.80, 0.75, 2.10]  — commercial surges
analytical: [1.00, 1.15, 1.00, 1.05]  — stays near base, slight financial lean
decisive:   [1.90, 0.85, 0.65, 0.80]  — schedule surges
```

Example — Sian (CFO) in Cautious mode:
```
Base:       [0.15, 0.45, 0.25, 0.15]
× Cautious: [0.90, 1.40, 1.10, 0.70]
Raw:        [0.135, 0.630, 0.275, 0.105]
Normalised: [12%, 56%, 24%, 9%]
```

The same CFO in Decisive mode:
```
× Decisive: [1.90, 0.85, 0.65, 0.80]
Normalised: [29%, 39%, 17%, 12%]
```

Same person. Different emotional state. Dramatically different weights. Different recommendation.

**Step 3 — Option scoring**

Each scenario option has performance scores on the four dimensions (0–100):

```
VO-112 Option A (Pay full £31.4M):   [Schedule:85, Financial:40, Political:65, Commercial:55]
VO-112 Option B (Pay £16.5M only):   [Schedule:30, Financial:75, Political:35, Commercial:70]
VO-112 Option C (Negotiate £23-25M): [Schedule:80, Financial:60, Political:70, Commercial:60]
```

**Step 4 — Weighted score**

```
Score = Σ (option_score[dimension] × effective_weight[dimension])
```

Example — Sian CFO, Cautious mode, Option C:
```
(80 × 0.12) + (60 × 0.56) + (70 × 0.24) + (60 × 0.09) = 9.6 + 33.6 + 16.8 + 5.4 = 65.4
```

**Step 5 — Hard constraint elimination**

Before scoring, certain options are **eliminated entirely** if a KPI condition is met. These override the score.

Example: If Sian's grant milestones at risk (K1) is red (≥2), Option B is blocked regardless of its weighted score. The reason is logged and displayed.

```python
P4 capital_discipline:
  If K2 (contingency) < 50% → eliminate Option A
  Reason: "Contingency below 50% — full payment violates capital preservation mandate"
```

**Step 6 — Sensitivity analysis**

After ranking, the engine tests: *what weight change would flip the recommendation?*

```
Margin over second option: 8.3 pts
Flips if Financial weight drops –12%
```

This tells decision-makers how robust the recommendation is.

---

## The matrix

Each persona gets their own **4×4 matrix**:

```
                CAUTIOUS    STRATEGIC    ANALYTICAL    DECISIVE
                ────────────────────────────────────────────────
Programme Del  │  cell   │   cell    │   cell     │   cell   │
Political/Grant│  cell   │   cell    │   cell     │   cell   │
Group Acctbty  │  cell   │   cell    │   cell     │   cell   │
Community/Legacy│  cell  │   cell    │   cell     │   cell   │
```

Each cell shows:
- **Live KPI signals** — the 2–3 numbers that drive this specific perspective × emotion
- **Decision text** — what this person would actually do in this emotional state
- **Computed score** — derived by the MCDA engine, not written by hand
- **Risk tags** — severity-coded (HIGH/MED/LOW)
- **Constraint badge** — if a hard constraint is active

Click any cell to see the full detail: effective weight bars, ranked option scores, sensitivity analysis, constraint flags, visualisation charts.

---

## The conflict matrix

Switch to **Conflict view** to see all five personas side by side for the active scenario and emotional state.

```
              Pay full    Pay £16.5M    Negotiate
              ─────────────────────────────────────
Rajesh (CEO)     63          49 [B]       69 ↑
Owen (PD)        71          58           74 ↑
Sian (CFO)       55          61 [B]       66 ↑
Chris (CHRO)     68          70 ↑         72
Priya (Comm)     70 ↑        65           73
```

The system automatically surfaces:
- **Full consensus** — all five recommend the same option
- **Majority with dissent** — names who disagree and why
- **Split decision** — no consensus; suggests switching emotional state
- **Hard constraints active** — options blocked for specific personas
- **High spread options** — options where score varies 20+ points across personas (structural disagreement)

Click any cell to see the two most-disagreeing personas compared side by side with their view text and effective weights.

---

## AI Assistant

The AI Assistant tab uses **Groq + Llama 3.3 70B** (free) or **Claude Sonnet** (paid). It answers questions about the active persona's matrix.

**Format:** Every answer returns:
- `VERDICT` — one sentence, number-first
- `DATA` — 2–3 key figures with RAG status
- `RISKS` — severity-prefixed phrases
- `highlight` — JSON block telling the frontend which cells to illuminate

The AI does not make decisions — it reads the computed engine output and explains it in plain English. The highlight block maps its answer to specific matrix cells so you can see exactly what it's talking about.

**It's free.** Groq gives 14,400 requests per day on the free tier. That's one question every 6 seconds sustained — far more than any team needs.

---

## Live KPI feed

Connect a Google Sheet to update KPI values without touching the code:

**Sheet columns:** `persona_id | kpi_code | val | rag`

**Example rows:**
```
P4, K2, 64%, y        Sian's contingency dropped to 64%
P3, K4, 1/5, r        Tenova cooperation hit critical red
P1, K1, 68%, r        Schedule adherence below red threshold
```

**To connect:**
1. File → Share → Publish to web → CSV → Copy URL
2. In the HTML, find `const SHEETS_CSV_URL = ''` and paste the URL
3. Click ⟳ Live KPIs to refresh

When values change, the engine recomputes all 80 cells. If a KPI crosses a constraint threshold, options get blocked automatically.

---

## Project structure

```
port-talbot-decision-framework/
│
├── port_talbot_decision_framework.html   # Complete frontend — open this
├── launch.py                             # One-click local server launcher
├── .gitignore
│
├── backend/                              # Python backend (optional)
│   ├── server.py                         # Flask app — all API routes
│   ├── decision_engine.py                # MCDA engine (Python)
│   ├── scenarios.py                      # 5 scenario definitions
│   ├── personas.py                       # Persona + KPI data
│   ├── conflict_engine.py                # Cross-persona conflict matrix
│   ├── kpi_feed.py                       # Google Sheets CSV fetcher
│   ├── requirements.txt
│   └── .env.example                      # Copy to .env, add your keys
│
└── docs/
    ├── BACKEND_SPEC.md                   # Full backend implementation guide
    └── AI_MATRIX_SPEC.md                 # AI highlight system specification
```

---

## Backend setup

For team use, hosting, or live KPI integration:

```bash
cd backend/
python -m venv venv
source venv/bin/activate      # Mac/Linux
venv\Scripts\activate         # Windows

pip install -r requirements.txt

cp .env.example .env
# Edit .env — add GROQ_API_KEY (free) or ANTHROPIC_API_KEY

python server.py
# → http://localhost:5000
```

**API endpoints:**

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/` | Serve the frontend |
| `GET` | `/health` | Status check |
| `GET` | `/scenarios` | Scenario list for dropdown |
| `POST` | `/compute` | Run MCDA engine for one cell |
| `POST` | `/conflict` | Full cross-persona conflict matrix |
| `POST` | `/conflict/detail` | Two-persona comparison |
| `GET/POST` | `/kpis/refresh` | Fetch live KPIs from Google Sheets |
| `POST` | `/query` | AI assistant question |

---

## Adding a new scenario

1. Add an entry to `SCENARIOS` in `backend/scenarios.py` (or the JS `SCENARIOS` object in the HTML)
2. Define 3 options with performance scores `[Schedule, Financial, Political, Commercial]`
3. Define `kpi_overrides` for any persona whose KPIs change in this scenario
4. Add an `<option>` to the `#scenario-select` dropdown in the HTML
5. Add any new hard constraints to `decision_engine.py` if needed

**Option score calibration guide:**

| Range | Meaning |
|---|---|
| 80–100 | Excellent for this dimension — directly solves it |
| 60–79 | Positive — helps without being the primary driver |
| 40–59 | Neutral/mixed |
| 20–39 | Negative — creates problems here |
| 0–19 | Actively harmful to this dimension |

---

## Technology

**Frontend (zero dependencies beyond the file itself)**
- Vanilla JavaScript — no React, no Vue, no build step
- Chart.js (CDN) — data visualisation
- IBM Plex Mono + Syne + Inter (Google Fonts)

**AI (free tier)**
- Groq API — Llama 3.3 70B Versatile
- 14,400 free requests/day, no credit card required

**Backend (optional)**
- Python 3.10+ / Flask / Flask-CORS
- Groq Python SDK or Anthropic Python SDK

---

## The project context

Tata Steel UK committed £1.25 billion to convert Port Talbot from blast furnace steelmaking to Electric Arc Furnace technology — the largest green industrial investment in UK history. The transformation eliminates 90% of the site's CO₂ emissions on commissioning but requires the most complex programme management challenge in UK steel history:

- 2,500 redundancies completed March 2025
- £500M UK government grant with milestone-linked covenant conditions
- 5,000 jobs retained at Port Talbot
- 400 EAF operators to train from scratch
- National Grid infrastructure dependency
- Major automotive customers (JLR, BMW) requiring grade commitments before commissioning
- A live 14-month construction programme with a single primary contractor

This framework was built to model how the leadership team navigates those decisions — not as a corporate communication tool, but as a genuine decision support system that computes rather than asserts.

---

## Licence

MIT — use freely, adapt for your own programme, cite the source if you share it.

---

## Contributing

The most useful contributions are:
- Additional scenarios (new programme decisions as they arise)
- Refined option scores based on actual programme data
- Additional hard constraint rules
- Improved AI system prompt for better cell highlighting

Open a PR or raise an issue.
