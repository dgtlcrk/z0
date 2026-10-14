# z0-cloud-01 / Phase 2 (draft)

A **standalone 24/7 ARM64 IRC/BotOps task** on Amazon ECS Fargate in us-east-1. No access to the home Raspberry Pi or home LAN. Nothing is provisioned by adding these files.

## Scope

- Dedicated VPC, single public subnet, internet gateway, route table, and outbound-only security group (no inbound rules).
- ECS Fargate service configured for one ARM64 task (0.25 vCPU / 512 MiB), **desired count zero by default** until launch approved, image pinned to an ECR commit tag.
- CloudWatch log group (14-day retention).
- Separate ECS execution and task IAM roles, no application AWS API permissions.
- Optional existing Secrets Manager secret for IRC_OP_SECRET; secret value never stored in Terraform.
- No ALB, NAT gateway, RDS, home tunnel, or public listener.

## Safety gate\n\nThe ECS service uses `enable_bot = false` by default, so a first Terraform apply provisions the service at desired count 0, **not** a running 24/7 bot. Do not turn it on until TLS-capable IRC application code is merged and tested, the destination approves bot connections, and deployment checks are complete. `enable_bot = true` is the explicitly reviewed production target.\n\n## Prerequisites before applying

1. Review IRC server policy and approve server/channel. Current Python IRC code does **not** set up SSL/TLS; default port 6667 uses plaintext IRC. Do not switch to 6697 assuming TLS is enabled.
2. Ensure the ECR SHA tag exists. This configuration initially pins `f595462a6e7a`.
3. Bootstrap a dedicated S3 Terraform-state bucket following `../../bootstrap-state/README.md` with versioning, encryption, public-access block, and restricted IAM access. Fill backend.hcl from backend.hcl.example. Backend initialization is deliberately blocked until this is done.
4. Prepare a separate least-privilege Terraform provisioner role; the ECR push role cannot create ECS/networking.
5. Optionally create a Secrets Manager secret outside Terraform, pass its ARN only, and consider KMS permissions if using a customer-managed key.
6. Review costs including Fargate 24/7, public IPv4, CloudWatch, and any Secrets Manager use. No automatic billing guardrail is included yet.
7. Confirm the public subnet's internet access and security egress meet your security requirements; destination IPs are not restricted and allow-listing should be considered.
8. Validate task runtime behavior. IRC bot reconnect / application-level health reporting is not an ECS container health check. A running ECS task is not proof of a successful IRC connection.
9. Confirm whether IRC nick and channel may conflict with the home instance (separate nickname is configured).

## Validation (after prerequisite setup)

```bash
cd infrastructure/terraform/environments/dev
cp backend.hcl.example backend.hcl
cp terraform.tfvars.example terraform.tfvars
# Fill both example files with actual values first.
terraform init -backend-config=backend.hcl
terraform fmt -check -recursive ../../
terraform validate
terraform plan -out=deploy.tfplan
# Review plan, IAM, networking and costs before:
# terraform apply deploy.tfplan
```

**Do not run apply until reviewed.** Terraform state configuration and permissions must be prepared separately. Nothing in this draft invokes terraform apply.

## Important limitations and next work

- ECS service is intended to run 24/7 after explicit enablement, but offers no availability SLA or application heartbeat yet.
- Network diagnostic commands (ping/traceroute) may require further testing and permissions under Fargate; do not presume they work.
- This container is the IRC BotOps workload, not the separate z0 API, scheduler, or home-network inventory.
- For secure IRC, implement and test TLS support in the application and select an approved TLS endpoint before production.
- Add CloudWatch alarms, cost budgets, and a separately scoped GitHub deployment role before enabling automated deployments. A GitHub Actions static validation workflow now checks formatting and validation on PRs, but does not plan/apply infrastructure.
