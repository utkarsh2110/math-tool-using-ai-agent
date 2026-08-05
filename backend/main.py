import os, time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from google import genai
from google.genai import types
from google.genai import errors
from ddgs import DDGS
from sympy import *

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL = "gemini-3.5-flash"

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


SYSTEM_PROMPT = (
    "You are a helpful assistant with math and search tools. "
    "When your answer contains mathematical expressions, wrap them in LaTeX "
    "delimiters: $...$ for inline math and $$...$$ for display math. "
    "For example, write the derivative as $3x^2 + 2$, not as 3*x**2 + 2."
)

def call_model(history):
    for attempt in range(3):
        try:
            return client.models.generate_content(
                model=MODEL,
                contents=history,
                config=types.GenerateContentConfig(
                    tools=ALL_TOOLS,
                    system_instruction=SYSTEM_PROMPT
                )
            )
        except errors.ClientError as e:
            if "429" in str(e):
                time.sleep(15)
            else:
                raise
    raise Exception("Rate limited — free-tier quota exhausted. Try again shortly.")


def run_agent(question, max_steps=10):
    trace = []
    history = [{"role": "user", "parts": [{"text": question}]}]

    for step in range(max_steps):
        response = call_model(history)

        if not response.function_calls:
            return response.text, trace

        history.append(response.candidates[0].content)

        for fc in response.function_calls:
            try:
                result = TOOLS[fc.name](**fc.args)
            except Exception as e:
                result = f"Error: {e}"

            trace.append({
                "tool": fc.name,
                "args": dict(fc.args),
                "result": str(result)[:500]
            })

            history.append(types.Content(
                role="tool",
                parts=[types.Part.from_function_response(
                    name=fc.name, response={"result": result})]
            ))

    return "Stopped: hit the step limit.", trace


app = FastAPI(title="Tool-Using AI Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


class Question(BaseModel):
    question: str


@app.get("/")
def health():
    return {"status": "ok", "tools": list(TOOLS.keys())}


@app.post("/ask")
def ask(payload: Question):
    if not payload.question.strip():
        return {"answer": "Please ask something.", "trace": []}
    try:
        answer, trace = run_agent(payload.question)
        return {"answer": answer, "trace": trace}
    except Exception as e:
        return {"answer": f"Something went wrong: {e}", "trace": []}
