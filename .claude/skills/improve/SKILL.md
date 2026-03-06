---
name: improve
description: "Apply user feedback to improve pipeline skills, templates, and configuration. Use when the user provides post-run feedback or asks to improve the pipeline."
---

# Self-Improvement Feedback Loop

Apply user feedback to improve pipeline skills, outreach templates, search logic, and agent configuration.

## Feedback Categories

| Category | Target Files |
|----------|-------------|
| Copy/Tone | `assets/templates/email_template.md`, `assets/templates/linkedin_message.md` |
| Pipeline Logic | `.claude/skills/prospect/SKILL.md` and individual stage skills |
| Search Quality | `.claude/skills/scrape-jobs/SKILL.md`, `.claude/skills/find-contacts/SKILL.md` |
| Tool/Integration | `.claude/skills/enrich-emails/SKILL.md`, `.claude/skills/draft-outreach/SKILL.md` |
| Data Schema | `CLAUDE.md` (schema definitions) |
| Architecture | `CLAUDE.md`, `.claude/settings.local.json` |

## Workflow

```
- [ ] Step 1: Parse feedback into specific, actionable items
- [ ] Step 2: Read current state of target files
- [ ] Step 3: Plan edits (show user what will change)
- [ ] Step 4: Apply edits
- [ ] Step 5: Verify changes and update memory
```

### Step 1: Parse Feedback

Take the user's feedback and categorize each item:
- What category does it fall into?
- Which specific file(s) need to change?
- What is the current behavior vs. desired behavior?

### Step 2: Read Current State

Read each target file to understand the current content before making changes.

### Step 3: Plan Edits

Present a summary of planned changes to the user:
```
## Proposed Changes

1. [file path] — [what will change and why]
2. [file path] — [what will change and why]
```

Wait for user approval before proceeding.

### Step 4: Apply Edits

Make targeted edits using the Edit tool. Prefer surgical edits over full rewrites.

### Step 5: Verify and Update Memory

1. Re-read modified files to confirm changes applied correctly
2. Update memory at `~/.claude/projects/-Users-peterdankert-Documents-Entrepreneurship-Open-Job-Prospector/memory/MEMORY.md` with:
   - What feedback was received
   - What changes were made
   - Date of changes

## Principles

- Positive feedback: reinforce the pattern (note it in memory for consistency)
- Negative feedback: identify root cause and fix it
- When unclear, ask for clarification rather than guessing
- Never make changes beyond what the feedback requests
