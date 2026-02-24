#!/usr/bin/env python3
"""
format-exa-jobs.py — Parse Exa MCP search results into clean job posting JSON.

Usage:
  python3 scripts/format-exa-jobs.py <file1> [file2] [file3] ... [--output FILE] [--csv]

Reads one or more Exa MCP tool-result files (the JSON arrays saved by Claude Code
when an Exa response exceeds the token limit). Extracts job postings, applies
quality filters, deduplicates, and outputs a numbered JSON array.

Filters applied:
  - US-based only (excludes Canada, UK, Australia, Kenya, India, Philippines, etc.)
  - Actual job postings only (excludes career landing pages, blog posts, job board aggregators)
  - Medical records / HIM / EHR related roles only
  - Direct employer postings only (excludes staffing agencies)
  - Deduplicates by normalized company + job title

Output format:
  [
    {
      "job_id": "1",
      "company_name": "Example Health",
      "job_title": "Medical Records Clerk",
      "location": "Houston, TX",
      "job_url": "https://...",
      "company_domain": "examplehealth.org"
    }
  ]
"""

import json
import sys
import re
import argparse
import csv
from urllib.parse import urlparse


# ---------------------------------------------------------------------------
# Domain / country exclusion lists
# ---------------------------------------------------------------------------

EXCLUDE_DOMAINS = {
    # Job boards / aggregators (pure aggregators with no employer identity)
    "indeed.com", "glassdoor.com", "ziprecruiter.com", "manpower.com",
    "eluta.ca", "jobillico.com", "jobright.ai",
    "jobservicehub.com", "kelolandemployment.com", "appliedeconjobs.substack.com",
    # Non-US LinkedIn subdomains (country-specific)
    "ca.linkedin.com", "au.linkedin.com", "uk.linkedin.com",
    # Non-US healthcare
    "nshealth.ca", "monashhealth.org", "nhs.uk",
    "workincharities.co.uk", "lcrbemore.co.uk",
    "careers.albertahealthservices.ca", "careers.wrha.mb.ca",
    "londonhealthjobs.ca", "ontariohealthathome.ca", "muhc.ca",
    "ottawahospital.on.ca", "ramsaycareers.com.au",
    "opportunitiesforyoungkenyans.co.ke",
    "ksatria.io",
    "pharmabharat.com",
    # Staffing / non-employer
    "insightglobal.com",
    # Other non-relevant
    "lifestyle.harianterbit.com",
}

# Domains where we allow results but need to extract employer from title
PASSTHROUGH_DOMAINS = {
    "linkedin.com", "career.com", "builtin.com", "higheredjobs.com",
    "insidehighered.com", "kalibrr.com",
}

EXCLUDE_DOMAIN_KEYWORDS = [
    ".ca/", ".co.uk/", ".com.au/", ".co.ke/", ".nhs.",
]

NON_US_TITLE_KEYWORDS = [
    "canada", "ontario", "toronto", "ottawa", "winnipeg", "edmonton",
    "australia", "melbourne", "sydney", "brisbane", "greater melbourne",
    "kenya", "kenyatta", "india", "bengaluru", "philippines",
    "united kingdom", "nhs vacancy",
    "st vincent's health australia",
]

# ---------------------------------------------------------------------------
# Relevance filters
# ---------------------------------------------------------------------------

# Title must contain at least one of these to be considered relevant
RELEVANT_KEYWORDS = [
    "medical record", "health information", "him ", "him-", "h.i.m",
    "ehr", "electronic health record", "health record",
    "chart", "coding", "medical coder",
    "documentation rep", "release of information", "roi ",
    "epic analyst", "epic application", "epic security",
    "epic beaker", "clinical informatics", "ehr application",
    "ehr analyst", "applications analyst-ehr", "applications analyst ehr",
    "archive data", "systems analyst", "clindoc",
    "health record associate", "file clerk",
    "admitting clerk", "registration clerk", "admissions clerk",
    "patient access clerk", "ward clerk", "unit clerk",
    "inpatient medical clerk", "outpatient clinic clerk",
    "er admitting", "emergency department clerk",
]

