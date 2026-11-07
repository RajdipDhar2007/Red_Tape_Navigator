output "region" {
  value       = var.region
  description = "Region the stack is deployed to."
}

output "tags" {
  value       = local.tags
  description = "Common resource tags."
}
