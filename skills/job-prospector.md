---
name: job-prospector
description: End-to-end job prospecting pipeline. Finds open roles matching search criteria, identifies hiring managers, finds their emails via Hunter.io, and saves personalized outreach emails as Gmail drafts. Use when the user wants to prospect jobs, find hiring contacts, or run the full outreach pipeline.
context: fork
---

# Job Prospector Pipeline

Autonomous lead prospecting: job discovery → hiring manager identification → email enrichment → Gmail draft creation → Google Sheets export.

## Tool Restrictions (Critical)

- Exa searches: ONLY use `web_search_advanced_exa`
- Email enrichment: Hunter.io via `curl` in Bash
- Email drafts: Gmail MCP `create_draft` tool
- Never run Exa searches in main context — always spawn Task agents
- Browser automation: Claude in Chrome tools for Google Sheets import

## Data Persistence (Critical)

**Every stage must save its results to CSV before proceeding to the next stage.** This ensures no data is lost if a stage fails or the session is interrupted.

All CSVs are saved to the `data/` directory:
- `data/jobs.csv` — all discovered job postings (written after Stage 1)
- `data/contacts.csv` — all identified contacts with job context (written after Stage 2)
- `data/enriched_contacts.csv` — contacts with email data (written after Stage 3)

### CSV Schemas

**jobs.csv** (written after Stage 1):
```
job_id,company_name,job_title,location,job_url,company_domain,date_found
1,Memorial Hermann,Medical Records Clerk,Houston TX,https://...,memorialhermann.org,2026-02-24
```

**contacts.csv** (written after Stage 2):
```
job_id,company_name,job_title,job_url,contact_name,contact_title,department,contact_location,local_match,linkedin_url,rank_reason
1,Memorial Hermann,Medical Records Clerk,https://...,Jane Smith,Director of HIM,HIM,Houston TX,Yes,https://linkedin.com/in/janesmith,HIM director same city
```

**enriched_contacts.csv** (written after Stage 3):
```
job_id,company_name,job_title,job_url,contact_name,contact_title,department,contact_location,local_match,linkedin_url,email,email_confidence,draft_status
1,Memorial Hermann,Medical Records Clerk,https://...,Jane Smith,Director of HIM,HIM,Houston TX,Yes,https://linkedin.com/in/janesmith,jane@memorialhermann.org,92,Saved
```

### How to Write CSVs

Use the Write tool to create/overwrite each CSV. Always include the header row. Quote any field that contains commas.

## Input

Ask the user for:
- **Role keywords**: e.g. "medical records clerk", "HIM technician", "EHR analyst" (HIMS and IT functions only — not HR/recruiting)
- **Location** (optional): city, state, or region
- **Number of results**: how many jobs to prospect (default: 10)
- **Email template**: use custom template or default from `hiring-manager-search/assets/email_template.md`

## Incremental Mode (Automated)

When the prompt specifies a state file path (e.g., "State file: data/state.json"), operate in incremental mode:

1. **Read state file**: Parse `data/state.json` at startup. If the file doesn't exist or is empty, create it with an empty `jobs` object.
2. **Use search_config from state**: Instead of asking the user, use the `search_config` block in the state file for role keywords, location, and result count.
3. **Dedup after Stage 1**: After job discovery, compute each job's dedup key as `company_domain::lowercase(job_title)`. Drop any job whose key already exists in `state.jobs`. If zero new jobs remain, update `last_run` timestamp and set `last_run_status: "no_new_jobs"`, then exit.
4. **Run Stages 2-4 on new jobs only**.
5. **Update state file atomically**: After completion, append all new jobs (with their contacts, emails, draft status) to `state.jobs`. Update `last_run` timestamp and `last_run_status`. Write to a temp file first (`data/state.tmp.json`), then rename over `data/state.json` to prevent corruption on crash.
6. **Output**: Write the summary table to stdout. Do NOT ask follow-up questions or wait for user input.

### State File Schema

```json
{
  "version": 1,
  "last_run": "2026-02-24T12:00:00Z",
  "last_run_status": "success",
  "search_config": {
    "role_keywords": ["medical records clerk", "EHR analyst"],
    "location": "Texas",
    "num_results": 10
  },
  "jobs": {
    "memorialhermann.org::medical records clerk": {
      "company_name": "Memorial Hermann",
      "job_title": "Medical Records Clerk",
      "location": "Houston, TX",
      "job_url": "https://...",
      "company_domain": "memorialhermann.org",
      "first_seen": "2026-02-24T06:00:00Z",
      "last_seen": "2026-02-24T12:00:00Z",
      "contacts": [
        {
          "name": "Jane Smith",
          "title": "Director of HIM",
          "department": "HIM",
          "location": "Houston, TX",
          "local_match": true,
          "email": "jane.smith@memorialhermann.org",
          "email_confidence": 92,
          "draft_created": true,
          "draft_date": "2026-02-24T06:00:00Z"
        }
      ]
    }
  }
}
```

## Pipeline

### Stage 1: Job Discovery

Spawn Task agent(s) to find open job postings via Exa.

