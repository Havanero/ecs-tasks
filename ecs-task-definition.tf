resource "aws_ecs_task_definition" "app" {
  family                   = "${var.project_name}-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.container_cpu
  memory                   = var.container_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name      = "${var.project_name}-container"
      image     = var.container_image
      essential = true

      readonlyRootFilesystem = true # Enable read-only container

      portMappings = [
        {
          containerPort = var.container_port
          hostPort      = var.container_port
          protocol      = "tcp"
        }
      ]

      mountPoints = [
        {
          sourceVolume  = "nginx-data"
          containerPath = "/usr/share/nginx/html"
          readOnly      = true
        },
        {
          sourceVolume  = "nginx-config"
          containerPath = "/etc/nginx/conf.d"
          readOnly      = true
        },
        {
          sourceVolume  = "tmp"
          containerPath = "/tmp"
          readOnly      = false
        },
        {
          sourceVolume  = "var-run"
          containerPath = "/var/run"
          readOnly      = false
        },
        {
          sourceVolume  = "var-cache-nginx"
          containerPath = "/var/cache/nginx"
          readOnly      = false
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ecs_tasks.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])

  volume {
    name = "nginx-data"

    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.app_data.id
      root_directory     = "/"
      transit_encryption = "ENABLED"
      authorization_config {
        access_point_id = aws_efs_access_point.app_data.id
        iam             = "ENABLED"
      }
    }
  }

  volume {
    name = "nginx-config"

    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.app_data.id
      root_directory     = "/"
      transit_encryption = "ENABLED"
      authorization_config {
        access_point_id = aws_efs_access_point.app_data.id
        iam             = "ENABLED"
      }
    }
  }

  # Required writable volumes for nginx when using readOnlyRootFilesystem
  volume {
    name = "tmp"

  }

  volume {
    name = "var-run"
  }

  volume {
    name = "var-cache-nginx"
  }

  tags = {
    Name        = "${var.project_name}-task-definition"
    Environment = "production"
  }
}

