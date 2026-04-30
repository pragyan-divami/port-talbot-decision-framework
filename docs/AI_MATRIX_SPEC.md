# AI Matrix Logic Specification
## Decision Intelligence Query System — 4×4 KPI Matrix Highlighter

**Version:** 1.0  
**Scenario:** VO-112 Tenova Variation Order Cascade  
**Purpose:** Full implementation guide for integrating the AI query layer into the production `decision_engine.py` + `server.py` application so that any natural-language question resolves to the correct matrix cell highlight, option score, and contextual answer.

---

## 1. System architecture overview

The AI matrix system has four components that must talk to each other in sequence:

```
User question
     ↓
[1] INPUT LAYER        — receives raw text, tracks conversation history
     ↓
[2] AI REASONING LAYER — Claude API call with full scenario context in system prompt
     ↓
[3] INSTRUCTION PARSER — extracts structured matrix highlight instruction from AI response
     ↓
[4] RENDER LAYER       — applies highlight instruction to KPI tiles and weight grid cells
```

Each layer has its own logic rules. This document specifies all four.

---

## 2. Data model — what the system must know

### 2.1 Emotions (4)

| Code | Label | Description |
|---|---|---|
| A | Cautious | Risk-first, downside-protective, seeks reversibility |
| B | Strategic | Long-horizon, thesis-protective, weighted toward future |
| C | Diplomatic | Stakeholder-balancing, coalition-sensitive |
| D | Decisive | Action-biased, fast-commitment, speed over completeness |

### 2.2 Perspectives (4 — the matrix columns)

| Code | Label | What it captures |
|---|---|---|
| `sched` | Schedule / Delivery | Programme milestones, timeline risk, contractor performance |
| `fin` | Financial | Cash, budget, grant, contingency, debt |
| `people` | People / Political | Workforce, union, community, political relationships |
| `comm` | Commercial / Strategic | Customers, contracts, supply chain, long-term positioning |

### 2.3 Per-persona data shape

Every persona must provide:

```json
{
  "id": "P1",
  "name": "Rajesh Nair",
  "role": "CEO, Tata Steel UK",
  "decision": "Pay full / pay £16.5M only / negotiate settlement",
  "tension": "Programme continuity and 2027 date vs fiduciary discipline and legal precedent",
  "kpis": [
    {
      "code": "K1",
      "name": "EAF schedule float remaining",
      "unit": "weeks",
      "val": "7 wks",
      "rag": "yellow",
      "hard": true,
      "note": "11-wk VO-112 + pre-existing consumption = ~2 wks margin if paid; suspension adds 6–8 wks"
    },
    { "code": "K2", ... },
    { "code": "K3", ... },
    { "code": "K7", ... }
  ],
  "weights": {
    "A": [30, 25, 30, 15],
    "B": [15, 15, 20, 50],
    "C": [20, 15, 40, 25],
    "D": [45, 25, 15, 15]
  }
}
```

**Weight array order:** `[sched, fin, people, comm]` — always in this order. Each row must sum to 100.

**KPI codes:** K1–K8 are position slots, not universal metrics. Each persona assigns their own meaning to each slot. A persona uses only the 4 slots most relevant to the scenario — the remaining slots are absent.

**Hard priority (`hard: true`):** A KPI flagged as hard priority overrides emotion weights when its `rag` is `"red"`. The system must surface it at the top of any recommendation regardless of the emotion state.

**RAG values:** `"red"` | `"yellow"` | `"green"` — derived from current readings vs thresholds defined per persona.

### 2.4 Option scoring — fixed across all personas for this scenario

These scores represent how well each decision option performs across the four perspectives, on a 0–100 scale. These are scenario-level inputs, not per-persona:

```json
{
  "A": {
    "label": "Pay full £31.4M under protest",
    "scores": { "sched": 85, "fin": 40, "people": 65, "comm": 55 }
  },
  "B": {
    "label": "Pay agreed £16.5M, dispute rest",
    "scores": { "sched": 30, "fin": 75, "people": 35, "comm": 70 }
  },
  "C": {
    "label": "Negotiate settlement £23–25M",
    "scores": { "sched": 80, "fin": 60, "people": 70, "comm": 60 }
  }
}
```

---

## 3. Scoring algorithm

To calculate the recommended option for a given persona + emotion state:

```
For each option (A, B, C):
  score = 0
  for each perspective p in [sched, fin, people, comm]:
    score += option.scores[p] × (persona.weights[emotion][p] / 100)
  
Winner = option with highest score
```

