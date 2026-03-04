---
name: improve
description: Self-improvement skill. Takes user feedback from a completed pipeline run and applies it to the relevant skills, templates, and pipeline configuration. Use when the user provides feedback after a job prospector run, or asks to improve the pipeline based on results.
context: fork
---

# Self-Improvement Skill

Takes user feedback and applies targeted modifications to pipeline skills, templates, and configuration files.

## When to Trigger

- User provides post-run feedback (e.g., "the emails were too aggressive", "4 emails bounced", "we need to add a validation step")
- User says "improve", "update the pipeline", "fix the skill", or similar
- User references specific quality issues from a previous run

## Process

### Step 1: Parse Feedback into Action Items

Read the user's feedback and classify each point into one of these categories:

| Category | Affected Files | Example Feedback |
|----------|---------------|------------------|
| **Copy/Tone** | `hiring-manager-search/assets/email_template.md`, `hiring-manager-search/assets/linkedin_message.md` | "Emails are too aggressive", "softer framing" |
| **Pipeline Logic** | `skills/job-prospector.md` | "Add a validation step", "batch the API calls differently" |
| **Search Quality** | `skills/job-prospector.md`, `skills/people-research.md` | "Too many stale jobs", "missing HIM contacts" |
| **Tool/Integration** | `CLAUDE.md`, skill files | "Add email validation tool", "connect to Google Sheets" |
| **Data Schema** | `skills/job-prospector.md` (CSV schemas section) | "Add a column for verification status" |
| **Architecture** | `CLAUDE.md`, `skills/*.md` | "Make skills more modular", "add a new MCP server" |

### Step 2: Read Current State

For each affected file, read its current contents. Understand what exists before modifying.

### Step 3: Apply Changes

For each action item:

1. **Read** the target file
2. **Plan** the specific edit (what to find, what to replace)
3. **Edit** using the Edit tool (prefer surgical edits over full rewrites)
4. **Verify** the edit was applied correctly by reading the file again

### Step 4: Update Memory

After all changes are applied, update `MEMORY.md` with:
- What feedback was received
- What changes were made
- What files were modified
- Date of the improvement

Append to the `## Pipeline Status` section under a new `### Improvements Applied` sub-heading (or update existing one).

### Step 5: Summarize

Tell the user:
- What changes were made
- Which files were modified
- What the next run will do differently
- Any changes that require user action (e.g., "restart Claude Code", "add an API key")

## Rules

- **Never delete functionality** unless explicitly asked. Add to or modify existing behavior.
- **Preserve merge fields** in templates. If rewriting copy, keep all `{{field}}` placeholders intact.
- **Test templates mentally** — after editing, verify the template still reads naturally when merge fields are filled in.
- **Don't over-engineer** — make the minimum change needed to address the feedback. Don't refactor unrelated code.
- **Log everything** — every change should be traceable in MEMORY.md.

## Feedback Log Format

When updating MEMORY.md, use this format:

```markdown
### Improvements Applied (YYYY-MM-DD)

**Feedback received:**
- [quote or paraphrase of user feedback]

**Changes made:**
- `file/path.md` — [description of what changed]
- `file/path2.md` — [description of what changed]

**Impact on next run:**
- [what will be different]
```
