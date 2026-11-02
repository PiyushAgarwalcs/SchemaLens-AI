import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

url = "https://api.fireworks.ai/inference/v1/chat/completions"
payload = {
    "model": os.getenv("LLM_MODEL"),
    "max_tokens": 100,
    "messages": [
        {"role": "user", "content": "Hello, how are you?"}
    ]
}
headers = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": f"Bearer {os.getenv('FIREWORKS_API_KEY')}"
}

response = requests.post(url, headers=headers, data=json.dumps(payload))
print(response.json())