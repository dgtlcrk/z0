data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  name       = "z0-cloud-01"
  image_uri  = "${var.aws_account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/z0:${var.image_tag}"
  secret_env = var.irc_op_secret_arn == null ? [] : [
    {
      name      = "IRC_OP_SECRET"
      valueFrom = var.irc_op_secret_arn
    }
  ]
}

resource "aws_vpc" "cloud" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = { Name = "${local.name}-vpc" }
}

resource "aws_internet_gateway" "cloud" {
  vpc_id = aws_vpc.cloud.id
  tags   = { Name = "${local.name}-igw" }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.cloud.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, 0)
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = false
  tags = { Name = "${local.name}-public-a" }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.cloud.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.cloud.id
  }
  tags = { Name = "${local.name}-public-rt" }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

resource "aws_security_group" "task" {
  name_prefix            = "${local.name}-task-"
  description            = "Outbound-only z0 BotOps ECS task"
  vpc_id                 = aws_vpc.cloud.id
  revoke_rules_on_delete = true
  tags = { Name = "${local.name}-task" }
}

resource "aws_vpc_security_group_egress_rule" "https" {
  security_group_id = aws_security_group.task.id
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
  cidr_ipv4         = "0.0.0.0/0"
  description       = "Public HTTPS endpoints"
}

resource "aws_vpc_security_group_egress_rule" "irc" {
  security_group_id = aws_security_group.task.id
  ip_protocol       = "tcp"
  from_port         = var.irc_port
  to_port           = var.irc_port
  cidr_ipv4         = "0.0.0.0/0"
  description       = "Outbound IRC service"
}

resource "aws_vpc_security_group_egress_rule" "dns_udp" {
  security_group_id = aws_security_group.task.id
  ip_protocol       = "udp"
  from_port         = 53
  to_port           = 53
  cidr_ipv4         = "0.0.0.0/0"
  description       = "DNS UDP"
}

resource "aws_vpc_security_group_egress_rule" "dns_tcp" {
  security_group_id = aws_security_group.task.id
  ip_protocol       = "tcp"
  from_port         = 53
  to_port           = 53
  cidr_ipv4         = "0.0.0.0/0"
  description       = "DNS TCP"
}

resource "aws_cloudwatch_log_group" "bot" {
  name              = "/ecs/${local.name}"
  retention_in_days = 14
}

data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "execution" {
  name               = "${local.name}-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy_attachment" "execution" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "secret_read" {
  count = var.irc_op_secret_arn == null ? 0 : 1
  name  = "${local.name}-secret-read"
  role  = aws_iam_role.execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = var.irc_op_secret_arn
    }]
  })
}

resource "aws_iam_role" "task" {
  name               = "${local.name}-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_ecs_cluster" "cloud" {
  name = "z0-cloud"
}

resource "aws_ecs_task_definition" "bot" {
  family                   = local.name
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "ARM64"
  }
  container_definitions = jsonencode([{
    name      = "z0-bot"
    image     = local.image_uri
    essential = true
    environment = [
      { name = "BOT_NAME", value = "z0-cloud-01" },
      { name = "IRC_SERVER", value = var.irc_server },
      { name = "IRC_PORT", value = tostring(var.irc_port) },
      { name = "IRC_CHANNEL", value = var.irc_channel },
      { name = "IRC_NICK", value = var.irc_nick }
    ]
    secrets = local.secret_env
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.bot.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "bot"
      }
    }
  }])
}

resource "aws_ecs_service" "bot" {
  name            = local.name
  cluster         = aws_ecs_cluster.cloud.id
  task_definition = aws_ecs_task_definition.bot.arn
  desired_count   = 1
  launch_type     = "FARGATE"
  platform_version = "LATEST"

  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100

  network_configuration {
    subnets          = [aws_subnet.public.id]
    security_groups  = [aws_security_group.task.id]
    assign_public_ip = true
  }

  depends_on = [aws_route_table_association.public]
}
