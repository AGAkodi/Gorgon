import urllib.request

url = "https://metamask.github.io/test-dapp/"
try:
    html = urllib.request.urlopen(url).read().decode('utf-8')
    # Search for ids or classes containing status or similar
    import re
    ids = re.findall(r'id=["\']([^"\']+)["\']', html)
    print("Found IDs in HTML:")
    for i in sorted(list(set(ids))):
        if 'status' in i.lower() or 'tx' in i.lower() or 'hash' in i.lower() or 'send' in i.lower() or 'account' in i.lower():
            print(f"  - {i}")
except Exception as e:
    print("Error:", e)
