# server.py
# Port Talbot Decision Framework — Flask Backend Server
# Serves the frontend and provides API endpoints for compute, conflict, KPI refresh, and AI query.
#
# Usage:
#   pip install -r requirements.txt
#   python server.py

import os
import json
import re
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
from decision_engine import compute_decision
from scenarios import get_scenario, get_all_scenarios, get_kpis_for_persona
from personas import get_persona_kpis, get_persona_context, PERSONA_IDS

load_dotenv()

app = Flask(__name__, static_folder="../", static_url_path="")
CORS(app)

# Lazy-load AI client (works with either Groq or Anthropic)
_ai_client = None
def get_ai_client():
    global _ai_client
    if _ai_client is None:
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            from groq import Groq
            _ai_client = ("groq", Groq(api_key=groq_key))
        else:
            import anthropic
            _ai_client = ("anthropic", anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY")))
    return _ai_client


@app.route("/")
def index():
    return send_from_directory("..", "port_talbot_decision_framework.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok", "version": "2.0"})


@app.route("/scenarios")
def scenarios():
    return jsonify(get_all_scenarios())


@app.route("/compute", methods=["POST"])
def compute():
    data = request.get_json()
    try:
        persona_id   = data["persona_id"]
        perspective  = data["perspective_id"]
        emotion      = data["emotion"]
        scenario_id  = data.get("scenario_id", "VO-112")
        kpis         = data.get("kpis") or get_persona_kpis(persona_id)
        live_kpis    = get_kpis_for_persona(persona_id, scenario_id, kpis)
        result       = compute_decision(persona_id, perspective, emotion, live_kpis, scenario_id)
        return jsonify(result)
    except (KeyError, ValueError) as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/conflict", methods=["POST"])
def conflict():
    from conflict_engine import compute_conflict_matrix
    data = request.get_json()
    try:
        result = compute_conflict_matrix(
            scenario_id=data.get("scenario_id", "VO-112"),
            emotion=data.get("emotion", "cautious"),
        )
        return jsonify(result)
    except (ValueError, KeyError) as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/kpis/refresh", methods=["GET", "POST"])
def kpis_refresh():
    from kpi_feed import fetch_live_kpis, apply_live_kpis
    csv_url = None
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        csv_url = body.get("csv_url")
    try:
        overrides = fetch_live_kpis(csv_url)
        summary   = apply_live_kpis(overrides)
        return jsonify({"status":"ok","count":len(summary["updated"]),
                        "updated":summary["updated"],"skipped":summary["skipped"]})
    except ValueError as e:
        return jsonify({"error": str(e), "hint": "Set SHEETS_CSV_URL in .env"}), 400
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 502
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/query", methods=["POST"])
def query():
    data        = request.get_json()
    persona_id  = data.get("persona_id", "P1")
    scenario_id = data.get("scenario_id", "VO-112")
    question    = data.get("question", "").strip()
    history     = data.get("history", [])

    if not question:
        return jsonify({"error": "Empty question"}), 400

    system_prompt = build_system_prompt(persona_id, scenario_id)
    messages = history + [{"role": "user", "content": question}]

    try:
        client_type, client = get_ai_client()
        if client_type == "groq":
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                max_tokens=500,
                temperature=0.3,
                messages=[{"role":"system","content":system_prompt}] + messages,
            )
            raw = response.choices[0].message.content
        else:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=500,
                system=system_prompt,
                messages=messages,
            )
            raw = response.content[0].text

        hl_match  = re.search(r"```highlight\s*([\s\S]*?)```", raw)
        highlight = {"primary": None, "supporting": []}
        if hl_match:
            try:
                highlight = json.loads(hl_match.group(1).strip())
            except json.JSONDecodeError:
                pass
        clean = re.sub(r"```highlight[\s\S]*?```", "", raw).strip()
        return jsonify({"answer": clean, "raw": raw, "highlight": highlight})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def build_system_prompt(persona_id: str, scenario_id: str = "VO-112") -> str:
    ctx      = get_persona_context(persona_id)
    kpis     = get_persona_kpis(persona_id)
    sc       = get_scenario(scenario_id)
    emotions = ["cautious", "strategic", "analytical", "decisive"]
    persp_ids = " | ".join(ctx["perspective_ids"])

    cell_lines = []
    for pid in ctx["perspective_ids"]:
        scores = []
        for emo in emotions:
            try:
                r = compute_decision(persona_id, pid, emo, kpis, scenario_id)
                scores.append(f"{emo[0].upper()}:{r['recommendation']['id']}({r['recommendation']['score']})")
            except Exception:
                scores.append(f"{emo[0].upper()}:C(60)")
        cell_lines.append(f"{pid}: {' '.join(scores)}")

    kpi_str = " | ".join(
        f"{k['code']}={k['val']}{'🔴' if k['rag']=='r' else '🟡' if k['rag']=='y' else '🟢'}"
        for k in kpis)
    opt_str = " | ".join(
        f"{oid}:{opt['short']}[S{opt['scores'][0]}/F{opt['scores'][1]}/P{opt['scores'][2]}/C{opt['scores'][3]}]"
        for oid, opt in sc["options"].items())

    return f"""Decision assistant for {ctx['name']} ({ctx['role']}). Scenario: {sc['label']}.
Non-negotiable: {ctx['non_negotiable']}
KPIs: {kpi_str}
Options: {opt_str}
Matrix (C=Cautious S=Strategic A=Analytical D=Decisive):
{chr(10).join(cell_lines)}
Valid perspective IDs: {persp_ids}

STRICT FORMAT:
VERDICT: <one sentence, lead with a number>
DATA: [value] label 🔴/🟡/🟢 (2-3 lines)
RISKS: HIGH/MED/LOW — phrase (2-3 lines)
```highlight
{{"primary":{{"persp":"PICK_FROM_VALID_IDS","emo":"PICK_EMOTION"}},"supporting":[]}}
```
Replace PICK_FROM_VALID_IDS with the most relevant ID from the valid list.
Replace PICK_EMOTION with: cautious, strategic, analytical, or decisive.
Max 60 words above the highlight block."""


if __name__ == "__main__":
    port  = int(os.getenv("PORT", 5000))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    print(f"\n  Port Talbot Decision Framework — http://localhost:{port}\n")
    app.run(port=port, debug=debug)
