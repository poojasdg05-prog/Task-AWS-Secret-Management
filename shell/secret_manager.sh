#!/bin/bash

SECRET_NAME="project/app-db"
ALIAS_NAME="alias/project-secret-key"

USERNAME="appadmin"
PASSWORD="DevOps@2026#Secure"

echo "Creating KMS Key..."

KEY_ID=$(aws kms create-key \
--description "Project Secret Key" \
--query KeyMetadata.KeyId \
--output text)

echo "Key ID: $KEY_ID"

aws kms create-alias \
--alias-name $ALIAS_NAME \
--target-key-id $KEY_ID

aws kms enable-key-rotation \
--key-id $KEY_ID

echo "Creating Secret..."

aws secretsmanager create-secret \
--name $SECRET_NAME \
--kms-key-id $ALIAS_NAME \
--secret-string "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}"

echo "Secret Created Successfully"

echo "Retrieving Secret..."

aws secretsmanager get-secret-value \
--secret-id $SECRET_NAME \
--query SecretString \
--output text



Run it:
chmod +x create_secret.sh
./create_secret.sh
