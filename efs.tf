resource "aws_efs_file_system" "app_data" {
  creation_token = "${var.project_name}-efs"
  encrypted      = true

  lifecycle_policy {
    transition_to_ia = "AFTER_30_DAYS"
  }

  tags = {
    Name = "${var.project_name}-efs"
  }
}

resource "aws_efs_mount_target" "app_data" {
  for_each = toset(local.selected_subnets)

  file_system_id  = aws_efs_file_system.app_data.id
  subnet_id       = each.value
  security_groups = [aws_security_group.efs.id]
}

resource "aws_efs_access_point" "app_data" {
  file_system_id = aws_efs_file_system.app_data.id

  posix_user {
    gid = 101 # nginx group ID
    uid = 101 # nginx user ID
  }

  root_directory {
    path = "/nginx"
    creation_info {
      owner_gid   = 101
      owner_uid   = 101
      permissions = "0755"
    }
  }

  tags = {
    Name = "${var.project_name}-access-point"
  }
}