**Target roles are in HIMS and IT functions ONLY:**
- Medical Records (clerks, technicians, coders, specialists)
- Health Information Management (HIM/HIMS coordinators, analysts, associates)
- Health IT / EHR (Epic analysts, EHR application analysts, clinical informatics, health IT specialists)

**Do NOT search for HR, talent acquisition, recruiting, or administrative roles.** HR contacts are found in Stage 2 as decision-makers to contact — they are not the jobs we're prospecting.

Use `web_search_advanced_exa` with `type: "auto"` and no category (job postings are general web content). Generate 2-3 query variations for coverage using `additionalQueries`. Run **multiple parallel searches** to maximize coverage — at least 3 searches targeting different role types.

Example searches:
```
// Search 1 — Medical Records roles
web_search_advanced_exa {
  "query": "medical records clerk hospital job opening hiring",
  "additionalQueries": ["medical records technician healthcare careers", "medical records specialist hospital apply"],
  "numResults": 40,
  "type": "auto",
  "livecrawl": "fallback",
  "startPublishedDate": "2025-10-01"
}

// Search 2 — HIM roles
web_search_advanced_exa {
  "query": "health information management clerk hospital hiring",
  "additionalQueries": ["HIM technician healthcare job opening", "health information associate medical center careers"],
  "numResults": 40,
  "type": "auto",
  "livecrawl": "fallback",
  "startPublishedDate": "2025-10-01"
}

// Search 3 — EHR / Health IT roles
web_search_advanced_exa {
  "query": "EHR analyst hospital health system job opening",
  "additionalQueries": ["Epic analyst healthcare hiring", "health IT specialist medical center careers"],
  "numResults": 40,
  "type": "auto",
  "livecrawl": "fallback",
  "startPublishedDate": "2025-10-01"
}
```

Tune `numResults` to 2-3x the user's requested count to allow for deduplication and filtering. Run all searches in parallel for speed.

**Filtering**: After receiving results, discard any postings that are not HIMS or IT roles (e.g., admitting clerks, unit clerks, ward clerks, patient registration, nursing, HR, recruiting roles). Only keep roles that clearly fall within medical records, HIM, or health IT.

The agent must return compact JSON only:
```json
[
  {
    "job_id": "1",
    "company_name": "Memorial Hermann",
    "job_title": "Medical Records Clerk",
    "location": "Houston, TX",
    "job_url": "https://...",
    "company_domain": "memorialhermann.org"
  }
]
```

After receiving results, deduplicate by company+title and trim to the user's requested count.

**Save to CSV**: Immediately write `data/jobs.csv` with all discovered jobs (header + one row per job). This persists the data before moving on.

### Stage 2: Hiring Manager Identification

For each job posting, spawn a Task agent to find **multiple** contacts. The goal is to surface every relevant person at the company — not just one.

#### Contact Qualifications

A qualified contact must be **manager level or above** in one of these departments:
- Medical Records / Health Information Management (HIM/HIMS)
- EHR / Health IT
- HR / Talent Acquisition
- Operations (if overseeing the above)

**Local proximity is a strong signal.** If a contact is located in or near the same city as the job posting, they are more likely to be the actual hiring manager. Prioritize local contacts in ranking.

#### Search Strategy

Run **3 parallel searches** per job within each agent:

**Search A — Medical Records / HIM leadership:**
```
web_search_advanced_exa {
  "query": "[company_name] medical records manager director HIM HIMS",
  "category": "people",
  "numResults": 15,
  "type": "auto"
}
```

**Search B — HR / Talent Acquisition leadership:**
```
web_search_advanced_exa {
  "query": "[company_name] HR manager director talent acquisition recruiting",
  "category": "people",
  "numResults": 15,
  "type": "auto"
}
```

**Search C — EHR / Health IT leadership:**
```
web_search_advanced_exa {
  "query": "[company_name] EHR health IT manager director",
  "category": "people",
  "numResults": 15,
  "type": "auto"
}
```

Run all three in parallel within each agent.

#### Filtering & Ranking

From the combined results, the agent must:
1. **Filter**: Keep only people who are manager level or above (Manager, Director, VP, Chief, Head of, etc.). Discard individual contributors, coordinators, specialists, clerks, analysts.
2. **Deduplicate**: Merge by name across the three searches.
3. **Rank** by these signals (best → worst):
   - Located in the same city/region as the job posting (strongest signal)
   - Title directly relates to the job's department (e.g., HIM Director for a medical records clerk role)
   - Senior title in HR/TA at the same company
   - Generic senior title at the company
4. **Return all qualified contacts** (no artificial cap), but at minimum 1 contact per job even if they don't perfectly match the qualifications above — fall back to the best available person at the company.

#### Agent Return Schema

```json
{
  "job_id": "1",
  "contacts": [
    {
      "name": "Jane Smith",
      "title": "Director of Health Information Management",
      "department": "HIM",
      "location": "Houston, TX",
      "local_match": true,
      "linkedin": "https://linkedin.com/in/janesmith",
      "rank_reason": "HIM director, same city as job"
    },
    {
      "name": "John Doe",
      "title": "VP Human Resources",
      "department": "HR",
      "location": "Houston, TX",
      "local_match": true,
      "linkedin": "https://linkedin.com/in/johndoe",
      "rank_reason": "HR VP, same city as job"
    }
  ]
}
```

