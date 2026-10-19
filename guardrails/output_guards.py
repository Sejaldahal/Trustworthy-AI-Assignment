"""Output guardrails: schema validation, groundedness validation, sensitive-info detection."""
import json
import re
from .input_guards import detect_pii, redact_pii

CATEGORIES = {"admissions", "tuition", "housing", "academics", "other"}
SCHEMA = {  # field -> (type, validator)
    "answer": (str, lambda v: 1 <= len(v) <= 1200),
    "confidence": ((int, float), lambda v: 0.0 <= v <= 1.0),
    "sources": (list, lambda v: all(isinstance(s, str) for s in v)),
    "category": (str, lambda v: v in CATEGORIES),
}


def validate_schema(raw: str):
    """Return (ok, errors, parsed)."""
    try:
        obj = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return False, ["not valid JSON"], None
    if not isinstance(obj, dict):
        return False, ["top level must be an object"], None
    errs = []
    for f, (typ, check) in SCHEMA.items():
        if f not in obj:
            errs.append(f"missing field '{f}'")
        elif isinstance(obj[f], bool) or not isinstance(obj[f], typ):
            errs.append(f"field '{f}' has wrong type")
        elif not check(obj[f]):
            errs.append(f"field '{f}' has invalid value")
    errs += [f"unexpected field '{k}'" for k in obj if k not in SCHEMA]
    return not errs, errs, obj


# ---- groundedness (lexical-overlap + numeric check; no model needed)
STOP = set("a an the is are was were be been of to in on for and or with at by from as that this it its you your we our will can may has have had not no do does".split())


def _tokens(text):
    return {w[:-1] if w.endswith("s") and len(w) > 3 else w for w in re.findall(r"[a-z0-9$%.,]+", text.lower())
            for w in [w.strip(".,")] if w and w not in STOP}


def _numbers(text):
    return set(re.findall(r"\d[\d,]*(?:\.\d+)?", text))


_NEG = {"not", "no", "non", "never", "cannot", "without"}


def _stem(w):
    return w[:-1] if w.endswith("s") and len(w) > 3 else w


def _negated(text):
    """Content words directly governed by a negator ("non-refundable", "not accepted")."""
    words = re.findall(r"[a-z0-9$]+", text.lower().replace("n't", ""))
    out = set()
    for i, w in enumerate(words):
        if w in _NEG:
            for nxt in words[i + 1:i + 4]:
                if nxt not in STOP and nxt not in _NEG:
                    out.add(_stem(nxt))
                    break
    return out


def _contradicts(claim, references):
    """True if a reference sentence shares words with the claim but negates one of them in only one side."""
    cn, ct = _negated(claim), {_stem(w) for w in re.findall(r"[a-z0-9$]+", claim.lower())}
    for ref in references:
        for rs in re.split(r"(?<=[.!?])\s+", ref):
            rn = _negated(rs)
            rt = {_stem(w) for w in re.findall(r"[a-z0-9$]+", rs.lower())}
            if len((ct & rt) - STOP) >= 2 and (((rn & ct) - cn) or ((cn & rt) - rn)):
                return True
    return False


def check_groundedness(answer: str, references: list, min_support=0.7):
    """Split into claim sentences; each must be supported by the references.
    Returns (ok, unsupported_sentences, per-claim scores)."""
    ref_text = " ".join(references)
    ref_tok, ref_num = _tokens(ref_text), {n.replace(",", "") for n in _numbers(ref_text)}
    bad, scores = [], []
    for sent in re.split(r"(?<=[.!?])\s+", answer.strip()):
        tok = _tokens(sent)
        if len(tok) < 3:
            continue  # greeting / filler, not a claim
        support = len(tok & ref_tok) / len(tok)
        nums_ok = {n.replace(",", "") for n in _numbers(sent)} <= ref_num
        scores.append(round(support, 2))
        if support < min_support or not nums_ok or _contradicts(sent, references):
            bad.append(sent)
    return not bad, bad, scores


# ---- sensitive information in outputs
SECRET_PATTERNS = {
    "API_KEY": re.compile(r"\b(sk|pk|api)[-_][A-Za-z0-9_-]{12,}\b"),
    "SYSTEM_PROMPT_LEAK": re.compile(r"\b(my system prompt|my instructions are|you are a helpful .{0,40} assistant for)\b", re.I),
    "INTERNAL_HOST": re.compile(r"\b(?:10|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}(?:\.\d{1,3})?\b"),
}
# contacts the assistant is *allowed* to publish
ALLOWED_PII = {"admissions@kss.edu", "counselling@kss.edu", "health@kss.edu", "+977-1-5551234"}


def detect_sensitive_output(text: str):
    """Return (findings, redacted_text). Allowlisted public contacts are not flagged."""
    findings = []
    for kind, s, e in detect_pii(text):
        if text[s:e] not in ALLOWED_PII:
            findings.append(kind)
    for kind, pat in SECRET_PATTERNS.items():
        if pat.search(text):
            findings.append(kind)
    return findings
