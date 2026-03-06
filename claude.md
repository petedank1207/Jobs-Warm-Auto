# Tavrn GTM Agent

Autonomous outbound sales prospecting agent for Tavrn's healthcare provider staffing service. Finds open hospital HIM/IT jobs, identifies hiring managers, enriches email addresses, and drafts personalized outreach.

## Company Context

- **Company**: Tavrn — legal technology for personal injury law firms (document generation, medical record retrieval)
- **New Service**: Staff augmentation for hospital Health Information Management (HIM) teams
- **Value Prop**: We hire a dedicated person to learn your ROI process end-to-end — intake, validation, record compilation, QA, delivery, audit logging. No cost to the facility.
- **User**: Peter Dankert, Chief of Staff (peter.dankert@tavrn.ai)
- **North Star**: AI-enabled tooling that accelerates record retrieval for HIM teams. Staffing is the entry point.

## Pipeline Overview

The prospecting pipeline has 4 stages, each independently invocable:

| Stage | Command | Tool | Input | Output |
|-------|---------|------|-------|--------|
| 1. Job Discovery | `/scrape-jobs` | Apify (`bebity/linkedin-jobs-scraper`, `epctex/google-jobs-scraper`) | Role keywords, location | `data/jobs.csv` |
| 2. Contact Search | `/find-contacts` | Exa (people search + company search) | `data/jobs.csv` | `data/contacts.csv` |
| 3. Email Enrichment | `/enrich-emails` | Hunter.io (email-finder + email-verifier) | `data/contacts.csv` | `data/enriched_contacts.csv` |
| 4. Outreach Drafts | `/draft-outreach` | Gmail MCP + cold-email skill | `data/enriched_contacts.csv` | Gmail drafts |

Run all 4 stages in sequence with `/prospect`.

### Data Flow

Google Sheets is the master storage for v1. CSV files in `data/` are intermediate persistence — every stage writes its CSV before proceeding to the next stage. If Google Sheets export fails, CSVs are the fallback.

## Integrations & API Keys

All keys are stored in `.env` at project root. Source with `source .env`.

| Integration | Env Var | Purpose | Free Tier Limits |
|-------------|---------|---------|-----------------|
| Apify | `APIFY_TOKEN` | Job scraping (LinkedIn + Google Jobs) | $5/month free compute |
| Exa | `EXA_API_KEY` | People search, company research | 1000 searches/month |
| Hunter.io | `HUNTER_API_KEY` | Email find + verification | 25 searches + 100 verifications/month |
| Gmail | OAuth at `~/.gmail-mcp/` | Draft creation | Unlimited |
| Slack | MCP server | Agent communication | Unlimited |

### MCP Servers

- **Exa**: `web_search_advanced_exa` — people search (Stage 2), company research
- **Gmail**: `gmail_create_draft`, `gmail_search_messages`, `gmail_list_drafts`
- **Slack**: `slack_send_message`, `slack_search_channels` — for asking clarifying questions

### Apify CLI

Apify actors are invoked via the `mcpc` CLI tool. See `.agents/skills/apify-ultimate-scraper/SKILL.md` for the full workflow pattern (fetch schema → run actor → parse results).

## Data Schemas

### jobs.csv (Stage 1 output)

```
job_id,company_name,job_title,location,job_url,company_domain,source,date_found
```

- `job_id`: Auto-generated UUID
- `source`: `linkedin` or `google_jobs`
- `date_found`: ISO date when the job was scraped
- Deduplication key: `job_url` (exact match)

### contacts.csv (Stage 2 output)

```
job_id,company_name,job_title,job_url,contact_name,contact_title,department,contact_location,local_match,linkedin_url,company_phone,rank_reason
```

- `local_match`: `true` if contact location matches job location
- `rank_reason`: Why this contact was selected (e.g., "HIM Director, local match")
- `company_phone`: Facility phone number for cold calling

### enriched_contacts.csv (Stage 3 output)

