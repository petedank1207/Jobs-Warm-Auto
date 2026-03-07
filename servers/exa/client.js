// Thin HTTP client for the Exa REST API
// Uses Node.js built-in fetch (Node 18+) — no external dependencies

const EXA_BASE_URL = 'https://api.exa.ai';

function createClient() {
  const apiKey = process.env.EXA_API_KEY;
  if (!apiKey) {
    throw new Error(
      'EXA_API_KEY not set. Add it to .env and run with: node --env-file=.env'
    );
  }

  async function search(params) {
    const response = await fetch(`${EXA_BASE_URL}/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': apiKey,
      },
      body: JSON.stringify(params),
    });

    if (!response.ok) {
      const body = await response.text();
      const error = new Error(`Exa API error ${response.status}: ${body}`);
      error.status = response.status;
      error.body = body;
      throw error;
    }

    return response.json();
  }

  return { search };
}

module.exports = { createClient };
