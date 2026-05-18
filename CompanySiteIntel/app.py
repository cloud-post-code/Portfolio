import io
import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from crawler import crawl
from llm_profile import build_profile
from models import CompanyProfile

load_dotenv()

APP_DIR = Path(__file__).resolve().parent
DEFAULT_CSV_PATH = APP_DIR / "company_intel.csv"

# Column order matches the requested output spec
CSV_COLUMNS = [
    "organization_type",
    "website",
    "company_name",
    "email_url_scraped",
    "phone_number",
    "social_links",
    "location",
    "industry",
    "company_summary",
    "what_the_company_does",
    "target_customers",
    "brand_tone",
    "likely_priorities",
    "about_url",
    "about_summary",
    "about_mission",
    "products_or_services",
    "team",
    "key_stakeholders",
]


def _profile_to_row(p: CompanyProfile) -> dict:
    """Flatten a CompanyProfile into a CSV-friendly dict."""
    return {
        "organization_type": p.organization_type,
        "website": p.website,
        "company_name": p.company_name,
        "email_url_scraped": " | ".join(p.email_url_scraped),
        "phone_number": p.phone_number,
        "social_links": " | ".join(p.social_links),
        "location": p.location,
        "industry": p.industry,
        "company_summary": p.company_summary,
        "what_the_company_does": p.what_the_company_does,
        "target_customers": p.target_customers,
        "brand_tone": p.brand_tone,
        "likely_priorities": " | ".join(p.likely_priorities),
        "about_url": p.about_url,
        "about_summary": p.about_summary,
        "about_mission": p.about_mission,
        "products_or_services": " | ".join(p.products_or_services),
        "team": p.team,
        "key_stakeholders": " | ".join(p.key_stakeholders),
    }


def _error_row(url: str, message: str) -> dict:
    row = {col: "" for col in CSV_COLUMNS}
    row["website"] = url
    row["company_name"] = "(failed)"
    row["company_summary"] = message
    return row


def _parse_urls(raw: str) -> list[str]:
    """Split a textarea blob into a cleaned list of unique URLs."""
    seen: set[str] = set()
    urls: list[str] = []
    for line in raw.splitlines():
        url = line.strip().strip(",").strip()
        if url and url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def _results_df() -> pd.DataFrame:
    rows = st.session_state.get("results", [])
    if not rows:
        return pd.DataFrame(columns=CSV_COLUMNS)
    return pd.DataFrame(rows, columns=CSV_COLUMNS)


def _write_results_csv(path: Path) -> None:
    """Persist current results to disk (rewritten after each company)."""
    df = _results_df()
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _analyze_url(
    url: str,
    *,
    api_key: str,
    model: str,
    max_pages: int,
) -> tuple[CompanyProfile | None, str | None]:
    """Crawl and profile one URL. Returns (profile, error_message)."""
    try:
        crawl_result = crawl(url, max_pages=max_pages)
    except Exception as exc:
        return None, f"Crawl failed: {exc}"

    if len(crawl_result.pages) == 0:
        return None, "No pages retrieved from crawl."

    try:
        profile = build_profile(
            crawl_result,
            api_key=api_key,
            model=model,
        )
    except Exception as exc:
        return None, f"Profiling failed: {exc}"

    return profile, None


def _run_batch_sequential(
    urls: list[str],
    *,
    api_key: str,
    model: str,
    max_pages: int,
    csv_path: Path,
) -> None:
    """Process every URL in order in one run; CSV is rewritten after each site."""
    total = len(urls)
    st.session_state.batch_running = True
    st.session_state.batch_total = total
    st.session_state.pending_urls = list(urls)

    progress = st.progress(0, text=f"Starting batch — 0 of {total}")
    log = st.container()

    for index, url in enumerate(urls, start=1):
        st.session_state.pending_urls = urls[index:]
        progress.progress(
            (index - 1) / total,
            text=f"Processing {index} of {total}: {url}",
        )

        with log:
            with st.status(f"[{index}/{total}] `{url}`", expanded=True) as status:
                st.write(f"Crawling `{url}` …")
                profile, err = _analyze_url(
                    url,
                    api_key=api_key,
                    model=model,
                    max_pages=max_pages,
                )

                if err:
                    status.update(label=f"✗ Failed — {url}", state="error", expanded=False)
                    st.session_state.results.append(_error_row(url, err))
                else:
                    status.update(
                        label=f"✓ {profile.company_name or url}",
                        state="complete",
                        expanded=False,
                    )
                    st.session_state.results.append(_profile_to_row(profile))

        _write_results_csv(csv_path)
        progress.progress(index / total, text=f"Completed {index} of {total}")
        st.caption(f"CSV updated ({index}/{total}): `{csv_path}`")

    st.session_state.pending_urls = []
    st.session_state.batch_running = False
    st.success(f"Batch complete — {total} URL(s) processed. CSV saved to `{csv_path}`.")


# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="CompanySiteIntel",
    page_icon="🏢",
    layout="wide",
)

# ── Session state init ─────────────────────────────────────────────────────────
if "pending_urls" not in st.session_state:
    st.session_state.pending_urls: list[str] = []
