#!/bin/bash

set -e

SECRET_NAME="project/db-secret"
KMS_ALIAS="alias/project-secret-key"

if [ -z "$SECRET_PASSWORD" ]; then
    echo "ERROR: SECRET_PASSWORD environment variable is not set."
    exit 1
fi

echo "=========================================="
echo "AWS Secrets Manager Automation"
echo "=========================================="

echo
echo "1. Checking whether secret exists..."

if aws secretsmanager describe-secret \
    --secret-id "$SECRET_NAME" >/dev/null 2>&1
then
    echo "Secret already exists: $SECRET_NAME"
else
    echo "Secret does not exist. Creating it..."

    aws secretsmanager create-secret \
        --name "$SECRET_NAME" \
        --kms-key-id "$KMS_ALIAS" \
        --secret-string "{\"username\":\"admin\",\"password\":\"$SECRET_PASSWORD\"}" \
        >/dev/null

    echo "Secret created successfully."
fi

echo
echo "2. Reading secret..."

SECRET_JSON=$(aws secretsmanager get-secret-value \
    --secret-id "$SECRET_NAME" \
    --query 'SecretString' \
    --output text)

USERNAME=$(echo "$SECRET_JSON" | python3 -c \
'import sys, json; print(json.load(sys.stdin)["username"])')

echo "Secret retrieved successfully."
echo "Username: $USERNAME"
echo "Password: [REDACTED]"

echo
echo "3. Updating secret..."

aws secretsmanager update-secret \
    --secret-id "$SECRET_NAME" \
    --secret-string "{\"username\":\"admin\",\"password\":\"$SECRET_PASSWORD\"}" \
    >/dev/null

echo "Secret updated successfully."

echo
echo "4. Reading updated secret..."

UPDATED_SECRET_JSON=$(aws secretsmanager get-secret-value \
    --secret-id "$SECRET_NAME" \
    --query 'SecretString' \
    --output text)

UPDATED_USERNAME=$(echo "$UPDATED_SECRET_JSON" | python3 -c \
'import sys, json; print(json.load(sys.stdin)["username"])')

echo "Updated secret retrieved successfully."
echo "Username: $UPDATED_USERNAME"
echo "Password: [REDACTED]"

echo
echo "5. Listing project secrets..."

aws secretsmanager list-secrets \
    --query 'SecretList[?starts_with(Name, `project/`)].Name' \
    --output table

echo
echo "=========================================="
echo "Automation completed successfully."
echo "=========================================="
