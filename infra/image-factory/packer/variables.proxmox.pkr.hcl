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

  validation {
    condition     = can(regex("^[^@[:space:]]+@[^![:space:]]+![^[:space:]]+$", var.proxmox_token_id))
    error_message = "proxmox_token_id must match user@realm!token-name."
  }
}

variable "proxmox_token_secret" {
  type      = string
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
  type = number

  validation {
    condition     = var.proxmox_vm_id >= 100 && var.proxmox_vm_id <= 999999999
    error_message = "proxmox_vm_id must be a valid Proxmox VMID."
  }
}

variable "proxmox_template_name" {
  type = string
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
  default = false
}

variable "proxmox_ssh_private_key_file" {
  type      = string
  sensitive = true
}