if "batch_running" not in st.session_state:
    st.session_state.batch_running = False
if "batch_total" not in st.session_state:
    st.session_state.batch_total = 0
if "results" not in st.session_state:
    st.session_state.results: list[dict] = []
if "csv_path" not in st.session_state:
    st.session_state.csv_path = str(DEFAULT_CSV_PATH)

batch_running = st.session_state.batch_running

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ Settings")
    api_key = st.text_input(
        "OpenAI API key",
        value=os.getenv("OPENAI_API_KEY", ""),
        type="password",
        help="Required for LLM profiling. Stored only in this session.",
        disabled=batch_running,
    )
    model = st.selectbox(
        "Model",
        ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"],
        index=0,
        disabled=batch_running,
    )
    max_pages = st.slider(
        "Max pages to crawl",
        1,
        20,
        10,
        disabled=batch_running,
    )
    csv_path_input = st.text_input(
        "CSV output path",
        value=st.session_state.csv_path,
        help="Rewritten after each company completes.",
        disabled=batch_running,
    )
    if not batch_running:
        st.session_state.csv_path = csv_path_input.strip() or str(DEFAULT_CSV_PATH)

    st.divider()

    pending_len = len(st.session_state.pending_urls)
    done_len = len(st.session_state.results)

    if batch_running:
        st.metric("Remaining in batch", pending_len)
    st.metric("Completed", done_len)

    if batch_running:
        st.warning("Batch in progress — do not refresh or close this tab until finished.")
    elif st.button("🗑 Clear all", use_container_width=True):
        st.session_state.pending_urls = []
        st.session_state.batch_running = False
        st.session_state.batch_total = 0
        st.session_state.results = []
        st.rerun()

    st.caption(
        "All pasted URLs are queued first, then processed back-to-back in one run. "
        "The CSV is rewritten after each site. Do not refresh until the batch finishes."
    )

# ── Main ───────────────────────────────────────────────────────────────────────
st.title("🏢 CompanySiteIntel")
st.caption(
    "Paste all URLs, then start. Every URL is ingested into a queue first, then processed "
    "sequentially without stopping until the queue is empty. CSV updates after each site."
)

csv_path = Path(st.session_state.csv_path)

# ── URL input ──────────────────────────────────────────────────────────────────
with st.expander("📋 URLs", expanded=not batch_running):
    url_blob = st.text_area(
        "Paste URLs (one per line)",
        placeholder="acme.com\nhttps://www.widgetco.io\nbuildright.co",
        height=200,
        disabled=batch_running,
    )

    col_start, col_replace = st.columns(2)
    with col_start:
        start_disabled = (
            batch_running
            or not url_blob.strip()
            or not (api_key or "").strip()
        )
        if st.button(
            "▶ Run all URLs",
            type="primary",
            disabled=start_disabled,
            use_container_width=True,
        ):
            urls = _parse_urls(url_blob)
            if not urls:
                st.error("No valid URLs found.")
            else:
                st.session_state.results = []
                _write_results_csv(csv_path)
                _run_batch_sequential(
                    urls,
                    api_key=api_key.strip(),
                    model=model,
                    max_pages=max_pages,
                    csv_path=csv_path,
                )

    with col_replace:
        append_disabled = batch_running or not url_blob.strip()
        if st.button(
            "Append & run",
            disabled=append_disabled,
            use_container_width=True,
            help="Add new URLs to the end of an existing results table and run them.",
        ):
            urls = _parse_urls(url_blob)
            existing_sites = {r.get("website", "") for r in st.session_state.results}
            new_urls = [u for u in urls if u not in existing_sites]
            if not new_urls:
                st.warning("All pasted URLs are already in results.")
            else:
                _run_batch_sequential(
                    new_urls,
                    api_key=api_key.strip(),
                    model=model,
                    max_pages=max_pages,
                    csv_path=csv_path,
                )

# ── Batch queue snapshot (shown after a run or if state was restored) ───────────
if st.session_state.pending_urls and not batch_running:
    with st.expander(f"Last batch queue ({len(st.session_state.pending_urls)} remaining — interrupted?)"):
        for i, u in enumerate(st.session_state.pending_urls, 1):
            st.markdown(f"{i}. `{u}`")

# ── Results table ──────────────────────────────────────────────────────────────
st.divider()

df = _results_df()

if not df.empty:
    st.subheader(f"Results ({len(df)} company{'ies' if len(df) != 1 else 'y'})")

    if csv_path.is_file():
        st.caption(f"On disk: `{csv_path}` ({csv_path.stat().st_size:,} bytes)")

    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    st.download_button(
        label="⬇️ Download CSV",
        data=csv_buffer.getvalue(),
        file_name=csv_path.name,
        mime="text/csv",
        type="primary",
        disabled=batch_running,
    )

    st.dataframe(
        df,
        use_container_width=True,
        height=420,
        column_config={
            "website": st.column_config.LinkColumn("website"),
            "about_url": st.column_config.LinkColumn("about_url"),
        },
    )
elif not batch_running:
    st.info("Paste URLs above and click **Run all URLs** to start a sequential batch.")
