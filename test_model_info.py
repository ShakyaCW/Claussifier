"""
Quick test script to check if the /model-info endpoint is working
"""

import requests

try:
    response = requests.get('http://localhost:8000/model-info')
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")
    print("\n⚠️ Make sure the server is running: python app.py")
