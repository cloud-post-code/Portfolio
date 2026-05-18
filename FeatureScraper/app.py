"""
app.py — FeatureScraper Streamlit app
"""
from __future__ import annotations

import os
import re

import streamlit as st
from dotenv import load_dotenv

from analyzer import analyze
from models import AnalysisResult, Feature, SchemaTable
from scraper import scrape

load_dotenv()

# ── Category colours (badge style) ─────────────────────────────────────────────
_CATEGORY_COLORS: dict[str, str] = {
    "Navigation":     "#3b82f6",
    "Auth":           "#f59e0b",
    "Forms":          "#10b981",
    "Data Display":   "#8b5cf6",
    "Search/Filter":  "#06b6d4",
    "Commerce":       "#ec4899",
    "Social":         "#f97316",
    "Media":          "#84cc16",
    "Settings":       "#6b7280",
    "Analytics":      "#a855f7",
    "Notifications":  "#eab308",
    "Other":          "#64748b",
}

_FIELD_TYPE_COLORS: dict[str, str] = {
    "uuid":     "#6366f1",
    "string":   "#3b82f6",
    "text":     "#0ea5e9",
    "integer":  "#10b981",
    "float":    "#14b8a6",
    "boolean":  "#f59e0b",
    "datetime": "#f97316",
    "date":     "#fb923c",
    "json":     "#a855f7",
    "enum":     "#ec4899",
}


# ── Render helpers ───────────────────────────────────────────────────────────────

def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:40]


def _render_feature_card(feat: Feature, color: str) -> None:
    ui_pills = "".join(
        f'<span class="tag-pill">{c}</span>' for c in feat.ui_components
    )
    action_pills = "".join(
        f'<span class="tag-pill action">{a}</span>' for a in feat.user_actions
    )
    data_pills = "".join(
        f'<span class="tag-pill data">{d}</span>' for d in feat.data_requirements
    )

    st.markdown(
        f"""
        <div class="feature-card">
            <span class="cat-badge" style="background:{color}">{feat.category}</span>
            <div class="feature-name">{feat.name}</div>
            <div class="feature-desc">{feat.description}</div>
            {"<div class='section-label' style='margin-bottom:4px'>UI</div><div class='tag-row'>" + ui_pills + "</div>" if ui_pills else ""}
            {"<div class='section-label' style='margin-bottom:4px'>USER ACTIONS</div><div class='tag-row'>" + action_pills + "</div>" if action_pills else ""}
            {"<div class='section-label' style='margin-bottom:4px'>DATA NEEDS</div><div class='tag-row'>" + data_pills + "</div>" if data_pills else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_schema_card(table: SchemaTable) -> None:
    field_rows = ""
    for f in table.fields:
        type_color = _FIELD_TYPE_COLORS.get(f.field_type, "#64748b")
        nullable_text = "nullable" if f.nullable else "NOT NULL"
        enum_hint = f" [{', '.join(f.enum_values[:4])}]" if f.enum_values else ""
        field_rows += f"""
        <div class="field-row">
            <div class="field-name">{f.name}</div>
            <div class="field-type-badge" style="background:{type_color}">{f.field_type}{enum_hint}</div>
            <div class="field-nullable">{nullable_text}</div>
            <div class="field-desc">{f.description}</div>
        </div>"""

    rel_badges = "".join(
        f'<span class="rel-badge">{r}</span>' for r in table.relationships
    )
    idx_badges = "".join(
        f'<span class="idx-badge">{ix}</span>' for ix in table.indexes
    )

    footer = ""
    if rel_badges:
        footer += (
            "<div style='padding:8px 18px 4px'>"
            "<span style='font-size:11px;color:#475569;font-family:IBM Plex Mono'>RELATIONS</span>"
            f"<br>{rel_badges}</div>"
        )
    if idx_badges:
        footer += (
            "<div style='padding:4px 18px 10px'>"
            "<span style='font-size:11px;color:#475569;font-family:IBM Plex Mono'>INDEXES</span>"
            f"<br>{idx_badges}</div>"
        )

    st.markdown(
        f"""
        <div class="schema-card">
            <div class="schema-header">
                <span style="color:#6366f1;font-size:14px">⬡</span>
                <span class="schema-table-name">{table.name}</span>
                <span style="color:#475569;font-size:12px;margin-left:auto">{len(table.fields)} fields</span>
            </div>
            <div class="schema-desc">{table.description}</div>
            {field_rows}
            {footer}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _schema_to_sql(tables: list[SchemaTable]) -> str:
    _TYPE_MAP = {
        "uuid":     "UUID",
        "string":   "VARCHAR(255)",
        "text":     "TEXT",
        "integer":  "INTEGER",
        "float":    "NUMERIC",
        "boolean":  "BOOLEAN",
        "datetime": "TIMESTAMP WITH TIME ZONE",
        "date":     "DATE",
        "json":     "JSONB",
        "enum":     "VARCHAR(100)",
    }

    lines: list[str] = ["-- Auto-generated schema by FeatureScraper\n"]
    for table in tables:
        lines.append(f"CREATE TABLE {table.name} (")
        field_defs = []
        for f in table.fields:
            sql_type = _TYPE_MAP.get(f.field_type, "TEXT")
            null_str = "" if f.nullable else " NOT NULL"
            default = ""
            if f.name == "id":
                default = " DEFAULT gen_random_uuid()" if f.field_type == "uuid" else ""
            if f.name in ("created_at", "updated_at"):
                default = " DEFAULT now()"
            comment = f"  -- {f.description}" if f.description else ""
            field_defs.append(f"  {f.name} {sql_type}{null_str}{default}{comment}")
        lines.append(",\n".join(field_defs))
        lines.append(");\n")

        for idx in table.indexes:
            unique = "UNIQUE " if "unique" in idx.lower() else ""
            idx_col = idx.replace("(unique)", "").replace("(UNIQUE)", "").strip()
            safe_col = re.sub(r"[^a-z0-9_]", "_", idx_col.lower())
            idx_name = f"idx_{table.name}_{safe_col}"
            lines.append(f"CREATE {unique}INDEX {idx_name} ON {table.name} ({idx_col});")
        lines.append("")

    return "\n".join(lines)


# ── Page config ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FeatureScraper",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Space+Grotesk:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
}

