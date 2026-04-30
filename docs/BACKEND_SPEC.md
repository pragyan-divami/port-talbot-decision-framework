# Port Talbot Decision Framework — Backend Specification v2
## Full implementation guide including Scenario Library, Live KPI Feed, and Cross-Persona Conflict Matrix

**Version:** 2.0  
**Supersedes:** PORT_TALBOT_BACKEND_SPEC.md (v1.0)  
**Frontend:** `port_talbot_decision_framework.html` — 174 KB, self-contained  
**New in v2:** Multi-scenario library · Live KPI feed (Google Sheets) · Cross-persona conflict matrix

---

## 1. What changed from v1

| Component | v1 | v2 |
|---|---|---|
| Scenarios | 1 hardcoded (VO-112) | 5 switchable scenarios |
| Option scores | Static in `OPTIONS` constant | Dynamic per scenario via `getActiveOptions()` |
| KPI values | Static in `PERSONAS` data | Live-overridable per scenario + Google Sheets feed |
| Views | Matrix only | Matrix + Conflict toggle |
| Conflict analysis | None | Full cross-persona scoring grid with insights |
| Backend routes | `/health` `/compute` `/query` | + `/scenarios` `/conflict` `/kpis/refresh` |

Everything in v1 still applies. This document extends it.

---

## 2. Updated architecture

```
Browser (HTML file)
       │
       ├── POST /compute           (MCDA engine — any scenario)
       ├── POST /conflict          (cross-persona scoring table)
       ├── POST /query             (AI assistant)
       ├── GET  /scenarios         (scenario library)
       ├── GET  /kpis/refresh      (fetch live KPIs from Google Sheets)
       └── GET  /health
              │
              ▼
Python Flask server  (localhost:5000)
       │
       ├── decision_engine.py      (MCDA + weights + constraints)
       ├── scenarios.py            (5 scenario definitions)       ← NEW
       ├── personas.py             (persona + KPI data)
       ├── conflict_engine.py      (cross-persona scoring)        ← NEW
       ├── kpi_feed.py             (Google Sheets CSV fetcher)    ← NEW
       └── anthropic_client.py
```

---

## 3. Scenario library — `scenarios.py`

### 3.1 Data structure

Every scenario defines three things:

