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
  default = "al2023-ami-2023.*-kernel-*-x86_64"
}

variable "aws_instance_type" {
  type    = string
  default = "t3.small"
}

variable "aws_subnet_id" {
  type    = string
  default = ""
}

variable "aws_security_group_id" {
  type    = string
  default = ""
}

variable "aws_iam_instance_profile" {
  type    = string
  default = ""
}

variable "aws_ami_name_prefix" {
  type    = string
  default = "flowform-golden-al2023"
}

variable "aws_root_volume_size" {
  type    = number
  default = 16
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
