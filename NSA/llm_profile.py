import json

from openai import OpenAI

from models import CompanyProfile, CrawlResult

_SYSTEM_PROMPT = """\
You are a business intelligence analyst. Given scraped website content, extract a structured company profile.
Return ONLY valid JSON matching the schema below — no markdown fences, no extra keys.

Schema:
{
  "organization_type": "One of: B2B, B2C, B2B2C, Nonprofit, Government, Agency, Marketplace, or best guess",
  "company_name": "string",
  "phone_number": "Primary phone number found, or empty string",
  "social_links": ["list of social media or external profile URLs found"],
  "location": "City, State/Country or Unknown",
  "industry": "e.g. SaaS, E-commerce, Healthcare, Retail, etc.",
  "company_summary": "One punchy sentence — who they are and what they do",
  "what_the_company_does": "2-3 sentence plain-English description of their core offering",
  "target_customers": "Who they sell to — demographics, company types, or roles",
  "brand_tone": "e.g. Professional, Friendly, Technical, Playful, Authoritative",
  "likely_priorities": ["3-5 strategic priorities inferred from messaging and content"],
  "about_summary": "2-3 sentence summary of the About page content, or empty string if not available",
  "about_mission": "The mission statement or core purpose, verbatim or paraphrased, or empty string",
  "products_or_services": ["list of distinct products or services offered"],
  "team": "Team size estimate or notable team structure (e.g. '10-50 employees, leadership team visible')",
  "key_stakeholders": ["names and roles of any founders, executives, or key people mentioned"]
}
"""


def build_profile(
    crawl: CrawlResult,
    *,
    api_key: str,
    model: str = "gpt-4o-mini",
) -> CompanyProfile:
    client = OpenAI(api_key=api_key)

    combined = crawl.combined_text[:20_000]
    emails_hint = ", ".join(crawl.emails) if crawl.emails else "None found"
    phones_hint = ", ".join(crawl.phones) if crawl.phones else "None found"
    about_section = (
        f"\n--- ABOUT PAGE ({crawl.about_url}) ---\n{crawl.about_text[:4_000]}"
        if crawl.about_text
        else ""
    )

    user_content = (
        f"Website: {crawl.base_url}\n"
        f"Contact emails found: {emails_hint}\n"
        f"Phone numbers found: {phones_hint}\n\n"
        f"--- SCRAPED CONTENT ---\n{combined}"
        f"{about_section}"
    )

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

    return CompanyProfile(
        organization_type=data.get("organization_type", ""),
        website=crawl.base_url,
        company_name=data.get("company_name", ""),
        email_url_scraped=crawl.emails,
        phone_number=data.get("phone_number", "") or (crawl.phones[0] if crawl.phones else ""),
        social_links=_as_list(data.get("social_links")),
        location=data.get("location", "Unknown"),
        industry=data.get("industry", ""),
        company_summary=data.get("company_summary", ""),
        what_the_company_does=data.get("what_the_company_does", ""),
        target_customers=data.get("target_customers", ""),
        brand_tone=data.get("brand_tone", ""),
        likely_priorities=_as_list(data.get("likely_priorities")),
        about_url=crawl.about_url,
        about_summary=data.get("about_summary", ""),
        about_mission=data.get("about_mission", ""),
        products_or_services=_as_list(data.get("products_or_services")),
        team=data.get("team", ""),
        key_stakeholders=_as_list(data.get("key_stakeholders")),
    )


def _as_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str) and value:
        return [value]
    return []
