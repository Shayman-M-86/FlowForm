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
  default = "flowform-golden-al2023"
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
