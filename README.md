AWS Secrets Manager + KMS Automation with Lambda (Real-Time DevOps Project)

Production-style AWS Secrets Management using Lambda, KMS, IAM Roles, EC2, CloudTrail, and Python

This project demonstrates how to securely manage database credentials in AWS without hardcoding passwords inside application code. A Lambda function automates KMS key creation, secret creation, and secret retrieval, while an EC2 application server securely fetches credentials from AWS Secrets Manager using an IAM Role. CloudTrail records every secret access for auditing.

Project Overview
Problem Statement

In many projects, database passwords are stored inside application code or configuration files.

Example:

DB_PASSWORD = "MyDB@123"

Problems:

Password exposed in Git repositories

Manual password updates

Service downtime after password changes

No audit trail

Security compliance issues

Solution

Store credentials in AWS Secrets Manager.

Encrypt secrets using AWS KMS.

Use Lambda for automation.

Allow EC2 to access secrets using IAM Roles.

Monitor all activities through CloudTrail.

Architecture
End-to-End Flow

Lambda creates a KMS Customer Managed Key.

Lambda enables KMS key rotation.

Lambda creates a secret in Secrets Manager.

Secret is encrypted using KMS.

EC2 Application Server requests the secret.

Secrets Manager asks KMS to decrypt it.

Credentials are returned.

Application connects to MySQL.

CloudTrail records every API call.

AWS Services Used

Service

	

Purpose




EC2

	

Application and Database Server




Lambda

	

Automation




Secrets Manager

	

Store credentials




KMS

	

Encryption




IAM

	

Secure access




CloudTrail

	

Audit logs




CloudWatch

	

Lambda logs

Project Setup (From Scratch)
Step 1 – Create Database Server EC2

Launch:

Setting

	

Value




Name

	

DB-Server




AMI

	

Ubuntu 22.04




Instance

	

t3.micro

Security Group

Type

	

Port




SSH

	

22




MySQL

	

3306

Install MySQL
sudo apt update
sudo apt install mysql-server -y
Login
sudo mysql

Notice:

The prompt changes from:

ubuntu@ip-172-31-xx-xx:~$

to

mysql>

This means you are inside the MySQL console.

Create Database
CREATE DATABASE appdb;

CREATE USER 'Application_user'@'%' IDENTIFIED BY 'MyDB@123';

GRANT ALL PRIVILEGES ON appdb.* TO 'Application_user'@'%';

FLUSH PRIVILEGES;
Verify
SHOW DATABASES;

SELECT User, Host FROM mysql.user WHERE User='Application_user';

Expected:

Application_user | %

The % means remote connections are allowed (subject to Security Groups).

Allow Remote Access

Edit:

sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf

Change

bind-address=127.0.0.1

to

bind-address=0.0.0.0

Restart:

sudo systemctl restart mysql

Verify:

sudo ss -lntp | grep 3306

Expected:

0.0.0.0:3306
Step 2 – Create Application Server EC2

Launch:

Setting

	

Value




Name

	

App-Server




AMI

	

Ubuntu

Install Python.

sudo apt update

sudo apt install python3-pip -y

python3 -m venv myenv

source myenv/bin/activate

pip install boto3 pymysql
Step 3 – Create KMS Key

Console

KMS

Customer Managed Keys

Create Key

Choose

Symmetric

Encrypt/Decrypt

Alias:

alias/demo-secret-key

Enable Automatic Rotation. 
amazon.com

Step 4 – IAM Roles
Lambda Role

Role Name

LambdaSecretsRole

Attach

AWSLambdaBasicExecutionRole

Custom Policy

{
 "Version":"2012-10-17",
 "Statement":[
  {
   "Effect":"Allow",
   "Action":[
    "kms:*",
    "secretsmanager:*"
   ],
   "Resource":"*"
  }
 ]
}
Application EC2 Role

Role Name

AppServerSecretsRole

Attach Policy


{
 "Version":"2012-10-17",
 "Statement":[
  {
   "Effect":"Allow",
   "Action":[
    "secretsmanager:GetSecretValue",
    "kms:Decrypt"
   ],
   "Resource":"*"
  }
 ]
}

