Step 1: Install or update Exa MCP

If Exa MCP already exists in your MCP configuration, either uninstall it first and install the new one, or update your existing MCP config with this endpoint. Run this command in your terminal:

claude mcp add --transport http exa "https://mcp.exa.ai/mcp?tools=web_search_advanced_exa"


Step 2: Add this Claude skill

---
name: people-research
description: People research using Exa search. Finds LinkedIn profiles, professional backgrounds, experts, team members, and public bios across the web. Use when searching for people, finding experts, or looking up professional profiles.
context: fork
---

# People Research

## Tool Restriction (Critical)

ONLY use `web_search_advanced_exa`. Do NOT use `web_search_exa` or any other Exa tools.

## Token Isolation (Critical)

Never run Exa searches in main context. Always spawn Task agents:
- Agent runs Exa search internally
- Agent processes results using LLM intelligence
- Agent returns only distilled output (compact JSON or brief markdown)
- Main context stays clean regardless of search volume

## Dynamic Tuning

No hardcoded numResults. Tune to user intent:
- User says "a few" → 10-20
- User says "comprehensive" → 50-100
- User specifies number → match it
- Ambiguous? Ask: "How many profiles would you like?"

## Query Variation

Exa returns different results for different phrasings. For coverage:
- Generate 2-3 query variations
- Run in parallel
- Merge and deduplicate

## Categories

Use appropriate Exa `category` depending on what you need:
- `people` → LinkedIn profiles, public bios (primary for discovery)
- `personal site` → personal blogs, portfolio sites, about pages
- `news` → press mentions, interviews, speaker bios
- No category (`type: "auto"`) → general web results, broader context

Start with `category: "people"` for profile discovery, then use other categories or no category with `livecrawl: "fallback"` for deeper research on specific individuals.

### Category-Specific Filter Restrictions

When using `category: "people"`, these parameters cause errors:
- `startPublishedDate` / `endPublishedDate`
- `startCrawlDate` / `endCrawlDate`
- `includeText` / `excludeText`
- `excludeDomains`
- `includeDomains` — **LinkedIn domains only** (e.g., "linkedin.com")

When searching without a category, all parameters are available (but `includeText`/`excludeText` still only support single-item arrays).

## LinkedIn

Public LinkedIn via Exa: `category: "people"`, no other filters.
Auth-required LinkedIn → use Claude in Chrome browser fallback.

## Browser Fallback

Auto-fallback to Claude in Chrome when:
- Exa returns insufficient results
- Content is auth-gated
- Dynamic pages need JavaScript

## Examples

### Discovery: find people by role
```
web_search_advanced_exa {
  "query": "VP Engineering AI infrastructure",
  "category": "people",
  "numResults": 20,
  "type": "auto"
}
```

### With query variations
```
web_search_advanced_exa {
  "query": "machine learning engineer San Francisco",
  "category": "people",
  "additionalQueries": ["ML engineer SF", "AI engineer Bay Area"],
  "numResults": 25,
  "type": "deep"
}
```

### Deep dive: research a specific person
```
web_search_advanced_exa {
  "query": "Dario Amodei Anthropic CEO background",
  "type": "auto",
  "livecrawl": "fallback",
  "numResults": 15
}
```

### News mentions
```
web_search_advanced_exa {
  "query": "Dario Amodei interview",
  "category": "news",
  "numResults": 10,
  "startPublishedDate": "2024-01-01"
}
```

## Output Format

Return:
1) Results (name, title, company, location if available)
2) Sources (Profile URLs)
3) Notes (profile completeness, verification status)


Step 3: Set up Hunter.io API

Hunter.io is used for email enrichment (finding hiring manager emails by name + company domain).

1. Sign up at https://hunter.io and get your API key
2. Add to `.gitignore/.env`:
   ```
   HUNTER_API_KEY=your_key_here
   ```
3. No MCP server needed — the pipeline calls Hunter.io via `curl`

Step 4: Set up Gmail MCP Server

Gmail MCP enables saving drafted outreach emails directly to your Gmail drafts folder.

1. Create a Google Cloud project and enable the Gmail API
2. Create OAuth Desktop credentials (download the JSON)
3. Run the auth flow:
   ```bash
   npx @shinzolabs/gmail-mcp auth
   ```
4. Add the MCP server:
   ```bash
   claude mcp add gmail -- npx @shinzolabs/gmail-mcp
   ```

Step 5: Ask User to Restart Claude Code

You should ask the user to restart Claude Code to have the config changes take effect after any MCP changes.

---

## Running the Job Prospector

Use the `/job-prospector` skill to run the full pipeline. It will:
1. Search for open jobs matching your criteria (via Exa)
2. Identify hiring managers at each company (via Exa people search)
3. Find their email addresses (via Hunter.io)
4. Draft personalized outreach emails (saved to Gmail drafts)

Edit the outreach template at `hiring-manager-search/assets/email_template.md` to customize your messaging.