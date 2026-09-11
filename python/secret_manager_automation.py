import json
import boto3
import pymysql
from botocore.exceptions import ClientError

# ==============================
# Configuration
# ==============================

SECRET_NAME = "myapp/database-secret"
AWS_REGION = "us-east-1"

# ==============================
# Get secret from AWS Secrets Manager
# ==============================

def get_secret():
    client = boto3.client(
        "secretsmanager",
        region_name=AWS_REGION
    )

    try:
        response = client.get_secret_value(
            SecretId=SECRET_NAME
        )

        secret_string = response["SecretString"]

        # Convert JSON string into Python dictionary
        secret = json.loads(secret_string)

        return secret

    except ClientError as e:
        print("Error retrieving secret from AWS Secrets Manager")
        print(e)
        return None


# ==============================
# Connect to MySQL database
# ==============================

def connect_to_database(secret):

    try:
        connection = pymysql.connect(
            host=secret["host"],
            user=secret["username"],
            password=secret["password"],
            database=secret["database"],
            port=int(secret["port"])
        )

        print("Database connection successful!")

        return connection

    except pymysql.MySQLError as e:
        print("Database connection failed")
        print(e)
        return None


# ==============================
# Main program
# ==============================

def main():

    print("Retrieving secret from AWS Secrets Manager...")

    secret = get_secret()

    if secret is None:
        return

    # --------------------------------
    # Do NOT print the real password
    # --------------------------------

    print("\nSecret retrieved successfully")
    print("Host     :", secret["host"])
    print("Username :", secret["username"])
    print("Password : ******")
    print("Database :", secret["database"])
    print("Port     :", secret["port"])

    # --------------------------------
    # Connect to database
    # --------------------------------

    connection = connect_to_database(secret)

    if connection is None:
        return

    # --------------------------------
    # Test database
    # --------------------------------

    try:
        cursor = connection.cursor()

        cursor.execute("SELECT VERSION();")

        result = cursor.fetchone()

        print("\nMySQL connection test successful!")
        print("MySQL Version:", result[0])

        cursor.close()
        connection.close()

        print("Database connection closed.")

    except pymysql.MySQLError as e:
        print("Database query failed")
        print(e)


# ==============================
# Run program
# ==============================

if __name__ == "__main__":
    main()
