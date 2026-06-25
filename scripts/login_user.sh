#!/bin/bash
set -euo pipefail

export AWS_PAGER=""

ENV=${ENV:-dev}
STACK_NAME="BookAppUser-${ENV}"

CLIENT_ID=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='UserPoolClientId'].OutputValue" \
  --output text 2>/dev/null || true)

if [[ -z "$CLIENT_ID" ]]; then
  echo "Warning: could not retrieve Client ID from stack $STACK_NAME."
  read -r -p "Enter User Pool Client ID manually: " CLIENT_ID
  if [[ -z "$CLIENT_ID" ]]; then
    echo "Error: Client ID is required."
    exit 1
  fi
fi

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
