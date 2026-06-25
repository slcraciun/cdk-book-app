#!/bin/bash
set -euo pipefail

export AWS_PAGER=""  # disable pager so output prints directly without requiring q to dismiss

ENV=${ENV:-dev}
STACK_NAME="BookAppUser-${ENV}"

POOL_ID=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='UserPoolId'].OutputValue" \
  --output text 2>/dev/null || true)

if [[ -z "$POOL_ID" ]]; then
  echo "Warning: could not retrieve User Pool ID from stack $STACK_NAME."
  read -r -p "Enter User Pool ID manually: " POOL_ID
  if [[ -z "$POOL_ID" ]]; then
    echo "Error: User Pool ID is required."
    exit 1
  fi
fi

read -r -p "Username (email): " USERNAME

read -r -s -p "Password: " PASSWORD
echo

while true; do
  read -r -p "Role (admin/reader): " ROLE
  if [[ "$ROLE" == "admin" || "$ROLE" == "reader" ]]; then
    break
  fi
  echo "Invalid role. Please enter 'admin' or 'reader'."
done

aws cognito-idp admin-create-user \
  --user-pool-id "$POOL_ID" \
  --username "$USERNAME" \
  --message-action SUPPRESS > /dev/null

aws cognito-idp admin-add-user-to-group \
  --user-pool-id "$POOL_ID" \
  --username "$USERNAME" \
  --group-name "$ROLE"

aws cognito-idp admin-set-user-password \
  --user-pool-id "$POOL_ID" \
  --username "$USERNAME" \
  --password "$PASSWORD" \
  --permanent

echo "User $USERNAME created with role '$ROLE'."
