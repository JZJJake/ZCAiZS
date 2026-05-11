import requests

for version in ["0.5.0", "0.5.5", "0.5.11"]:
    url = f"https://pypi.org/pypi/chromadb/{version}/json"
    resp = requests.get(url)
    if resp.status_code == 200:
        for req in resp.json()["info"]["requires_dist"]:
            if "chroma-hnswlib" in req:
                print(f"chromadb {version} needs {req}")
