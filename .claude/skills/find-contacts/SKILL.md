---
name: find-contacts
description: "Find hiring managers and company contacts for job postings using Exa people search. Takes jobs from data/jobs.csv and outputs contacts to data/contacts.csv. Use when the user wants to find contacts, hiring managers, or run Stage 2."
---

# Stage 2: Contact Search via Exa

Find hiring managers and facility phone numbers for each job posting using Exa's semantic people search and company search.

## Tools

- `web_search_advanced_exa` (Exa MCP) — people search with `category: "people"`
- `web_search_advanced_exa` — company phone lookup with `category: "company"`

## Workflow

```
- [ ] Step 1: Load jobs from data/jobs.csv
- [ ] Step 2: Group jobs by company (deduplicate contact searches)
- [ ] Step 3: Run parallel contact searches per company
- [ ] Step 4: Run company phone lookups
- [ ] Step 5: Rank and write data/contacts.csv
```

### Step 1: Load Jobs

Read `data/jobs.csv`. If the file doesn't exist or is empty, instruct user to run `/scrape-jobs` first.

### Step 2: Group by Company

Multiple jobs at the same company should share a single contact search. Group jobs by `company_domain` and search once per company.

### Step 3: Contact Search

For each unique company, spawn a **Task agent** that runs 3 parallel Exa searches:

**Search A — HIM/Medical Records leadership:**
```
web_search_advanced_exa:
  query: "HIM director OR health information management manager at {company_name} {location}"
  category: "people"
  numResults: 5
  includeDomains: ["linkedin.com"]
```

**Search B — HR/Talent Acquisition leadership:**
```
web_search_advanced_exa:
  query: "HR director OR talent acquisition manager OR recruiting manager at {company_name} {location}"
  category: "people"
  numResults: 5
  includeDomains: ["linkedin.com"]
```

**Search C — Health IT/Operations leadership:**
```
web_search_advanced_exa:
  query: "health IT director OR EHR manager OR operations director at {company_name} {location}"
  category: "people"
  numResults: 5
  includeDomains: ["linkedin.com"]
```

**Important Exa restrictions** (from `.agents/skills/exa-people-search/SKILL.md`):
- When using `category: "people"`, do NOT use `startPublishedDate`, `endPublishedDate`, or `includeText`/`excludeText` filters — they are incompatible
- Use multiple query phrasings to improve recall
- Parse LinkedIn profile titles in format: "Name - Title - Company | LinkedIn"

### Step 4: Company Phone Lookup

For each unique company, run a separate search for the facility phone number:

```
web_search_advanced_exa:
  query: "{company_name} {location} hospital phone number contact"
  numResults: 3
```

Extract phone numbers from result text/highlights. Prefer numbers associated with the specific facility location matching the job posting.

### Step 5: Rank and Output

**Contact ranking criteria:**
1. **Department match** (highest weight): HIM > HR > IT > Ops
2. **Seniority**: Director > VP > Manager > Supervisor
3. **Location match**: Contact in same city/state as job posting
4. **Profile completeness**: Has LinkedIn URL, clear title

**For each contact, extract:**
- `contact_name`: Full name from LinkedIn profile
- `contact_title`: Job title
- `department`: Inferred from title (HIM, HR, IT, Ops)
- `contact_location`: From LinkedIn profile
- `local_match`: `true` if location matches job posting
- `linkedin_url`: Full LinkedIn profile URL
- `company_phone`: From Step 4
- `rank_reason`: Brief explanation (e.g., "HIM Director, local match, top priority")

**Write `data/contacts.csv`** with columns:
```
job_id,company_name,job_title,job_url,contact_name,contact_title,department,contact_location,local_match,linkedin_url,company_phone,rank_reason
```

Return ALL qualified contacts (minimum 1, target 2-3 per company). Do not artificially cap results.

**Summary output:**
- Companies searched
- Total contacts found
- Contacts per department (HIM/HR/IT/Ops breakdown)
- Companies with no contacts found (flag for manual review)
- Exa search credits used

## Error Handling

- No contacts found for a company: Report it, suggest broadening search terms
- Exa rate limit: Batch companies in groups of 5, pause between batches
- LinkedIn profile parsing failure: Fall back to raw title text
