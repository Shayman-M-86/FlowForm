source "amazon-ebs" "amazon_linux_2023" {
  region        = var.aws_region
  instance_type = var.aws_instance_type
  ssh_username  = var.ssh_username

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

  subnet_id                   = var.aws_subnet_id != "" ? var.aws_subnet_id : null
  security_group_id           = var.aws_security_group_id != "" ? var.aws_security_group_id : null
  iam_instance_profile        = var.aws_iam_instance_profile != "" ? var.aws_iam_instance_profile : null
  associate_public_ip_address = var.aws_subnet_id == "" ? true : null
  ami_name                    = "${var.aws_ami_name_prefix}-${local.build_timestamp}"
  ami_description             = "FlowForm ${var.image_role} ${var.os_name} image built by Packer"

  launch_block_device_mappings {
    device_name           = "/dev/xvda"
    volume_size           = var.aws_root_volume_size
    volume_type           = "gp3"
    encrypted             = var.aws_encrypt_boot
    kms_key_id            = var.aws_kms_key_id != "" ? var.aws_kms_key_id : null
    delete_on_termination = true
  }

  run_tags = merge(local.common_tags, { build_timestamp = local.build_timestamp })
  tags     = merge(local.common_tags, { Name = "${var.aws_ami_name_prefix}-${local.build_timestamp}", build_timestamp = local.build_timestamp })
}
