// Company search wrappers for Exa API
// Encodes patterns from .agents/skills/exa-company-research/SKILL.md

const { createClient } = require('./client');
const { validateParams } = require('./validators');

let _client;
function getClient() {
  if (!_client) _client = createClient();
  return _client;
}

// Match US phone numbers: (xxx) xxx-xxxx, xxx-xxx-xxxx, xxx.xxx.xxxx, +1xxxxxxxxxx
const PHONE_REGEX =
  /(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}/g;

function extractPhones(text) {
  if (!text) return [];
  const matches = text.match(PHONE_REGEX) || [];
  // Deduplicate by normalized digits
  const seen = new Set();
  return matches.filter((phone) => {
    const digits = phone.replace(/\D/g, '');
    if (seen.has(digits)) return false;
    seen.add(digits);
    return digits.length >= 10;
  });
}

async function searchCompanies({ query, numResults = 10 }) {
  const client = getClient();
  const raw = { query, numResults, category: 'company', type: 'auto' };
  const { params, warnings } = validateParams('company', raw);
  const result = await client.search(params);
  return { ...result, _warnings: warnings };
}

async function searchCompanyNews({
  query,
  numResults = 10,
  startPublishedDate,
  includeDomains,
}) {
  const client = getClient();
  const params = {
    query,
    numResults,
    category: 'news',
    type: 'auto',
    ...(startPublishedDate && { startPublishedDate }),
    ...(includeDomains && { includeDomains }),
  };
  const result = await client.search(params);
  return result;
}

async function searchCompanyPhone({ companyName, location }) {
  const client = getClient();
  const query = `${companyName} ${location} hospital phone number contact`;
  const result = await client.search({
    query,
    numResults: 3,
    type: 'auto',
  });

  // Extract phone numbers from all result text and highlights
  const phones = new Set();
  for (const item of result.results || []) {
    const text = [item.text, item.title, ...(item.highlights || [])].join(' ');
    for (const phone of extractPhones(text)) {
      phones.add(phone);
    }
  }

  return {
    companyName,
    location,
    phones: [...phones],
    phone: [...phones][0] || null,
    _sourceUrls: (result.results || []).map((r) => r.url),
  };
}

module.exports = {
  searchCompanies,
  searchCompanyNews,
  searchCompanyPhone,
  extractPhones,
};
