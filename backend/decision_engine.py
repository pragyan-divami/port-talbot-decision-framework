# decision_engine.py
# Port Talbot Decision Framework — Core MCDA Engine
# Pure Python. No external dependencies. Identical logic to the frontend JS engine.

import re
from typing import Optional

# ── DIMENSION INDEX ───────────────────────────────────────────────────────────
S, F, P, C = 0, 1, 2, 3
DIM_LABELS = ["Schedule", "Financial", "Political", "Commercial"]

# ── BASE WEIGHTS ─────────────────────────────────────────────────────────────
# Role-level weights: what this persona fundamentally cares about.
# These are their professional DNA. Sum = 1.0.
BASE_WEIGHTS = {
    "P1":  [0.30, 0.20, 0.30, 0.20],  # CEO
    "P3":  [0.45, 0.20, 0.10, 0.25],  # Project Director
    "P4":  [0.15, 0.45, 0.25, 0.15],  # CFO
    "P2":  [0.20, 0.15, 0.45, 0.20],  # CHRO
    "P10": [0.15, 0.20, 0.15, 0.50],  # Commercial Director
}

# ── EMOTION MULTIPLIERS ───────────────────────────────────────────────────────
# Applied to base weights then renormalised to sum = 1.0.
EMOTION_MULTIPLIERS = {
    "cautious":   [0.90, 1.40, 1.10, 0.70],
    "strategic":  [0.70, 0.80, 0.75, 2.10],
    "analytical": [1.00, 1.15, 1.00, 1.05],
    "decisive":   [1.90, 0.85, 0.65, 0.80],
}

# ── HARD CONSTRAINTS ──────────────────────────────────────────────────────────
def _make_constraints():
    return {
        "P1": {
            "political_grant": [
                {"option": "B",
                 "condition": lambda k: k.get("K3", {}).get("rag_score", 0) >= 2,
                 "reason": "Withholding creates a grant covenant notification gap — disclosure obligation is live."},
            ],
            "programme_delivery": [
                {"option": "B",
                 "condition": lambda k: k.get("K1", {}).get("num_val", 99) <= 5,
                 "reason": "Schedule float ≤5 weeks. Suspension risk makes Option B a programme-ending move."},
            ],
        },
        "P3": {
            "safety_compliance": [
                {"option": "A",
                 "condition": lambda k: k.get("K3", {}).get("num_val", 0) >= 1.2,
                 "reason": "LTIFR above 1.2 — acceleration without safety review violates zero-tolerance constraint."},
            ],
            "cost_discipline": [
                {"option": "B",
                 "condition": lambda k: k.get("K4", {}).get("num_val", 0) >= 25,
                 "reason": "Open change orders above £25M — withholding escalates dispute risk beyond programme tolerance."},
            ],
        },
        "P4": {
            "grant_covenant": [
                {"option": "B",
                 "condition": lambda k: k.get("K1", {}).get("rag_score", 0) >= 2,
                 "reason": "Two grant milestones at risk. Withholding adds a third — covenant breach becomes highly probable."},
            ],
            "capital_discipline": [
                {"option": "A",
                 "condition": lambda k: k.get("K2", {}).get("num_val", 100) <= 50,
                 "reason": "Contingency below 50% — full payment without adjudication violates capital preservation mandate."},
            ],
        },
        "P2": {
            "legal_compliance": [
                {"option": "A",
                 "condition": lambda k: k.get("K2", {}).get("num_val", 100) <= 70,
                 "reason": "Graduation rate below 70% — action that increases pressure without legal cover is eliminated."},
            ],
            "union_relations": [
                {"option": "B",
                 "condition": lambda k: k.get("K4", {}).get("num_val", 5) <= 2,
                 "reason": "Union relationship below 2/5 — partial payment without union briefing triggers formal dispute."},
            ],
        },
        "P10": {
            "offtake_pipeline": [
                {"option": "B",
                 "condition": lambda k: k.get("K8", {}).get("num_val", 0) >= 2,
                 "reason": "Two+ customers in alternative qualification. Withholding signals instability."},
            ],
            "product_capability": [
                {"option": "A",
                 "condition": lambda k: k.get("K3", {}).get("num_val", 0) >= 40,
                 "reason": "BMW revenue at risk exceeds £40M. Committing without LMF validation is eliminated."},
            ],
        },
    }