**Example — P1 Rajesh in Cautious (A) mode:**
- Weights: sched=30, fin=25, people=30, comm=15
- Option A: (85×30 + 40×25 + 65×30 + 55×15) / 100 = (2550+1000+1950+825)/100 = 63.25
- Option B: (30×30 + 75×25 + 35×30 + 70×15) / 100 = (900+1875+1050+1050)/100 = 48.75
- Option C: (80×30 + 60×25 + 70×30 + 60×15) / 100 = (2400+1500+2100+900)/100 = 69.00
- **Winner: Option C (69.00)**

**Hard priority override rule:**  
Before finalising the recommendation, check if any hard-priority KPI is red. If yes, apply a penalty of 20 points to any option that does not address that KPI. The penalty is not applied if the option explicitly resolves the hard-priority red (this is scenario-specific logic — document it per option in the scenario file).

---

## 4. System prompt specification

The system prompt is rebuilt on every API call. It contains:

### 4.1 Scenario context block (static)

```
You are an AI assistant embedded in a decision intelligence tool for the 
Tata Steel UK Port Talbot EAF project.

SCENARIO: {scenario.title}
DATE: {scenario.date}
TRIGGER: {scenario.trigger}
CLAIM: {scenario.claim}
AGREED: {scenario.agreed}
DISPUTED: {scenario.disputed}
DECISION WINDOW: {scenario.window}

The tool shows a 4×4 KPI matrix for {n} personas.
Each persona has 4 scenario KPIs and a 4×4 emotion×perspective weight table.

EMOTIONS: A=Cautious, B=Strategic, C=Diplomatic, D=Decisive
PERSPECTIVES: Schedule/Delivery (sched), Financial (fin), 
              People/Political (people), Commercial/Strategic (comm)
Weights in each emotion row sum to 100.
```

### 4.2 Option scoring block (static per scenario)

```
OPTION SCORES (perspective scores on 0–100 scale):
Option A ({label}): sched={n}, fin={n}, people={n}, comm={n}
Option B ({label}): sched={n}, fin={n}, people={n}, comm={n}
Option C ({label}): sched={n}, fin={n}, people={n}, comm={n}

SCORING FORMULA:
weighted_score = sum(option.score[p] × persona.weight[emotion][p] / 100 for p in perspectives)
Winner = highest weighted_score
```

### 4.3 Persona data block (dynamic — built from data)

```
PERSONA DATA (all {n} personas):
{for each persona p:}
{p.id} {p.name} ({p.role}):
  Decision: "{p.decision}"
  Tension: "{p.tension}"
  KPIs: {for each k: "{k.code} {k.name} [{k.val} {flag_emoji} {hard_marker}]"}
  Weights: A=[{sched},{fin},{people},{comm}] B=[...] C=[...] D=[...]
           (order: sched / fin / people / comm)
```

### 4.4 Behavioural rules block (static)

```
YOUR ROLE AND RULES:

RULE 1 — ANSWER IN CONTEXT:
Answer questions about the scenario, personas, KPIs, emotion weights, and option 
recommendations. Use exact KPI codes (K1, K2…) and persona IDs (P1, P2…).

RULE 2 — CALCULATE, DON'T GUESS:
When asked about a specific persona + emotion, apply the scoring formula and 
state the exact weighted scores for all options, then declare the winner.
Show the arithmetic. Do not estimate.

RULE 3 — MAP TO CELLS:
When a question references a KPI, perspective, or emotion, identify exactly 
which matrix cells are relevant and state them explicitly in your answer.
Example: "This touches K3 for P1 (grant covenant, currently 🔴) and K1 for P4."

RULE 4 — CATCH VAGUE QUESTIONS:
If the question is ambiguous or references something not in the scenario:
(a) State what you understood from the question.
(b) State specifically what is unclear or missing.
(c) Offer exactly 2–3 suggested questions that ARE answerable from the data.
Do NOT guess or hallucinate data that isn't in the persona definitions.

RULE 5 — CATCH OUT-OF-CONTEXT QUESTIONS:
If the question has no connection to the scenario, personas, or KPI matrix:
(a) Clearly state the question is outside this scenario's scope.
(b) Suggest the single most relevant in-scope question.

RULE 6 — ALWAYS EMIT A MATRIX INSTRUCTION:
At the end of EVERY response, append a JSON block in this exact format:
```matrix
{
  "persona": "<P1|P2|...|P10|ALL|null>",
  "kpis": ["K1", "K3"],
  "emotion": "<A|B|C|D|null>",
  "persp": "<sched|fin|people|comm|null>"
}
```
Rules for the matrix block:
- "persona": use the specific ID if question is about one persona; "ALL" if 
  the answer spans multiple; null if no persona is relevant.
- "kpis": array of KPI codes mentioned in the answer; empty array [] if none.
- "emotion": the emotion code if the question or answer targets a specific 
  emotion row; null if the answer spans all emotions.
- "persp": the perspective code if the answer targets a specific column; 
  null if the answer spans all columns or no column is relevant.
- Do not omit this block. It must be valid JSON. It must use only values 
  defined above.

ACTIVE CONTEXT: Persona {activePersona or "ALL"}. Emotion {activeEmotion or "none"}.
```

