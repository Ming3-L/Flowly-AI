# Test backend API

# 1. Register a new user
Write-Host "=== 1. 注册用户 ==="
$r = Invoke-WebRequest -Uri 'http://localhost:8000/api/auth/register' -Method POST -ContentType 'application/json' -Body '{"username":"testuser","email":"test@example.com","password":"Test1234!","password_confirm":"Test1234!"}' -TimeoutSec 10 -UseBasicParsing
Write-Host "Status:" $r.StatusCode
Write-Host "Content:" $r.Content

# 2. Login and get JWT token
Write-Host "`n=== 2. 登录获取 JWT Token ==="
$r2 = Invoke-WebRequest -Uri 'http://localhost:8000/api/auth/login/' -Method POST -ContentType 'application/json' -Body '{"username":"testuser","password":"Test1234!"}' -TimeoutSec 10 -UseBasicParsing
Write-Host "Status:" $r2.StatusCode
Write-Host "Content:" $r2.Content

# 3. OpenAPI docs
Write-Host "`n=== 3. OpenAPI 文档 ==="
$r3 = Invoke-WebRequest -Uri 'http://localhost:8000/api/docs' -TimeoutSec 5 -UseBasicParsing
Write-Host "Status:" $r3.StatusCode
