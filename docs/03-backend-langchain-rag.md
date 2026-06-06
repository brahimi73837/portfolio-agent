# 03 — Backend: the LangChain RAG chain

This chapter is the heart of the system: how a question becomes a grounded answer.

## The pieces

| File | Job |
|---|---|
| [`app/config.py`](../backend/app/config.py) | All settings from env (one place for every knob) |
| [`app/retriever.py`](../backend/app/retriever.py) | Load FAISS, embed a query, fetch top-k chunks |
| [`app/prompts.py`](../backend/app/prompts.py) | The system prompt (brand + safety) and canned replies |
| [`app/chain.py`](../backend/app/chain.py) | The LangChain LCEL chain → Gemini |
| [`app/main.py`](../backend/app/main.py) | FastAPI routes + the request pipeline |

## Retrieval (RAG, part 2)

`KnowledgeRetriever` wraps the FAISS store and exposes three methods:

```python
retriever.embed_query(text)            # text -> 768-dim vector (Vertex AI)
retriever.search_by_vector(vector, k)  # vector -> top-k Documents
retriever.format_context(docs)         # Documents -> one context string
```

**Key trick:** we embed the query **once** and reuse that vector for *both* the semantic cache lookup and
the FAISS search. Embeddings are cheap, but "compute once, use twice" is free and clean.

For follow-up questions ("tell me more about that"), we prepend the previous user turn before embedding so
retrieval still finds the right chunks (`_retrieval_query` in `main.py`).

## The chain (LCEL)

LangChain's LCEL (LangChain Expression Language) lets us compose steps with `|`. Our chain in
[`app/chain.py`](../backend/app/chain.py) is deliberately small:

```python
messages = _build_messages(context, history, question)  # system+context, prior turns, question
chain = get_llm() | StrOutputParser()                    # model -> plain string
return chain.invoke(messages).strip()
```

`_build_messages` assembles:

1. **SystemMessage** = the strict system prompt **+ the retrieved CONTEXT** between clear delimiters.
2. The last few **Human/AI** turns (short-term memory).
3. The new **HumanMessage** (the question).

## The model

`ChatVertexAI(model="gemini-2.5-flash", temperature=0.3, max_output_tokens=512, thinking_budget=0)`.

- **Vertex AI** → authenticated via the service account / your ADC, billed to credits. No API key string.
- **`thinking_budget=0`** → Gemini 2.5 Flash can "think" before answering, which spends extra tokens and
  time. For short, grounded RAG answers we don't need it, so we turn it off for speed + cost. (The code
  degrades gracefully if your library version doesn't support the parameter.)
- **`max_output_tokens=512`** → a hard cap so no single answer runs away.

## Why grounding works

The system prompt orders the model to answer **only** from CONTEXT and to refuse when the answer isn't
there. Because we feed real retrieved facts, the model has what it needs for legit questions and
visibly *lacks* what it needs for made-up ones — so it declines instead of hallucinating.

Try it:

```bash
curl -s localhost:8000/chat -H 'content-type: application/json' \
  -d '{"message":"What has Brahim built?"}' | python3 -m json.tool
```

Next: [04 — Caching & guardrails](04-caching-and-guardrails.md).
