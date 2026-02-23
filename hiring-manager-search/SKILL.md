---
name: hiring-manager-search
description: Finds hiring managers for job postings using Exa people search. Takes a JSON array of job postings and returns the same array enriched with hiring manager name, title, LinkedIn URL, and email where findable. Use this skill whenever the user provides job postings and wants to find who to contact, who is hiring, or who the recruiter or hiring manager is.
---

# Hiring Manager Search

Given a JSON array of job postings, find the likely hiring manager or recruiter at each company and enrich each entry with contact details.

## Tool Requirement

ONLY use `web_search_advanced_exa`. Do not use any other search tools.

## Input

A JSON array where each object has at minimum:
- `company_name` — name of the hiring company
- `job_title` — the open role
- `location` — city/state (optional but helpful)
- `company_domain` — company website (optional but helpful)

Other fields (job_id, job_url, source, etc.) should be passed through unchanged.

## Output

Return the same JSON array with these fields populated where found:
- `poster_name` — full name of the hiring manager or recruiter
- `poster_title` — their job title
- `poster_linkedin` — URL to their LinkedIn profile
- `poster_email` — public contact email if findable (leave blank if not)

## Execution Strategy

### Step 1: Determine department from job title

Map the job title to a department/function so searches target the right manager:
- Clinical/medical roles → HR, Clinical Operations, or Medical Director
- Administrative/clerical → HR, Office Manager, or Operations Manager
- Engineering/tech → Engineering Manager, CTO, VP Engineering
- Sales → Sales Manager, VP Sales
- Finance → Finance Director, CFO

### Step 2: For each job posting, spawn a Task agent

Never run Exa searches in the main context. Spawn one Task agent per job posting. Pass the agent:
- `company_name`
- `job_title`
- `department` (derived in Step 1)
- `location`
- `company_domain` (if non-empty)

The agent should:

**Search A — LinkedIn people discovery**
```
web_search_advanced_exa {
  "query": "[company_name] recruiter HR talent acquisition",
  "category": "people",
  "numResults": 10,
  "type": "auto"
}
```

**Search B — Hiring manager by department**
```
web_search_advanced_exa {
  "query": "[company_name] [department] manager director",
  "category": "people",
  "numResults": 10,
  "type": "auto"
}
```

Run Search A and Search B in parallel.

**Search C — Email/contact (only if company_domain is non-empty)**
```
web_search_advanced_exa {
  "query": "site:[company_domain] contact email HR recruiter",
  "numResults": 5,
  "type": "auto",
  "livecrawl": "fallback"
}
```

### Step 3: Agent selection logic

From the combined results, the agent should pick the single best match — the person most likely to be the decision-maker or point of contact for this specific role. Prefer:
1. A recruiter or HR person at the company if the role is support/admin
2. A department manager or director if the role is professional/technical
3. A general HR contact as fallback

The agent returns a compact JSON object:
```json
{
  "job_id": "...",
  "poster_name": "Jane Smith",
  "poster_title": "Talent Acquisition Specialist",
  "poster_linkedin": "https://linkedin.com/in/janesmith",
  "poster_email": ""
}
```

If no credible match is found, return empty strings for all four fields.

### Step 4: Merge and output

After all agents finish, merge their results back into the original job posting objects. Output the complete enriched JSON array.

## Parallelism

Spawn all Task agents in a single message to run in parallel. Do not wait for one to finish before starting the next.

## Confidence Notes

After the JSON, add a brief section listing which postings had confident matches vs. low-confidence ones, so the user knows where to verify manually.

## Example Agent Prompt Template

```
You are a research agent. Search for the hiring manager or recruiter at a company for a job posting.

Job details:
- Company: [company_name]
- Role: [job_title]
- Department/function: [department]
- Location: [location]
- Company domain: [company_domain or "unknown"]

Use ONLY web_search_advanced_exa. Run these two searches in parallel:

Search 1:
{
  "query": "[company_name] recruiter HR talent acquisition",
  "category": "people",
  "numResults": 10,
  "type": "auto"
}

Search 2:
{
  "query": "[company_name] [department] manager director",
  "category": "people",
  "numResults": 10,
  "type": "auto"
}

[If company_domain is known, also run:]
Search 3:
{
  "query": "site:[company_domain] HR recruiter contact email",
  "numResults": 5,
  "type": "auto",
  "livecrawl": "fallback"
}

From the results, pick the single best hiring contact. Return ONLY this JSON (no other text):
{
  "job_id": "[job_id]",
  "poster_name": "",
  "poster_title": "",
  "poster_linkedin": "",
  "poster_email": ""
}
```
