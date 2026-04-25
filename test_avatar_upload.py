import requests
import json

# JWT token from localStorage (user_id=1)
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzc3MTgzODk5LCJpYXQiOjE3NzcwOTc0OTksImp0aSI6IjE3YTI4ZmJlZWYwMjQ2YTU5N2NiN2QzNGY5OTliZWVmIiwidXNlcl9pZCI6IjEifQ.KLOsgzOwI2Gp737qMlZjk_iN8IiQ5PbORj7jc00sd7s"

url = "http://localhost:8000/api/auth/profile/avatar"

# Read the QQ.png image file
with open("Frontend/src/assets/images/QQ.png", "rb") as f:
    files = {"file": ("test_avatar.png", f, "image/png")}
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"Sending POST request to {url}")
    print(f"Headers: {headers}")
    print()
    
    # IMPORTANT: Do NOT set Content-Type header manually for multipart/form-data
    # requests library will set it automatically with correct boundary
    response = requests.post(url, files=files, headers=headers)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print()
    print(f"Response Body:")
    try:
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    except:
        print(response.text)
