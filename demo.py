"""Interactive / one-shot demo.  python3 demo.py "question"   |   python3 demo.py --real "question"   |   python3 demo.py (REPL)"""
import sys
from guardrails import GuardedApp
from guardrails.audit import AuditLogger

args = sys.argv[1:]
llm = None
if args and args[0] == "--real":
    from guardrails.llm_anthropic import claude_llm
    llm, args = claude_llm, args[1:]
app = GuardedApp(**({"llm": llm} if llm else {}))
audit = AuditLogger()


def ask(q):
    r = app.ask(q)
    audit.log(q, r)
    print(f"[{r.status}] {r.answer}\n  flags={r.flags} trace={r.trace}")


if args:
    ask(" ".join(args))
else:
    while True:
        try:
            ask(input("you> "))
        except (EOFError, KeyboardInterrupt):
            break
