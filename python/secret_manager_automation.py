import boto3
import json

REGION = "us-east-1"

ALIAS_NAME = "alias/project-secret-key-2"
SECRET_NAME = "project/app1-db"

USERNAME = "admin-Developers"
PASSWORD = "DevOps@2026#Secure"

kms = boto3.client("kms", region_name=REGION)
secrets = boto3.client("secretsmanager", region_name=REGION)

print("Starting AWS Secret Automation...")

# 1. Check if KMS alias already exists
print("Checking KMS key...")
aliases = kms.list_aliases()["Aliases"]
key_id = None
for alias in aliases:
    if alias.get("AliasName") == ALIAS_NAME:
        key_id = alias["TargetKeyId"]
        break

# 2. Create KMS key if it doesn't exist
if key_id:
    print("Existing KMS key found:", key_id)
else:
    print("Creating new KMS key...")
  response = kms.create_key(
        Description="Project Secret Encryption Key"
    )
  key_id = response["KeyMetadata"]["KeyId"]
 kms.create_alias(
        AliasName=ALIAS_NAME,
        TargetKeyId=key_id
    )
print("KMS key created:", key_id)

# 3. Enable key rotation
print("Enabling KMS key rotation...")
kms.enable_key_rotation(
    KeyId=key_id
)
print("KMS rotation enabled.")

# 4. Prepare username/password
secret_value = json.dumps({
    "username": USERNAME,
    "password": PASSWORD
})

# 5. Create or update secret
print("Checking Secrets Manager secret...")

try:
    response = secrets.create_secret(
        Name=SECRET_NAME,
        Description="Application Database Credentials",
        KmsKeyId=key_id,
        SecretString=secret_value
    )
 print("Secret created successfully.")
 except secrets.exceptions.ResourceExistsException:
   print("Secret already exists.")
    print("Updating existing secret...")

      secrets.update_secret(
        SecretId=SECRET_NAME,
        SecretString=secret_value
    )
    print("Secret updated successfully.")

# 6. Retrieve secret
print("Retrieving secret...")
response = secrets.get_secret_value(
    SecretId=SECRET_NAME
)
secret = json.loads(response["SecretString"])
print("Username:", secret["username"])
print("Password:", secret["password"])

# 7. Verify KMS encryption
print("Checking encryption key...")
response = secrets.describe_secret(
    SecretId=SECRET_NAME
)
print("Secret name:", response["Name"])
print("KMS key:", response["KmsKeyId"])
print("Automation completed successfully!")
