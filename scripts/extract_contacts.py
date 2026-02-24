import json, re, os

DIR = "/Users/peterdankert/.claude/projects/-Users-peterdankert-Documents-Entrepreneurship-Open-Job-Prospector/e2fe1d74-4dab-49da-9218-5e9e0724086a/tool-results"

files = {
    "Jefferson Health IT": "1771952452959",
    "Jefferson Health HR": "1771952453196",
    "Beth Israel IT": "1771952453982",
    "Beth Israel HR": "1771952454784",
    "UK Healthcare IT": "1771952456256",
    "UK Healthcare HR": "1771952456348",
    "Memorial Health IT": "1771952456764",
    "Memorial Health HR": "1771952457373",
    "BMC IT": "1771952459089",
    "BMC HR": "1771952459091",
    "UPMC IT": "1771952459404",
    "UPMC HR": "1771952460837",
    "Texas Health IT": "1771952461289",
    "Texas Health HR": "1771952461695",
}

for label, ts in files.items():
    fpath = os.path.join(DIR, f"mcp-exa-web_search_advanced_exa-{ts}.txt")
    with open(fpath) as f:
        data = json.load(f)
    text = data[0]["text"] if isinstance(data, list) else data["text"]

    urls = re.findall(r'https?://(?:www\.)?linkedin\.com/in/[^\s\]\)\"\'<>,;]+', text)
    print(f"\n=== {label} ({len(urls)} LinkedIn URLs) ===")
    seen = set()
    for url in urls:
        url = url.rstrip('/')
        if url in seen:
            continue
        seen.add(url)
        idx = text.find(url)
        start = max(0, idx - 300)
        end = min(len(text), idx + len(url) + 20)
        context = text[start:end].replace('\n', ' ')
        print(f"\nURL: {url}")
        print(f"CTX: ...{context[-350:]}...")