All `contacts.csv` columns plus:

```
email,email_confidence,email_verified,verification_status
```

- `email_confidence`: Hunter.io score (0-100)
- `email_verified`: `true`, `false`, or `unverified`
- `verification_status`: `valid`, `invalid`, `accept_all`, `disposable`, `unknown`

## Target Roles

### Stage 1 — Jobs to Scrape (HIMS + IT only)

Include:
- Medical Records (clerks, technicians, coders, specialists)
- Health Information Management (HIM/HIMS coordinators, analysts, associates)
- Health IT / EHR (Epic analysts, EHR application analysts, clinical informatics)
- Release of Information (ROI specialists, correspondence clerks)

Exclude:
- HR, recruiting, talent acquisition roles
- Administrative/nursing/clinical roles
- Generic hospital clerks (admitting, unit, ward, registration)
- Staffing agency postings

### Stage 2 — Contacts to Find (decision-makers)

Search for manager-level or above individuals. Priority order:
1. HIM/Medical Records leadership
2. HR/Talent Acquisition leadership
3. Health IT/EHR leadership
4. Operations leadership

Local proximity to job posting is the strongest ranking signal.

## Outreach Principles

- Frame as **staff augmentation** — never "outsourcing" or "taking over"
- "We hire a dedicated person to learn your process end-to-end"
- "No cost to the facility"
- Subject lines: ASCII only, no Unicode, no em-dashes
- Tone: peer-to-peer, not vendor-to-customer
- Templates: `assets/templates/email_template.md` and `assets/templates/linkedin_message.md`
- Writing frameworks: `.agents/skills/cold-email/` (PAS, BAB, etc.)

## Agent Behaviors

### Token Isolation

Never run Exa or Apify operations in the main context. Always spawn Task agents for API calls. Agents return compact JSON — no raw search results in the main thread.

### Cost Consciousness

Before any batch API operation, calculate and display the estimated credit cost:
- Hunter.io: 1 credit per email-finder call, 1 credit per email-verifier call (25 + 100 free/month)
- Apify: varies by actor — display estimated cost before running
- Exa: 1 search credit per query (1000 free/month)

Always confirm with the user before proceeding with operations that consume significant credits.

### Error Handling

- Partial failures: complete what is possible, report failures in summary
- Missing API key: stop and instruct user to add it to `.env`
- Gmail MCP unavailable: save drafts to `data/email_drafts.md` as fallback
- Google Sheets unavailable: CSVs in `data/` are the fallback
- Apify actor timeout: reduce batch size and retry

### Communication

- Use Slack to message the user when running autonomously and hitting a decision point
- When a process completes, summarize: jobs found, contacts identified, emails enriched, drafts created
- Surface data quality issues (stale postings, low-confidence emails, missing contacts)
- Highlight the highest-quality opportunities to pursue first
- When in doubt, ask rather than guess

### Feedback Loop

Use `/improve` to apply post-run feedback. Categories: Copy/Tone, Pipeline Logic, Search Quality, Tool/Integration, Data Schema, Architecture.

## Project Structure

```
.
├── CLAUDE.md                     # This file — primary agent instructions
├── .env                          # API keys (gitignored)
├── .gitignore
├── skills-lock.json              # Imported skills manifest
├── Tavrn GTM Agent PRD.pdf       # Product requirements
├── .agents/skills/               # Imported skills (open ecosystem)
├── .claude/skills/               # Invocable skills (slash commands)
│   ├── prospect/                 # /prospect — full pipeline
│   ├── scrape-jobs/              # /scrape-jobs — Stage 1
│   ├── find-contacts/            # /find-contacts — Stage 2
│   ├── enrich-emails/            # /enrich-emails — Stage 3
│   ├── draft-outreach/           # /draft-outreach — Stage 4
│   └── improve/                  # /improve — feedback loop
├── assets/templates/             # Email + LinkedIn outreach templates
└── data/                         # Runtime CSVs (gitignored)
```
