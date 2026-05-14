import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

# ── canvas ──────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(20, 13))
ax.set_xlim(0, 20)
ax.set_ylim(0, 13)
ax.axis("off")
fig.patch.set_facecolor("#0f172a")
ax.set_facecolor("#0f172a")

# ── colour palette ───────────────────────────────────────────────────────────
C = {
    "title_bg":    "#1e293b",
    "frontend":    "#1d4ed8",
    "frontend_bg": "#1e3a5f",
    "backend":     "#15803d",
    "backend_bg":  "#14532d",
    "scanner":     "#b45309",
    "scanner_bg":  "#451a03",
    "invest":      "#7c3aed",
    "invest_bg":   "#2e1065",
    "tech":        "#0e7490",
    "tech_bg":     "#164e63",
    "db":          "#be185d",
    "db_bg":       "#500724",
    "pinecone":    "#065f46",
    "pinecone_bg": "#022c22",
    "pdf":         "#92400e",
    "pdf_bg":      "#451a03",
    "openai":      "#374151",
    "openai_bg":   "#111827",
    "arrow":       "#94a3b8",
    "text":        "#f1f5f9",
    "subtext":     "#94a3b8",
    "border":      "#334155",
    "group_bg":    "#1e293b",
}

def box(ax, x, y, w, h, label, sublabel="", color="#1d4ed8", bg="#1e3a5f",
        fontsize=10, sublabel_size=8, radius=0.25):
    rect = FancyBboxPatch((x, y), w, h,
                          boxstyle=f"round,pad=0.05,rounding_size={radius}",
                          linewidth=1.5, edgecolor=color, facecolor=bg, zorder=3)
    ax.add_patch(rect)
    ty = y + h / 2 + (0.15 if sublabel else 0)
    ax.text(x + w / 2, ty, label, ha="center", va="center",
            fontsize=fontsize, fontweight="bold", color=C["text"], zorder=4)
    if sublabel:
        ax.text(x + w / 2, y + h / 2 - 0.2, sublabel, ha="center", va="center",
                fontsize=sublabel_size, color=C["subtext"], zorder=4)

def group(ax, x, y, w, h, label, color="#334155"):
    rect = FancyBboxPatch((x, y), w, h,
                          boxstyle="round,pad=0.05,rounding_size=0.4",
                          linewidth=1, edgecolor=color, facecolor="#1e293b",
                          alpha=0.6, zorder=1)
    ax.add_patch(rect)
    ax.text(x + 0.2, y + h - 0.01, label, ha="left", va="top",
            fontsize=8, color=color, fontweight="bold", zorder=2,
            style="italic")

def arrow(ax, x1, y1, x2, y2, label="", color="#94a3b8", lw=1.2):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=color,
                                lw=lw, mutation_scale=14),
                zorder=5)
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(mx, my + 0.12, label, ha="center", va="bottom",
                fontsize=6.5, color=color, zorder=6)

# ═══════════════════════════════════════════════════════════════════════════
# TITLE
# ═══════════════════════════════════════════════════════════════════════════
title_rect = FancyBboxPatch((0.3, 11.9), 19.4, 0.9,
                             boxstyle="round,pad=0.05,rounding_size=0.3",
                             linewidth=2, edgecolor="#3b82f6", facecolor="#1e3a5f", zorder=3)
ax.add_patch(title_rect)
ax.text(10, 12.35, "Production Issue AI Assistant — System Architecture",
        ha="center", va="center", fontsize=17, fontweight="bold",
        color="#f1f5f9", zorder=4)

# ═══════════════════════════════════════════════════════════════════════════
# ROW 1  — Frontend
# ═══════════════════════════════════════════════════════════════════════════
group(ax, 0.3, 9.7, 19.4, 2.0, "  Frontend  —  React · Vite · Tailwind (port 5173)", C["frontend"])

components = [
    ("Sensor\nStream Panel", "Live SSE table"),
    ("Trigger\nButton", "Scenario selector"),
    ("Agent Pipeline\nStatus", "Stepper"),
    ("Investigator\nReport", "Verdict + confidence"),
    ("Action Plan\nPanel", "Handoff · MR · CAPA"),
    ("Approval\nGate", "Approve / Reject"),
    ("PDF\nDownload", ""),
]
fe_xs = [0.55, 3.15, 5.75, 8.35, 10.95, 13.55, 16.15]
fe_w, fe_h = 2.4, 1.55
for (lbl, sub), fx in zip(components, fe_xs):
    box(ax, fx, 9.85, fe_w, fe_h, lbl, sub,
        color=C["frontend"], bg=C["frontend_bg"], fontsize=8, sublabel_size=6.5)

