source "amazon-ebs" "amazon_linux_2023_base" {
  region                    = var.aws_region
  instance_type             = var.aws_instance_type
  communicator              = "ssh"
  ssh_username              = var.ssh_username
  ssh_interface             = "session_manager"
  pause_before_ssm          = "30s"
  ssh_timeout               = "15m"
  ssh_clear_authorized_keys = true

  source_ami_filter {
    filters = {
      name                = var.aws_source_ami_name
      root-device-type    = "ebs"
      virtualization-type = "hvm"
      architecture        = var.aws_architecture
    }
    owners      = [var.aws_source_ami_owner]
    most_recent = true
  }

  subnet_id                   = var.aws_subnet_id
  user_data_file              = "${var.image_root}/packer/user-data/aws-builder-diagnostics.sh"
  iam_instance_profile        = var.aws_iam_instance_profile
  associate_public_ip_address = true
  ami_name                    = "${var.aws_ami_name_prefix}-${local.build_timestamp}"
  ami_description             = "FlowForm base ${var.os_name} image built by Packer"
  imds_support                = "v2.0"

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
    instance_metadata_tags      = "disabled"
  }

  launch_block_device_mappings {
    device_name           = "/dev/xvda"
    volume_size           = var.aws_root_volume_size
    volume_type           = "gp3"
    encrypted             = var.aws_encrypt_boot
    kms_key_id            = var.aws_kms_key_id != "" ? var.aws_kms_key_id : null
    delete_on_termination = true
  }

  run_tags = merge(local.common_tags, { build_timestamp = local.build_timestamp, image_role = "base" })
  tags     = merge(local.common_tags, { Name = "${var.aws_ami_name_prefix}-${local.build_timestamp}", build_timestamp = local.build_timestamp, image_role = "base" })
}

source "amazon-ebs" "flowform_role" {
  region                    = var.aws_region
  instance_type             = var.aws_instance_type
  communicator              = "ssh"
  ssh_username              = var.ssh_username
  ssh_interface             = "session_manager"
  pause_before_ssm          = "30s"
  ssh_timeout               = "15m"
  ssh_clear_authorized_keys = true
  source_ami                = var.aws_base_ami_id

  subnet_id                   = var.aws_subnet_id
  user_data_file              = "${var.image_root}/packer/user-data/aws-builder-diagnostics.sh"
  iam_instance_profile        = var.aws_iam_instance_profile
  associate_public_ip_address = true
  ami_name                    = "flowform-${var.image_role}-al2023-${local.build_timestamp}"
  ami_description             = "FlowForm ${var.image_role} AMI derived from exact base ${var.aws_base_ami_id}"
  imds_support                = "v2.0"

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"
    http_put_response_hop_limit = 1
    instance_metadata_tags      = "disabled"
  }

  launch_block_device_mappings {
    device_name           = "/dev/xvda"
    volume_size           = var.aws_root_volume_size
    volume_type           = "gp3"
    encrypted             = var.aws_encrypt_boot
    kms_key_id            = var.aws_kms_key_id != "" ? var.aws_kms_key_id : null
    delete_on_termination = true
  }

  run_tags = merge(local.common_tags, {
    build_timestamp = local.build_timestamp
    parent_ami_id   = var.aws_base_ami_id
  })
  tags = merge(local.common_tags, {
    Name            = "flowform-${var.image_role}-al2023-${local.build_timestamp}"
    build_timestamp = local.build_timestamp
    parent_ami_id   = var.aws_base_ami_id
  })
}