# Titles containing these are excluded even if they match above
EXCLUDE_TITLE_KEYWORDS = [
    "nurse", "nursing", "doctor", "physician", "medical officer",
    "sales manager", "call centre", "shipping", "receiving",
    "wic integrity", "credentialing specialist",
    "careers at", "job opportunities", "job search",
    "top healthcare it skills", "careers in health information technology",
    "junior data analyst", "cognizant hiring",
    "total rewards", "neurology data hub",
    "archive data analyst", "sr archive data",
    "now hiring",  # vendor homepages like "1st Providers Choice EMR - Now Hiring"
    "ramsay careers",  # Australian hospital chain
]

# These are career landing pages, not individual job postings
LANDING_PAGE_PATTERNS = [
    r"careers\.epic\.com/jobs/?$",
    r"/careers/?$",
    r"/careers/home/?$",
    r"/join-our-team/?$",
    r"/job-list/",
    r"category/.*-jobs/",
    r"search-jobs/",
    r"linkedin\.com/company/",  # Company pages, not job postings
]

# Title patterns that indicate aggregator pages, not real job postings
AGGREGATOR_TITLE_PATTERNS = [
    r"\d{1,3},?\d{3}\+?\s+\w+.*\bjobs\b",  # "47,000+ Medical Records Clerk jobs"
    r"\d+\s+\w+.*\bjobs\b\s+in\s+",  # "84 Medical Records Clerk jobs in Ottawa"
    r"^\d+\s+vacancies",  # "23 Vacancies Open At..."
]


def is_excluded_domain(url: str) -> bool:
    """Check if URL's domain is in the exclusion list."""
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return True
    for d in EXCLUDE_DOMAINS:
        if host == d or host.endswith("." + d):
            return True
    return False


def is_non_us_url(url: str) -> bool:
    """Heuristic: check URL path for non-US TLD patterns."""
    lower = url.lower()
    for kw in EXCLUDE_DOMAIN_KEYWORDS:
        if kw in lower:
            return True
    return False


def is_landing_page(url: str) -> bool:
    """Check if URL looks like a generic careers landing page."""
    for pat in LANDING_PAGE_PATTERNS:
        if re.search(pat, url, re.IGNORECASE):
            return True
    return False


def is_relevant_title(title: str) -> bool:
    """Check if the job title/page title relates to medical records/HIM/EHR."""
    t = title.lower()
    # First check exclusions
    for kw in EXCLUDE_TITLE_KEYWORDS:
        if kw in t:
            return False
    # Then check relevance
    for kw in RELEVANT_KEYWORDS:
        if kw in t:
            return True
    return False


def is_non_us_title(title: str) -> bool:
    t = title.lower()
    for kw in NON_US_TITLE_KEYWORDS:
        if kw in t:
            return True
    return False


def extract_company_from_title(title: str) -> str:
    """Try to extract company name from LinkedIn-style titles or other patterns."""
    # Pattern: "Company hiring Title in Location | LinkedIn"
    m = re.match(r"^(.+?)\s+hiring\s+", title)
    if m:
        return m.group(1).strip()
    # Pattern: "Title at Company"
    m = re.search(r"\bat\s+(.+?)(?:\s*\||\s*-\s*|\s*$)", title)
    if m:
        return m.group(1).strip()
    # Pattern: "Title - Company"
    m = re.match(r"^.+?\s*-\s*(.+?)(?:\s*\|.*)?$", title)
    if m:
        candidate = m.group(1).strip()
        # Avoid returning generic suffixes
        if len(candidate) > 3 and "job" not in candidate.lower():
            return candidate
    return ""