---

## 5. Input layer logic

### 5.1 Conversation history management

The system maintains a rolling conversation history array. Every API call sends the full history plus the new user message:

```python
conversation_history = []  # persists across messages in a session

def send_query(user_message: str) -> str:
    conversation_history.append({
        "role": "user",
        "content": user_message
    })
    
    response = call_claude_api(
        system=build_system_prompt(active_persona, active_emotion),
        messages=conversation_history
    )
    
    conversation_history.append({
        "role": "assistant", 
        "content": response
    })
    
    return response
```

**Session boundary:** Clear `conversation_history` when the user switches scenario, not when they switch persona. Persona switching within a scenario is part of the same conversational context.

### 5.2 Context state variables

The following state variables must be maintained by the application:

```python
active_persona: str | None = None   # e.g., "P1", or None for all
active_emotion: str | None = None   # e.g., "A", or None
highlighted_kpis: list[str] = []    # e.g., ["K1", "K3"]
highlighted_emotion: str | None = None
highlighted_persp: str | None = None
```

These are updated by the render layer after each API response, not by the user directly (except persona selection via sidebar click).

---

## 6. Instruction parser logic

### 6.1 Extraction

The matrix instruction is embedded in the AI response inside a fenced code block tagged `matrix`. Extract it with this pattern:

```python
import re, json

def parse_matrix_instruction(response_text: str) -> dict | None:
    match = re.search(r'```matrix\s*([\s\S]*?)```', response_text)
    if not match:
        return None
    try:
        return json.loads(match.group(1).strip())
    except json.JSONDecodeError:
        return None
```

### 6.2 Validation

Before applying the instruction, validate it:

```python
VALID_PERSONAS = {"P1","P2","P3","P4","P5","P6","P7","P8","P9","P10","ALL"}
VALID_EMOTIONS = {"A","B","C","D"}
VALID_PERSPS = {"sched","fin","people","comm"}
VALID_KPIS = {"K1","K2","K3","K4","K5","K6","K7","K8"}

def validate_instruction(instr: dict) -> dict:
    return {
        "persona": instr.get("persona") if instr.get("persona") in VALID_PERSONAS else None,
        "kpis": [k for k in (instr.get("kpis") or []) if k in VALID_KPIS],
        "emotion": instr.get("emotion") if instr.get("emotion") in VALID_EMOTIONS else None,
        "persp": instr.get("persp") if instr.get("persp") in VALID_PERSPS else None,
    }
```

### 6.3 Clean response text for display

Strip the matrix instruction block before displaying the AI response to the user:

```python
def clean_response(response_text: str) -> str:
    return re.sub(r'```matrix[\s\S]*?```', '', response_text).strip()
```

---

## 7. Render layer logic — cell highlighting rules

### 7.1 KPI tile highlighting

A KPI tile is highlighted when:

```python
def should_highlight_kpi_tile(kpi_code: str, persona_id: str, instruction: dict) -> bool:
    # Persona must match: either specific match or ALL
    persona_match = (
        instruction["persona"] == persona_id or
        instruction["persona"] == "ALL" or
        instruction["persona"] is None
    )
    # KPI code must be in the highlighted list
    kpi_match = kpi_code in instruction["kpis"]
    
    return persona_match and kpi_match
```

When highlighted, the KPI tile:
- Gets a distinct border colour (accent/info colour)
- Shows its full `note` text (normally hidden or truncated)
- Optionally shows a subtle background tint

### 7.2 Weight grid cell highlighting — 3-level system

The weight grid has three distinct highlight states applied to cells, rows, and columns:

