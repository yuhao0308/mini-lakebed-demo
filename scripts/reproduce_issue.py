import requests
import uuid
import json

BASE_URL = "http://localhost:8000/api"
SESSION_ID = str(uuid.uuid4())

def chat_test():
    print(f"Starting test with Session ID: {SESSION_ID}")
    
    # 1. Search for inventory to populate context
    print("\n1. Searching for 'SUVs'...")
    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json={"message": "Show me SUVs", "session_id": SESSION_ID}
        )
        response.raise_for_status()
        print("   Success! Found SUVs.")
    except Exception as e:
        print(f"   Failed to search inventory: {e}")
        return

    # 2. Ask for details about the first result (#1)
    print("\n2. Asking for details about '#1'...")
    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json={"message": "Tell me about #1", "session_id": SESSION_ID}
        )
        
        if response.status_code == 200:
            data = response.json()
            print("   Success! Received response:")
            print(f"   Response: {data['response'][:100]}...")
        else:
            print(f"   Failed! Status Code: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"   Exception occurred: {e}")

if __name__ == "__main__":
    chat_test()
