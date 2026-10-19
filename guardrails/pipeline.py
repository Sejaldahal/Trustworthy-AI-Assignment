"""Guardrail orchestration: INPUT guards -> LLM -> OUTPUT guards (with regenerate / fallback)."""
import json
import re
from dataclasses import dataclass, field
from . import input_guards as ig
from . import output_guards as og

FALLBACK = "Sorry, I couldn't produce a reliable answer. Please contact admissions@kss.edu."

KNOWLEDGE_BASE = [
    "The application deadline for fall admission is March 15. Late applications are not accepted.",
    "Undergraduate tuition is $12,000 per year. The application fee is $50 and is non-refundable.",
    "On-campus housing is guaranteed for first-year students. Housing applications open on April 1.",
    "Admission requires a minimum GPA of 3.0 and two letters of recommendation.",
    "Contact admissions at admissions@kss.edu or +977-1-5551234.",
]


def mock_llm(question: str, references: list, attempt: int = 0) -> str:
    """Deterministic stand-in for a real LLM: answers from the best-matching reference.
    Replace with a real API call returning the same JSON schema."""
    q = og._tokens(question)
    best = max(references, key=lambda r: len(q & og._tokens(r)), default="")
    cat = "tuition" if "tuition" in best else "housing" if "housing" in best else "admissions"
    return json.dumps({"answer": best, "confidence": 0.8, "sources": [best[:40]], "category": cat})


@dataclass
class Result:
    status: str                      # ok | blocked | support | disclaimer | fallback
    answer: str
    flags: list = field(default_factory=list)
    trace: list = field(default_factory=list)


class GuardedApp:
    def __init__(self, llm=mock_llm, references=None, max_regen=1):
        self.llm, self.refs, self.max_regen = llm, references or KNOWLEDGE_BASE, max_regen

    # ---- input stage
    def check_input(self, text):
        inj, score = ig.detect_injection(text)
        if inj:
            return "blocked", "Request refused: it appears to try to override my instructions.", ["injection"], text
        topic = ig.classify_topic(text)
        if topic:
            pol = ig.TOPIC_POLICIES[topic]
            if pol.action in ("block", "support", "disclaimer"):
                return pol.action, pol.message, [f"topic:{topic}"], text
        clean, kinds = ig.redact_pii(text)
        return "ok", "", [f"pii:{k}" for k in kinds], clean

    # ---- output stage
    def check_output(self, raw):
        """Return (action, final_text, flags). action: pass | redact | invalid"""
        ok, errs, obj = og.validate_schema(raw)
        if not ok:
            return "invalid", "", [f"schema:{e}" for e in errs]
        gok, bad, _ = og.check_groundedness(obj["answer"], self.refs)
        if not gok:
            return "invalid", "", [f"ungrounded:{s}" for s in bad]
        sens = og.detect_sensitive_output(obj["answer"])
        if sens:
            if any(s in ("API_KEY", "SYSTEM_PROMPT_LEAK", "INTERNAL_HOST") for s in sens):
                return "invalid", "", [f"sensitive:{s}" for s in sens]  # secrets: never redact-and-send
            txt = obj["answer"]
            for kind, s, e in reversed(ig.detect_pii(txt)):
                if txt[s:e] not in og.ALLOWED_PII:
                    txt = txt[:s] + f"[{kind}]" + txt[e:]
            return "redact", txt, [f"sensitive:{s}" for s in sens]
        return "pass", obj["answer"], []

    def ask(self, text) -> Result:
        status, msg, flags, clean = self.check_input(text)
        trace = [f"input:{status}"]
        if status != "ok":
            return Result(status, msg, flags, trace)
        for attempt in range(self.max_regen + 1):
            raw = self.llm(clean, self.refs, attempt)
            action, out, oflags = self.check_output(raw)
            trace.append(f"output[{attempt}]:{action}")
            flags += oflags
            if action in ("pass", "redact"):
                return Result("ok", out, flags, trace)
        return Result("fallback", FALLBACK, flags, trace)
