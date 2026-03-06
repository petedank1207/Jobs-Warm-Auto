---
name: enrich-emails
description: "Find and validate email addresses for contacts using Hunter.io. Takes contacts from data/contacts.csv and outputs enriched contacts to data/enriched_contacts.csv. Use when the user wants to find emails, validate emails, or run Stage 3."
---

# Stage 3: Email Enrichment via Hunter.io

Find work email addresses for contacts and validate deliverability using Hunter.io's API.

## API Endpoints

| Endpoint | Purpose | Cost |
|----------|---------|------|
| `/v2/email-finder` | Find email by name + domain | 1 search credit |
| `/v2/email-verifier` | Validate email deliverability | 1 verification credit |

Free tier: 25 searches + 100 verifications per month.

## Workflow

```
- [ ] Step 1: Load contacts from data/contacts.csv
- [ ] Step 2: Calculate credit cost and confirm with user
- [ ] Step 3: Find emails via Hunter.io email-finder
- [ ] Step 4: Validate found emails via Hunter.io email-verifier
- [ ] Step 5: Write data/enriched_contacts.csv and summarize
```

### Step 1: Load Contacts

Read `data/contacts.csv`. If the file doesn't exist or is empty, instruct user to run `/find-contacts` first.

Parse each contact to extract `contact_name` (split into first/last) and `company_domain`.

### Step 2: Cost Estimate

Calculate and display:
```
Contacts to enrich: N
Email-finder calls: N (1 credit each) = N search credits
Email-verifier calls: up to N (1 credit each) = up to N verification credits
Total estimated cost: N search + N verification credits

Hunter.io free tier: 25 searches + 100 verifications/month
```

**Confirm with user before proceeding.** If the batch would exceed free tier limits, warn and ask how to prioritize.

### Step 3: Email Finder

For each contact, call the Hunter.io email-finder API:

```bash
source .env && curl -s "https://api.hunter.io/v2/email-finder?first_name=${FIRST_NAME}&last_name=${LAST_NAME}&domain=${COMPANY_DOMAIN}&api_key=$HUNTER_API_KEY"
```

Parse the response:
- `data.email` — the found email address
- `data.score` — confidence score (0-100)
- If `data.email` is null or score < 30, mark as "not found"
- If score is 30-49, mark as "low confidence" (still attempt verification)

### Step 4: Email Verification

For each found email, validate deliverability:

```bash
source .env && curl -s "https://api.hunter.io/v2/email-verifier?email=${EMAIL}&api_key=$HUNTER_API_KEY"
```

Parse `data.status` and set verification fields:

| Status | `email_verified` | Action |
|--------|-----------------|--------|
| `valid` | `true` | Proceed to drafting |
| `accept_all` | `unverified` | Proceed with caution flag |
| `invalid` | `false` | Skip drafting for this contact |
| `disposable` | `false` | Skip drafting |
| `unknown` | `unverified` | Proceed with caution flag |

### Step 5: Write Output

Write `data/enriched_contacts.csv` — all columns from `contacts.csv` plus:

```
email,email_confidence,email_verified,verification_status
```

**Summary output:**
- Total contacts processed
- Emails found: N (with average confidence score)
- Emails not found: N
- Verification results: N valid, N invalid, N unverified
- Credits consumed: N searches + N verifications
- Contacts ready for outreach (valid + unverified emails)

## Error Handling

- `HUNTER_API_KEY not found`: Instruct user to add to `.env`
- HTTP 429 (rate limit): Wait 10 seconds and retry, max 3 retries
- HTTP 401 (invalid key): Report to user
- Partial failure: Save progress after each contact, don't lose completed lookups
