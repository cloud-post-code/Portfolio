from dataclasses import dataclass, field


# ── Raw scraped page ────────────────────────────────────────────────────────────

@dataclass
class FormField:
    tag: str           # input | select | textarea | checkbox | radio
    input_type: str    # text | email | password | file | number | date …
    name: str
    placeholder: str
    label: str
    required: bool


@dataclass
class Form:
    action: str
    method: str
    purpose_hint: str  # e.g. "login", "search", "subscribe"
    fields: list[FormField] = field(default_factory=list)
    submit_text: str = ""


@dataclass
class NavItem:
    text: str
    href: str
    depth: int = 0     # 0 = top-level, 1 = dropdown child …


@dataclass
class DataTable:
    headers: list[str]
    sample_rows: list[list[str]]  # up to 2 sample rows


@dataclass
class PageStructure:
    url: str
    title: str
    meta_description: str
    nav_items: list[NavItem] = field(default_factory=list)
    forms: list[Form] = field(default_factory=list)
    buttons: list[str] = field(default_factory=list)       # de-duped button/CTA texts
    tables: list[DataTable] = field(default_factory=list)
    list_headings: list[str] = field(default_factory=list) # <h*> near <ul> / <ol>
    external_scripts: list[str] = field(default_factory=list)  # src domains of known libs
    json_ld_types: list[str] = field(default_factory=list)    # @type values from JSON-LD
    visible_text_snippet: str = ""  # first ~3 000 chars of visible text


# ── Analysis results ────────────────────────────────────────────────────────────

@dataclass
class Feature:
    name: str
    category: str       # Navigation | Auth | Forms | Data Display | Search/Filter |
                        # Commerce | Social | Media | Settings | Analytics | Other
    description: str
    ui_components: list[str] = field(default_factory=list)  # e.g. ["modal", "table"]
    user_actions: list[str] = field(default_factory=list)   # e.g. ["submit form", "sort column"]
    data_requirements: list[str] = field(default_factory=list)  # short hints for schema


@dataclass
class SchemaField:
    name: str
    field_type: str     # string | text | integer | float | boolean | datetime | json | uuid | enum
    nullable: bool
    description: str
    enum_values: list[str] = field(default_factory=list)  # non-empty for enum fields


@dataclass
class SchemaTable:
    name: str
    description: str
    fields: list[SchemaField] = field(default_factory=list)
    relationships: list[str] = field(default_factory=list)  # e.g. "has many orders", "belongs to user"
    indexes: list[str] = field(default_factory=list)        # e.g. "email (unique)", "user_id + created_at"


@dataclass
class AnalysisResult:
    url: str
    page_title: str
    app_name: str
    summary: str
    tech_stack_hints: list[str] = field(default_factory=list)
    features: list[Feature] = field(default_factory=list)
    schema_tables: list[SchemaTable] = field(default_factory=list)
    cursor_prompt: str = ""