```python
def get_cell_class(emotion: str, persp: str, persona_id: str, instruction: dict) -> str:
    # Check if this persona is in scope
    persona_in_scope = (
        instruction["persona"] == persona_id or
        instruction["persona"] == "ALL" or
        instruction["persona"] is None
    )
    
    if not persona_in_scope:
        return ""
    
    row_match = instruction["emotion"] == emotion
    col_match = instruction["persp"] == persp
    
    if row_match and col_match:
        return "cell-active"    # FULL HIGHLIGHT: specific intersection targeted
    elif row_match:
        return "row-active"     # DIM HIGHLIGHT: whole emotion row is relevant
    elif col_match:
        return "col-active"     # DIM HIGHLIGHT: whole perspective column is relevant
    else:
        return ""
```

**Visual distinction between the three states:**

| State | CSS class | Visual |
|---|---|---|
| Full intersection targeted | `cell-active` | Strong background, bold text, border glow |
| Emotion row relevant | `row-active` | Subtle background tint, no border |
| Perspective column relevant | `col-active` | Subtle background tint (different hue), no border |
| Not relevant | `` (empty) | Default appearance |

### 7.3 Perspective column header highlighting

When `instruction["persp"]` is set, apply the same `col-active` class to the column header cell in the weight grid. This makes it immediately clear which perspective dimension is being discussed.

### 7.4 Sidebar persona button highlighting

When `instruction["persona"]` is a specific persona ID (not "ALL" or null):
- Set that persona button to `active` state in the sidebar
- Update the `active-ctx` display chip with the persona's name
- Re-render the matrix panel to show that persona's full detail

When `instruction["persona"]` is "ALL":
- Keep current sidebar state unchanged
- Render all (or first N) personas in the matrix panel
- Apply KPI tile highlights across all personas where the code matches

When `instruction["persona"]` is null:
- Do not change the current persona selection

---

## 8. Vague question handling — the clarification flow

When the AI detects a vague or out-of-context question (Rule 4 or Rule 5 triggers), the response format changes. The application must recognise this and render it differently.

### 8.1 Recognising a clarification response

The clarification response will contain one or more of these signals:
- Phrases like "I understood your question as…", "What's unclear is…", "Did you mean…"
- A suggestion list formatted as numbered or bullet options
- The `matrix` block will have `"persona": null, "kpis": [], "emotion": null, "persp": null` (all nulls)

### 8.2 Rendering clarification responses

Render suggestion items as clickable buttons in the chat UI. When clicked, the suggestion text is injected directly into the query input and submitted as if the user typed it:

```javascript
// Frontend
function renderSuggestionButtons(suggestions) {
    return suggestions.map(s => 
        `<button onclick="submitQuery('${escapeQuotes(s)}')">${s}</button>`
    ).join('');
}

function submitQuery(text) {
    document.getElementById('query').value = text;
    sendQuery();
}
```

### 8.3 The null matrix instruction

When all fields in the matrix instruction are null or empty, the render layer must not change any current highlight state. The matrix stays in whatever state it was before the vague question was asked.

```python
def should_update_highlights(instruction: dict) -> bool:
    return not (
        instruction["persona"] is None and
        len(instruction["kpis"]) == 0 and
        instruction["emotion"] is None and
        instruction["persp"] is None
    )
```

---

## 9. Integration into decision_engine.py + server.py

### 9.1 New endpoint in server.py

Add a `POST /query` endpoint alongside the existing `POST /analyze`:

```python
def do_POST(self) -> None:
    if self.path == "/analyze":
        # existing logic
        ...
    elif self.path == "/query":
        self.handle_query()
    else:
        self.send_error(HTTPStatus.NOT_FOUND)

def handle_query(self) -> None:
    content_length = int(self.headers.get("Content-Length", 0))
    body = json.loads(self.rfile.read(content_length))
    
    question = body.get("question", "").strip()
    session_id = body.get("session_id", "default")
    active_persona = body.get("active_persona")     # e.g., "P1" or None
    active_emotion = body.get("active_emotion")     # e.g., "A" or None
    conversation_history = body.get("history", [])  # full history from client
    
    if not question:
        self.respond_json({"status": "error", "message": "No question provided."}, 
                          status=HTTPStatus.BAD_REQUEST)
        return
    
    result = query_matrix(
        question=question,
        active_persona=active_persona,
        active_emotion=active_emotion,
        history=conversation_history
    )
    self.respond_json(result)
```

### 9.2 New function in decision_engine.py

