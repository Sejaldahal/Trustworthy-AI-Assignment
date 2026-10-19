# Architecture

```mermaid
flowchart TD
    U[User message] --> I1{Injection detector}
    I1 -- flagged --> B[Refuse: blocked]
    I1 -- clean --> I2{Sensitive-topic classifier}
    I2 -- self_harm --> S[Support message + resources]
    I2 -- violence --> B
    I2 -- medical / legal / financial --> D[Disclaimer, no LLM answer]
    I2 -- none --> I3[PII detector -> redact]
    I3 --> L[(LLM + reference KB)]
    L --> O1{Schema validator}
    O1 -- invalid --> R{Retries left?}
    O1 -- valid --> O2{Groundedness check}
    O2 -- unsupported --> R
    O2 -- supported --> O3{Sensitive-info check}
    O3 -- secret / prompt leak --> R
    O3 -- PII --> X[Redact] --> OK
    O3 -- clean --> OK[Return answer]
    R -- yes --> L
    R -- no --> F[Safe fallback + contact info]
```

Order rationale: injection runs first (cheapest, and a hijacked request must never reach topic logic or the LLM);
topics next (some need a special response, not an LLM answer); PII redaction last on input so the LLM never sees raw PII.
On output, schema comes first because the later checks need parsed fields; groundedness before sensitive-info so
we don't spend effort redacting an answer that will be discarded. Secrets/prompt leaks are never "redacted and sent" - they trigger regeneration/fallback.
