import urllib.request
import re

url = "https://metamask.github.io/test-dapp/main.js"
try:
    js = urllib.request.urlopen(url).read().decode('utf-8')
    # Find occurrences of status
    idx = 0
    for match in re.finditer(r"status", js, re.IGNORECASE):
        start = max(0, match.start() - 100)
        end = min(len(js), match.end() + 200)
        # Only print if it looks like DOM or ID manipulation
        snippet = js[start:end]
        if 'document' in snippet or 'id' in snippet or 'class' in snippet or 'inner' in snippet:
            print(f"Match {idx+1}:")
            print(snippet)
            print("-" * 50)
            idx += 1
except Exception as e:
    print("Error:", e)