def extract_job_title_from_title(title: str) -> str:
    """Extract the actual job role from the page title."""
    # Remove " | LinkedIn", " | Career.com", etc.
    t = re.sub(r"\s*\|.*$", "", title).strip()
    # Remove "Company hiring " prefix
    t = re.sub(r"^.+?\s+hiring\s+", "", t, flags=re.IGNORECASE).strip()
    # Remove " in Location" suffix
    t = re.sub(r"\s+in\s+[\w\s,]+$", "", t).strip()
    # Remove " at Company" suffix
    t = re.sub(r"\s+at\s+.+$", "", t).strip()
    # Remove " - Company" suffix
    t = re.sub(r"\s*-\s*[^-]+$", "", t).strip()
    return t if t else title


def extract_location_from_title(title: str) -> str:
    """Try to extract location from title string."""
    # Pattern: "in City, ST"
    m = re.search(r"\bin\s+([\w\s]+,\s*[A-Z]{2})\b", title)
    if m:
        return m.group(1).strip()
    return ""


def extract_company_domain(url: str, company_name: str = "") -> str:
    """Extract the root domain from a job URL.

    For LinkedIn/aggregator URLs, tries to infer domain from company name.
    For direct employer URLs, extracts from the URL itself.
    """
    try:
        host = urlparse(url).netloc.lower()
        # Remove www.
        host = re.sub(r"^www\.", "", host)

        # If this is a LinkedIn or aggregator URL, we can't get the employer domain from URL
        if "linkedin.com" in host or host in PASSTHROUGH_DOMAINS:
            # Try to guess from company name
            if company_name:
                slug = re.sub(r"[^a-z0-9]+", "", company_name.lower())
                return f"{slug}.com"  # Best guess; will need manual review
            return ""

        # For subdomains like jobs.bilh.org, return bilh.org
        parts = host.split(".")
        if len(parts) > 2:
            return ".".join(parts[-2:])
        return host
    except Exception:
        return ""


# Known company domain mappings for LinkedIn results
COMPANY_DOMAIN_MAP = {
    "penn medicine": "pennmedicine.org",
    "university of pennsylvania health system": "pennmedicine.org",
    "maimonides medical center": "maimonides.org",
    "magee general hospital": "mageegeneralhospital.com",
    "nyu langone health": "nyulangone.org",
    "kaiser permanente": "kaiserpermanente.org",
    "northwell health": "northwell.edu",
    "baptist health": "baptisthealth.net",
    "ssm health": "ssmhealth.com",
    "rwjbarnabas health": "rwjbh.org",
    "prime healthcare": "primehealthcare.com",
    "beth israel lahey health": "bilh.org",
    "jefferson health": "jeffersonhealth.org",
    "memorial": "memorial.health",
    "rush university medical center": "rush.edu",
    "university of kentucky": "uky.edu",
    "upmc": "upmc.com",
    "boston medical center": "bmc.org",
    "geisinger": "geisinger.org",
    "onslow memorial hospital": "onslowmemorial.org",
    "carthage area hospital": "carthagehospital.com",
    "appalachian regional healthcare": "arh.org",
    "cabell huntington hospital": "cabellhuntington.org",
    "natchitoches regional medical center": "nrmchospital.org",
    "oroville hospital": "orovillehospital.com",
    "san joaquin general hospital": "sanjoaquingeneral.org",
}


def lookup_company_domain(company_name: str) -> str:
    """Look up known company domain from company name."""
    cn = company_name.lower().strip()
    for key, domain in COMPANY_DOMAIN_MAP.items():
        if key in cn or cn in key:
            return domain
    return ""


def parse_exa_file(filepath: str) -> list:
    """Parse an Exa MCP tool-result file and return raw results."""
    with open(filepath, "r") as f:
        data = json.load(f)
    # The file is a JSON array with one element containing {"type":"text","text":"..."}
    if isinstance(data, list) and len(data) > 0 and "text" in data[0]:
        inner = json.loads(data[0]["text"])
        return inner.get("results", [])
    return []


