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

variable "proxmox_build_ip_cidr" {
  type        = string
  description = "Dedicated temporary IPv4 address in CIDR notation used only by the Proxmox Packer VM"
  default     = "192.0.2.10/24"

  validation {
    condition     = can(cidrnetmask(var.proxmox_build_ip_cidr))
    error_message = "The Proxmox build IP must be an IPv4 address in CIDR notation, for example 192.168.1.240/24."
  }
}

variable "proxmox_build_gateway" {
  type        = string
  description = "IPv4 gateway reachable from the dedicated Proxmox Packer build address"
  default     = "192.0.2.1"

  validation {
    condition     = can(cidrnetmask("${var.proxmox_build_gateway}/32"))
    error_message = "The Proxmox build gateway must be an IPv4 address, for example 192.168.1.1."
  }
}

variable "proxmox_vm_id" {
  type    = number
  default = 9000
}

variable "proxmox_template_name" {
  type    = string
  default = "flowform-golden-al2023"
}

variable "proxmox_golden_template" {
  type        = string
  description = "Packer-built Proxmox golden template used as the LocalStack fixture base"
  default     = ""
}

variable "proxmox_localstack_fixture_vm_id" {
  type    = number
  default = 9001
}

variable "proxmox_localstack_fixture_template_name" {
  type    = string
  default = "flowform-localstack-fixture-al2023"
}

variable "proxmox_cpu" {
  type    = number
  default = 2
}

variable "proxmox_cpu_type" {
  type        = string
  description = "Proxmox CPU model; AL2023 requires x86-64-v2 instruction support"
  default     = "x86-64-v2-AES"
}

variable "proxmox_memory" {
  type    = number
  default = 2048
}

variable "proxmox_insecure_skip_tls_verify" {
  type    = bool
  default = true
}
