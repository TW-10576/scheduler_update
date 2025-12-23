#!/bin/bash

# Get emp1 token
TOKEN=$(curl -s http://localhost:8000/token -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=emp1&password=emp123" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['access_token'])")

echo "Checking notifications for emp1..."
curl -s -X GET "http://localhost:8000/notifications" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
