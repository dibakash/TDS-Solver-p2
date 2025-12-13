import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_URL = "http://localhost:7860/solve"
EMAIL = os.getenv("EMAIL", "your.email@example.com")
SECRET = os.getenv("SECRET", "your_secret_string")
# Example URL from README, user might want to change this
TARGET_URL = "https://tds-llm-analysis.s-anand.net/demo" 

payload = {
    "email": EMAIL,
    "secret": SECRET,
    "url": TARGET_URL
}

print(f"Testing API at: {API_URL}")
print(f"Payload: {json.dumps(payload, indent=2)}")

try:
    response = requests.post(API_URL, json=payload)
    print(f"\nStatus Code: {response.status_code}")
    try:
        data = response.json()
        print(f"Response JSON: {json.dumps(data, indent=2)}")
    except json.JSONDecodeError:
        print(f"Response Text: {response.text}")

    if response.status_code == 200:
        print("\nSUCCESS: Server accepted the request.")
    else:
        print("\nFAILURE: Server returned an error.")

except requests.exceptions.ConnectionError:
    print(f"\nERROR: Could not connect to {API_URL}. Is the server running?")
except Exception as e:
    print(f"\nAn unexpected error occurred: {e}")
