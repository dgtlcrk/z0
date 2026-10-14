output "cluster_name" {
  value = aws_ecs_cluster.cloud.name
}

output "service_name" {
  value = aws_ecs_service.bot.name
}

output "log_group" {
  value = aws_cloudwatch_log_group.bot.name
}

output "image_uri" {
  value = local.image_uri
}
