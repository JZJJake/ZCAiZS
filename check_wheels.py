import requests

def get_wheels(package_name):
    url = f"https://pypi.org/pypi/{package_name}/json"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        version = data["info"]["version"]
        print(f"Latest version of {package_name}: {version}")
        for url_info in data["urls"]:
            if url_info["filename"].endswith(".whl"):
                print(url_info["filename"])
    else:
        print(f"Package {package_name} not found.")

get_wheels("chroma-hnswlib")
