"""
analyzer.py — send page structure to an LLM, get back features + schema + cursor prompt.
"""
from __future__ import annotations

import json

from openai import OpenAI

from models import (
    AnalysisResult,
    Feature,
    PageStructure,
    SchemaField,
    SchemaTable,
)
from scraper import to_llm_text

_SYSTEM_PROMPT = """\
You are a senior full-stack software architect and product analyst.
Given a structured summary of a web page, you will:
  1. Identify every meaningful feature on the page.
  2. Infer the full data schema needed to support those features.
  3. Write a comprehensive Cursor AI prompt that an engineer could paste directly
     into Cursor to rebuild the entire application from scratch.

Return ONLY valid JSON — no markdown fences, no extra keys — matching this exact schema:

{
  "app_name": "Short product / app name (string)",
  "summary": "2-3 sentence description of what this app does and who it's for (string)",
  "tech_stack_hints": ["list of inferred technologies, e.g. React, Stripe, PostgreSQL"],

  "features": [
    {
      "name": "Feature name (string)",
      "category": "One of: Navigation | Auth | Forms | Data Display | Search/Filter | Commerce | Social | Media | Settings | Analytics | Notifications | Other",
      "description": "What this feature does (1-2 sentences)",
      "ui_components": ["list of UI elements involved, e.g. modal, table, dropdown, date-picker"],
      "user_actions": ["list of actions a user can perform, e.g. submit form, sort column, upload file"],
      "data_requirements": ["brief hints about data needed, e.g. user email, order total, product SKU"]
    }
  ],

  "schema_tables": [
    {
      "name": "table_name (snake_case)",
      "description": "What this table stores (string)",
      "fields": [
        {
          "name": "field_name (snake_case)",
          "field_type": "One of: uuid | string | text | integer | float | boolean | datetime | date | json | enum",
          "nullable": true,
          "description": "What this field holds",
          "enum_values": []
        }
      ],
      "relationships": ["e.g. has many orders", "belongs to user (user_id FK)"],
      "indexes": ["e.g. email (unique)", "user_id + created_at"]
    }
  ],

  "cursor_prompt": "A complete, detailed prompt an engineer can paste into Cursor to rebuild this application. Include: app purpose, all features with specifics, full data schema, suggested tech stack, UI/UX notes, file structure suggestions, and any important implementation details. Write it in second person, imperative style. Minimum 400 words."
}

Rules:
- Be exhaustive: capture every visible feature, even minor ones (theme toggle, language selector, breadcrumbs, etc.)
- Schema must cover ALL data needed by ALL features — include auth tables, junction tables, settings tables, etc.
- Always include an `id` (uuid or integer primary key), `created_at`, and `updated_at` on every table.
- The cursor_prompt must be self-contained — someone reading it with no other context should be able to rebuild the app.
- Infer reasonable fields even when not directly visible (e.g. a login form implies users.password_hash).
"""


def analyze(
    page: PageStructure,
    *,
    api_key: str,
    model: str = "gpt-4o",
) -> AnalysisResult:
    client = OpenAI(api_key=api_key)

    user_content = to_llm_text(page)

    response = client.chat.completions.create(
        model=model,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )

    raw = response.choices[0].message.content or "{}"
    data: dict = json.loads(raw)

    features = [_parse_feature(f) for f in data.get("features", [])]
    schema_tables = [_parse_table(t) for t in data.get("schema_tables", [])]

    return AnalysisResult(
        url=page.url,
        page_title=page.title,
        app_name=data.get("app_name", page.title or "Unknown App"),
        summary=data.get("summary", ""),
        tech_stack_hints=_as_list(data.get("tech_stack_hints")),
        features=features,
        schema_tables=schema_tables,
        cursor_prompt=data.get("cursor_prompt", ""),
    )


# ── Parsers ─────────────────────────────────────────────────────────────────────

def _parse_feature(d: dict) -> Feature:
    return Feature(
        name=d.get("name", "Unnamed Feature"),
        category=d.get("category", "Other"),
        description=d.get("description", ""),
        ui_components=_as_list(d.get("ui_components")),
        user_actions=_as_list(d.get("user_actions")),
        data_requirements=_as_list(d.get("data_requirements")),
    )


def _parse_table(d: dict) -> SchemaTable:
    fields = [_parse_field(f) for f in d.get("fields", [])]
    return SchemaTable(
        name=d.get("name", "unnamed_table"),
        description=d.get("description", ""),
        fields=fields,
        relationships=_as_list(d.get("relationships")),
        indexes=_as_list(d.get("indexes")),
    )


def _parse_field(d: dict) -> SchemaField:
    return SchemaField(
        name=d.get("name", "field"),
        field_type=d.get("field_type", "string"),
        nullable=bool(d.get("nullable", True)),
        description=d.get("description", ""),
        enum_values=_as_list(d.get("enum_values")),
    )


def _as_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str) and value:
        return [value]
    return []