1. **options** — the decision choices available, each with performance scores on the 4 dimensions
2. **kpi_overrides** — which KPI values change from baseline for this scenario (e.g. Grid Delay makes Owen's schedule 14 weeks behind instead of 5)
3. **metadata** — id, label, badge, description, date

```python
# scenarios.py

SCENARIOS = {

    "VO-112": {
        "id":          "VO-112",
        "label":       "VO-112 — Tenova Payment",
        "badge":       "CONTRACT",
        "description": "Tenova variation order £31.4M claim + 11-week extension. 21-day payment window.",
        "date":        "Oct 2026",
        "options": {
            "A": {"id":"A", "label":"Pay full £31.4M under protest",   "short":"Pay full",    "scores":[85,40,65,55]},
            "B": {"id":"B", "label":"Pay agreed £16.5M, dispute rest", "short":"Pay £16.5M",  "scores":[30,75,35,70]},
            "C": {"id":"C", "label":"Negotiate £23–25M settlement",    "short":"Negotiate",   "scores":[80,60,70,60]},
        },
        "kpi_overrides": {},
    },

    "GRID-DELAY": {
        "id":          "GRID-DELAY",
        "label":       "National Grid — 14-week Delay",
        "badge":       "INFRASTRUCTURE",
        "description": "National Grid cannot energise the EAF substation until Q1 2028. 14-week programme slip.",
        "date":        "Oct 2026",
        "options": {
            "A": {"id":"A", "label":"Accept delay, revise programme formally",        "short":"Accept & revise", "scores":[40,65,70,55]},
            "B": {"id":"B", "label":"Legal action against National Grid for damages", "short":"Legal action",    "scores":[30,70,30,65]},
            "C": {"id":"C", "label":"Accelerate parallel works to recover 8 weeks",   "short":"Accelerate",      "scores":[75,40,50,60]},
        },
        "kpi_overrides": {
            "P1": {"K1": {"val":"59%",  "rag":"r"}},
            "P3": {"K1": {"val":"14 wks behind", "rag":"r"}, "K6": {"val":"0 wks", "rag":"r"}},
            "P4": {"K1": {"val":"2",    "rag":"r"}, "K2": {"val":"61%", "rag":"y"}},
        },
    },

    "BMW-AHSS": {
        "id":          "BMW-AHSS",
        "label":       "BMW AHSS Grade Commitment",
        "badge":       "COMMERCIAL",
        "description": "BMW requires DP1000/DP1200 AHSS grade commitment by Q3 2026. LMF validation Q2 2028. £48M/yr at stake.",
        "date":        "Sep 2026",
        "options": {
            "A": {"id":"A", "label":"Commit to BMW on DP1000 now, accelerate validation",  "short":"Commit now",       "scores":[70,55,60,85]},
            "B": {"id":"B", "label":"Decline commitment, offer IJmuiden as interim supply", "short":"IJmuiden interim",  "scores":[50,65,55,55]},
            "C": {"id":"C", "label":"Propose BMW co-development partnership",               "short":"Co-develop",        "scores":[65,60,65,80]},
        },
        "kpi_overrides": {
            "P10": {"K3": {"val":"£48M", "rag":"r"}, "K8": {"val":"1", "rag":"y"}, "K1": {"val":"61%", "rag":"y"}},
            "P1":  {"K7": {"val":"61%",  "rag":"y"}},
        },
    },

    "IJMUIDEN-PRICE": {
        "id":          "IJMUIDEN-PRICE",
        "label":       "IJmuiden Transfer Price Renegotiation",
        "badge":       "FINANCIAL",
        "description": "IJmuiden slab transfer price running £38/tonne above plan. £79M projected overshoot. Group CFO review pending.",
        "date":        "Nov 2026",
        "options": {
            "A": {"id":"A", "label":"Renegotiate IJmuiden price to arm's-length market rate", "short":"Renegotiate",   "scores":[55,85,40,65]},
            "B": {"id":"B", "label":"Activate £50M early grant draw from DBET",              "short":"Early draw",    "scores":[50,80,55,50]},
            "C": {"id":"C", "label":"Reduce downstream mill volumes to cut slab imports",     "short":"Reduce volume", "scores":[40,70,45,40]},
        },
        "kpi_overrides": {
            "P4": {"K2": {"val":"61%",  "rag":"y"}, "K7": {"val":"£97M", "rag":"r"}, "K8": {"val":"£79M", "rag":"r"}},
            "P10":{"K1": {"val":"55%",  "rag":"y"}},
        },
    },

    "EAF-STAFFING": {
        "id":          "EAF-STAFFING",
        "label":       "EAF Operator Staffing Crisis",
        "badge":       "WORKFORCE",
        "description": "47% of 400 EAF operators trained. European specialist pool constrained by VO-112 Factor 2. 20 months to commissioning.",
        "date":        "Oct 2026",
        "options": {
            "A": {"id":"A", "label":"Approve £52K premium grade + external market hire",    "short":"Premium hire",     "scores":[75,50,55,65]},
            "B": {"id":"B", "label":"Mandate 20 IJmuiden secondments via group escalation", "short":"IJmuiden mandate",  "scores":[70,65,65,70]},
            "C": {"id":"C", "label":"Revise commissioning headcount target to 300 minimum", "short":"Revise target",     "scores":[50,70,60,55]},
        },
        "kpi_overrides": {
            "P2": {"K1": {"val":"47%", "rag":"r"}, "K2": {"val":"74%", "rag":"y"}, "K4": {"val":"3/5", "rag":"y"}},
            "P1": {"K4": {"val":"47%", "rag":"r"}},
        },
    },
}


def get_scenario(scenario_id: str) -> dict:
    sc = SCENARIOS.get(scenario_id)
    if not sc:
        raise ValueError(f"Unknown scenario: {scenario_id}. Valid: {list(SCENARIOS.keys())}")
    return sc


def get_all_scenarios() -> list[dict]:
    """Return metadata for all scenarios (no options/overrides — for the selector dropdown)."""
    return [
        {"id": sc["id"], "label": sc["label"], "badge": sc["badge"],
         "description": sc["description"], "date": sc["date"]}
        for sc in SCENARIOS.values()
    ]


def get_kpis_for_persona(persona_id: str, scenario_id: str, base_kpis: list[dict]) -> list[dict]:
    """
    Apply scenario KPI overrides to the persona's base KPI values.

    Example: In GRID-DELAY, P3's K1 changes from '5 behind' to '14 wks behind'.
    If no override exists for a KPI, the base value is returned unchanged.
    """
    sc = get_scenario(scenario_id)
    overrides = sc.get("kpi_overrides", {}).get(persona_id, {})
    result = []
    for kpi in base_kpis:
        ov = overrides.get(kpi["code"])
        result.append({**kpi, **ov} if ov else kpi)
    return result
```

### 3.2 Option score design rules

Option scores are on a 0–100 scale per dimension `[Schedule, Financial, Political, Commercial]`.  
Use these benchmarks when adding new scenarios:

| Score range | Meaning |
|---|---|
| 80–100 | This option is excellent for this dimension — it directly solves or strongly advances it |
| 60–79 | This option is positive for this dimension — it helps without being the primary driver |
| 40–59 | This option is neutral/mixed — it neither helps nor harms this dimension significantly |
| 20–39 | This option is negative for this dimension — it creates problems or costs here |
| 0–19 | This option is actively harmful to this dimension — it makes things significantly worse |

**Calibration example — VO-112 Option B (Pay agreed £16.5M only):**
- Schedule: 30 — withholding the disputed amount risks contractor suspension (6–8 week delay). Very bad for schedule.
- Financial: 75 — preserves £14.9M in contingency. Good for financial position.
- Political: 35 — confrontational signal to Tenova and government. Bad for political.
- Commercial: 70 — preserves legal dispute position and precedent. Good for commercial.

---

## 4. Updated decision engine — dynamic scenario support

The core `compute_decision` function (specified in v1) requires one change: instead of reading from a global `OPTIONS` constant, it accepts the scenario's options as a parameter.

```python
def compute_decision(
    persona_id: str,
    perspective_id: str,
    emotion: str,
    kpis: list[dict],
    scenario_id: str = "VO-112",          # ← NEW parameter
) -> dict:
    """
    All logic identical to v1 except OPTIONS are loaded from the scenario.
    """
    from scenarios import get_scenario, get_kpis_for_persona
    from personas import get_persona_kpis

    # Apply scenario KPI overrides
    base_kpis = kpis if kpis else get_persona_kpis(persona_id)
    live_kpis = get_kpis_for_persona(persona_id, scenario_id, base_kpis)
    parsed_kpis = parse_kpis(live_kpis)

    # Load scenario options (replaces static OPTIONS constant from v1)
    sc = get_scenario(scenario_id)
    options = sc["options"]

    weights = compute_weights(persona_id, emotion)

    # Hard constraint check (unchanged from v1)
    constraints = HARD_CONSTRAINTS.get(persona_id, {}).get(perspective_id, [])
    eliminated = set()
    constraints_fired = []
    for c in constraints:
        if c["condition"](parsed_kpis):
            eliminated.add(c["option"])
            constraints_fired.append({"option": c["option"], "reason": c["reason"]})

    # Score all options
    scored = []
    for opt_id, opt in options.items():
        raw = score_option(opt["scores"], weights)
        scored.append({
            "id": opt_id,
            "label": opt["label"],
            "short": opt["short"],
            "raw_score": raw,
            "score": round(raw),
            "eliminated": opt_id in eliminated,
            "elimination_reason": next(
                (cf["reason"] for cf in constraints_fired if cf["option"] == opt_id), None
            ),
        })

    scored.sort(key=lambda o: o["raw_score"], reverse=True)
    for i, o in enumerate(scored):
        o["rank"] = i + 1

    active = [o for o in scored if not o["eliminated"]]
    recommendation = active[0] if active else scored[0]

    # Sensitivity analysis (unchanged from v1)
    sensitivity = None
    if len(active) >= 2:
        second = active[1]
        margin = recommendation["raw_score"] - second["raw_score"]
        sensitivity = compute_sensitivity(recommendation["id"], second["id"], weights, margin, options)

    return {
        "weights": [round(w * 100) for w in weights],
        "options": scored,
        "recommendation": recommendation,
        "sensitivity": sensitivity,
        "constraints_fired": constraints_fired,
        "emotion": emotion,
        "persona_id": persona_id,
        "perspective_id": perspective_id,
        "scenario_id": scenario_id,
    }
```

The `compute_sensitivity` function also needs the options dict passed in (since option score lookups must use the active scenario):

```python
def compute_sensitivity(
    recommendation_id: str,
    second_id: str,
    weights: list[float],
    margin: float,
    options: dict,            # ← pass scenario options, not global constant
) -> dict | None:
    rec_scores = options[recommendation_id]["scores"]
    sec_scores = options[second_id]["scores"]
    # ... rest identical to v1
```

---

## 5. Conflict engine — `conflict_engine.py`

This is the backend implementation of the cross-persona conflict matrix. It runs `compute_decision` for every persona × option combination in a given scenario and emotion state, then derives consensus, dissent, and score spread insights.

```python
# conflict_engine.py

from decision_engine import compute_decision, compute_weights
from scenarios import get_scenario, get_kpis_for_persona
from personas import get_persona_kpis, get_persona_context, PERSONA_IDS

PERSONA_IDS = ["P1", "P3", "P4", "P2", "P10"]


def compute_conflict_matrix(scenario_id: str, emotion: str) -> dict:
    """
    Compute the full cross-persona conflict matrix for a scenario + emotion.

    For each persona, uses their first (primary) perspective to represent
    their overall stance on the scenario. This matches the frontend behaviour.

    Returns:
        {
            "scenario_id":    str,
            "emotion":        str,
            "options":        [OptionMeta, ...],
            "rows":           [PersonaRow, ...],
            "insights":       InsightBlock,
        }

    PersonaRow shape:
        {
            "persona_id":    str,
            "name":          str,
            "role":          str,
            "color":         str,
            "recommendation": str,         # winning option id
            "scores": {                    # option_id → score
                "A": int,
                "B": int,
                "C": int,
            },
            "blocked": {                   # option_id → bool
                "A": False,
                "B": True,
                "C": False,
            },
            "weights": [int, int, int, int],   # effective weights %
        }

    InsightBlock shape:
        {
            "consensus_type":   "full" | "majority" | "split",
            "winning_option":   str,
            "winning_count":    int,
            "consensus_names":  [str],
            "dissenter_names":  [str],
            "blocked_entries":  [{"persona": str, "option": str}],
            "high_spread_opts": [{"option": str, "spread": int}],
        }
    """
    sc = get_scenario(scenario_id)
    opts = sc["options"]

    rows = []
    scores_table = {}   # persona_id → option_id → score
    blocked_table = {}  # persona_id → option_id → bool

    for pid in PERSONA_IDS:
        ctx = get_persona_context(pid)
        base_kpis = get_persona_kpis(pid)
        live_kpis = get_kpis_for_persona(pid, scenario_id, base_kpis)
        persp_id = ctx["perspective_ids"][0]  # primary perspective

        try:
            result = compute_decision(pid, persp_id, emotion, live_kpis, scenario_id)
        except Exception as e:
            # Safe fallback — never crash the whole conflict matrix
            result = {
                "options": [{"id":o,"score":60,"eliminated":False} for o in opts],
                "recommendation": {"id": list(opts.keys())[0]},
                "weights": [25, 25, 25, 25],
            }

        scores_table[pid] = {}
        blocked_table[pid] = {}
        for opt_id in opts:
            found = next((o for o in result["options"] if o["id"] == opt_id), None)
            scores_table[pid][opt_id] = found["score"] if found else 0
            blocked_table[pid][opt_id] = found["eliminated"] if found else False

        # Find best non-blocked option
        recommendation = None
        best_score = -1
        for opt_id in opts:
            if not blocked_table[pid][opt_id] and scores_table[pid][opt_id] > best_score:
                best_score = scores_table[pid][opt_id]
                recommendation = opt_id

        rows.append({
            "persona_id":     pid,
            "name":           ctx["name"],
            "role":           ctx["role"],
            "recommendation": recommendation,
            "scores":         scores_table[pid],
            "blocked":        blocked_table[pid],
            "weights":        result["weights"],
        })

    # Derive insights
    insights = _derive_insights(rows, opts, scores_table, blocked_table, emotion)

    return {
        "scenario_id": scenario_id,
        "emotion":     emotion,
        "options":     [{"id": k, "label": v["label"], "short": v["short"]} for k, v in opts.items()],
        "rows":        rows,
        "insights":    insights,
    }


def _derive_insights(rows, opts, scores_table, blocked_table, emotion) -> dict:
    """Derive consensus, dissent, constraint, and spread insights."""

    # Vote count per option
    opt_votes = {opt_id: [] for opt_id in opts}
    for row in rows:
        if row["recommendation"]:
            opt_votes[row["recommendation"]].append(row["name"].split()[0])

    # Find winning option
    winning_opt = max(opt_votes, key=lambda o: len(opt_votes[o]))
    winning_count = len(opt_votes[winning_opt])
    total = len(rows)

    consensus_names = opt_votes[winning_opt]
    dissenter_names = [
        r["name"].split()[0] for r in rows
        if r["recommendation"] != winning_opt
    ]

    if winning_count == total:
        consensus_type = "full"
    elif winning_count >= (total // 2 + 1):
        consensus_type = "majority"
    else:
        consensus_type = "split"

    # Hard constraints active
    blocked_entries = []
    for row in rows:
        for opt_id, is_blocked in row["blocked"].items():
            if is_blocked:
                blocked_entries.append({
                    "persona": row["name"].split()[0],
                    "option":  opts[opt_id]["short"],
                })

    # Score spread per option (max - min across personas)
    high_spread_opts = []
    for opt_id, opt in opts.items():
        opt_scores = [scores_table[pid][opt_id] for pid in scores_table]
        spread = max(opt_scores) - min(opt_scores)
        if spread >= 20:
            high_spread_opts.append({"option": opt["short"], "spread": spread})

    return {
        "consensus_type":   consensus_type,
        "winning_option":   winning_opt,
        "winning_count":    winning_count,
        "consensus_names":  consensus_names,
        "dissenter_names":  dissenter_names,
        "blocked_entries":  blocked_entries,
        "high_spread_opts": high_spread_opts,
    }


def compute_persona_pair_detail(
    persona_id_a: str,
    persona_id_b: str,
    option_id: str,
    emotion: str,
    scenario_id: str,
) -> dict:
    """
    Compare two personas' view of a specific option in a given emotion + scenario.
    Used to populate the detail panel when a conflict cell is clicked.

    Returns:
        {
            "option":   {"id": str, "label": str, "short": str},
            "persona_a": {
                "id":      str,
                "name":    str,
                "score":   int,
                "weights": [int, int, int, int],
                "view":    str,   # first 300 chars of the cell view text
                "gap":     int,   # |score_a - score_b|
            },
            "persona_b": { ... same shape ... },
            "gap":        int,
            "driver":     str,   # which weight dimension explains the gap
        }
    """
    sc = get_scenario(scenario_id)
    opt = sc["options"].get(option_id)
    if not opt:
        raise ValueError(f"Unknown option {option_id} in scenario {scenario_id}")

    results = {}
    for pid in [persona_id_a, persona_id_b]:
        ctx = get_persona_context(pid)
        base_kpis = get_persona_kpis(pid)
        live_kpis = get_kpis_for_persona(pid, scenario_id, base_kpis)
        persp_id = ctx["perspective_ids"][0]
        try:
            r = compute_decision(pid, persp_id, emotion, live_kpis, scenario_id)
        except Exception:
            r = {"options": [{"id": option_id, "score": 60}], "weights": [25,25,25,25]}
        found = next((o for o in r["options"] if o["id"] == option_id), {"score": 60})
        results[pid] = {"result": r, "score": found["score"]}

    gap = abs(results[persona_id_a]["score"] - results[persona_id_b]["score"])

    # Find which weight dimension most explains the gap
    wa = results[persona_id_a]["result"]["weights"]
    wb = results[persona_id_b]["result"]["weights"]
    dim_labels = ["Schedule", "Financial", "Political", "Commercial"]
    weight_diffs = [abs(wa[i] - wb[i]) for i in range(4)]
    driver_dim = dim_labels[weight_diffs.index(max(weight_diffs))]

    def build_side(pid, score, result):
        ctx = get_persona_context(pid)
        from personas import PERSONA_CONTENT
        persp_id = ctx["perspective_ids"][0]
        # Get view text from personas data if available
        # Falls back to empty string — cell prose is in the frontend
        return {
            "id":      pid,
            "name":    ctx["name"],
            "role":    ctx["role"],
            "score":   score,
            "weights": result["result"]["weights"],
            "view":    "",  # populated from frontend cell data
        }

    return {
        "option":    {"id": option_id, "label": opt["label"], "short": opt["short"]},
        "persona_a": build_side(persona_id_a, results[persona_id_a]["score"], results[persona_id_a]),
        "persona_b": build_side(persona_id_b, results[persona_id_b]["score"], results[persona_id_b]),
        "gap":       gap,
        "driver":    driver_dim,
    }
```

---

## 6. Live KPI feed — `kpi_feed.py`

```python
# kpi_feed.py
# Fetches live KPI values from a published Google Sheets CSV.
# The CSV has four columns: persona_id, kpi_code, val, rag

import csv
import io
import urllib.request
from personas import PERSONA_KPIS  # base values

# Published CSV URL — set via environment variable or hardcode here
# To get this URL: File → Share → Publish to web → Select sheet → CSV → Publish
SHEETS_CSV_URL = ""  # set in .env as SHEETS_CSV_URL


def fetch_live_kpis(csv_url: str | None = None) -> dict:
    """
    Fetch and parse the Google Sheets CSV.

    Returns a nested dict of overrides:
        { "P4": { "K2": {"val": "64%", "rag": "y"} }, ... }

    Raises:
        ValueError  if the URL is not set
        RuntimeError if the fetch or parse fails
    """
    url = csv_url or SHEETS_CSV_URL
    if not url:
        raise ValueError(
            "No Google Sheets URL configured. "
            "Set SHEETS_CSV_URL in .env or pass csv_url parameter."
        )

    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            raw = resp.read().decode("utf-8")
    except Exception as e:
        raise RuntimeError(f"Failed to fetch KPI CSV from {url}: {e}")

    overrides = {}
    reader = csv.DictReader(io.StringIO(raw))

    required_cols = {"persona_id", "kpi_code", "val"}
    if not required_cols.issubset(set(reader.fieldnames or [])):
        raise ValueError(
            f"CSV missing required columns. Expected: {required_cols}. "
            f"Found: {reader.fieldnames}"
        )

    for row in reader:
        pid   = row.get("persona_id", "").strip()
        code  = row.get("kpi_code",   "").strip()
        val   = row.get("val",        "").strip()
        rag   = row.get("rag",        "").strip().lower()

        if not pid or not code or not val:
            continue
        if rag not in ("r", "y", "g", ""):
            rag = ""  # ignore invalid rag values, keep existing

        if pid not in overrides:
            overrides[pid] = {}
        overrides[pid][code] = {"val": val, **({"rag": rag} if rag else {})}

    return overrides


def apply_live_kpis(overrides: dict) -> dict:
    """
    Apply a set of KPI overrides to the in-memory PERSONA_KPIS.
    Returns a summary of what was updated.

    This mutates PERSONA_KPIS in place so all subsequent engine calls
    use the updated values without needing to pass them explicitly.

    Returns:
        {
            "updated":  [{"persona": str, "code": str, "old_val": str, "new_val": str}],
            "skipped":  [{"persona": str, "code": str, "reason": str}],
        }
    """
    updated = []
    skipped = []

    for pid, kpi_overrides in overrides.items():
        if pid not in PERSONA_KPIS:
            skipped.append({"persona": pid, "code": "*", "reason": "Unknown persona ID"})
            continue
        for code, new_vals in kpi_overrides.items():
            kpi = next((k for k in PERSONA_KPIS[pid] if k["code"] == code), None)
            if not kpi:
                skipped.append({"persona": pid, "code": code, "reason": "KPI code not found"})
                continue
            old_val = kpi["val"]
            kpi.update(new_vals)
            updated.append({
                "persona":  pid,
                "code":     code,
                "old_val":  old_val,
                "new_val":  kpi["val"],
            })

    return {"updated": updated, "skipped": skipped}


# ── GOOGLE SHEETS SETUP GUIDE ──────────────────────────────────────────────────
#
# Column headers (row 1): persona_id | kpi_code | val | rag
#
# Valid persona_id values: P1 P2 P3 P4 P10
# Valid kpi_code values:   K1 K2 K3 K4 K5 K6 K7 K8
# Valid rag values:        r (red) | y (yellow) | g (green)
#
# Example rows:
#   P4,K2,64%,y           → Sian's contingency dropped to 64%, still amber
#   P3,K4,1/5,r           → Owen's Tenova cooperation score hit critical red
#   P1,K1,68%,r           → Rajesh's schedule adherence below red threshold
#
# To publish:
#   1. Create the sheet with these four columns
#   2. File → Share → Publish to web
#   3. Select your sheet tab → CSV format → Publish
#   4. Copy the URL and set SHEETS_CSV_URL in .env
#
# The URL looks like:
#   https://docs.google.com/spreadsheets/d/XXXXXX/pub?gid=0&single=true&output=csv
```

---

## 7. Updated Flask server — `server.py`

Full server with all v2 routes:

```python
import os
import json
import anthropic
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from decision_engine import compute_decision
from conflict_engine import compute_conflict_matrix, compute_persona_pair_detail
from scenarios import get_scenario, get_all_scenarios, get_kpis_for_persona
from personas import get_persona_kpis, get_persona_context, PERSONA_IDS
from kpi_feed import fetch_live_kpis, apply_live_kpis

load_dotenv()

app = Flask(__name__, static_folder="frontend")
CORS(app)
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


# ── SERVE FRONTEND ─────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("frontend", "index.html")


# ── HEALTH ─────────────────────────────────────────────────────────────────────

@app.route("/health")
def health():
    return jsonify({"status": "ok", "version": "2.0", "scenarios": list(get_all_scenarios())})


# ── SCENARIO LIST ──────────────────────────────────────────────────────────────

@app.route("/scenarios")
def scenarios():
    """
    GET /scenarios
    Returns metadata for all 5 scenarios (no option scores — just for the dropdown).

    Response: [ {id, label, badge, description, date}, ... ]
    """
    return jsonify(get_all_scenarios())


# ── COMPUTE DECISION ───────────────────────────────────────────────────────────

@app.route("/compute", methods=["POST"])
def compute():
    """
    POST /compute
    Run the MCDA engine for a specific persona × perspective × emotion × scenario.

    Request:
        {
            "persona_id":     "P4",
            "perspective_id": "grant_covenant",
            "emotion":        "cautious",
            "scenario_id":    "VO-112",      ← NEW (defaults to "VO-112" if omitted)
            "kpis":           [...] | null   ← if null, server loads from personas.py
        }

    Response: full compute_decision output (see decision_engine.py)
    """
    data = request.get_json()
    try:
        scenario_id = data.get("scenario_id", "VO-112")
        kpis = data.get("kpis") or get_persona_kpis(data["persona_id"])
        # Apply scenario overrides to base KPIs
        live_kpis = get_kpis_for_persona(data["persona_id"], scenario_id, kpis)
        result = compute_decision(
            persona_id=data["persona_id"],
            perspective_id=data["perspective_id"],
            emotion=data["emotion"],
            kpis=live_kpis,
            scenario_id=scenario_id,
        )
        return jsonify(result)
    except (KeyError, ValueError) as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── CONFLICT MATRIX ────────────────────────────────────────────────────────────

@app.route("/conflict", methods=["POST"])
def conflict():
    """
    POST /conflict
    Compute the full cross-persona conflict matrix for a scenario + emotion.

    Request:
        {
            "scenario_id": "VO-112",
            "emotion":     "cautious"
        }

    Response: full compute_conflict_matrix output (see conflict_engine.py)
    """
    data = request.get_json()
    try:
        result = compute_conflict_matrix(
            scenario_id=data.get("scenario_id", "VO-112"),
            emotion=data.get("emotion", "cautious"),
        )
        return jsonify(result)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/conflict/detail", methods=["POST"])
def conflict_detail():
    """
    POST /conflict/detail
    Get the side-by-side comparison of two personas on a specific option.
    Called when a conflict grid cell is clicked.

    Request:
        {
            "persona_a":   "P1",
            "persona_b":   "P4",
            "option_id":   "A",
            "emotion":     "cautious",
            "scenario_id": "VO-112"
        }

    Response: compute_persona_pair_detail output (see conflict_engine.py)
    """
    data = request.get_json()
    try:
        result = compute_persona_pair_detail(
            persona_id_a=data["persona_a"],
            persona_id_b=data["persona_b"],
            option_id=data["option_id"],
            emotion=data.get("emotion", "cautious"),
            scenario_id=data.get("scenario_id", "VO-112"),
        )
        return jsonify(result)
    except (KeyError, ValueError) as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── LIVE KPI FEED ──────────────────────────────────────────────────────────────

@app.route("/kpis/refresh", methods=["GET", "POST"])
def kpis_refresh():
    """
    GET/POST /kpis/refresh
    Fetch latest KPI values from Google Sheets and apply them to the persona data.

    Optional POST body:
        { "csv_url": "https://docs.google.com/..." }  ← override the .env URL

    Response:
        {
            "status":  "ok",
            "updated": [ {"persona": "P4", "code": "K2", "old_val": "67%", "new_val": "64%"} ],
            "skipped": [],
            "count":   3
        }
    """
    csv_url = None
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        csv_url = body.get("csv_url")

    try:
        overrides = fetch_live_kpis(csv_url)
        summary = apply_live_kpis(overrides)
        return jsonify({
            "status":  "ok",
            "updated": summary["updated"],
            "skipped": summary["skipped"],
            "count":   len(summary["updated"]),
        })
    except ValueError as e:
        return jsonify({"error": str(e), "hint": "Set SHEETS_CSV_URL in .env"}), 400
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 502
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── AI QUERY ───────────────────────────────────────────────────────────────────

@app.route("/query", methods=["POST"])
def query():
    """
    POST /query
    Send a natural-language question to Claude with live engine context.

    Request:
        {
            "persona_id":  "P4",
            "scenario_id": "VO-112",     ← NEW (defaults to "VO-112")
            "question":    "What is the commercial variance?",
            "history":     []
        }

    Response:
        {
            "answer":    str,
            "raw":       str,
            "highlight": {"primary": {...} | null, "supporting": [...]}
        }
    """
    data = request.get_json()
    persona_id  = data.get("persona_id", "P1")
    scenario_id = data.get("scenario_id", "VO-112")
    question    = data.get("question", "").strip()
    history     = data.get("history", [])

    if not question:
        return jsonify({"error": "Empty question"}), 400

    system_prompt = build_system_prompt(persona_id, scenario_id)
    messages = history + [{"role": "user", "content": question}]

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            system=system_prompt,
            messages=messages,
        )
        raw = response.content[0].text
        import re
        hl_match = re.search(r"```highlight\s*([\s\S]*?)```", raw)
        highlight = {"primary": None, "supporting": []}
        if hl_match:
            try:
                highlight = json.loads(hl_match.group(1).strip())
            except json.JSONDecodeError:
                pass
        clean = re.sub(r"```highlight[\s\S]*?```", "", raw).strip()
        return jsonify({"answer": clean, "raw": raw, "highlight": highlight})
    except anthropic.APIError as e:
        return jsonify({"error": f"Anthropic API error: {e}"}), 502
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── SYSTEM PROMPT BUILDER ──────────────────────────────────────────────────────

def build_system_prompt(persona_id: str, scenario_id: str = "VO-112") -> str:
    """
    Build the AI system prompt from live engine outputs.
    Now scenario-aware — includes the active scenario's option labels and computed scores.
    """
    ctx = get_persona_context(persona_id)
    base_kpis = get_persona_kpis(persona_id)
    sc = get_scenario(scenario_id)
    emotions = ["cautious", "strategic", "analytical", "decisive"]

    cell_lines = []
    for persp_id in ctx["perspective_ids"]:
        for emo in emotions:
            try:
                live_kpis = get_kpis_for_persona(persona_id, scenario_id, base_kpis)
                result = compute_decision(persona_id, persp_id, emo, live_kpis, scenario_id)
                w = result["weights"]
                rec = result["recommendation"]
                blocked = "; ".join(
                    f"{c['option']} blocked" for c in result["constraints_fired"]
                )
                cell_lines.append(
                    f"[{persp_id}·{emo}] rec={rec['id']}({rec['score']}) "
                    f"weights=[S:{w[0]}%,F:{w[1]}%,P:{w[2]}%,C:{w[3]}%]"
                    f"{' CONSTRAINTS:' + blocked if blocked else ''}"
                )
            except Exception:
                cell_lines.append(f"[{persp_id}·{emo}] rec=C(60)")

    kpi_str = " | ".join(
        f"{k['code']} {k['name']} {k['val']}{'🔴' if k['rag']=='r' else '🟡' if k['rag']=='y' else '🟢'}"
        for k in base_kpis
    )

    opt_str = " | ".join(
        f"{oid}: {opt['label']} (S:{opt['scores'][0]} F:{opt['scores'][1]} P:{opt['scores'][2]} C:{opt['scores'][3]})"
        for oid, opt in sc["options"].items()
    )

    return f"""You are a decision intelligence assistant for {ctx['name']} ({ctx['role']}) in the Port Talbot EAF Transformation.

ACTIVE SCENARIO: {sc['label']} — {sc['description']}
OPTIONS: {opt_str}

PERSONA CONTEXT:
Non-negotiable: {ctx['non_negotiable']}
Core tension: {ctx['tension']}
KPIs: {kpi_str}

MATRIX (perspective_id · emotion → rec option(score) weights constraints):
{chr(10).join(cell_lines)}

PERSPECTIVE IDs: {" | ".join(ctx["perspective_ids"])}

STRICT OUTPUT FORMAT:
VERDICT: <one sentence. Single best decision. Lead with a number or concrete action.>
DATA: <2-4 key numbers. Format: [value] label. Use 🔴🟡🟢 for status.>
RISKS: <2-3 risks, 8 words max each. HIGH / MED / LOW prefix.>

If asked about "variance", "commercial variance", "financials", "exposure":
treat as a question about the Financial perspective cells.

IF VAGUE: UNCLEAR: <one sentence> / TRY: <2 questions as bullet points>

HIGHLIGHT (end of EVERY response):
```highlight
{{"primary":{{"persp":"perspective_id","emo":"emotion"}},"supporting":[]}}
```

TONE: CXO. Numbers first. Max 80 words. No preamble."""


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    print(f"Port Talbot Decision Framework v2 — http://localhost:{port}")
    app.run(port=port, debug=debug)
```

---

## 8. Updated project structure

```
port_talbot/
├── server.py                  # Flask app — all routes (v2)
├── decision_engine.py         # MCDA engine — now scenario-aware
├── conflict_engine.py         # Cross-persona conflict matrix   ← NEW
├── scenarios.py               # 5 scenario definitions          ← NEW
├── kpi_feed.py                # Google Sheets CSV fetcher       ← NEW
├── personas.py                # Persona + KPI data (unchanged)
├── requirements.txt
├── .env
├── .gitignore
└── frontend/
    └── index.html
```

---

## 9. Updated API reference

| Method | Endpoint | Purpose |
|---|---|---|
| `GET`  | `/` | Serve frontend |
| `GET`  | `/health` | Status + scenario list |
| `GET`  | `/scenarios` | All scenario metadata |
| `POST` | `/compute` | MCDA engine (single cell) |
| `POST` | `/conflict` | Cross-persona conflict matrix |
| `POST` | `/conflict/detail` | Two-persona comparison detail |
| `GET/POST` | `/kpis/refresh` | Fetch live KPIs from Google Sheets |
| `POST` | `/query` | AI assistant |

### `POST /conflict` — request

```json
{
    "scenario_id": "VO-112",
    "emotion":     "cautious"
}
```

### `POST /conflict` — response (abbreviated)

```json
{
    "scenario_id": "VO-112",
    "emotion":     "cautious",
    "options": [
        {"id":"A","label":"Pay full £31.4M under protest","short":"Pay full"},
        {"id":"B","label":"Pay agreed £16.5M, dispute rest","short":"Pay £16.5M"},
        {"id":"C","label":"Negotiate £23–25M settlement","short":"Negotiate"}
    ],
    "rows": [
        {
            "persona_id":    "P1",
            "name":          "Rajesh Nair",
            "recommendation": "C",
            "scores":  {"A": 63, "B": 49, "C": 69},
            "blocked": {"A": false, "B": true, "C": false},
            "weights": [20, 31, 28, 21]
        }
    ],
    "insights": {
        "consensus_type":   "majority",
        "winning_option":   "C",
        "winning_count":    3,
        "consensus_names":  ["Rajesh", "Owen", "Chris"],
        "dissenter_names":  ["Sian", "Priya"],
        "blocked_entries":  [{"persona": "Rajesh", "option": "Pay £16.5M"}],
        "high_spread_opts": [{"option": "Pay full", "spread": 24}]
    }
}
```

### `GET /kpis/refresh` — response

```json
{
    "status":  "ok",
    "count":   3,
    "updated": [
        {"persona": "P4", "code": "K2", "old_val": "67%", "new_val": "64%"},
        {"persona": "P3", "code": "K4", "old_val": "2/5", "new_val": "1/5"},
        {"persona": "P1", "code": "K1", "old_val": "73%", "new_val": "68%"}
    ],
    "skipped": []
}
```

---

## 10. Frontend integration — pointing the HTML to the backend

Three changes to `port_talbot_decision_framework.html` when moving to the backend:

### Change 1 — Scenario switching

```javascript
// BEFORE: frontend switches scenarios using in-memory SCENARIOS object
function switchScenario(scenarioId) {
    activeScenario = scenarioId;
    renderPersona(activePid);
}

// AFTER: fetch scenario options and KPI overrides from server
async function switchScenario(scenarioId) {
    activeScenario = scenarioId;
    // Server applies KPI overrides and recomputes
    renderPersona(activePid);  // unchanged — engine call still goes to /compute
}
```

### Change 2 — Conflict matrix

```javascript
// BEFORE: browser runs renderConflictMatrix() locally
// AFTER: fetch from server (heavier computation, result is cacheable)
async function renderConflictMatrix() {
    const result = await fetch('/conflict', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ scenario_id: activeScenario, emotion: conflictEmo })
    }).then(r => r.json());
    // Render using result.rows, result.insights
}
```

### Change 3 — Live KPI refresh

```javascript
// BEFORE: browser fetches CSV directly (CORS issues on some sheets)
// AFTER: server fetches the CSV, browser just triggers the refresh
async function refreshKPIs() {
    const result = await fetch('/kpis/refresh').then(r => r.json());
    if (result.status === 'ok') {
        // Re-render matrix with updated values
        renderPersona(activePid);
        console.log(`Updated ${result.count} KPIs`);
    }
}
```

---

## 11. Running v2

```bash
# Same as v1 — one additional env variable
echo "ANTHROPIC_API_KEY=sk-ant-api03-..." >> .env
echo "SHEETS_CSV_URL=https://docs.google.com/spreadsheets/d/YOUR_ID/pub?output=csv" >> .env

python server.py
# Port Talbot Decision Framework v2 — http://localhost:5000
```

---

## 12. Adding a new scenario (checklist)

1. Add entry to `SCENARIOS` dict in `scenarios.py`
   - Define 3 options with performance scores `[S, F, P, C]`
   - Define `kpi_overrides` for any persona whose KPIs change in this scenario
2. Add `<option>` to the `#scenario-select` dropdown in `index.html`
3. Update any hard constraints in `decision_engine.py` if the new scenario introduces new constraint conditions
4. Test via `POST /conflict` with the new scenario ID to verify all 5 personas score correctly

---

*Port Talbot Decision Framework · Backend Specification v2.0*  
*New: Multi-scenario library · Live KPI feed (Google Sheets) · Cross-persona conflict matrix*  
*Engine: MCDA + emotion weight modifiers + hard constraint elimination + sensitivity analysis*  
*AI: claude-sonnet-4-6, scenario-aware system prompt, key server-side only*
