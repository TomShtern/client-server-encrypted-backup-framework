import requests

try:
    print("Attempting to connect to http://127.0.0.1:9090/ ...")
    response = requests.get("http://127.0.0.1:9090/", timeout=5)
    print(f"Status Code: {response.status_code}")
    print(f"Content Length: {len(response.text)}")
    print(f"Head: {response.text[:100]}")
except Exception as e:
    print(f"Failed to connect: {e}")