.feature-card {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 16px 18px;
    margin-bottom: 14px;
    position: relative;
}
.feature-card:hover { border-color: #334155; }

.cat-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    font-family: 'IBM Plex Mono', monospace;
    letter-spacing: 0.05em;
    color: #fff;
    margin-bottom: 8px;
}
.feature-name {
    font-size: 16px;
    font-weight: 700;
    color: #f1f5f9;
    margin-bottom: 4px;
}
.feature-desc {
    font-size: 13px;
    color: #94a3b8;
    line-height: 1.5;
    margin-bottom: 10px;
}
.tag-row {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 6px;
}
.tag-pill {
    background: #1e293b;
    color: #94a3b8;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
    font-family: 'IBM Plex Mono', monospace;
}
.tag-pill.action {
    background: #172554;
    color: #93c5fd;
}
.tag-pill.data {
    background: #134e4a;
    color: #6ee7b7;
}

.schema-card {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 0;
    margin-bottom: 20px;
    overflow: hidden;
}
.schema-header {
    background: #1e293b;
    padding: 12px 18px;
    display: flex;
    align-items: center;
    gap: 10px;
}
.schema-table-name {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 15px;
    font-weight: 600;
    color: #e2e8f0;
}
.schema-desc {
    font-size: 12px;
    color: #64748b;
    padding: 8px 18px 12px;
}
.field-row {
    display: flex;
    align-items: flex-start;
    padding: 6px 18px;
    border-top: 1px solid #1e293b;
    gap: 10px;
}
.field-row:hover { background: #111827; }
.field-name {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 13px;
    color: #f8fafc;
    min-width: 160px;
}
.field-type-badge {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    padding: 1px 7px;
    border-radius: 4px;
    color: #fff;
    min-width: 68px;
    text-align: center;
}
.field-nullable {
    font-size: 11px;
    color: #475569;
    min-width: 50px;
}
.field-desc {
    font-size: 12px;
    color: #64748b;
    flex: 1;
}
.rel-badge {
    display: inline-block;
    background: #1e1b4b;
    color: #a5b4fc;
    font-size: 11px;
    font-family: 'IBM Plex Mono', monospace;
    padding: 2px 8px;
    border-radius: 4px;
    margin: 2px;
}
.idx-badge {
    display: inline-block;
    background: #0c2226;
    color: #67e8f9;
    font-size: 11px;
    font-family: 'IBM Plex Mono', monospace;
    padding: 2px 8px;
    border-radius: 4px;
    margin: 2px;
}
.prompt-box {
    background: #020617;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 20px 24px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 13px;
    color: #cbd5e1;
    line-height: 1.7;
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 600px;
    overflow-y: auto;
}
.summary-banner {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
    border: 1px solid #312e81;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 24px;
}
.app-name-display {
    font-size: 26px;
    font-weight: 700;
    color: #e2e8f0;
    margin-bottom: 6px;
}
.summary-text {
    color: #94a3b8;
    font-size: 14px;
    line-height: 1.6;
}
.tech-tag {
    display: inline-block;
    background: #1e293b;
    color: #7dd3fc;
    border: 1px solid #0ea5e9;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    padding: 2px 10px;
    border-radius: 20px;
    margin: 3px;
}
.stat-box {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 8px;
    padding: 14px 18px;
    text-align: center;
}
.stat-number {
    font-size: 28px;
    font-weight: 700;
    font-family: 'IBM Plex Mono', monospace;
    color: #818cf8;
}
.stat-label {
    font-size: 12px;
    color: #475569;
    margin-top: 2px;
}
.section-label {
    font-size: 11px;
    font-family: 'IBM Plex Mono', monospace;
    color: #475569;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 12px;
}
</style>
""",
    unsafe_allow_html=True,
)

# ── Session init ────────────────────────────────────────────────────────────────
if "result" not in st.session_state:
    st.session_state.result: AnalysisResult | None = None

# ── Sidebar ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Settings")
    st.divider()

    api_key = st.text_input(
        "OpenAI API key",
        value=os.getenv("OPENAI_API_KEY", ""),
        type="password",
        help="Required for LLM analysis. Stored in session only.",
    )

    model = st.selectbox(
        "Model",
        ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        index=0,
        help="gpt-4o gives the most thorough analysis.",
    )

    st.divider()
    st.caption(
        "**FeatureScraper** fetches a web page, extracts its structural "
        "features, infers a supporting data schema, and generates a ready-to-use "
        "Cursor AI prompt to rebuild the app from scratch."
    )

    if st.session_state.result:
        st.divider()
        st.markdown("### Last result")
        r = st.session_state.result
        st.markdown(f"**{r.app_name}**")
        st.caption(r.url)
        c1, c2 = st.columns(2)
        c1.metric("Features", len(r.features))
        c2.metric("Tables", len(r.schema_tables))

        if st.button("🗑 Clear", use_container_width=True):
            st.session_state.result = None
            st.rerun()

# ── Header ───────────────────────────────────────────────────────────────────────
st.markdown("# 🔬 FeatureScraper")
st.markdown(
    "Paste any URL → get a complete feature inventory, data schema, and a Cursor prompt to rebuild it."
)
st.divider()

# ── URL input ────────────────────────────────────────────────────────────────────
col_url, col_btn = st.columns([5, 1])
with col_url:
    url_input = st.text_input(
        "URL",
        label_visibility="collapsed",
        placeholder="https://app.example.com/dashboard",
    )
with col_btn:
    run = st.button("Analyze →", type="primary", use_container_width=True)

# ── Run analysis ─────────────────────────────────────────────────────────────────
if run:
    if not url_input.strip():
        st.error("Please enter a URL.")
        st.stop()
    if not api_key.strip():
        st.error("Add your OpenAI API key in the sidebar.")
        st.stop()

    with st.status("Analyzing page…", expanded=True) as status:
        st.write(f"Fetching `{url_input.strip()}`…")
        try:
            page_structure = scrape(url_input.strip())
        except Exception as exc:
            status.update(label="Scrape failed", state="error")
            st.error(f"Could not fetch the page: {exc}")
            st.stop()

        st.write(
            f"Scraped: **{len(page_structure.forms)} form(s)**, "
            f"**{len(page_structure.nav_items)} nav items**, "
            f"**{len(page_structure.buttons)} buttons** detected."
        )

        st.write("Running LLM analysis…")
        try:
            result = analyze(page_structure, api_key=api_key.strip(), model=model)
        except Exception as exc:
            status.update(label="Analysis failed", state="error")
            st.error(f"LLM analysis failed: {exc}")
            st.stop()

        st.session_state.result = result
        status.update(
            label=f"✓ Done — {len(result.features)} features · {len(result.schema_tables)} tables",
            state="complete",
            expanded=False,
        )

# ── Results ─────────────────────────────────────────────────────────────────────
result: AnalysisResult | None = st.session_state.result

if result:
    tech_tags = "".join(
        f'<span class="tech-tag">{t}</span>' for t in result.tech_stack_hints
    )
    st.markdown(
        f"""
        <div class="summary-banner">
            <div class="app-name-display">{result.app_name}</div>
            <div class="summary-text">{result.summary}</div>
            <div style="margin-top:12px">{tech_tags}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Stats row
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.markdown(
            f'<div class="stat-box"><div class="stat-number">{len(result.features)}</div>'
            f'<div class="stat-label">Features found</div></div>',
            unsafe_allow_html=True,
        )
    with s2:
        st.markdown(
            f'<div class="stat-box"><div class="stat-number">{len(result.schema_tables)}</div>'
            f'<div class="stat-label">Schema tables</div></div>',
            unsafe_allow_html=True,
        )
    with s3:
        total_fields = sum(len(t.fields) for t in result.schema_tables)
        st.markdown(
            f'<div class="stat-box"><div class="stat-number">{total_fields}</div>'
            f'<div class="stat-label">Schema fields</div></div>',
            unsafe_allow_html=True,
        )
    with s4:
        cats = set(f.category for f in result.features)
        st.markdown(
            f'<div class="stat-box"><div class="stat-number">{len(cats)}</div>'
            f'<div class="stat-label">Feature categories</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    tab_features, tab_schema, tab_prompt = st.tabs(
        ["📋 Features", "🗄 Data Schema", "🤖 Cursor Prompt"]
    )

    # ── Features tab ────────────────────────────────────────────────────────────
    with tab_features:
        all_cats = sorted(set(f.category for f in result.features))
        selected_cats = st.multiselect(
            "Filter by category",
            all_cats,
            default=all_cats,
            label_visibility="collapsed",
        )

        filtered = [f for f in result.features if f.category in selected_cats]

        grouped: dict[str, list[Feature]] = {}
        for feat in filtered:
            grouped.setdefault(feat.category, []).append(feat)

        for cat, feats in grouped.items():
            color = _CATEGORY_COLORS.get(cat, "#64748b")
            st.markdown(
                f'<div class="section-label" style="color:{color}">▸ {cat} ({len(feats)})</div>',
                unsafe_allow_html=True,
            )
            cols = st.columns(2)
            for i, feat in enumerate(feats):
                with cols[i % 2]:
                    _render_feature_card(feat, color)

        # Build markdown export
        md_lines = [f"# {result.app_name} — Feature List\n\n{result.summary}\n"]
        for cat, feats in grouped.items():
            md_lines.append(f"\n## {cat}\n")
            for feat in feats:
                md_lines.append(f"### {feat.name}\n{feat.description}\n")
                if feat.ui_components:
                    md_lines.append("**UI:** " + ", ".join(feat.ui_components))
                if feat.user_actions:
                    md_lines.append("\n**Actions:** " + ", ".join(feat.user_actions))
                if feat.data_requirements:
                    md_lines.append("\n**Data needs:** " + ", ".join(feat.data_requirements))
                md_lines.append("")

        st.download_button(
            "⬇️ Download Features (Markdown)",
            data="\n".join(md_lines),
            file_name=f"features_{_slug(result.app_name)}.md",
            mime="text/markdown",
        )

    # ── Schema tab ──────────────────────────────────────────────────────────────
    with tab_schema:
        for table in result.schema_tables:
            _render_schema_card(table)

        sql = _schema_to_sql(result.schema_tables)
        st.download_button(
            "⬇️ Download Schema (SQL)",
            data=sql,
            file_name=f"schema_{_slug(result.app_name)}.sql",
            mime="text/plain",
        )

    # ── Cursor Prompt tab ───────────────────────────────────────────────────────
    with tab_prompt:
        if result.cursor_prompt:
            st.markdown(
                f'<div class="prompt-box">{result.cursor_prompt}</div>',
                unsafe_allow_html=True,
            )
            st.markdown("<br>", unsafe_allow_html=True)
            st.download_button(
                "⬇️ Download Cursor Prompt (.txt)",
                data=result.cursor_prompt,
                file_name=f"cursor_prompt_{_slug(result.app_name)}.txt",
                mime="text/plain",
                type="primary",
            )
        else:
            st.info("No cursor prompt was generated.")

else:
    st.markdown(
        """
        <div style="text-align:center; padding: 60px 20px; color: #475569;">
            <div style="font-size:48px; margin-bottom:16px">🔬</div>
            <div style="font-size:18px; font-weight:600; color:#64748b; margin-bottom:8px">
                No analysis yet
            </div>
            <div style="font-size:14px; color:#334155;">
                Enter a URL above and click <strong>Analyze →</strong> to begin.<br>
                You'll get a full feature inventory, data schema, and a Cursor rebuild prompt.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