Attach this IAM Role to the App Server EC2.

Step 5 – Create Lambda Function

Runtime

Python 3.12

Role

LambdaSecretsRole

Handler

lambda_function.lambda_handler
What does lambda_handler(event, context) do?
def lambda_handler(event, context):

This is the entry point of Lambda.

When AWS invokes Lambda, it automatically calls this function.

event → Trigger input

context → Execution information

Lambda Python Code

This single Lambda will:

Create KMS Key

Enable Key Rotation

Create Secret

Store Database Credentials

Retrieve Secret

Return Output


import boto3
import json
from botocore.exceptions import ClientError

kms=boto3.client("kms")
secrets=boto3.client("secretsmanager")

SECRET_NAME="DemoDBSecret"

def lambda_handler(event,context):

    key=kms.create_key(
        Description="Demo Secret Key"
    )

    key_id=key["KeyMetadata"]["KeyId"]

    kms.enable_key_rotation(
        KeyId=key_id
    )

    kms.create_alias(
        AliasName="alias/demo-secret-key",
        TargetKeyId=key_id
    )

    secret_value={
        "host":"YOUR_DB_PUBLIC_IP",
        "username":"Application_user",
        "password":"MyDB@123",
        "database":"appdb",
        "port":"3306"
    }

    try:

        secrets.create_secret(
            Name=SECRET_NAME,
            SecretString=json.dumps(secret_value),
            KmsKeyId=key_id
        )

    except ClientError as e:

        if e.response["Error"]["Code"]=="ResourceExistsException":

            secrets.put_secret_value(
                SecretId=SECRET_NAME,
                SecretString=json.dumps(secret_value)
            )

    response=secrets.get_secret_value(
        SecretId=SECRET_NAME
    )

    data=json.loads(response["SecretString"])

    return{
        "statusCode":200,
        "body":{
            "SecretName":SECRET_NAME,
            "Host":data["host"],
            "Username":data["username"],
            "KMSKey":key_id
        }
    }

Replace

YOUR_DB_PUBLIC_IP

with your MySQL server IP.

Lambda Test

Click

Test

Expected Output


{
 "statusCode":200,
 "body":{
  "SecretName":"DemoDBSecret",
  "Host":"98.xx.xx.xx",
  "Username":"Application_user",
  "KMSKey":"abcd-1234..."
 }
}
Step 6 – Verify Secret

Secrets Manager

Open

DemoDBSecret

Secret


{
 "host":"98.xx.xx.xx",
 "username":"Application_user",
 "password":"MyDB@123",
 "database":"appdb",
 "port":"3306"
}

The password remains encrypted at rest using KMS. 
amazon.com

Step 7 – Enable Secret Rotation

Open Secret

Rotation

Enable Rotation

Choose a Lambda rotation function.

AWS updates both the secret and the database credentials according to the configured schedule. 
amazon.com

Step 8 – Application Fetches Secret

The application never stores the password.

Python Code

import boto3
import json
import pymysql

client=boto3.client("secretsmanager")

response=client.get_secret_value(
    SecretId="DemoDBSecret"
)

secret=json.loads(response["SecretString"])

print("Retrieved Secret")

print("Host:",secret["host"])
print("Username:",secret["username"])
print("Database:",secret["database"])
print("Password: ********")

conn=pymysql.connect(
    host=secret["host"],
    user=secret["username"],
    password=secret["password"],
    database=secret["database"],
    port=int(secret["port"])
)

print("Connected Successfully")

Run

python3 demo-secret-manager.py

Expected Output

Retrieved Secret

Host:98.xx.xx.xx

Username:Application_user

Database:appdb

Password:********

Connected Successfully
How Secret Retrieval Works Internally
Key Rotation vs Secret Rotation

Feature

	

KMS Key Rotation

	

Secret Rotation




Rotates

	

Encryption Key

	

Database Password




Service

	

KMS

	

Secrets Manager




Code Change

	

No

	

No




