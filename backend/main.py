
import os, time
from google import genai
from google.genai import types
from google.genai import errors
from ddgs import DDGS
from sympy import *
import gradio as gr

# Key comes from Hugging Face Spaces secrets
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL = "gemini-3.5-flash"

# ============ TOOL DECLARATIONS (what the model reads) ============

math_solver_tool = types.Tool(function_declarations=[{
    "name": "math_solver",
    "description": "Symbolic and numeric math via SymPy. Use for arithmetic, "
                   "derivatives, integrals, solving equations, simplification, "
                   "expansion, and factoring. Always use this instead of "
                   "calculating mentally.",
    "parameters": {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["evaluate", "differentiate", "integrate", "solve",
                         "simplify", "expand", "factor"]
            },
            "expression": {"type": "string"},
            "variable": {"type": "string"}
        },
        "required": ["operation", "expression"]
    }
}])

search_tool = types.Tool(function_declarations=[{
    "name": "web_search",
    "description": "Searches the internet for current facts, news, statistics, "
                   "or recent events. Use when you need up-to-date information "
                   "you don't already know.",
    "parameters": {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"]
    }
}])

# ============ TOOL IMPLEMENTATIONS (what the code runs) ============

def math_solver(operation, expression, variable=None):
    try:
        expr = sympify(expression)
        if variable:
            var = Symbol(variable)

        if operation == "evaluate":
            return str(expr.evalf())
        elif operation == "differentiate":
            if not variable:
                return "Error: Variable is required for differentiation."
            return str(diff(expr, var))
        elif operation == "integrate":
            if not variable:
                return "Error: Variable is required for integration."
            return str(integrate(expr, var))
        elif operation == "solve":
            return str(solve(expr, var)) if variable else str(solve(expr))
        elif operation == "simplify":
            return str(simplify(expr))
        elif operation == "expand":
            return str(expand(expr))
        elif operation == "factor":
            return str(factor(expr))
        else:
            return f"Error: Unsupported operation '{operation}'."
    except Exception as e:
        return f"Error: {e}"

def web_search(query):
    try:
        results = DDGS().text(query, max_results=3)
        return "\n".join(f"{r['title']}: {r['body']}" for r in results)
    except Exception as e:
        return f"Search failed: {e}"

TOOLS = {"math_solver": math_solver, "web_search": web_search}
ALL_TOOLS = [math_solver_tool, search_tool]

# ============ API CALL with retry on rate limits ============

def call_model(history):
    for attempt in range(3):
        try:
            return client.models.generate_content(
                model=MODEL,
                contents=history,
                config=types.GenerateContentConfig(tools=ALL_TOOLS)
            )
        except errors.ClientError as e:
            if "429" in str(e):
                time.sleep(20)
            else:
                raise
    raise Exception("Rate limited — the free-tier quota is exhausted. Try again shortly.")

# ============ THE AGENT ============

def agent_ui(question, max_steps=10):
    if not question.strip():
        return "Ask me something!", ""

    logs = []
    history = [{"role": "user", "parts": [{"text": question}]}]

    try:
        for step in range(max_steps):
            response = call_model(history)                    # 1. read the model the slip

            if not response.function_calls:                   # 2. the fork
                return response.text, ("\n\n".join(logs) if logs
                                       else "No tools used — answered directly.")

            history.append(response.candidates[0].content)    # 3. save its request

            for fc in response.function_calls:                # 4. run each tool
                try:
                    result = TOOLS[fc.name](**fc.args)
                except Exception as e:
                    result = f"Error: {e}"
                logs.append(f"🔧 {fc.name}({dict(fc.args)})\n   → {str(result)[:300]}")

                history.append(types.Content(
                    role="tool",
                    parts=[types.Part.from_function_response(
                        name=fc.name, response={"result": result})]
                ))
            # 5. loop back with the longer slip

        return "Stopped: hit the step limit.", "\n\n".join(logs)

    except Exception as e:
        return f"Something went wrong: {e}", "\n\n".join(logs)

# ============ UI ============

with gr.Blocks(title="Tool-Using AI Agent") as demo:
    gr.Markdown(
        "## 🤖 Tool-Using AI Agent\n"
        "The model decides on its own whether to do symbolic math (SymPy), "
        "search the web, or answer directly. The trace shows exactly what it chose.\n\n"
        "*Running on a free API tier — you may occasionally hit rate limits.*"
    )

    inp = gr.Textbox(label="Your question",
                     placeholder="e.g. integrate x**2 * sin(x) with respect to x")
    btn = gr.Button("Ask", variant="primary")
    out = gr.Textbox(label="Answer", lines=4)
    trace = gr.Textbox(label="🔍 Tool trace", lines=8)

    btn.click(agent_ui, inputs=inp, outputs=[out, trace])
    inp.submit(agent_ui, inputs=inp, outputs=[out, trace])

    gr.Examples([
        "What is 45678 * 12345?",
        "Differentiate x**3 + 2*x with respect to x",
        "Integrate x**2 * sin(x) with respect to x",
        "Solve x**2 - 5*x + 6 = 0",
        "Factor x**2 - 9",
        "What's the latest news about ISRO?",
        "What is India's population multiplied by 3?",
    ], inputs=inp)

demo.launch()
