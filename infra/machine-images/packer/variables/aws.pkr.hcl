variable "aws_region" {
  type    = string
  default = "ap-southeast-2"
}

variable "aws_source_ami_owner" {
  type    = string
  default = "amazon"
}

variable "aws_source_ami_name" {
  type    = string
  default = "al2023-ami-minimal-2023.*-kernel-6.1-x86_64"
}

variable "aws_instance_type" {
  type    = string
  default = "t3.small"
}

variable "aws_subnet_id" {
  type = string

  validation {
    condition     = can(regex("^subnet-[0-9a-f]+$", var.aws_subnet_id))
    error_message = "AWS Packer builds require an explicit subnet ID."
  }
}

variable "aws_iam_instance_profile" {
  type    = string
  default = "FlowFormPackerBuildProfile"

  validation {
    condition     = can(regex("^[A-Za-z0-9+=,.@_-]{1,128}$", var.aws_iam_instance_profile))
    error_message = "AWS Packer builds require a valid SSM-enabled IAM instance profile name."
  }
}

variable "aws_ami_name_prefix" {
  type    = string
  default = "flowform-base-al2023"
}

variable "aws_base_ami_id" {
  type        = string
  default     = ""
  description = "Exact base AMI consumed by the app and proxy child builds"

  validation {
    condition     = var.aws_base_ami_id == "" || can(regex("^ami-[0-9a-f]+$", var.aws_base_ami_id))
    error_message = "AWS base AMI ID must be empty or a valid AMI ID."
  }
}

variable "aws_root_volume_size" {
  type    = number
  default = 10
}

variable "aws_encrypt_boot" {
  type    = bool
  default = true
}

variable "aws_kms_key_id" {
  type    = string
  default = ""
}

variable "aws_architecture" {
  type    = string
  default = "x86_64"
}
