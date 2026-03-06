---
name: draft-outreach
description: "Draft personalized outreach emails and LinkedIn messages for enriched contacts. Creates Gmail drafts via MCP. Use when the user wants to draft emails, create outreach, or run Stage 4."
---

# Stage 4: Outreach Drafting

Draft personalized emails and LinkedIn messages for contacts with verified email addresses. Save as Gmail drafts for user review before sending.

## Tools

- Gmail MCP: `gmail_create_draft` — save drafts for review
- Cold-email skill: `.agents/skills/cold-email/SKILL.md` — writing frameworks and principles
- Templates: `assets/templates/email_template.md`, `assets/templates/linkedin_message.md`

## Workflow

```
- [ ] Step 1: Load enriched contacts from data/enriched_contacts.csv
- [ ] Step 2: Filter to contacts eligible for outreach
- [ ] Step 3: Draft personalized emails using template + cold-email principles
- [ ] Step 4: Save drafts via Gmail MCP (or fallback to file)
- [ ] Step 5: Generate LinkedIn messages
- [ ] Step 6: Summarize and update CSV
```

### Step 1: Load Enriched Contacts

Read `data/enriched_contacts.csv`. If the file doesn't exist or is empty, instruct user to run `/enrich-emails` first.

### Step 2: Filter Eligible Contacts

Only draft outreach for contacts where:
- `email` is not empty
- `email_verified` is `true` OR `unverified` (skip `false`/invalid)

Report how many contacts are eligible vs. skipped.

### Step 3: Draft Emails

For each eligible contact:

1. Read the email template from `assets/templates/email_template.md`
2. Fill merge fields:
   - `{{hiring_manager_name}}` — first name from `contact_name`
   - `{{hiring_manager_title}}` — from `contact_title`
   - `{{company_name}}` — from `company_name`
   - `{{job_title}}` — from `job_title`
3. Apply cold-email principles (from `.agents/skills/cold-email/SKILL.md`):
   - Write like a peer, not a vendor
   - Keep it concise (under 150 words body)
   - One clear ask (15-minute call)
   - Personalize the opening line to reference the specific job posting or company context
4. Subject line: Use the template subject, ensure ASCII-only characters

**Outreach framing rules:**
- Always say "staff augmentation" — never "outsourcing" or "takeover"
- "We hire a dedicated person to learn your process end-to-end"
- "No cost to the facility"
- Tone: helpful peer, not salesy vendor

### Step 4: Save Drafts

**Primary method — Gmail MCP:**
```
gmail_create_draft:
  to: {contact_email}
  subject: {email_subject}
  body: {email_body}
  contentType: "text/plain"
```

**Fallback — if Gmail MCP is unavailable:**
Append each draft to `data/email_drafts.md` in this format:

```markdown
---
## Draft for {contact_name} at {company_name}
**To:** {email}
**Subject:** {subject}

{body}

**LinkedIn Connection Request:**
{connection_request}

**LinkedIn Follow-Up:**
{follow_up}
---
```

### Step 5: Generate LinkedIn Messages

For each contact, also generate:

1. **Connection request** (max 300 characters) — use template from `assets/templates/linkedin_message.md`, personalized
2. **Follow-up message** (max 100 words) — use template, personalized

These are NOT auto-sent. Include them in the summary output for the user to copy/paste manually.

### Step 6: Summary and CSV Update

Update `data/enriched_contacts.csv` with a `draft_status` column:
- `drafted` — Gmail draft created successfully
- `drafted_file` — Saved to email_drafts.md (Gmail MCP unavailable)
- `skipped_invalid` — Email was invalid
- `skipped_no_email` — No email found
- `failed` — Draft creation failed (include error)

**Summary output:**
- Drafts created: N (Gmail) + N (file fallback)
- Contacts skipped: N (with reasons)
- LinkedIn messages generated: N
- Table of all drafts with: contact name, company, email, subject line, draft status

**Remind the user:** All drafts are saved for review. Nothing has been sent.

## Error Handling

- Gmail MCP not connected: Automatically fall back to `data/email_drafts.md`
- Template file missing: Use inline default template with the standard Tavrn messaging
- Contact missing required fields: Skip and report
