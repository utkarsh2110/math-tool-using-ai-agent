# Copy for resume, GitHub, and LinkedIn

*(This file is for your own use — delete it before pushing, or keep it, it does no harm.)*

---

## GitHub repo "About" description (350 char limit)

> LLM agent built from scratch — no framework. Autonomously routes between SymPy symbolic math and web search via function calling, with a bounded execution loop, error containment, and a visible tool trace.

**Topics/tags to add:** `llm` `ai-agents` `function-calling` `gemini-api` `tool-use` `sympy` `gradio` `python`

---

## Resume bullets

Pick 2–3. The first one should always be included.

**Version A — architecture-focused (recommended)**

- Built a tool-using LLM agent from scratch without an agent framework, implementing the full reason–act loop: structured function-call parsing, application-side conversation state, and a name-based tool dispatcher that scales to N tools without loop changes.
- Integrated SymPy (7 symbolic operations) and web search as callable tools; tool selection is performed entirely by the model from JSON Schema descriptions, with no hard-coded routing logic.
- Hardened the loop for production failure modes: bounded step count to prevent runaway tool cycles, tool-error containment that returns failures to the model for self-correction, and retry-with-backoff on rate-limited requests.

**Version B — shorter, two-bullet**

- Built a framework-free LLM agent implementing the reason–act loop with function calling, routing autonomously between SymPy symbolic math and web search; deployed with a Gradio interface exposing the agent's tool-call trace.
- Addressed core agent failure modes — unbounded loops, tool exceptions, rate limits, and declaration/implementation drift — and documented context-growth and error-compounding limits at scale.

**Version C — one-liner, if space is tight**

- Tool-using LLM agent built from scratch (no LangChain): function-calling loop with SymPy and web-search tools, model-driven routing, bounded execution, and error containment. [GitHub]

---

## LinkedIn post (if you want one)

> Spent the last few days building an AI agent from scratch — deliberately without LangChain, because I wanted to understand what these frameworks are actually abstracting.
>
> The answer, it turns out, is a while loop.
>
> An LLM can't *do* anything. It's stateless and it only outputs text. What makes it an "agent" is that you hand it descriptions of tools, it emits a structured request for one, your code executes it, and you feed the result back — repeat until it stops asking. The model decides; the code executes; the loop provides persistence.
>
> Mine routes between SymPy (derivatives, integrals, equation solving) and web search, and it picks between them entirely on its own — there's no keyword matching anywhere in my code, just two well-written tool descriptions.
>
> The interesting part wasn't the happy path. It was everything around it: bounding the loop so a failing tool can't cycle forever, returning tool errors *to the model* so it can self-correct instead of crashing, and a silent bug where my tool declaration promised seven operations while the implementation supported two.
>
> Code + writeup: [link]

---

## The 90-second verbal explanation

Practise this until it's fluent. It is the single highest-leverage thing for interviews.

> "An LLM is stateless and can't execute anything — it only produces text. So I give it tool declarations in JSON Schema, and instead of answering it can emit a structured request naming a tool and its arguments.
>
> My application is the runtime. It parses that request, looks the function up in a dispatcher dictionary, executes it, and appends *both the request and the result* to the conversation history. Then it re-sends the entire history, because the model remembers nothing between calls.
>
> The model then either answers or requests another tool. That loop is the agent — one tool-using turn produces four messages: user, model request, tool result, model answer.
>
> I have two tools: SymPy for symbolic math and DuckDuckGo for current facts. The routing between them is done entirely by the model reading their descriptions — there's no routing logic in my code at all, which makes description quality the main engineering lever.
>
> The interesting work was the failure modes: bounding the loop so a repeatedly-failing tool can't cycle forever, catching tool exceptions and returning them to the model as text so it can self-correct, and retry-with-backoff on rate limits — since one user question costs several API calls, not one."

---

## Questions you should expect, and where the answers live

| Question | Covered in |
|---|---|
| "Walk me through the architecture." | The 90-second explanation above |
| "Where does the intelligence actually live?" | README → How it works (last paragraph) |
| "How does it choose between two tools?" | README → Tools (description-driven routing) |
| "What happens if a tool throws?" | README → Engineering notes (error containment) |
| "What stops it looping forever?" | README → Engineering notes (bounded execution) |
| "Why is this stateless thing a problem?" | README → Engineering notes (statelessness) |
| "What breaks on a 200-step task?" | README → Known limitations (context, error compounding) |
| "What are the security risks?" | README → Known limitations (untrusted tool arguments) |
| "What would you do differently?" | Multi-turn memory; a callback-based loop instead of the duplicated UI function; schema generated from the function signature to prevent drift |
