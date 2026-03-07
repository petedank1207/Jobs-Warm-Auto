// People search wrappers for Exa API
// Encodes patterns from .agents/skills/exa-people-search/SKILL.md

const { createClient } = require('./client');
const { validateParams } = require('./validators');

let _client;
function getClient() {
  if (!_client) _client = createClient();
  return _client;
}

// Parse LinkedIn profile title: "Name - Title - Company | LinkedIn"
function parseName(title) {
  if (!title) return { name: null, jobTitle: null, company: null };
  // Remove " | LinkedIn" suffix
  const cleaned = title.replace(/\s*\|\s*LinkedIn\s*$/, '');
  const parts = cleaned.split(/\s*[-–—]\s*/);
  return {
    name: parts[0]?.trim() || null,
    jobTitle: parts[1]?.trim() || null,
    company: parts[2]?.trim() || null,
  };
}

async function searchPeople({ query, numResults = 10, includeDomains }) {
  const client = getClient();
  const raw = {
    query,
    numResults,
    category: 'people',
    type: 'auto',
    ...(includeDomains && { includeDomains }),
  };
  const { params, warnings } = validateParams('people', raw);
  const result = await client.search(params);
  return { ...result, _warnings: warnings };
}

async function searchPeopleLinkedIn({ query, numResults = 10 }) {
  return searchPeople({
    query,
    numResults,
    includeDomains: ['linkedin.com'],
  });
}

async function searchNews({ query, numResults = 10, startPublishedDate }) {
  const client = getClient();
  const params = {
    query,
    numResults,
    category: 'news',
    type: 'auto',
    ...(startPublishedDate && { startPublishedDate }),
  };
  const result = await client.search(params);
  return result;
}

async function searchWithVariations({ queries, numResults = 10, ...opts }) {
  if (!queries || queries.length === 0) {
    throw new Error('queries array is required and must not be empty');
  }

  const results = await Promise.all(
    queries.map((query) => searchPeople({ query, numResults, ...opts }))
  );

  // Merge and deduplicate by URL
  const seen = new Set();
  const merged = [];
  const allWarnings = [];

  for (const result of results) {
    if (result._warnings) allWarnings.push(...result._warnings);
    for (const item of result.results || []) {
      if (!seen.has(item.url)) {
        seen.add(item.url);
        merged.push(item);
      }
    }
  }

  return {
    results: merged,
    _warnings: [...new Set(allWarnings)],
    _queriesRun: queries.length,
    _totalBeforeDedup: results.reduce(
      (sum, r) => sum + (r.results?.length || 0),
      0
    ),
  };
}

module.exports = {
  searchPeople,
  searchPeopleLinkedIn,
  searchNews,
  searchWithVariations,
  parseName,
};
