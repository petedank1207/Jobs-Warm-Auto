// Exa API wrapper — public API
// Direct REST client that replaces the Exa MCP server dependency

const {
  searchPeople,
  searchPeopleLinkedIn,
  searchNews,
  searchWithVariations,
  parseName,
} = require('./people-search');

const {
  searchCompanies,
  searchCompanyNews,
  searchCompanyPhone,
  extractPhones,
} = require('./company-search');

const { validateParams } = require('./validators');
const { createClient } = require('./client');

module.exports = {
  // People
  searchPeople,
  searchPeopleLinkedIn,
  searchNews,
  searchWithVariations,
  parseName,
  // Companies
  searchCompanies,
  searchCompanyNews,
  searchCompanyPhone,
  extractPhones,
  // Low-level
  validateParams,
  createClient,
};