# ═══════════════════════════════════════════════════════════════════════════
# ROW 2  — Backend
# ═══════════════════════════════════════════════════════════════════════════
group(ax, 0.3, 7.55, 19.4, 2.0, "  Backend  —  FastAPI · uvicorn (port 8000)", C["backend"])

endpoints = [
    ("GET /stream/sensor", "SSE stream"),
    ("POST /issues/analyze", "Trigger pipeline"),
    ("GET /issues/:id", "Poll status"),
    ("POST /issues/:id/approve", "Human gate"),
    ("GET /reports/:id/pdf", "Download PDF"),
]
ep_xs = [0.55, 4.45, 8.35, 11.55, 15.45]
ep_w, ep_h = 3.6, 1.55
for (lbl, sub), ex in zip(endpoints, ep_xs):
    box(ax, ex, 7.7, ep_w, ep_h, lbl, sub,
        color=C["backend"], bg=C["backend_bg"], fontsize=8, sublabel_size=6.5)

# ═══════════════════════════════════════════════════════════════════════════
# ROW 3  — Agent Pipeline
# ═══════════════════════════════════════════════════════════════════════════
group(ax, 0.3, 5.1, 12.9, 2.2, "  Agent Pipeline  —  LangGraph", "#eab308")

box(ax, 0.55, 5.3, 3.8, 1.8,
    "Scanner Agent",
    "Rule-based · groups by line\naffected_lines output",
    color=C["scanner"], bg=C["scanner_bg"], fontsize=9)

box(ax, 4.65, 5.3, 4.0, 1.8,
    "Investigator Agent",
    "gpt-4o-mini · RAG\nRoot-cause · confidence",
    color=C["invest"], bg=C["invest_bg"], fontsize=9)

box(ax, 8.95, 5.3, 4.0, 1.8,
    "Technician Agent",
    "gpt-4o-mini\nHandoff · MR · CAPA · PDF",
    color=C["tech"], bg=C["tech_bg"], fontsize=9)

# ═══════════════════════════════════════════════════════════════════════════
# ROW 3  — Services (right side)
# ═══════════════════════════════════════════════════════════════════════════
group(ax, 13.4, 5.1, 6.3, 2.2, "  Services", C["border"])

box(ax, 13.6, 5.3, 1.8, 1.8, "PostgreSQL", "9 tables\naudit log",
    color=C["db"], bg=C["db_bg"], fontsize=8, sublabel_size=7)
box(ax, 15.6, 5.3, 1.8, 1.8, "Pinecone", "Vector KB\nRAG retrieval",
    color=C["pinecone"], bg=C["pinecone_bg"], fontsize=8, sublabel_size=7)
box(ax, 17.6, 5.3, 1.8, 1.8, "PDF Service", "ReportLab\nAction plan",
    color=C["pdf"], bg=C["pdf_bg"], fontsize=8, sublabel_size=7)

# ═══════════════════════════════════════════════════════════════════════════
# ROW 4  — External + Data store
# ═══════════════════════════════════════════════════════════════════════════
box(ax, 0.55, 2.8, 5.0, 1.8,
    "OpenAI API",
    "gpt-4o-mini · text-embedding-3-small",
    color="#6b7280", bg=C["openai_bg"], fontsize=9)

box(ax, 6.0, 2.8, 5.0, 1.8,
    "Simulation Service",
    "Synthetic sensor data\nDemo scenario generator",
    color="#0369a1", bg="#0c1a2e", fontsize=9)

box(ax, 11.5, 2.8, 7.9, 1.8,
    "Human Approval Gate",
    "plant_manager reviews → approve / reject before CMMS action\naudit_log written on every decision (immutable)",
    color="#be123c", bg="#4c0519", fontsize=9)

# ═══════════════════════════════════════════════════════════════════════════
# ARROWS
# ═══════════════════════════════════════════════════════════════════════════
# Frontend → Backend (vertical, sampled)
fe_centers = [fx + fe_w / 2 for fx in fe_xs]
ep_centers = [ex + ep_w / 2 for ex in ep_xs]

