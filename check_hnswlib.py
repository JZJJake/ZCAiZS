import requests

def get_chromadb_reqs(version):
    url = f"https://pypi.org/pypi/chromadb/{version}/json"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        reqs = data["info"]["requires_dist"]
        for req in reqs:
            if "chroma-hnswlib" in req:
                print(req)
    else:
        print(f"Package chromadb {version} not found.")

get_chromadb_reqs("0.4.24")
get_chromadb_reqs("0.5.0")
get_chromadb_reqs("0.5.5")
