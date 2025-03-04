output "region" {
  value = data.aws_region.current.name
}

output "vpc" {
  value = data.aws_vpc.selected.id
}

output "subnets" {
  value = data.aws_subnets.example.ids
}



output "subnet_to_az_mapping" {
  value = local.subnet_to_az
}

output "az_to_subnet_mapping" {
  value = local.az_to_subnet
}

output "subnet_details" {
  value = local.subnet_details
}

output "selected_subnet_id" {
  value = local.selected_subnet_id
}

output "availability_zones" {
  description = "List of all availability zones for the subnets"
  value       = distinct(values(local.subnet_to_az))
}

output "selected_subnets" {
  value = local.selected_subnets
}
