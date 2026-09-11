AWS Secrets Manager + KMS Automation using Lambda (Real-Time DevOps Project)

A production-style AWS DevOps project demonstrating secure database credential management using AWS Secrets Manager, AWS KMS, Lambda, IAM Roles, EC2, CloudTrail, and Python (Boto3).

AWS Python Lambda KMS CloudTrail

Project Overview
Problem Statement

In many applications, database credentials are hardcoded inside source code or configuration files.

DB_HOST="98.xx.xx.xx"
DB_USER="Application_user"
DB_PASSWORD="MyDB@123"
Problems with Hardcoded Credentials

Password exposed in Git repositories.

Manual password updates.

Application redeployment after password changes.

No centralized credential management.

No audit trail.

Increased security risk.

Solution

This project automates secure secret management using AWS native services.

Lambda automatically creates KMS Keys.

Lambda creates Secrets Manager secrets.

KMS encrypts database credentials.

EC2 Application Server retrieves secrets using IAM Roles.

CloudTrail records every secret access.

CloudWatch stores Lambda execution logs.

Architecture
Workflow

Lambda creates a Customer Managed KMS Key.

Lambda enables Key Rotation.

Lambda stores database credentials in Secrets Manager.

Secret is encrypted using KMS.

Application Server requests the secret.

Secrets Manager calls KMS for decryption.

Credentials are returned securely.

Application connects to MySQL.

CloudTrail records every API call.

AWS Services Used

Service

	

Purpose




EC2

	

Application & Database Server




Lambda

	

Automation




Secrets Manager

	

Secure credential storage




KMS

	

Encryption




IAM

	

Secure authentication




CloudTrail

	

Audit logging




CloudWatch

	

Lambda logs

Prerequisites

AWS Account

IAM User with Administrator Access (for demo)

AWS CLI (optional)

Python 3.12

Boto3

PyMySQL

Install Python packages.

python3 -m venv myenv
source myenv/bin/activate

pip install boto3 pymysql
Step 1 – Create Database Server

Launch an EC2 instance.

Setting

	

Value




Name

	

DB-Server




AMI

	

Ubuntu 22.04




Instance

	

t3.micro




Storage

	

8 GB

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
Login to MySQL
sudo mysql

The prompt changes to:

mysql>
Create Database and User
CREATE DATABASE appdb;

CREATE USER 'Application_user'@'%' IDENTIFIED BY 'MyDB@123';

GRANT ALL PRIVILEGES ON appdb.* TO 'Application_user'@'%';

FLUSH PRIVILEGES;
Verify
SHOW DATABASES;

SELECT User,Host FROM mysql.user;

Expected:

Application_user | %
Enable Remote Access

Edit:

sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf

Change

bind-address = 127.0.0.1

to

bind-address = 0.0.0.0

Restart MySQL.

sudo systemctl restart mysql

Verify.

sudo ss -lntp | grep 3306

Expected:

0.0.0.0:3306
Step 2 – Create Application Server

Launch another EC2.

Setting

	

Value




Name

	

App-Server




AMI

	

Ubuntu




Instance

	

t3.micro

Install Python.

sudo apt update
sudo apt install python3-pip -y

python3 -m venv myenv
source myenv/bin/activate

pip install boto3 pymysql
Step 3 – Create Customer Managed KMS Key

Open:

AWS Console → KMS → Customer Managed Keys

Click Create Key.

Choose:

Symmetric

Encrypt/Decrypt

Alias:

alias/demo-secret-key

Enable Automatic Key Rotation. 
amazon.com

Step 4 – IAM Roles
Lambda Role

Role Name

LambdaSecretsRole
Attach Managed Policy

AWSLambdaBasicExecutionRole

Custom IAM Policy
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
Why?

Permission

	

Purpose




kms:CreateKey

	

Create encryption key




kms:EnableKeyRotation

	

Enable rotation




secretsmanager:CreateSecret

	

Store credentials




secretsmanager:GetSecretValue

	

Retrieve credentials

EC2 Application Role

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

Attach this role to your App-Server EC2.

Step 5 – Create Lambda Function

Runtime:

Python 3.12

Execution Role:

LambdaSecretsRole

Handler:

lambda_function.lambda_handler
Understanding lambda_handler(event, context)
def lambda_handler(event, context):

This is the entry point of Lambda.

Whenever Lambda is invoked, AWS automatically executes this function.

Parameter

	

Purpose




event

	

Trigger input




context

	

Execution metadata

Lambda Automation Code

This single Lambda performs:

Create KMS Key

Enable Rotation

Create Secret

Store Credentials

Retrieve Secret

import boto3
import json
from botocore.exceptions import ClientError

kms = boto3.client("kms")
secrets = boto3.client("secretsmanager")

SECRET_NAME = "DemoDBSecret"