```python
def query_matrix(
    question: str,
    active_persona: str | None,
    active_emotion: str | None, 
    history: list[dict],
    scenario_data: dict | None = None,
    persona_data: list[dict] | None = None,
) -> dict:
    """
    Send a natural-language question to the AI layer with full scenario context.
    Returns the AI answer + a structured matrix instruction for the frontend.
    
    Returns:
        {
            "status": "ok",
            "answer": "<clean response text for display>",
            "matrix_instruction": {
                "persona": "P1" | "ALL" | null,
                "kpis": ["K1", "K3"],
                "emotion": "A" | null,
                "persp": "sched" | null
            },
            "option_scores": {          # populated when a scoring question is answered
                "A": 69.0,
                "B": 48.75,
                "C": 63.25,
                "winner": "C"
            } | null
        }
    """
    import anthropic
    
    client = anthropic.Anthropic()
    
    system_prompt = build_query_system_prompt(
        active_persona=active_persona,
        active_emotion=active_emotion,
        scenario_data=scenario_data or DEFAULT_SCENARIO,
        persona_data=persona_data or load_personas_for_query(),
    )
    
    messages = history + [{"role": "user", "content": question}]
    
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=system_prompt,
        messages=messages,
    )
    
    raw_text = response.content[0].text
    matrix_instr = parse_matrix_instruction(raw_text)
    validated_instr = validate_instruction(matrix_instr) if matrix_instr else {
        "persona": None, "kpis": [], "emotion": None, "persp": None
    }
    clean_text = clean_response(raw_text)
    
    return {
        "status": "ok",
        "answer": clean_text,
        "matrix_instruction": validated_instr,
        "option_scores": extract_option_scores(clean_text),  # regex parse if present
    }
```

### 9.3 System prompt builder function

```python
def build_query_system_prompt(
    active_persona: str | None,
    active_emotion: str | None,
    scenario_data: dict,
    persona_data: list[dict],
) -> str:
    
    persona_summaries = "\n".join([
        f"{p['id']} {p['name']} ({p['role']}):\n"
        f"  Decision: \"{p['decision']}\"\n"
        f"  Tension: \"{p['tension']}\"\n"
        f"  KPIs: {', '.join(f\"{k['code']} {k['name']} [{k['val']} {'⚑' if k['hard'] else ''}]\" for k in p['kpis'])}\n"
        f"  Weights: A={p['weights']['A']} B={p['weights']['B']} C={p['weights']['C']} D={p['weights']['D']} (sched/fin/people/comm)"
        for p in persona_data
    ])
    
    option_lines = "\n".join([
        f"Option {k} ({v['label']}): sched={v['scores']['sched']}, fin={v['scores']['fin']}, "
        f"people={v['scores']['people']}, comm={v['scores']['comm']}"
        for k, v in scenario_data['options'].items()
    ])
    
    active_ctx = f"Persona {active_persona}" if active_persona else "All personas"
    emotion_ctx = f"Emotion {active_emotion} ({EMOTION_LABELS[active_emotion]})" if active_emotion else "No emotion filter"
    
    return f"""You are an AI assistant embedded in a decision intelligence tool.

SCENARIO: {scenario_data['title']}
DATE: {scenario_data['date']}
CLAIM: {scenario_data['claim']}
AGREED: {scenario_data['agreed']}
DISPUTED: {scenario_data['disputed']}
DECISION WINDOW: {scenario_data['window']}

MATRIX STRUCTURE:
- 4×4 weight table per persona: rows = emotions (A/B/C/D), columns = perspectives (sched/fin/people/comm)
- Each row sums to 100. Weights determine how much each perspective drives the decision.
- ⚑ = hard priority KPI: if red, overrides emotion weights.

EMOTIONS: A=Cautious, B=Strategic, C=Diplomatic, D=Decisive
PERSPECTIVES: sched=Schedule/Delivery, fin=Financial, people=People/Political, comm=Commercial/Strategic

OPTION SCORES:
{option_lines}

SCORING FORMULA:
weighted_score(persona, emotion, option) = sum(option_score[p] × persona_weight[emotion][p] / 100 for p in perspectives)

PERSONA DATA:
{persona_summaries}

RULES:
1. Answer questions about personas, KPIs, weights, and option recommendations.
2. For scoring questions: calculate and show the weighted scores for all options, declare winner.
3. Map every answer to matrix cells. State which KPI codes and personas are involved.
4. If vague: (a) state what you understood, (b) state what is unclear, (c) offer 2–3 specific answerable questions.
5. If out of scope: say so clearly and suggest the most relevant in-scope question.
6. Always end your response with a matrix instruction block:

```matrix
{{"persona": "<P1..P10|ALL|null>", "kpis": ["K1"], "emotion": "<A|B|C|D|null>", "persp": "<sched|fin|people|comm|null>"}}
```

ACTIVE CONTEXT: {active_ctx}. {emotion_ctx}."""
```

