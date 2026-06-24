#!/bin/bash
set -euo pipefail

CLIENT_ID="7kc9u6k0vfotopd4nb8sslgcvt"

read -r -p "Username (email): " USERNAME
read -r -s -p "Password: " PASSWORD
echo

RESPONSE=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id "$CLIENT_ID" \
  --auth-parameters USERNAME="$USERNAME",PASSWORD="$PASSWORD")

echo "$RESPONSE"

TOKEN=$(echo "$RESPONSE" | python3 -c "import sys,json; r=json.load(sys.stdin); print(r.get('AuthenticationResult', {}).get('IdToken', 'No token — check ChallengeName above'))")
echo ""
echo "IdToken: $TOKEN"
