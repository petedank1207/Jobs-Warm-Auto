---
name: scrape-jobs
description: "Scrape open job postings from LinkedIn and Google Jobs using Apify. Filters for HIMS/IT roles at US healthcare organizations. Use when the user wants to find jobs, scrape jobs, or run Stage 1 of the pipeline."
---

# Stage 1: Job Discovery via Apify

Scrape LinkedIn and Google Jobs for open HIMS/IT roles at US healthcare organizations using Apify actors.

## Actors

| Actor ID | Source |
|----------|--------|
| `bebity/linkedin-jobs-scraper` | LinkedIn Jobs |
| `epctex/google-jobs-scraper` | Google Jobs |

## Workflow

```
- [ ] Step 1: Calculate cost estimate and confirm with user
- [ ] Step 2: Fetch actor schemas via mcpc
- [ ] Step 3: Run both scrapers in parallel (Task agents)
- [ ] Step 4: Filter and deduplicate results
- [ ] Step 5: Write data/jobs.csv and summarize
```

### Step 1: Cost Estimate

Display the estimated Apify compute cost before running. Both actors are lightweight — typically < $0.10 per run for 10-20 results. Confirm with user before proceeding.

### Step 2: Fetch Actor Schemas

For each actor, fetch the input schema to understand available filters:

```bash
source .env && export APIFY_TOKEN && mcpc --json mcp.apify.com --header "Authorization: Bearer $APIFY_TOKEN" tools-call fetch-actor-details actor:="bebity/linkedin-jobs-scraper" | jq -r ".content"
```

```bash
source .env && export APIFY_TOKEN && mcpc --json mcp.apify.com --header "Authorization: Bearer $APIFY_TOKEN" tools-call fetch-actor-details actor:="epctex/google-jobs-scraper" | jq -r ".content"
```

### Step 3: Run Scrapers

Spawn two Task agents in parallel — one for each actor. Use the `run_actor.js` script from `.agents/skills/apify-ultimate-scraper/reference/scripts/run_actor.js`.

**LinkedIn Jobs:**
```bash
source .env && node --env-file=.env .agents/skills/apify-ultimate-scraper/reference/scripts/run_actor.js \
  --actor "bebity/linkedin-jobs-scraper" \
  --input '{"searchQueries": ["medical records clerk", "HIM technician", "health information management", "EHR analyst", "Epic analyst", "release of information specialist"], "location": "United States", "maxResults": 20}' \
  --output data/linkedin_jobs_raw.json \
  --format json
```

**Google Jobs:**
```bash
source .env && node --env-file=.env .agents/skills/apify-ultimate-scraper/reference/scripts/run_actor.js \
  --actor "epctex/google-jobs-scraper" \
  --input '{"queries": ["medical records clerk", "HIM technician", "health information management analyst", "EHR analyst healthcare"], "country": "US", "maxResults": 20}' \
  --output data/google_jobs_raw.json \
  --format json
```

Adapt the input JSON based on the actual schema returned in Step 2. The above is a starting template.

### Step 4: Filter and Deduplicate

After both scrapers complete, process combined results:

**Include roles matching these keywords** (case-insensitive):
- medical record, medical records
- health information, HIM, HIMS
- EHR, Epic, Cerner, electronic health record
- clinical informatics, health IT
- release of information, ROI specialist
- coding specialist, medical coder (HIM context only)

**Exclude:**
- HR, recruiting, talent acquisition, staffing
- Nurse, nursing, RN, LPN, CNA
- Admitting clerk, registration clerk, unit clerk, ward clerk
- Physician, provider, clinical (unless "clinical informatics")
- Results from staffing agency domains (roberthalf.com, indeed.com/hire, etc.)
- Non-US locations

**Deduplication:**
1. Load existing `data/jobs.csv` if it exists
2. For each new result, check if `job_url` already exists in the CSV
3. Skip duplicates, report count of new vs. existing

### Step 5: Write Output

Write `data/jobs.csv` with columns:

```
job_id,company_name,job_title,location,job_url,company_domain,source,date_found
```

- `job_id`: Generate a short unique ID (e.g., first 8 chars of UUID)
- `company_domain`: Extract from job URL or company website
- `source`: `linkedin` or `google_jobs`
- `date_found`: Today's date in ISO format

**Summary output:**
- Total jobs found (new + existing)
- New jobs added this run
- Duplicates skipped
- Breakdown by source (LinkedIn vs Google Jobs)
- List of unique companies with job counts

## Error Handling

- `APIFY_TOKEN not found`: Instruct user to add to `.env`
- `mcpc not found`: Run `npm install -g @apify/mcpc`
- Actor timeout: Reduce `maxResults` and retry
- Zero results: Try broader search terms, report to user
