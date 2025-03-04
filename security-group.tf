resource "aws_security_group" "ecs_tasks" {
  name        = "${var.project_name}-ecs-tasks-sg"
  description = "Allow inbound traffic to ECS tasks"
  vpc_id      = data.aws_vpc.selected.id

  # We'll add the ingress rule after both security groups are created
  # to avoid circular dependency

  egress {
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-ecs-tasks-sg"
  }
}

#---------------------------------------------------------
# 3. Security Group for EFS
#---------------------------------------------------------
resource "aws_security_group" "efs" {
  name        = "${var.project_name}-efs-sg"
  description = "Allow EFS access from ECS tasks"
  vpc_id      = data.aws_vpc.selected.id

  # We'll add the ingress rule after both security groups are created
  # to avoid circular dependency

  egress {
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-efs-sg"
  }
}

# Add security group rules after creating both groups to avoid circular dependency
resource "aws_security_group_rule" "efs_ingress" {
  security_group_id        = aws_security_group.efs.id
  type                     = "ingress"
  protocol                 = "tcp"
  from_port                = 2049
  to_port                  = 2049
  source_security_group_id = aws_security_group.ecs_tasks.id
}

resource "aws_security_group_rule" "ecs_tasks_ingress" {
  security_group_id        = aws_security_group.ecs_tasks.id
  type                     = "ingress"
  protocol                 = "tcp"
  from_port                = var.container_port
  to_port                  = var.container_port
  source_security_group_id = aws_security_group.efs.id
}

