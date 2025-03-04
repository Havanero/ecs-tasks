data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

data "aws_vpc" "selected" {
  #  id = var.vpc_id
}

data "aws_subnets" "example" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.selected.id]
  }
}


data "aws_subnet" "selected" {
  for_each = toset(data.aws_subnets.example.ids)
  id       = each.value
}

