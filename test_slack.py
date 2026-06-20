

import os
import requests
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SLACK_WEBHOOK_URL")

response = requests.post(
    url,
    json={"text": "🚀 SentinelFinOps test message"}
)

print(response.status_code)
print(response.text)