---

## 10. Question classification reference

Use this table to understand how different question types map to matrix instruction outputs. This helps when testing the system.

| Question type | Example | Expected instruction |
|---|---|---|
| Persona + emotion + option | "What does Rajesh do as Decisive?" | `{"persona":"P1", "kpis":["K1","K3"], "emotion":"D", "persp":null}` |
| Persona + KPI | "What is P4's grant risk?" | `{"persona":"P4", "kpis":["K8"], "emotion":null, "persp":null}` |
| Perspective only | "Which personas are most financially exposed?" | `{"persona":"ALL", "kpis":[], "emotion":null, "persp":"fin"}` |
| Emotion only | "How does Diplomatic mode change the answer?" | `{"persona":null, "kpis":[], "emotion":"C", "persp":null}` |
| Cross-persona | "Which personas face a red KPI?" | `{"persona":"ALL", "kpis":["K1","K3","K4"], "emotion":null, "persp":null}` |
| Vague | "What about the money?" | `{"persona":null, "kpis":[], "emotion":null, "persp":null}` |
| Out of scope | "What is the weather in Port Talbot?" | `{"persona":null, "kpis":[], "emotion":null, "persp":null}` |
| Scoring calculation | "Score all options for P3 Strategic" | `{"persona":"P3", "kpis":[], "emotion":"B", "persp":null}` |
| Hard priority | "Which KPIs can't be overridden?" | `{"persona":"ALL", "kpis":["K1","K3","K4","K1","K8"], "emotion":null, "persp":null}` |

---

## 11. Error handling

| Error | Cause | Handling |
|---|---|---|
| No `matrix` block in response | Model skipped the instruction | Return null instruction; log warning; do not change highlight state |
| Invalid JSON in matrix block | Model malformed the JSON | Catch parse exception; return null instruction; display answer without matrix update |
| Unknown persona in instruction | Model hallucinated a persona ID | Fail the persona field to null; still apply KPI and emotion highlights |
| API timeout | Network or rate limit | Show typing indicator for max 15s; then show "Connection error" message in chat; do not corrupt history |
| Empty question | User submitted blank input | Do not send API call; show inline validation message |
| Question too long (>2000 chars) | Paste error | Trim to 2000 chars; show truncation notice |

---

## 12. What makes the system different from keyword search

This is important context for any developer integrating this logic.

**Keyword search** would match "grant" → highlight K3 for P1 and K1 for P4 and K8 for P4, because those KPIs mention "grant" in their name. It would have no understanding of whether the question is about the *risk* of the grant condition or the *drawdown schedule* or the *clawback mechanism*.

**This system** passes the full question to Claude with complete scenario context. Claude reads the question semantically, resolves the intent, calculates weighted scores if required, and returns both a human-readable answer and a structured instruction. The instruction is derived from Claude's understanding — not from keyword matching. So "which option is safest for Sian?" correctly surfaces Option A vs Option B vs Option C for P4 in the current emotional state, with the financial column highlighted, because Claude knows Sian is the CFO, knows what "safest" means for a CFO in this context (contingency preservation, grant covenant protection), calculates the scores, and maps the result to the right matrix cells.

The keyword system would not be able to answer that question at all.

---

## 13. Testing checklist

Before integrating into production, verify each of these:

- [ ] Persona + emotion query returns correct weighted score for all three options
- [ ] Hard-priority red KPI is surfaced in answer even when emotion weights de-prioritise it
- [ ] Vague question returns null matrix instruction and 2–3 clarifying suggestions
- [ ] Out-of-context question returns null instruction and suggests one in-scope question
- [ ] Cross-persona question uses `"persona":"ALL"` and highlights KPIs across all rendered personas
- [ ] Conversation follow-up ("now change it to Strategic") resolves correctly using history
- [ ] Switching persona via sidebar does not reset conversation history
- [ ] Matrix block is stripped from displayed answer text before rendering
- [ ] Invalid JSON in matrix block does not crash the application
- [ ] Empty question input is blocked before API call
- [ ] `cell-active`, `row-active`, `col-active` all render as visually distinct states
- [ ] KPI tile `note` text is only expanded when the tile is highlighted
- [ ] Sidebar persona button updates to `active` state when instruction specifies a persona

---

*Port Talbot EAF Transformation · AI Matrix Logic Specification · v1.0 · install into decision_engine.py + server.py*
