"""Append-only JSONL audit trail. Only the *redacted* input is logged, so the log itself holds no raw PII."""
import json
import time
from .input_guards import redact_pii


class AuditLogger:
    def __init__(self, path="audit_log.jsonl"):
        self.path = path

    def log(self, question, result):
        clean_q, _ = redact_pii(question)
        rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "question": clean_q, "status": result.status,
               "flags": result.flags, "trace": result.trace}
        with open(self.path, "a") as f:
            f.write(json.dumps(rec) + "\n")