def lambda_handler(event, context):

    key = kms.create_key(
        Description="Demo Secret Key"
    )

    key_id = key["KeyMetadata"]["KeyId"]

    kms.enable_key_rotation(
        KeyId=key_id
    )

    kms.create_alias(
        AliasName="alias/demo-secret-key",
        TargetKeyId=key_id
    )

    secret_value = {
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

Replace:

YOUR_DB_PUBLIC_IP

with your database server IP.

Lambda Test

Click Test.

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

Open:

Secrets Manager → DemoDBSecret

Secret looks like:

{
 "host":"98.xx.xx.xx",
 "username":"Application_user",
 "password":"MyDB@123",
 "database":"appdb",
 "port":"3306"
}

Notice:

Password is encrypted.

KMS protects the secret at rest. 
amazon.com

Step 7 – Enable Secret Rotation

Open:

Secrets Manager → Rotation

Enable Rotation.

Choose a Lambda rotation function.

AWS automatically rotates the database credential according to the configured schedule. 
amazon.com

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




Application Changes

	

No

	

No




Example

	

Key Version V1 → V2

	

MyDB@123 → MyDB@456

Example

Before Rotation

Password: MyDB@123

After Rotation

Password: MyDB@456

The application continues working because it always retrieves the latest secret dynamically.

Step 8 – Application Fetches Secret

The application never stores credentials locally.

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

Run:

python3 demo-secret-manager.py

Expected Output

Retrieved Secret

Host:98.xx.xx.xx

Username:Application_user

Database:appdb

Password:********

Connected Successfully
How Secret Retrieval Works
CloudTrail Monitoring

CloudTrail automatically records all Secrets Manager and KMS API calls. 
amazon.com

Create Trail

Open:

CloudTrail → Create Trail

Enable:

Management Events

Read Events

Write Events

View Secret Access

Open:

CloudTrail → Event History

Filter

Event Source:
secretsmanager.amazonaws.com

Expected Events

Event

	

Meaning




CreateSecret

	

Secret created




GetSecretValue

	

Application accessed secret




PutSecretValue

	

Secret updated




RotateSecret

	

Secret rotated

View KMS Events

Filter

kms.amazonaws.com

Expected

Event

	

Meaning




CreateKey

	

Key created




EnableKeyRotation

	

Rotation enabled




Decrypt

	

Secret decrypted

Example CloudTrail Event

CloudTrail automatically generates JSON similar to:

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
Event Analysis

Field

	

Meaning




eventName

	

Secret accessed




userIdentity

	

IAM Role used




sourceIPAddress

	

EC2 source




eventTime

	

Time of access

CloudWatch Logs

Lambda automatically writes execution logs.

Example

START RequestId

Secret Created

Secret Retrieved Successfully

END RequestId

CloudWatch is the first place to troubleshoot Lambda execution failures.

End-to-End Testing

Test

	

Expected Result




Invoke Lambda

	

Secret created




Verify Secret

	

Encrypted




Run Python App

	

Connected Successfully




CloudTrail

	

GetSecretValue logged




KMS

	

Decrypt logged




CloudWatch

	

Logs generated

Common Issues & Fixes

Issue

	

Cause

	

Fix




AccessDenied

	

Missing IAM permission

	

Attach required policy




KMS Decrypt Denied

	

Missing kms:Decrypt

	

Update IAM Role




Secret Exists

	

Duplicate secret

	

Use put_secret_value()




MySQL Access Denied

	

User mismatch

	

Create correct MySQL user




Connection Timeout

	

Security Group

	

Allow Port 3306




Rotation Failed

	

Lambda error

	

Check CloudWatch




Wrong Region

	

Resource mismatch

	

Keep resources in same Region

Real-Time Use Case

Imagine an e-commerce company.

Without Secrets Manager:

Password stored in code.

Password shared manually.

Redeployment required after updates.

With Secrets Manager:

Application requests credentials.

IAM Role authenticates.

Secrets Manager returns encrypted credentials.

KMS decrypts automatically.

CloudTrail records the access.

This same pattern is used in:

Banking Applications

Healthcare Systems

CI/CD Pipelines

Microservices

SaaS Platforms

Cost Optimization

This automation reduces operational costs, not the AWS service cost itself.

Before Automation

Manual secret creation

Manual password updates

Application redeployment

Manual auditing

After Automation

Lambda creates secrets automatically.

Password rotation is automated.

No redeployment required.

CloudTrail provides instant auditing.

Example:

Applications

	

Manual

	

Automated




20 Applications

	

8–10 hours

	

10 minutes

Project Outcome

This project successfully automated secure credential management using AWS native services.

Achievements

Created encrypted database secrets.

Enabled KMS key rotation.

Allowed EC2 to retrieve secrets securely using IAM Roles.

Eliminated hardcoded credentials.

Monitored every access through CloudTrail.

Demonstrated a production-style DevOps security workflow.

Business Benefits

Improved Security

Reduced Manual Effort

Automatic Credential Rotation

Centralized Secret Management

Faster Deployments

Complete Audit Trail

Repository Structure
aws-secret-manager-automation/
│
├── lambda/
│   └── lambda_function.py
│
├── app/
│   └── demo-secret-manager.py
│
├── policies/
│   ├── lambda-policy.json
│   └── appserver-policy.json
│
├── screenshots/
│   ├── architecture.png
│   ├── lambda-output.png
│   ├── cloudtrail-events.png
│   └── secret-created.png
│
└── README.md
