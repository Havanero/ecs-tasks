locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.name

  # Map of subnet ID to availability zone
  subnet_to_az = {
    for id, subnet in data.aws_subnet.selected :
    id => subnet.availability_zone
  }

  # Map of availability zone to subnet ID
  az_to_subnet = {
    for id, subnet in data.aws_subnet.selected :
    subnet.availability_zone => id
  }

  # List of all subnet IDs
  subnet_ids = keys(local.subnet_to_az)

  # List of all availability zones
  availability_zones = values(local.subnet_to_az)

  # More structured mapping for easier access
  subnet_details = {
    for id, subnet in data.aws_subnet.selected : id => {
      az            = subnet.availability_zone
      cidr_block    = subnet.cidr_block
      available_ips = subnet.available_ip_address_count
      az_id         = subnet.availability_zone_id
      public_ip     = subnet.map_public_ip_on_launch
    }
  }

  selected_subnet_id = sort(local.subnet_ids)[0]
  selected_subnets   = [for s in data.aws_subnet.selected : s.id]
  #  availability_zones = distinct([for s in data.aws_subnet.selected : s.availability_zone])
}