Spawn all job agents in a single message for parallelism.

**Save to CSV**: After all agents return, immediately write `data/contacts.csv` with all contacts (one row per contact, with job context columns included). This preserves job URLs and LinkedIn URLs.

### Stage 3: Email Enrichment via Hunter.io

For **each contact** (not each job — each contact across all jobs), spawn a Task agent to find their email.

The agent reads the Hunter.io API key from the environment:
```bash
source .gitignore/.env
curl -s "https://api.hunter.io/v2/email-finder?first_name=Jane&last_name=Smith&domain=memorialhermann.org&api_key=$HUNTER_API_KEY"
```

Parse the response:
- `data.email` → the email address
- `data.score` → confidence score (0-100)
- Skip results with score < 50

Agent returns:
```json
{
  "job_id": "1",
  "contact_name": "Jane Smith",
  "email": "jane.smith@memorialhermann.org",
  "email_confidence": 92
}
```

Spawn all email agents in parallel. Rate limit: batch in groups of 10 if more than 15 lookups.

**Save to CSV**: After all email agents return, immediately write `data/enriched_contacts.csv` with all contacts including email and confidence data. Also add a `draft_status` column (initially empty, filled in Stage 4).

### Stage 4: Email Drafting via Gmail

For **each contact** with a valid email (confidence >= 50), spawn a Task agent to:

1. Read the email template from `hiring-manager-search/assets/email_template.md`
2. Fill in merge fields with prospect data
3. Personalize the email body — reference the specific job title, company, and any relevant details from that contact's profile
4. Call Gmail MCP `create_draft` with:
   - `to`: the contact's email
   - `subject`: filled template subject
   - `body`: personalized email body (plain text)

Each job may produce **multiple drafts** (one per qualified contact with a valid email).

Spawn all draft agents in parallel.

### Stage 5: Google Sheets Export

After Stage 4 completes (or after Stage 3 if email drafting is skipped), export the data to Google Sheets using Claude in Chrome browser automation.

#### Steps:

1. **Open Google Sheets**: Use `tabs_context_mcp` to check current tabs, then `tabs_create_mcp` to open `https://sheets.google.com`.
2. **Create a new spreadsheet**: Click "+ Blank" to create a new sheet. Name it "Job Prospector — [today's date]".
3. **Create "Jobs" sheet**: Populate the first sheet with the contents of `data/jobs.csv`:
   - Row 1: Headers — Job ID, Company, Job Title, Location, Job URL, Company Domain, Date Found
   - Rows 2+: One row per job
4. **Create "Contacts" sheet**: Add a second sheet tab. Populate it with the contents of `data/enriched_contacts.csv`:
   - Row 1: Headers — Job ID, Company, Job Title, Job URL, Contact Name, Contact Title, Department, Contact Location, Local Match, LinkedIn URL, Email, Email Confidence, Draft Status
   - Rows 2+: One row per contact
5. **Format**: Bold the header rows. Auto-resize columns if possible.

#### Fallback

If browser automation fails (Chrome not available, extension not responding), skip this stage and tell the user:
- CSVs are saved at `data/jobs.csv`, `data/contacts.csv`, and `data/enriched_contacts.csv`
- They can manually import to Google Sheets via File → Import

## Output

After all stages complete, present a summary table grouped by job:

```
| # | Company | Job Title | Contact | Contact Title | Local? | Email | Confidence | Draft |
|---|---------|-----------|---------|---------------|--------|-------|------------|-------|
| 1 | Memorial Hermann | Medical Records Clerk | Jane Smith | Dir. of HIM | Yes | jane@... | 92% | Saved |
| 1 | Memorial Hermann | Medical Records Clerk | John Doe | VP of HR | Yes | john@... | 85% | Saved |
| 2 | HCA Healthcare | EHR Analyst | ... | ... | ... | ... | ... | ... |
```

Then list:
- **High confidence**: contacts with email confidence >= 80%
- **Low confidence**: contacts with email confidence 50-79% (verify manually)
- **No email found**: contacts where Hunter.io returned nothing or confidence < 50%
- **No contacts found**: jobs where Stage 2 returned no results
- **Google Sheet link**: URL to the exported spreadsheet (if Stage 5 succeeded)
- **Local CSVs**: paths to `data/jobs.csv`, `data/contacts.csv`, `data/enriched_contacts.csv`

## Error Handling

- If Exa returns no job results: suggest broadening keywords or removing location filter
- If no hiring managers found for a company: flag it and continue with remaining jobs
- If Hunter.io API key is missing: stop and instruct user to add `HUNTER_API_KEY` to `.gitignore/.env`
- If Gmail MCP is not available: output the draft emails as text instead of saving to Gmail
- If any stage partially fails: complete what's possible and report failures in the summary
- If state file is corrupt or unparseable: back up the file as `data/state.json.bak`, start fresh with empty state, and log a warning
- If budget limit is hit mid-pipeline: save partial state (whatever stages completed) before exiting
