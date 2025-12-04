import requests

try:
    response = requests.get("http://127.0.0.1:9090/")
    print(f"Status Code: {response.status_code}")
    print("Headers:")
    for key, value in response.headers.items():
        print(f"{key}: {value}")

    print("\nEncoding:", response.encoding)
    print("Apparent Encoding:", response.apparent_encoding)
except Exception as e:
    print(f"Error: {e}")
