import requests

response = requests.get(
    f"http://localhost:8084/hotels?city=Bengaluru"
)
data = response.json()

print(data)