Example

	

V1 → V2

	

MyDB@123 → MyDB@456

KMS rotation changes the encryption key material while Secrets Manager rotation changes the actual credential used by the application. 
amazon.com
+1

CloudTrail Monitoring

CloudTrail automatically records every Secrets Manager and KMS API call. 
amazon.com

Create Trail

CloudTrail

Create Trail

Enable:

Management Events

Read Events

Write Events

View Secret Access Events

Open

CloudTrail

Event History

Filter

Event Source:
secretsmanager.amazonaws.com

Events:

Event

	

Meaning




CreateSecret

	

Secret created




GetSecretValue

	

App accessed secret




PutSecretValue

	

Secret updated




RotateSecret

	

Secret rotated

View KMS Events

Filter

kms.amazonaws.com

Events:

Event

	

Meaning




CreateKey

	

KMS Key created




EnableKeyRotation

	

Rotation enabled




Decrypt

	

Secret decrypted

Example CloudTrail Event

This JSON is generated automatically by CloudTrail after your application accesses the secret.


{
 "eventName":"GetSecretValue",
 "userIdentity":{
  "type":"AssumedRole",
  "sessionContext":{
   "sessionIssuer":{
    "userName":"AppServerSecretsRole"
   }
  }
 },
 "sourceIPAddress":"54.xx.xx.xx",
 "eventTime":"2026-08-31T10:15:00Z"
}
How to Analyze It

Field

	

Meaning




eventName

	

Secret accessed




userIdentity

	

IAM Role used




sourceIPAddress

	

EC2 IP




eventTime

	

Time of access

CloudWatch Logs

Lambda automatically writes logs.

Example

START RequestId

Secret Created

Secret Retrieved Successfully

END RequestId

CloudWatch is the first place to investigate Lambda failures. 
amazon.com

Testing Checklist

Test

	

Expected Result




Lambda Invoke

	

Secret created




Secrets Manager

	

Secret visible




EC2 Python

	

Connected Successfully




CloudTrail

	

GetSecretValue logged




CloudTrail

	

Decrypt logged




CloudWatch

	

Lambda logs visible

Common Issues & Fixes

Issue

	

Cause

	

Fix




AccessDenied

	

Missing IAM permission

	

Attach required policies




KMS Decrypt Denied

	

Missing kms:Decrypt

	

Update IAM policy




Secret Already Exists

	

Duplicate name

	

Use put_secret_value()




MySQL Access Denied

	

User mismatch

	

Create correct MySQL user




Connection Timeout

	

Security Group

	

Allow port 3306




Rotation Failed

	

Lambda issue

	

Check CloudWatch




Wrong Region

	

Resource mismatch

	

Keep resources in same Region

Real-Time Use Case

Imagine an e-commerce application.

Without Secrets Manager:

DB_PASSWORD="MyDB@123"

Problems

Password exposed

Manual updates

Redeployment required

With Secrets Manager

EC2 requests the secret.

IAM Role authenticates.

Secrets Manager returns credentials.

KMS decrypts automatically.

Application connects without exposing passwords.

The same pattern is used in:

Banking

Healthcare

CI/CD pipelines

Microservices

SaaS platforms

Cost Optimization Through Automation

Automation does not remove the Secrets Manager service cost, but it significantly reduces operational effort.

Before

Manual secret creation

Manual password updates

Application redeployment

Manual auditing

After

Lambda creates secrets automatically.

Password rotation is automatic.

No redeployment after password changes.

CloudTrail provides instant auditing.

Example

Environment

	

Manual

	

Automated




20 Applications

	

8–10 hours

	

10 minutes

Project Outcome

This project successfully automated secure credential management using AWS native services.

Achievements

Created encrypted secrets.

Enabled KMS key rotation.

Allowed EC2 to fetch secrets securely.

Eliminated hardcoded passwords.

Audited every access through CloudTrail.

Demonstrated a production-style DevOps security workflow.

Business Benefits

Improved security

Reduced manual effort

Automatic credential rotation

Centralized secret management

Faster deployments

Complete audit trail
