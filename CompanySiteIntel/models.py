from dataclasses import dataclass, field


@dataclass
class CrawledPage:
    url: str
    title: str
    raw_html: str
    text: str
    status_code: int


@dataclass
class CrawlResult:
    base_url: str
    pages: list[CrawledPage] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    about_url: str = ""
    about_text: str = ""
    errors: list[str] = field(default_factory=list)

    @property
    def combined_text(self) -> str:
        chunks = []
        for page in self.pages:
            if page.text.strip():
                chunks.append(f"## {page.title or page.url}\n{page.text.strip()}")
        return "\n\n".join(chunks)


@dataclass
class CompanyProfile:
    organization_type: str = ""
    website: str = ""
    company_name: str = ""
    email_url_scraped: list[str] = field(default_factory=list)
    phone_number: str = ""
    social_links: list[str] = field(default_factory=list)
    location: str = ""
    industry: str = ""
    company_summary: str = ""
    what_the_company_does: str = ""
    target_customers: str = ""
    brand_tone: str = ""
    likely_priorities: list[str] = field(default_factory=list)
    about_url: str = ""
    about_summary: str = ""
    about_mission: str = ""
    products_or_services: list[str] = field(default_factory=list)
    team: str = ""
    key_stakeholders: list[str] = field(default_factory=list)
