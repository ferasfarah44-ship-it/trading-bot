import requests

print("requests works")

r = requests.get("https://api.telegram.org")
print(r.status_code)