def process_results(all_results: list) -> list:
    """Filter, deduplicate, and format results into job postings."""
    seen = set()  # (normalized_company, normalized_title)
    jobs = []

    for r in all_results:
        url = r.get("url", "")
        title = r.get("title", "")

        # Apply filters
        if is_excluded_domain(url):
            continue
        if is_non_us_url(url):
            continue
        if is_landing_page(url):
            continue
        if is_non_us_title(title):
            continue
        # Check for aggregator title patterns
        is_aggregator = False
        for pat in AGGREGATOR_TITLE_PATTERNS:
            if re.search(pat, title, re.IGNORECASE):
                is_aggregator = True
                break
        if is_aggregator:
            continue
        if not is_relevant_title(title):
            continue

        # Extract fields
        company = extract_company_from_title(title)
        job_title = extract_job_title_from_title(title)
        location = extract_location_from_title(title)

        # For LinkedIn job view URLs, try harder to extract company from title
        if "linkedin.com/jobs/view/" in url:
            # Pattern: "... at CompanyName 1234567890"
            m = re.search(r"\bat\s+(.+?)(?:\s+\d{5,}|\s*$)", title)
            if m:
                company = m.group(1).strip().rstrip("| -")
            # If company came out as "LinkedIn", re-extract
            if company.lower() == "linkedin":
                m = re.search(r"at\s+(.+?)(?:\s*\||\s*-\s*|\s*$)", title)
                if m:
                    company = m.group(1).strip()

        # Skip if company is still "LinkedIn" or empty vendor pages
        if company.lower() in ("linkedin", "now hiring", ""):
            # For direct employer sites, use the domain as company hint
            host = urlparse(url).netloc.lower()
            if "linkedin.com" in host:
                pass  # keep going, domain will be empty
            else:
                pass  # keep going with empty company

        domain = lookup_company_domain(company) if company else ""
        if not domain:
            domain = extract_company_domain(url, company)

        # Skip vendor homepages (URL is just a root domain)
        if re.match(r"^https?://[^/]+/?$", url):
            continue

        # Deduplicate
        key = (company.lower().strip(), job_title.lower().strip())
        if key in seen:
            continue
        seen.add(key)

        jobs.append({
            "company_name": company,
            "job_title": job_title,
            "location": location,
            "job_url": url,
            "company_domain": domain,
        })

    # Number them
    for i, job in enumerate(jobs, 1):
        job["job_id"] = str(i)

    return jobs


def main():
    parser = argparse.ArgumentParser(
        description="Format Exa MCP job search results into clean JSON."
    )
    parser.add_argument(
        "files", nargs="+", help="Exa MCP tool-result JSON files"
    )
    parser.add_argument(
        "--output", "-o", default=None,
        help="Output file path (default: stdout)"
    )
    parser.add_argument(
        "--csv", dest="write_csv", action="store_true",
        help="Also write a CSV version (same path with .csv extension)"
    )
    args = parser.parse_args()

    # Collect all results from all files
    all_results = []
    for fp in args.files:
        results = parse_exa_file(fp)
        print(f"  Loaded {len(results)} results from {fp}", file=sys.stderr)
        all_results.extend(results)

    print(f"  Total raw results: {len(all_results)}", file=sys.stderr)

    # Process
    jobs = process_results(all_results)
    print(f"  After filtering: {len(jobs)} qualifying jobs", file=sys.stderr)

    # Output JSON
    output_json = json.dumps(jobs, indent=2)
    if args.output:
        with open(args.output, "w") as f:
            f.write(output_json + "\n")
        print(f"  JSON written to {args.output}", file=sys.stderr)
    else:
        print(output_json)

    # Optionally write CSV
    if args.write_csv and args.output:
        csv_path = re.sub(r"\.json$", ".csv", args.output)
        if csv_path == args.output:
            csv_path = args.output + ".csv"
        fieldnames = ["job_id", "company_name", "job_title", "location", "job_url", "company_domain"]
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(jobs)
        print(f"  CSV written to {csv_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
