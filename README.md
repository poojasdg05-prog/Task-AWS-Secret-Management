# AWS Secrets Manager + KMS Automation with Lambda (Real-Time DevOps Project)

> **Production-style AWS Secrets Management using Lambda, KMS, IAM Roles, EC2, CloudTrail, and Python**

This project demonstrates how to securely manage database credentials in AWS without hardcoding passwords inside application code. A Lambda function automates KMS key creation, secret creation, and secret retrieval, while an EC2 Application Server securely fetches credentials from AWS Secrets Manager using an IAM Role. CloudTrail records every secret access for auditing.

---

## Table of Contents

* [Project Overview](#project-overview)
* [Architecture](#architecture)
* [AWS Services Used](#aws-services-used)
* [Project Setup](#project-setup)
* [IAM Roles and Policies](#iam-roles-and-policies)
* [Lambda Automation](#lambda-automation)
* [Application Secret Retrieval](#application-secret-retrieval)
* [Key Rotation vs Secret Rotation](#key-rotation-vs-secret-rotation)
* [CloudTrail Monitoring](#cloudtrail-monitoring)
* [Testing](#testing)
* [Troubleshooting](#troubleshooting)
* [Real-Time Use Case](#real-time-use-case)
* [Cost Optimization](#cost-optimization)
* [Project Outcome](#project-outcome)
* [Interview Summary](#interview-summary)

---

# Project Overview

## Problem Statement

Many organizations still store database passwords inside application code or configuration files.

Example:

```python
DB_PASSWORD = "MyDB@123"
```

### Problems

* Credentials exposed in Git repositories.
* Manual password updates.
* Application downtime after password changes.
* No audit trail.
* Security compliance issues.

## Solution

This project solves those problems by:

* Storing credentials in AWS Secrets Manager.
* Encrypting secrets using AWS KMS.
* Automating secret creation using AWS Lambda.
* Allowing EC2 to securely access secrets using IAM Roles.
* Monitoring every access through CloudTrail.

---

# Architecture

## High-Level Flow

```text
             Lambda
                │
                ▼
      Create KMS Customer Key
                │
                ▼
      Enable Key Rotation
                │
                ▼
      Create Secret in Secrets Manager
                │
                ▼
        Encrypted using KMS
                │
                ▼
      App Server (EC2) requests Secret
                │
                ▼
   Secrets Manager asks KMS to Decrypt
                │
                ▼
      Database Credentials Returned
                │
                ▼
      MySQL Database Connection
                │
                ▼
 CloudTrail Logs Every API Call
```

---

# AWS Services Used

| Service         | Purpose                       |
| --------------- | ----------------------------- |
| EC2             | Application & Database Server |
| Lambda          | Automation                    |
| Secrets Manager | Secure credential storage     |
| KMS             | Encryption                    |
| IAM             | Secure authentication         |
| CloudTrail      | Auditing                      |
| CloudWatch      | Lambda logs                   |

---

# Project Setup

## Step 1: Create Database Server EC2

Launch an EC2 instance.

| Setting       | Value        |
| ------------- | ------------ |
| Name          | DB-Server    |
| AMI           | Ubuntu 22.04 |
| Instance Type | t3.micro     |

### Security Group

| Type  | Port |
| ----- | ---- |
| SSH   | 22   |
| MySQL | 3306 |

### Install MySQL

```bash
sudo apt update
sudo apt install mysql-server -y
```

### Open MySQL

```bash
sudo mysql
```

The prompt changes from:

```text
ubuntu@ip-172-31-xx-xx:~$
```

to

```text
mysql>
```

### Create Database and User

Run inside the MySQL console.

```sql
CREATE DATABASE appdb;

CREATE USER 'Application_user'@'%' IDENTIFIED BY 'MyDB@123';

GRANT ALL PRIVILEGES ON appdb.* TO 'Application_user'@'%';

FLUSH PRIVILEGES;
```

### Verify

```sql
SHOW DATABASES;

SELECT User, Host FROM mysql.user WHERE User='Application_user';
```

Expected:

```text
Application_user | %
```

### Allow Remote Connections

Edit:

```bash
sudo nano /etc/mysql/mysql.conf.d/mysqld.cnf
```

Change:

```text
bind-address = 127.0.0.1
```

to

```text
bind-address = 0.0.0.0
```

Restart MySQL.

```bash
sudo systemctl restart mysql
```

Verify.

```bash
sudo ss -lntp | grep 3306
```

Expected:

```text
0.0.0.0:3306
```

---

## Step 2: Create Application Server EC2

Launch another EC2.

| Setting | Value      |
| ------- | ---------- |
| Name    | App-Server |
| AMI     | Ubuntu     |

### Install Python

```bash
sudo apt update
sudo apt install python3-pip -y

python3 -m venv myenv
source myenv/bin/activate

pip install boto3 pymysql
```

This EC2 will securely fetch database credentials from Secrets Manager.

---

# Step 3: Create KMS Customer Managed Key

1. Open AWS Console.
2. Go to **KMS**.
3. Select **Customer Managed Keys**.
4. Click **Create Key**.
5. Choose:

   * Symmetric
   * Encrypt/Decrypt
6. Alias:

```text
alias/demo-secret-key
```

7. Enable automatic key rotation.

---

# IAM Roles and Policies

## Lambda Role

**Role Name**

```text
LambdaSecretsRole
```

### Attach Managed Policy

* `AWSLambdaBasicExecutionRole`

### Custom Policy

```json
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
```

### Why These Permissions?

| Permission                    | Purpose         |
| ----------------------------- | --------------- |
| kms:CreateKey                 | Create KMS Key  |
| kms:EnableKeyRotation         | Enable rotation |
| secretsmanager:CreateSecret   | Create secret   |
| secretsmanager:PutSecretValue | Update secret   |
| secretsmanager:GetSecretValue | Retrieve secret |

---

## EC2 Application Role

**Role Name**

```text
AppServerSecretsRole
```

### Custom Policy

```json
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
```

Attach this IAM Role to the Application Server EC2.

---

# Lambda Automation

## Create Lambda

| Setting | Value                            |
| ------- | -------------------------------- |
| Runtime | Python 3.12                      |
| Role    | LambdaSecretsRole                |
| Handler | `lambda_function.lambda_handler` |

## What is `lambda_handler(event, context)`?

```python
def lambda_handler(event, context):
```

This is the **entry point** of the Lambda function.

When AWS invokes Lambda:

* `event` → Input data
* `context` → Execution metadata

Execution starts from this function.

---

# Complete Lambda Code

This single Lambda will:

* Create KMS Key
* Enable Key Rotation
* Create Secret
* Store Database Credentials
* Retrieve Secret
* Return Output

```python
import boto3
import json
from botocore.exceptions import ClientError

kms = boto3.client("kms")
secrets = boto3.client("secretsmanager")

SECRET_NAME = "DemoDBSecret"

def lambda_handler(event, context):

    # Create KMS Key
    key = kms.create_key(
        Description="Demo Secret Key"
    )

    key_id = key["KeyMetadata"]["KeyId"]

    # Enable Rotation
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

    response = secrets.get_secret_value(
        SecretId=SECRET_NAME
    )

    data = json.loads(response["SecretString"])

    return{
        "statusCode":200,
        "body":{
            "SecretName":SECRET_NAME,
            "Host":data["host"],
            "Username":data["username"],
            "KMSKey":key_id
        }
    }
```

Replace:

```text
YOUR_DB_PUBLIC_IP
```

with your Database Server IP.

---

## Lambda Test

Click **Test**.

Expected Output

```json
{
 "statusCode":200,
 "body":{
   "SecretName":"DemoDBSecret",
   "Host":"98.xx.xx.xx",
   "Username":"Application_user",
   "KMSKey":"abcd-1234..."
 }
}
```

---

# Verify Secret

Open:

**Secrets Manager → DemoDBSecret**

Stored Secret

```json
{
 "host":"98.xx.xx.xx",
 "username":"Application_user",
 "password":"MyDB@123",
 "database":"appdb",
 "port":"3306"
}
```

The secret is encrypted using KMS.

---

# Enable Secret Rotation

1. Open Secret.
2. Go to **Rotation**.
3. Enable Rotation.
4. Choose a Lambda rotation function.
5. Configure a schedule.

---

# Application Secret Retrieval

The application never stores passwords locally.

## Python Code

```python
import boto3
import json
import pymysql

client = boto3.client("secretsmanager")

response = client.get_secret_value(
    SecretId="DemoDBSecret"
)

secret = json.loads(response["SecretString"])

print("Retrieved Secret")

print("Host:", secret["host"])
print("Username:", secret["username"])
print("Database:", secret["database"])
print("Password: ********")

conn = pymysql.connect(
    host=secret["host"],
    user=secret["username"],
    password=secret["password"],
    database=secret["database"],
    port=int(secret["port"])
)

print("Connected Successfully")
```

Run

```bash
python3 demo-secret-manager.py
```

Expected Output

```text
Retrieved Secret

Host:98.xx.xx.xx

Username:Application_user

Database:appdb

Password:********

Connected Successfully
```

---

# How Secret Retrieval Works

```text
App Server
    │
    ▼
GetSecretValue()
    │
    ▼
Secrets Manager
    │
    ▼
KMS Decrypt
    │
    ▼
Credentials Returned
    │
    ▼
MySQL Database
```

---

# Key Rotation vs Secret Rotation

| Feature              | KMS Key Rotation | Secret Rotation         |
| -------------------- | ---------------- | ----------------------- |
| Rotates              | Encryption Key   | Database Password       |
| Service              | KMS              | Secrets Manager         |
| Code Change Required | No               | No                      |
| Example              | Key V1 → V2      | `MyDB@123` → `MyDB@456` |

### KMS Key Rotation

* Rotates encryption key material.
* Same Key ID.
* Applications continue working.

### Secret Rotation

* Changes actual database password.
* Updates both Secrets Manager and MySQL.
* Application automatically receives the latest password.

---

# CloudTrail Monitoring

CloudTrail automatically records every API call made to Secrets Manager and KMS.

## Create Trail

1. Open CloudTrail.
2. Create Trail.
3. Enable:

   * Management Events
   * Read Events
   * Write Events

---

## Monitor Secret Access

Go to:

**CloudTrail → Event History**

Filter:

```text
Event Source

secretsmanager.amazonaws.com
```

Events:

| Event          | Meaning            |
| -------------- | ------------------ |
| CreateSecret   | Secret created     |
| GetSecretValue | App fetched secret |
| PutSecretValue | Secret updated     |
| RotateSecret   | Secret rotated     |

---

## Monitor KMS Events

Filter:

```text
kms.amazonaws.com
```

Events:

| Event             | Meaning          |
| ----------------- | ---------------- |
| CreateKey         | Key created      |
| EnableKeyRotation | Rotation enabled |
| Decrypt           | Secret decrypted |

---

## Example CloudTrail Event

```json
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
```

### How to Analyze It

| Field           | Meaning         |
| --------------- | --------------- |
| eventName       | Secret accessed |
| userIdentity    | IAM Role used   |
| sourceIPAddress | EC2 IP          |
| eventTime       | Access time     |

---

# CloudWatch Logs

Lambda automatically writes logs.

Example

```text
START RequestId

Secret Created

Secret Retrieved Successfully

END RequestId
```

CloudWatch is the first place to troubleshoot Lambda failures.

---

# Testing

| Test          | Expected Result        |
| ------------- | ---------------------- |
| Invoke Lambda | Secret created         |
| Verify Secret | Secret stored          |
| Run EC2 App   | Connected Successfully |
| CloudTrail    | GetSecretValue logged  |
| KMS           | Decrypt event logged   |
| CloudWatch    | Lambda logs visible    |

---

# Troubleshooting

| Issue               | Cause                  | Fix                            |
| ------------------- | ---------------------- | ------------------------------ |
| AccessDenied        | Missing IAM permission | Attach correct policy          |
| KMS Decrypt Denied  | Missing `kms:Decrypt`  | Update IAM Role                |
| Secret Exists       | Duplicate name         | Use `put_secret_value()`       |
| MySQL Access Denied | User mismatch          | Create correct MySQL user      |
| Connection Timeout  | Security Group         | Allow port 3306                |
| Lambda Timeout      | Low timeout            | Increase timeout               |
| Wrong Region        | Resource mismatch      | Keep everything in same Region |

---

# Real-Time Use Case

Imagine an E-Commerce Application.

Without Secrets Manager

```python
DB_PASSWORD="MyDB@123"
```

Problems

* Password exposed
* Manual updates
* Redeployment required

With Secrets Manager

1. EC2 requests the secret.
2. IAM Role authenticates.
3. Secrets Manager returns credentials.
4. KMS decrypts them.
5. Application connects securely.

The same approach is used in:

* Banking
* Healthcare
* CI/CD Pipelines
* Microservices
* SaaS Platforms

---

# Cost Optimization

This project reduces operational costs by automating repetitive tasks.

## Before Automation

* Manual secret creation
* Manual password updates
* Application redeployment
* Manual auditing

## After Automation

* Lambda creates secrets automatically.
* Password rotation is automated.
* Applications continue working without code changes.
* CloudTrail provides instant auditing.

Example

| Applications | Manual     | Automated  |
| ------------ | ---------- | ---------- |
| 20 Apps      | 8–10 hours | 10 minutes |

---

# Project Outcome

## Achievements

* Automated KMS Key creation.
* Enabled Key Rotation.
* Created encrypted Secrets.
* Securely retrieved credentials from EC2.
* Eliminated hardcoded passwords.
* Monitored every access through CloudTrail.
* Demonstrated a production-style DevOps workflow.

## Business Benefits

* Improved Security
* Reduced Manual Effort
* Automatic Credential Rotation
* Centralized Secret Management
* Faster Deployments
* Complete Audit Trail

---

# Interview Summary (1 Minute)

> In this project, I automated secret management using AWS Lambda, Secrets Manager, and KMS. Lambda creates the encryption key and stores database credentials securely in Secrets Manager. The EC2 Application Server retrieves credentials dynamically using an IAM Role instead of hardcoding passwords. KMS encrypts and decrypts the secret transparently, while CloudTrail records every access for auditing. This solution improves security, supports automatic credential rotation, reduces operational effort, and follows production-grade AWS security best practices.

---

## Repository Structure

```text
aws-secrets-manager-demo/
│
├── README.md
├── lambda/
│   └── lambda_function.py
├── app/
│   └── demo-secret-manager.py
├── screenshots/
│   ├── architecture.png
│   ├── lambda-output.png
│   ├── secret-manager.png
│   ├── cloudtrail-events.png
│   └── cloudwatch-logs.png
└── IAM-Policies/
    ├── LambdaSecretsRole.json
    └── AppServerSecretsRole.json
```

---

## Future Enhancements

* Store RDS credentials instead of EC2-hosted MySQL.
* Integrate with ECS and EKS workloads.
* Enable EventBridge-triggered secret rotation.
* Replicate secrets across AWS Regions.
* Add Terraform or CloudFormation for Infrastructure as Code (IaC).
* Integrate with Jenkins and GitHub Actions for CI/CD secret management.

---

## Author

**AWS DevOps Hands-on Project**

Secure Secret Management • AWS Lambda • Secrets Manager • KMS • IAM • EC2 • CloudTrail • Python
