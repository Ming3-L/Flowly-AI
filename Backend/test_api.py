import urllib.request, json

BASE = "http://127.0.0.1:8000"

def post(path, data, token=None):
    body = json.dumps(data).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, data=body, headers=headers, method="POST")
    try:
        r = urllib.request.urlopen(req)
        return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return e.code, json.loads(body)
        except:
            return e.code, body
    except Exception as e:
        return 0, str(e)

def get(path, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, headers=headers, method="GET")
    try:
        r = urllib.request.urlopen(req)
        return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except:
            return e.code, e.read().decode()
    except Exception as e:
        return 0, str(e)

# 1. Register
print("=== 1. 注册 ===")
code, resp = post("/api/auth/register", {"username": "bob", "email": "bob@example.com", "password": "Test123456!", "password_confirm": "Test123456!"})
print(f"Status: {code}")
print(f"Response: {json.dumps(resp, ensure_ascii=False)}")

# 2. Login
print("\n=== 2. 登录 ===")
code2, resp2 = post("/api/auth/login", {"username": "bob", "password": "Test123456!"})
print(f"Status: {code2}")
print(f"Response: {json.dumps(resp2, ensure_ascii=False)}")
if code2 == 200:
    token = resp2["access"]
    print(f"Access token: {token[:30]}...")
    # 3. Get profile
    print("\n=== 3. 用户资料 ===")
    code3, resp3 = get("/api/auth/me", token)
    print(f"Status: {code3}")
    print(f"Response: {json.dumps(resp3, ensure_ascii=False)}")

# 4. Workflows list
print("\n=== 4. 工作流列表 ===")
code4, resp4 = get("/api/workflows/")
print(f"Status: {code4}")
if code4 == 200:
    print(f"Total: {resp4.get('total', 'N/A')}")

# 5. OpenAPI
print("\n=== 5. 所有 API 端点 ===")
code5, resp5 = get("/api/openapi.json")
print(f"Status: {code5}")
if code5 == 200:
    for p in sorted(resp5.get("paths", {}).keys()):
        print(f"  {p}")