HARD_CONSTRAINTS = _make_constraints()


def parse_kpis(kpis: list[dict]) -> dict:
    result = {}
    for k in kpis:
        num_match = re.search(r"[\d.]+", str(k.get("val", "")))
        num_val = float(num_match.group()) if num_match else 0.0
        rag = k.get("rag", "g")
        rag_score = 2 if rag == "r" else 1 if rag == "y" else 0
        result[k["code"]] = {**k, "num_val": num_val, "rag_score": rag_score}
    return result


def compute_weights(persona_id: str, emotion: str) -> list[float]:
    base = BASE_WEIGHTS.get(persona_id, [0.25, 0.25, 0.25, 0.25])
    mults = EMOTION_MULTIPLIERS.get(emotion, [1.0, 1.0, 1.0, 1.0])
    raw = [b * m for b, m in zip(base, mults)]
    total = sum(raw)
    return [r / total for r in raw]


def score_option(option_scores: list[int], weights: list[float]) -> float:
    return sum(s * w for s, w in zip(option_scores, weights))


def compute_sensitivity(rec_id, second_id, weights, margin, options):
    rec_scores = options[rec_id]["scores"]
    sec_scores = options[second_id]["scores"]
    for d in range(4):
        for step in range(1, 11):
            delta = step * 0.02
            tweaked = weights[:]
            tweaked[d] = max(0.0, tweaked[d] - delta)
            total = sum(tweaked)
            norm = [w / total for w in tweaked]
            if score_option(sec_scores, norm) > score_option(rec_scores, norm):
                return {
                    "margin": round(margin, 1),
                    "second_option": options[second_id]["short"],
                    "flip_dim": DIM_LABELS[d],
                    "flip_amount": step * 2,
                }
    return {"margin": round(margin, 1), "second_option": options[second_id]["short"],
            "flip_dim": None, "flip_amount": None}


def compute_decision(persona_id: str, perspective_id: str, emotion: str,
                     kpis: list[dict], scenario_id: str = "VO-112") -> dict:
    from scenarios import get_scenario, get_kpis_for_persona
    sc = get_scenario(scenario_id)
    live_kpis = get_kpis_for_persona(persona_id, scenario_id, kpis)
    parsed = parse_kpis(live_kpis)
    weights = compute_weights(persona_id, emotion)
    options = sc["options"]

    constraints = HARD_CONSTRAINTS.get(persona_id, {}).get(perspective_id, [])
    eliminated, constraints_fired = set(), []
    for c in constraints:
        if c["condition"](parsed):
            eliminated.add(c["option"])
            constraints_fired.append({"option": c["option"], "reason": c["reason"]})

    scored = []
    for opt_id, opt in options.items():
        raw = score_option(opt["scores"], weights)
        scored.append({
            "id": opt_id, "label": opt["label"], "short": opt["short"],
            "raw_score": raw, "score": round(raw),
            "eliminated": opt_id in eliminated,
            "elimination_reason": next(
                (cf["reason"] for cf in constraints_fired if cf["option"] == opt_id), None),
        })

    scored.sort(key=lambda o: o["raw_score"], reverse=True)
    for i, o in enumerate(scored):
        o["rank"] = i + 1

    active = [o for o in scored if not o["eliminated"]]
    recommendation = active[0] if active else scored[0]

    sensitivity = None
    if len(active) >= 2:
        margin = recommendation["raw_score"] - active[1]["raw_score"]
        sensitivity = compute_sensitivity(
            recommendation["id"], active[1]["id"], weights, margin, options)

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
