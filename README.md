# Input & Output Guardrails - University Admissions Assistant

Domain: a support chatbot answering admissions questions from a small knowledge base (`guardrails/pipeline.py`).
Pure Python 3.8+, **no dependencies**; the LLM is a deterministic mock so everything runs offline.

## Setup & run
```bash
python3 run_eval.py                    # runs all 56 cases, prints tables + metrics, writes RESULTS.md
python3 -m unittest tests.test_guardrails   # regression tests (known limitations are skipped)
```
```python
from guardrails import GuardedApp
app = GuardedApp()
r = app.ask("My email is x@y.com, when is the deadline?")
print(r.status, r.answer, r.flags, r.trace)   # ok ... ['pii:EMAIL'] ['input:ok','output[0]:pass']
```
To use a real LLM pass `GuardedApp(llm=fn)` where `fn(question, references, attempt) -> str` returns JSON
`{"answer","confidence","sources","category"}`.

## Layout
| File | Purpose |
|---|---|
| `guardrails/input_guards.py` | PII, injection, topic classification |
| `guardrails/output_guards.py` | schema, groundedness, sensitive-output |
| `guardrails/pipeline.py` | orchestration, mock LLM, KB, handling policy |
| `tests/cases.py` | 51 labelled guardrail cases (+5 end-to-end in `run_eval.py`) |
| `RESULTS.md` | generated: per-case input / expected / actual / pass-fail, metrics |
| `REPORT.md` | design, evaluation, failure analysis, trade-offs, risks |
| `ARCHITECTURE.md` | diagram (Mermaid) |

## Guardrail summary
| Guardrail | Approach | Action when flagged | Main limitation |
|---|---|---|---|
| PII | regex (email, phone, SSN, NID) + Luhn for cards | redact to `[TYPE]`, continue | obfuscated / spelled-out PII, names, addresses |
| Injection | weighted regex rules on Unicode-normalised text, threshold 0.7 | refuse before LLM | paraphrase, non-English; some false positives |
| Sensitive topic | keyword regex per category | self-harm: support msg; violence: refuse; medical/legal/finance: disclaimer | implicit phrasing, no context |
| Schema | hand-written validator (types, ranges, enum, no extra fields) | regenerate once, then fallback | checks structure, not truth |
| Groundedness | per-sentence content-word overlap >= 0.7 and all numbers present in references | regenerate, then fallback | negation flips, paraphrase |
| Output sensitive info | PII detector w/ allowlist of public contacts, secret & prompt-leak patterns | PII: redact; secrets/leak: regenerate then fallback | same as PII |

## Results (see RESULTS.md / REPORT.md)
49/56 pass; the 7 failures are deliberately-included known limitations. Precision 0.86-1.00, recall 0.75-1.00 per guardrail.
