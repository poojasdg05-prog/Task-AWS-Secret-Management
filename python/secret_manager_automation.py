import json
import os

import boto3
from botocore.exceptions import ClientError


SECRET_NAME = "project/db-secret"
KMS_ALIAS = "alias/project-secret-key"


def get_password():
    """Read the password from an environment variable."""
    password = os.environ.get("SECRET_PASSWORD")

    if not password:
        raise RuntimeError(
            "SECRET_PASSWORD environment variable is not set."
        )

    return password


def get_secrets_manager_client():
    """Create and return a Secrets Manager client."""
    return boto3.client("secretsmanager")


def create_secret(client, password):
    """Create the secret if it does not already exist."""
    try:
        response = client.create_secret(
            Name=SECRET_NAME,
            KmsKeyId=KMS_ALIAS,
            SecretString=json.dumps(
                {
                    "username": "admin",
                    "password": password
                }
            )
        )

        print("Secret created.")
        print("ARN:", response["ARN"])

    except client.exceptions.ResourceExistsException:
        print("Secret already exists. Skipping creation.")


def get_secret(client):
    """Retrieve the secret without displaying the password."""
    try:
        response = client.get_secret_value(
            SecretId=SECRET_NAME
        )

        secret = json.loads(response["SecretString"])

        print("Secret retrieved successfully.")
        print("Username:", secret.get("username"))
        print("Password: [REDACTED]")

    except ClientError as error:
        print("Error reading secret:")
        print(error)


def update_secret(client, password):
    """Update the secret."""
    try:
        client.update_secret(
            SecretId=SECRET_NAME,
            SecretString=json.dumps(
                {
                    "username": "admin",
                    "password": password
                }
            )
        )

        print("Secret updated successfully.")

    except ClientError as error:
        print("Error updating secret:")
        print(error)


def list_secrets(client):
    """List secrets beginning with project/."""
    try:
        response = client.list_secrets()

        print("Project secrets:")

        for secret in response["SecretList"]:
            name = secret["Name"]

            if name.startswith("project/"):
                print(name)

    except ClientError as error:
        print("Error listing secrets:")
        print(error)


def main():
    """Run the complete Secrets Manager automation."""

    password = get_password()
    client = get_secrets_manager_client()

    print("==========================================")
    print("AWS Secrets Manager Python Automation")
    print("==========================================")

    create_secret(client, password)

    print()
    print("Reading secret...")
    get_secret(client)

    print()
    print("Updating secret...")
    update_secret(client, password)

    print()
    print("Reading updated secret...")
    get_secret(client)

    print()
    list_secrets(client)

    print("==========================================")
    print("Automation completed successfully.")
    print("==========================================")


if __name__ == "__main__":
    main()
