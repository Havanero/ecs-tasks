resource "aws_ecs_cluster" "main" {
  name = "test-cluster"
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  
  tags = {
    Name        = "terra-test-cluster"
    Environment = "production"
  }
}

