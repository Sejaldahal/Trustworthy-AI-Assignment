"""Optional real-LLM backend (Claude Messages API via urllib; no extra dependency).
Usage: ANTHROPIC_API_KEY=... python3 demo.py --real "When is the deadline?"
The model is told to answer ONLY from the references and return the JSON schema the output guards expect."""
import json
import os
import urllib.request

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5")
SYSTEM = ("You are a university admissions assistant. Answer ONLY from the reference passages. "
          'Reply with a single JSON object: {"answer": str, "confidence": number 0-1, "sources": [str], '
          '"category": one of admissions|tuition|housing|academics|other}. No text outside the JSON.')


def claude_llm(question, references, attempt=0):
    body = {"model": MODEL, "max_tokens": 500, "system": SYSTEM,
            "messages": [{"role": "user", "content": "References:\n- " + "\n- ".join(references) + f"\n\nQuestion: {question}"}]}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", json.dumps(body).encode(),
                                 {"content-type": "application/json", "anthropic-version": "2023-06-01",
                                  "x-api-key": os.environ["ANTHROPIC_API_KEY"]})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["content"][0]["text"]
