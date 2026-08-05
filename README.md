# Tool-Using AI Agent

An LLM agent that autonomously decides whether to solve symbolic mathematics, search the web, or answer directly — built from scratch in ~150 lines, without any agent framework (no LangChain, no LlamaIndex).

The goal of this project was to understand agent architecture from first principles rather than through a framework abstraction.

[![demo](demo.png)](https://math-tool-using-ai-agent.onrender.com)

---

## What it does

Ask it anything. The model reads the available tool descriptions and decides on its own what to do:

| Question | What the agent does |
|---|---|
| `What is the capital of France?` | Answers directly — no tool needed |
| `Integrate x**2 * sin(x) with respect to x` | Calls `math_solver` with SymPy |
| `What's the latest news about ISRO?` | Calls `web_search` |
| `What is India's population multiplied by 3?` | Chains both — searches for the figure, then computes |

The UI exposes a **tool trace** showing exactly which tools fired, with what arguments, and what they returned — the agent's reasoning is visible rather than hidden.

---

## How it works

An LLM is stateless and cannot execute anything. It only produces text. When given tool descriptions, it can produce a *structured request* — "call `math_solver` with `{operation: integrate, expression: x**2}`" — and then it stops and waits.

This application is the runtime that turns those requests into real actions:

```
1. Send the full conversation history + tool declarations to the model
2. FORK: did the model return a tool request, or plain text?
       plain text  → done, return the answer
       tool request → continue
3. Append the model's request to the history
4. Execute the requested function; append the result to the history
5. Loop back to step 1 with the enriched history
```

A single tool-using turn therefore produces a four-message exchange:

```
user   →  "What is 45678 * 12345?"
model  →  [request: math_solver(operation="evaluate", expression="45678*12345")]
tool   →  "563,793,510"
model  →  "The answer is 563,793,510."
```

**The model decides; the code executes; the loop provides persistence.** The intelligence lives in the model's tool-selection and argument-formatting decisions. The loop itself is trivial — and that is the point.

---

## Architecture

```
                      ┌─────────────────┐
   question ────────► │   Agent loop    │ ◄──── history (grows each turn)
                      └────────┬────────┘
                               │  full history + tool declarations
                               ▼
                      ┌─────────────────┐
                      │  Gemini Flash   │  decides: answer, or request a tool?
                      └────────┬────────┘
                               │  structured tool request
                               ▼
                      ┌─────────────────┐
                      │   Dispatcher    │  TOOLS[name](**args)
                      └───┬─────────┬───┘
                          ▼         ▼
                   math_solver   web_search
                     (SymPy)     (DuckDuckGo)
```

### Tools

| Tool | Capabilities |
|---|---|
| `math_solver` | SymPy-backed: `evaluate`, `differentiate`, `integrate`, `solve`, `simplify`, `expand`, `factor` |
| `web_search` | DuckDuckGo text search, top 3 results |

Each tool is two separate artifacts: a **JSON Schema declaration** (the only thing the model ever sees) and a **Python implementation** (what actually runs). They are linked solely by name.

**Tool selection is performed entirely by the model, from the natural-language descriptions.** There is no keyword matching, routing table, or `if/else` dispatch logic in the codebase. This makes description quality the primary engineering lever: a vague description produces unreliable routing.

---

## Engineering notes

**Statelessness.** The LLM API retains nothing between calls. Conversation state is maintained application-side as a list and re-sent in full on every request. This is why cost and latency grow with conversation length — the entire history is reprocessed each turn.

**Request/result pairing.** The model's tool request *and* the tool's result must both be appended to the history. Appending only the result produces a malformed exchange in which a value appears with no record of it having been requested.

**Dispatcher pattern.** Tools are registered in a dictionary (`{name: function}`) and invoked via `TOOLS[fc.name](**fc.args)`. Adding a tool requires a declaration, a function, and a dictionary entry — no change to the agent loop.

**Bounded execution.** The loop is capped at a fixed step count rather than `while True`. Without this, a model that repeatedly requests a failing tool will loop indefinitely, consuming quota.

**Error containment.** Tool exceptions are caught and returned to the model *as text* rather than propagating. This lets the model observe the failure and adapt (e.g. correcting a malformed expression) instead of crashing the run.

**Rate-limit handling.** Free-tier quotas are hit easily because a single user question consumes multiple API requests — one per reasoning turn, not one per question. The client retries with backoff on HTTP 429.

**Declaration/implementation drift.** An early bug: the declaration advertised seven operations while the function implemented two. Because tool errors are caught, this failed *silently* — the model kept receiving `Error: unsupported operation`. Declaration and implementation are two artifacts with nothing keeping them in sync; this is a recurring failure mode in tool-based systems.

**Secrets.** The API key is injected at runtime via an environment variable and is never committed to source.

---

## Known limitations

- **Single-turn.** Each question starts a fresh history, so follow-ups like *"now differentiate that"* are not supported. Multi-turn would require persisting history across requests.
- **Context growth.** History grows monotonically within a run. Long tasks would eventually exceed the context window; mitigation would require summarising older turns or offloading state to external notes.
- **Error compounding.** Reliability degrades multiplicatively with step count — at 95% per-step success, a 20-step task succeeds ~36% of the time. Long-horizon tasks need checkpointing and verification.
- **Untrusted tool arguments.** Tool arguments originate from model output, which is influenced by user input and (via `web_search`) by arbitrary internet text. Model output should be treated as untrusted input; SymPy's `sympify` was chosen over `eval()` for exactly this reason.

---

## Running locally

```bash
git clone https://github.com/utkarsh2110/tool-using-ai-agent.git
cd tool-using-ai-agent
pip install -r requirements.txt

export GEMINI_API_KEY=your_key_here   # get one free at aistudio.google.com
python app.py
```

Then open the local URL Gradio prints.

---

## Stack

Python · Google Gemini API (function calling) · SymPy · DuckDuckGo Search · Gradio

## License

MIT
