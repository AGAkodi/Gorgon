import urllib.request
import re

url = "https://metamask.github.io/test-dapp/main.js"
try:
    js = urllib.request.urlopen(url).read().decode('utf-8')
    # Find occurrences of connectButton
    idx = 0
    for match in re.finditer(r"connectButton", js):
        start = max(0, match.start() - 200)
        end = min(len(js), match.end() + 500)
        print(f"Match {idx+1}:")
        print(js[start:end])
        print("-" * 50)
        idx += 1
except Exception as e:
    print("Error:", e)
