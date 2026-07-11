import urllib.request
import re

url = "https://metamask.github.io/test-dapp/main.js"
try:
    js = urllib.request.urlopen(url).read().decode('utf-8')
    # Find occurrences of txStatus or similar
    idx = 0
    for match in re.finditer(r"txStatus|status", js, re.IGNORECASE):
        start = max(0, match.start() - 150)
        end = min(len(js), match.end() + 250)
        snippet = js[start:end]
        if 'txStatus' in snippet or 'status' in snippet:
            print(f"Match {idx+1}:")
            print(snippet)
            print("-" * 50)
            idx += 1
except Exception as e:
    print("Error:", e)
