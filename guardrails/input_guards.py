"""Input guardrails: PII detection, prompt-injection detection, sensitive-topic classification."""
import re
import unicodedata
from dataclasses import dataclass

# ---------------------------------------------------------------- PII
PII_PATTERNS = {
    "EMAIL": re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b"),
    "SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "CREDIT_CARD": re.compile(r"\b(?:\d[ -]?){13,16}\b"),
    "PHONE": re.compile(r"(?<!\d)(?:\+?\d{1,3}[ -]?)?(?:\(\d{3}\)|\d{3})[ -]?\d{3}[ -]?\d{4}(?!\d)"),
    "NATIONAL_ID": re.compile(r"\b(?:NID|ID|passport)[ #:]*[A-Z0-9]{7,12}\b", re.I),
}


def _luhn(num: str) -> bool:
    d = [int(c) for c in re.sub(r"\D", "", num)][::-1]
    if not 13 <= len(d) <= 16:
        return False
    s = sum(x if i % 2 == 0 else (x * 2 - 9 if x * 2 > 9 else x * 2) for i, x in enumerate(d))
    return s % 10 == 0


def detect_pii(text: str):
    """Return list of (type, start, end). Credit cards must pass Luhn to cut false positives."""
    found, taken = [], []
    for kind, pat in PII_PATTERNS.items():
        for m in pat.finditer(text):
            if kind == "CREDIT_CARD" and not _luhn(m.group()):
                continue
            if any(m.start() < e and s < m.end() for s, e in taken):
                continue  # overlapping with a higher-priority match
            taken.append((m.start(), m.end()))
            found.append((kind, m.start(), m.end()))
    return sorted(found, key=lambda x: x[1])


def redact_pii(text: str):
    spans = detect_pii(text)
    for kind, s, e in reversed(spans):
        text = text[:s] + f"[{kind}]" + text[e:]
    return text, [k for k, _, _ in spans]


# ---------------------------------------------------------------- Prompt injection
# (regex, weight). Score >= THRESHOLD => flagged.
INJECTION_RULES = [
    (r"\b(ignore|disregard|forget|override)\b.{0,30}\b(previous|prior|above|earlier|all|your)\b.{0,20}\b(instructions?|rules?|prompts?|guidelines?)", 1.0),
    (r"\b(reveal|show|print|repeat|output|leak)\b.{0,30}\b(system prompt|hidden prompt|initial instructions|your instructions|api key|secret|password)", 1.0),
    (r"\byou are now\b|\bpretend (to be|you are)\b|\bact as (an? )?(unrestricted|unfiltered|dan)\b", 0.7),
    (r"\b(jailbreak|DAN mode|developer mode|no restrictions|without (any )?(restrictions|filters|rules))\b", 0.8),
    (r"\bdo anything now\b", 0.8),
    (r"(^|\n)\s*(system|assistant)\s*:", 0.6),
    (r"</?(system|instructions?)>|\[/?INST\]", 0.7),
    (r"\bbypass\b.{0,20}\b(safety|filter|guardrail|restriction|policy)", 0.9),
    (r"\bnew instructions?\b\s*:", 0.6),
]
INJECTION_THRESHOLD = 0.7
_ZW = dict.fromkeys(map(ord, "​‌‍⁠﻿"), None)


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).translate(_ZW)
    return re.sub(r"[ \t]+", " ", text)


def detect_injection(text: str):
    t = normalize(text)
    hits = [(p, w) for p, w in INJECTION_RULES if re.search(p, t, re.I | re.S)]
    score = min(1.0, sum(w for _, w in hits))
    return score >= INJECTION_THRESHOLD, score


# ---------------------------------------------------------------- Sensitive topics
@dataclass
class TopicPolicy:
    action: str   # block | support | disclaimer
    message: str

TOPIC_PATTERNS = {
    "self_harm": r"\b(kill myself|suicide|end my life|self[- ]harm|hurt myself|don'?t want to live)\b",
    "violence_weapons": r"\b(build|make|construct)\b.{0,20}\b(bomb|explosive|weapon)\b|\bhow to (poison|stalk|hurt) (someone|a person|people)\b",
    "medical": r"\b(diagnos\w+|prescri\w+|medication|dosage|symptoms? of|chest pain)\b",
    "legal": r"\b(sue|lawsuit|legal advice|immigration (law|status)|visa denial appeal)\b",
    "financial_advice": r"\b(invest|stock tips?|crypto|loan advice|which stocks?)\b",
}
TOPIC_POLICIES = {
    "self_harm": TopicPolicy("support", "I'm really sorry you're feeling this way. You're not alone - please contact a local crisis line or emergency services right now. University counselling: counselling@kss.edu."),
    "violence_weapons": TopicPolicy("block", "I can't help with that request."),
    "medical": TopicPolicy("disclaimer", "I can't give medical advice. Please consult a licensed professional. (Campus health centre: health@kss.edu.)"),
    "legal": TopicPolicy("disclaimer", "I can't give legal advice. Please consult a qualified lawyer or the international student office."),
    "financial_advice": TopicPolicy("disclaimer", "I can't give investment advice. For tuition payment or aid questions, ask me about those."),
}


def classify_topic(text: str):
    """Return the highest-severity matching topic or None."""
    t = normalize(text).lower()
    for topic in TOPIC_PATTERNS:  # dict order = severity order
        if re.search(TOPIC_PATTERNS[topic], t, re.S):
            return topic
    return None
