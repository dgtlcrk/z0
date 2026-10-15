# Bootstrap Terraform state (manual controlled prerequisite)

Do not use the application Terraform state to create its own backend.

For the initial bootstrap, create a **dedicated globally unique S3 bucket** in account YOUR_AWS_ACCOUNT_ID, region us-east-1. State contains sensitive infrastructure metadata and must not be committed.

The following commands intentionally require a real bucket name and an authenticated administrator with appropriate permissions. They are **examples, not an automated deployment**.

```bash
aws sts get-caller-identity
# Stop if Account is not YOUR_AWS_ACCOUNT_ID.
export AWS_REGION=us-east-1
export TF_STATE_BUCKET=REPLACE_WITH_UNIQUE_Z0_STATE_BUCKET
test "$TF_STATE_BUCKET" != REPLACE_WITH_UNIQUE_Z0_STATE_BUCKET || exit 1

aws s3api create-bucket --bucket "$TF_STATE_BUCKET" --region "$AWS_REGION"
aws s3api put-public-access-block --bucket "$TF_STATE_BUCKET" --public-access-block-configuration 'BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true'
aws s3api put-bucket-versioning --bucket "$TF_STATE_BUCKET" --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption --bucket "$TF_STATE_BUCKET" --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
aws s3api put-bucket-policy --bucket "$TF_STATE_BUCKET" --policy file://state-bucket-policy.json
```

**Never run the last command until you replace the example bucket ARN in the JSON policy below.** Apply least-privilege IAM permissions to the Terraform operator/role for the specific state key and lockfile. For the S3 native lockfile mechanism, the operator requires GetObject/PutObject/DeleteObject on `z0/dev/terraform.tfstate.tflock` and GetObject/PutObject on the state key; bucket ListBucket scope should be restricted to these keys. Terraform does not require DeleteObject on the state object itself.

Example additional *bucket policy* guardrails (replace bucket name):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyInsecureTransport",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "s3:*",
      "Resource": [
        "arn:aws:s3:::REPLACE_WITH_UNIQUE_Z0_STATE_BUCKET",
        "arn:aws:s3:::REPLACE_WITH_UNIQUE_Z0_STATE_BUCKET/*"
      ],
      "Condition": { "Bool": { "aws:SecureTransport": "false" } }
    }
  ]
}
```

Also enable the AWS account-level S3 public-access block, where organizational permissions allow it. Review backup/recovery and restricted access before first `terraform init`.

A secure backend bucket does not grant Terraform permission to provision ECS: provisioning needs a separately reviewed role and policy. No provisioning role is created by this draft.
