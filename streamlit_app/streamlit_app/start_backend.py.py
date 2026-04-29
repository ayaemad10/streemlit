"""
start_backend.py
----------------
Quick script to verify backend is running.
Save this in your backend folder and run:
python start_backend.py
"""

import requests
import sys

def check_backend(url="http://localhost:8000"):
    print(f"Checking API at {url}...")
    try:
        resp = requests.get(f"{url}/health", timeout=5)
        if resp.status_code == 200:
            print(f"✅ Backend is running! Response: {resp.json()}")
            return True
        else:
            print(f"❌ Backend returned status {resp.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to {url}")
        print("\nPlease start the backend with:")
        print("  cd /path/to/backend")
        print("  uvicorn main:app --host 0.0.0.0 --port 8000 --reload")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    check_backend()