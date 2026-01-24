import requests
import uuid
import json

BASE_URL = "http://localhost:8000/api"
SESSION_ID = str(uuid.uuid4())

def test_yes_response():
    print(f"Starting test with Session ID: {SESSION_ID}")
    
    # 1. Search for inventory (setup)
    print("\n1. Searching for 'SUVs'...")
    requests.post(f"{BASE_URL}/chat", json={"message": "Show me SUVs", "session_id": SESSION_ID})

    # 2. Get details for #1
    print("\n2. Asking for details about '#1'...")
    response = requests.post(
        f"{BASE_URL}/chat",
        json={"message": "Tell me about #1", "session_id": SESSION_ID}
    )
    print(f"   Bot: {response.json()['response'][-100:]}") # Show end of message

    # 3. Say "Yes"
    print("\n3. Saying 'Yes'...")
    response = requests.post(
        f"{BASE_URL}/chat",
        json={"message": "Yes", "session_id": SESSION_ID}
    )
    data = response.json()
    print(f"   Bot: {data['response']}")
    
    if "payment" in data['response'].lower() and "estimate" in data['response'].lower() and "monthly" in data['response'].lower():
        print("\nSUCCESS: Bot provided payment estimate.")
    elif "hello" in data['response'].lower() and "inventory" in data['response'].lower():
        print("\nFAILURE: Bot sent greeting.")
    else:
        print("\nUNKNOWN RESPONSE.")

if __name__ == "__main__":
    test_yes_response()
