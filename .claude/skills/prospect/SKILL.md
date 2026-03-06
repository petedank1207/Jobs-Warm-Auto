---
name: prospect
description: "Full prospecting pipeline. Runs all 4 stages: scrape jobs, find contacts, enrich emails, draft outreach. Use when the user wants to run the complete pipeline, prospect, or find leads."
---

# Full Prospecting Pipeline

Orchestrates all 4 pipeline stages in sequence to go from job discovery to outreach drafts.

## Pipeline Stages

| Stage | Skill | Tool | Output |
|-------|-------|------|--------|
| 1. Job Discovery | `/scrape-jobs` | Apify | `data/jobs.csv` |
| 2. Contact Search | `/find-contacts` | Exa | `data/contacts.csv` |
| 3. Email Enrichment | `/enrich-emails` | Hunter.io | `data/enriched_contacts.csv` |
| 4. Outreach Drafts | `/draft-outreach` | Gmail MCP | Gmail drafts |
| 5. Export | Google Sheets | Browser | Master spreadsheet |

## Workflow

```
- [ ] Step 1: Confirm parameters and estimate total cost
- [ ] Step 2: Run Stage 1 — Job Discovery
- [ ] Step 3: Validate jobs.csv, run Stage 2 — Contact Search
- [ ] Step 4: Validate contacts.csv, run Stage 3 — Email Enrichment
- [ ] Step 5: Validate enriched_contacts.csv, run Stage 4 — Outreach Drafts
- [ ] Step 6: Export to Google Sheets
- [ ] Step 7: Final summary with recommendations
```

### Step 1: Confirm Parameters

Before starting, display and confirm:
- **Search terms**: Default HIMS/IT keywords (or user-provided)
- **Location**: Default United States (or user-provided)
- **Result count**: Default 10-20 jobs
- **Estimated API costs**:
  - Apify: ~$0.10-0.20 for job scraping
  - Exa: ~N searches (depends on unique companies found)
  - Hunter.io: ~N search + N verify credits (depends on contacts found)
- **Template**: `assets/templates/email_template.md` (or user-provided)

Confirm with user before proceeding.

### Steps 2-5: Execute Pipeline

Run each stage in sequence. Between stages:
1. Verify the output CSV exists and has data rows
2. Display a brief progress summary (rows found, any issues)
3. If a stage produces zero results, **stop the pipeline** and report — do not proceed to the next stage with empty input

If a stage partially fails (some items succeed, some fail), continue with successful items and report failures.

### Step 6: Google Sheets Export

After all stages complete, export the final data to Google Sheets via browser automation:
1. Open or create the master Google Sheet
2. Create/update "Jobs" tab with `data/jobs.csv` contents
3. Create/update "Contacts" tab with `data/enriched_contacts.csv` contents (including draft_status)

If browser automation fails, report the failure and note that CSVs in `data/` are the fallback.

### Step 7: Final Summary

Present a comprehensive summary:

```
## Pipeline Results

### Jobs Found
- New jobs: N | Existing: N | Total: N
- Sources: LinkedIn (N), Google Jobs (N)
- Companies: [list unique companies]

### Contacts Identified
- Total contacts: N across N companies
- By department: HIM (N), HR (N), IT (N), Ops (N)
- Companies with no contacts: [list]

### Emails Enriched
- Found: N | Not found: N
- Valid: N | Invalid: N | Unverified: N
- Credits used: N search + N verify

### Drafts Created
- Gmail drafts: N | File fallback: N | Skipped: N

### Top Opportunities
[Rank the best leads based on: email verified + HIM department contact + local match + recent job posting]

### Issues & Recommendations
[Any data quality concerns, missing contacts, low-confidence emails, etc.]
```

## Error Handling

- Any stage fails completely: Stop pipeline, save partial progress, report what completed
- API key missing: Stop and instruct user
- Gmail MCP unavailable: Stage 4 falls back to file, continue pipeline
- Google Sheets unavailable: Skip export, CSVs are the fallback
- If the pipeline is interrupted, the user can resume from any stage by running the individual skill command (e.g., `/find-contacts` to resume from Stage 2)