# SSE arrow: sensor panel → GET /stream
arrow(ax, fe_centers[0], 9.85, ep_centers[0], 9.25, "SSE", C["frontend"])
# analyze: trigger → POST analyze
arrow(ax, fe_centers[1], 9.85, ep_centers[1], 9.25, "POST", C["frontend"])
# poll: status, report, approval panels → their endpoints
arrow(ax, fe_centers[2], 9.85, ep_centers[2], 9.25, "GET", C["frontend"])
arrow(ax, fe_centers[5], 9.85, ep_centers[3], 9.25, "POST", C["frontend"])
arrow(ax, fe_centers[6], 9.85, ep_centers[4], 9.25, "GET", C["frontend"])

# Backend → Pipeline
arrow(ax, ep_centers[1], 7.7, 2.45, 7.1, "BackgroundTask", C["backend"])

# SSE → Simulation
arrow(ax, ep_centers[0], 7.7, 7.5, 4.6, "generate batch", C["backend"])

# Pipeline internal
arrow(ax, 4.35, 6.2, 4.65, 6.2, "anomaly=True", "#eab308", lw=1.5)
arrow(ax, 8.65, 6.2, 8.95, 6.2, "", "#eab308", lw=1.5)

# Agents → Services
arrow(ax, 10.95, 5.3, 14.5, 7.1, "save_run", C["db"])          # technician → postgres
arrow(ax, 6.65, 5.3, 16.5, 5.3, "retrieve_similar", C["pinecone"]) # investigator → pinecone
arrow(ax, 10.95, 5.3, 18.5, 5.3, "generate PDF", C["pdf"])     # technician → pdf

# Agents → OpenAI
arrow(ax, 6.65, 5.3, 2.05, 4.6, "gpt-4o-mini", "#6b7280")
arrow(ax, 10.95, 5.3, 3.05, 4.6, "gpt-4o-mini", "#6b7280")
arrow(ax, 16.5, 5.3, 2.55, 4.6, "embed query", "#6b7280")

# Approve endpoint → DB
arrow(ax, ep_centers[3], 7.7, 14.5, 4.6, "audit_log", C["db"])

# PDF endpoint → PDF service
arrow(ax, ep_centers[4], 7.7, 18.5, 5.3, "", C["pdf"])

# Approval gate
arrow(ax, ep_centers[3], 7.7, 15.45, 4.6, "", "#be123c")

# ═══════════════════════════════════════════════════════════════════════════
# LEGEND
# ═══════════════════════════════════════════════════════════════════════════
legend_items = [
    (C["frontend"],  C["frontend_bg"],  "Frontend (React/Vite)"),
    (C["backend"],   C["backend_bg"],   "Backend (FastAPI)"),
    (C["scanner"],   C["scanner_bg"],   "Scanner Agent"),
    (C["invest"],    C["invest_bg"],    "Investigator Agent"),
    (C["tech"],      C["tech_bg"],      "Technician Agent"),
    (C["db"],        C["db_bg"],        "PostgreSQL"),
    (C["pinecone"],  C["pinecone_bg"],  "Pinecone (Vector KB)"),
    ("#6b7280",      C["openai_bg"],    "OpenAI API"),
]
lx, ly, lw, lh = 0.4, 0.2, 2.1, 0.38
for i, (edge, bg, label) in enumerate(legend_items):
    col = i % 4
    row = i // 4
    rx = lx + col * (lw + 0.3)
    ry = ly + row * (lh + 0.06)
    rect = FancyBboxPatch((rx, ry), lw, lh,
                          boxstyle="round,pad=0.02,rounding_size=0.1",
                          linewidth=1, edgecolor=edge, facecolor=bg, zorder=3)
    ax.add_patch(rect)
    ax.text(rx + lw / 2, ry + lh / 2, label, ha="center", va="center",
            fontsize=7, color=C["text"], zorder=4)

plt.tight_layout(pad=0)
plt.savefig(
    "/Users/saharatif/Production_issue_ai/Presentation/architecture.png",
    dpi=180, bbox_inches="tight",
    facecolor=fig.get_facecolor()
)
print("saved")
