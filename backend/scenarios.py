# scenarios.py
# Port Talbot Decision Framework — Scenario Library
# 5 live programme decisions, each with option scores and KPI overrides.

SCENARIOS = {
    "VO-112": {
        "id": "VO-112", "label": "VO-112 — Tenova Payment",
        "badge": "CONTRACT",
        "description": "Tenova variation order £31.4M claim + 11-week extension. 21-day payment window.",
        "date": "Oct 2026",
        "options": {
            "A": {"id":"A","label":"Pay full £31.4M under protest",   "short":"Pay full",    "scores":[85,40,65,55]},
            "B": {"id":"B","label":"Pay agreed £16.5M, dispute rest", "short":"Pay £16.5M",  "scores":[30,75,35,70]},
            "C": {"id":"C","label":"Negotiate £23–25M settlement",    "short":"Negotiate",   "scores":[80,60,70,60]},
        },
        "kpi_overrides": {},
    },
    "GRID-DELAY": {
        "id": "GRID-DELAY", "label": "National Grid — 14-week Delay",
        "badge": "INFRASTRUCTURE",
        "description": "National Grid cannot energise the EAF substation until Q1 2028. 14-week programme slip.",
        "date": "Oct 2026",
        "options": {
            "A": {"id":"A","label":"Accept delay, revise programme formally",        "short":"Accept & revise","scores":[40,65,70,55]},
            "B": {"id":"B","label":"Legal action against National Grid for damages", "short":"Legal action",   "scores":[30,70,30,65]},
            "C": {"id":"C","label":"Accelerate parallel works to recover 8 weeks",  "short":"Accelerate",     "scores":[75,40,50,60]},
        },
        "kpi_overrides": {
            "P1": {"K1": {"val":"59%","rag":"r"}},
            "P3": {"K1": {"val":"14 wks behind","rag":"r"}, "K6": {"val":"0 wks","rag":"r"}},
            "P4": {"K1": {"val":"2","rag":"r"}, "K2": {"val":"61%","rag":"y"}},
        },
    },
    "BMW-AHSS": {
        "id": "BMW-AHSS", "label": "BMW AHSS Grade Commitment",
        "badge": "COMMERCIAL",
        "description": "BMW requires DP1000/DP1200 AHSS grade commitment by Q3 2026. LMF validation Q2 2028. £48M/yr at stake.",
        "date": "Sep 2026",
        "options": {
            "A": {"id":"A","label":"Commit to BMW on DP1000 now, accelerate validation","short":"Commit now",      "scores":[70,55,60,85]},
            "B": {"id":"B","label":"Decline, offer IJmuiden as interim supply",          "short":"IJmuiden interim","scores":[50,65,55,55]},
            "C": {"id":"C","label":"Propose BMW co-development partnership",             "short":"Co-develop",     "scores":[65,60,65,80]},
        },
        "kpi_overrides": {
            "P10": {"K3":{"val":"£48M","rag":"r"},"K8":{"val":"1","rag":"y"},"K1":{"val":"61%","rag":"y"}},
            "P1":  {"K7": {"val":"61%","rag":"y"}},
        },
    },
    "IJMUIDEN-PRICE": {
        "id": "IJMUIDEN-PRICE", "label": "IJmuiden Transfer Price Renegotiation",
        "badge": "FINANCIAL",
        "description": "IJmuiden slab transfer price running £38/tonne above plan. £79M projected overshoot.",
        "date": "Nov 2026",
        "options": {
            "A": {"id":"A","label":"Renegotiate IJmuiden price to arm's-length market rate","short":"Renegotiate",  "scores":[55,85,40,65]},
            "B": {"id":"B","label":"Activate £50M early grant draw from DBET",             "short":"Early draw",   "scores":[50,80,55,50]},
            "C": {"id":"C","label":"Reduce downstream mill volumes to cut slab imports",    "short":"Reduce volume","scores":[40,70,45,40]},
        },
        "kpi_overrides": {
            "P4":  {"K2":{"val":"61%","rag":"y"},"K7":{"val":"£97M","rag":"r"},"K8":{"val":"£79M","rag":"r"}},
            "P10": {"K1": {"val":"55%","rag":"y"}},
        },
    },
    "EAF-STAFFING": {
        "id": "EAF-STAFFING", "label": "EAF Operator Staffing Crisis",
        "badge": "WORKFORCE",
        "description": "47% of 400 EAF operators trained. European specialist pool constrained. 20 months to commissioning.",
        "date": "Oct 2026",
        "options": {
            "A": {"id":"A","label":"Approve £52K premium grade + external market hire",    "short":"Premium hire",    "scores":[75,50,55,65]},
            "B": {"id":"B","label":"Mandate 20 IJmuiden secondments via group escalation", "short":"IJmuiden mandate","scores":[70,65,65,70]},
            "C": {"id":"C","label":"Revise commissioning headcount target to 300 minimum", "short":"Revise target",   "scores":[50,70,60,55]},
        },
        "kpi_overrides": {
            "P2": {"K1":{"val":"47%","rag":"r"},"K2":{"val":"74%","rag":"y"},"K4":{"val":"3/5","rag":"y"}},
            "P1": {"K4": {"val":"47%","rag":"r"}},
        },
    },
}


def get_scenario(scenario_id: str) -> dict:
    sc = SCENARIOS.get(scenario_id)
    if not sc:
        raise ValueError(f"Unknown scenario: {scenario_id}. Valid: {list(SCENARIOS.keys())}")
    return sc


def get_all_scenarios() -> list[dict]:
    return [{"id":s["id"],"label":s["label"],"badge":s["badge"],
             "description":s["description"],"date":s["date"]}
            for s in SCENARIOS.values()]


def get_kpis_for_persona(persona_id: str, scenario_id: str, base_kpis: list[dict]) -> list[dict]:
    sc = get_scenario(scenario_id)
    overrides = sc.get("kpi_overrides", {}).get(persona_id, {})
    return [{**k, **overrides[k["code"]]} if k["code"] in overrides else k
            for k in base_kpis]
