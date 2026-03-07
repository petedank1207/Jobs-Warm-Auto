// Category-specific parameter restrictions for Exa API
// Source: .agents/skills/exa-people-search/SKILL.md, .agents/skills/exa-company-research/SKILL.md

const CATEGORY_RESTRICTIONS = {
  people: {
    strip: [
      'startPublishedDate',
      'endPublishedDate',
      'startCrawlDate',
      'endCrawlDate',
      'includeText',
      'excludeText',
      'excludeDomains',
    ],
    // includeDomains only allows LinkedIn
    allowedDomains: ['linkedin.com'],
  },
  company: {
    strip: [
      'includeDomains',
      'excludeDomains',
      'startPublishedDate',
      'endPublishedDate',
      'startCrawlDate',
      'endCrawlDate',
    ],
  },
};

function validateParams(category, params) {
  const warnings = [];
  const sanitized = { ...params };

  // Apply category-specific restrictions
  const restrictions = CATEGORY_RESTRICTIONS[category];
  if (restrictions) {
    for (const key of restrictions.strip) {
      if (key in sanitized) {
        warnings.push(`Stripped "${key}" — not allowed with category "${category}"`);
        delete sanitized[key];
      }
    }

    // For "people" category, validate includeDomains
    if (category === 'people' && sanitized.includeDomains) {
      const invalid = sanitized.includeDomains.filter(
        (d) => !restrictions.allowedDomains.includes(d)
      );
      if (invalid.length > 0) {
        warnings.push(
          `Stripped non-LinkedIn domains from includeDomains: ${invalid.join(', ')}. Only linkedin.com is allowed with category "people".`
        );
        sanitized.includeDomains = sanitized.includeDomains.filter((d) =>
          restrictions.allowedDomains.includes(d)
        );
        if (sanitized.includeDomains.length === 0) {
          delete sanitized.includeDomains;
        }
      }
    }
  }

  // Universal: includeText/excludeText max 1 item per array
  for (const key of ['includeText', 'excludeText']) {
    if (Array.isArray(sanitized[key]) && sanitized[key].length > 1) {
      warnings.push(
        `Truncated "${key}" to 1 item — multi-item arrays cause 400 errors`
      );
      sanitized[key] = [sanitized[key][0]];
    }
  }

  return { params: sanitized, warnings };
}

module.exports = { validateParams, CATEGORY_RESTRICTIONS };
