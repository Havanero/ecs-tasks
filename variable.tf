# Variables
variable "aws_region" {
  description = "AWS region"
  default     = "eu-central-1"
}

variable "project_name" {
  description = "Project name to be used for resource naming"
  default     = "nginx-app"
}

variable "vpc_id" {
  description = "VPC ID"
  default     = "vpc-ca5b39a0"  # From your provided data
}

variable "container_image" {
  description = "Docker image for the container"
  default     = "nginx:latest"
}

variable "container_port" {
  description = "Port exposed by the container"
  default     = 80
}

variable "container_cpu" {
  description = "CPU units for the container"
  default     = 256
}

variable "container_memory" {
  description = "Memory for the container in MiB"
  default     = 512
}

variable "desired_count" {
  description = "Desired count of tasks"
  default     = 1
}

