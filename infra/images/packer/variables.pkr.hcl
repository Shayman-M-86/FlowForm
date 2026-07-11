variable "image_role" {
  type    = string
  default = "golden"
}

variable "os_name" {
  type    = string
  default = "amazon-linux-2023"
}

variable "ssh_username" {
  type    = string
  default = "ec2-user"
}

variable "source_commit" {
  type    = string
  default = "unknown"
}

variable "proxmox_api_url" {
  type    = string
  default = "https://pve.example.invalid:8006/api2/json"
}

variable "proxmox_node" {
  type    = string
  default = "pve"
}

variable "proxmox_token_id" {
  type      = string
  default   = "packer@pve!flowform"
  sensitive = true
}

variable "proxmox_token_secret" {
  type      = string
  default   = "change-me"
  sensitive = true
}

variable "proxmox_storage_pool" {
  type    = string
  default = "ZFS-RAIDZ"
}

variable "proxmox_source_template" {
  type    = string
  default = "amazon-linux-2023-kvm-base"
}

variable "proxmox_network_bridge" {
  type    = string
  default = "vmbr0"
}

variable "proxmox_vm_id" {
  type    = number
  default = 9000
}

variable "proxmox_template_name" {
  type    = string
  default = "flowform-rehearsal-golden-al2023"
}

variable "proxmox_cpu" {
  type    = number
  default = 2
}

variable "proxmox_memory" {
  type    = number
  default = 2048
}

variable "proxmox_insecure_skip_tls_verify" {
  type    = bool
  default = true
}

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
  default = "flowform-rehearsal-golden-al2023"
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
