import requests
import json

try:
    response = requests.get('http://localhost:8080/api/history')
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")