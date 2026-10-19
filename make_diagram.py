"""Render architecture.png (matplotlib; no graphviz needed).  python3 make_diagram.py"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

fig, ax = plt.subplots(figsize=(13, 8)); ax.set_xlim(0, 13); ax.set_ylim(0, 8); ax.axis("off")
C = {"in": "#dbeafe", "llm": "#fde68a", "out": "#dcfce7", "end": "#fee2e2", "io": "#e5e7eb"}


def box(x, y, w, h, text, kind):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05", fc=C[kind], ec="#374151"))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=9)


def arrow(a, b, label="", off=(0, 0.12)):
    ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="->", color="#374151"))
    if label:
        ax.text((a[0] + b[0]) / 2 + off[0], (a[1] + b[1]) / 2 + off[1], label, fontsize=8, color="#b91c1c", ha="center")


ax.text(6.5, 7.7, "Guardrail architecture - University Admissions Assistant", ha="center", fontsize=13, weight="bold")
ax.text(3.0, 7.25, "INPUT STAGE", ha="center", weight="bold", color="#1d4ed8")
ax.text(10.0, 7.25, "OUTPUT STAGE", ha="center", weight="bold", color="#15803d")
box(0.3, 6.1, 2.4, 0.7, "User message", "io")
box(0.3, 4.9, 2.4, 0.7, "1. Injection detector\n(normalise + weighted regex)", "in")
box(0.3, 3.7, 2.4, 0.7, "2. Sensitive-topic classifier\n(self-harm/violence/med/legal/fin)", "in")
box(0.3, 2.5, 2.4, 0.7, "3. PII detector -> redact\n(regex + Luhn + obfuscation)", "in")
box(3.6, 2.5, 2.2, 0.7, "LLM + reference KB\n(mock or Claude)", "llm")
box(6.7, 6.1, 2.4, 0.7, "4. Schema validator\n(types, ranges, enum)", "out")
box(6.7, 4.9, 2.4, 0.7, "5. Groundedness check\n(overlap, numbers, negation)", "out")
box(6.7, 3.7, 2.4, 0.7, "6. Sensitive-info check\n(PII, secrets, prompt leak)", "out")
box(10.2, 3.7, 2.5, 0.7, "Return answer\n(PII redacted if needed)", "io")
box(10.2, 5.6, 2.5, 0.9, "Regenerate (1 retry)\nthen SAFE FALLBACK\n+ human contact", "end")
box(3.6, 5.8, 2.4, 0.9, "Refuse (injection/violence)\nSupport msg (self-harm)\nDisclaimer (med/legal/fin)", "end")
box(0.3, 0.9, 12.4, 0.8, "Audit logger: JSONL of redacted input, status, flags and trace (no raw PII)   |   Output failures never reach the user", "io")
arrow((1.5, 6.1), (1.5, 5.6)); arrow((1.5, 4.9), (1.5, 4.4), "clean"); arrow((1.5, 3.7), (1.5, 3.2), "none")
arrow((2.7, 5.25), (3.6, 6.1), "flagged"); arrow((2.7, 4.05), (3.6, 5.9), "flagged")
arrow((2.7, 2.85), (3.6, 2.85)); arrow((5.8, 2.85), (7.2, 6.1)); arrow((7.9, 6.1), (7.9, 5.6), "valid")
arrow((7.9, 4.9), (7.9, 4.4), "grounded"); arrow((9.1, 4.05), (10.2, 4.05), "clean / PII")
arrow((9.1, 6.45), (10.2, 6.1), "invalid"); arrow((9.1, 5.25), (10.2, 5.8), "unsupported"); arrow((9.1, 4.3), (10.6, 5.6), "secret / leak")
plt.savefig("architecture.png", dpi=150, bbox_inches="tight")
