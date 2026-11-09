variable "proxmox_endpoint" {
  type = string
  validation {
    condition     = startswith(var.proxmox_endpoint, "https://")
    error_message = "Use an HTTPS Proxmox endpoint with a trusted certificate."
  }
}

variable "proxmox_node" {
  type = string
}

variable "storage_pool" {
  type = string
}

variable "ssh_public_keys" {
  type = list(string)
  validation {
    condition     = length(var.ssh_public_keys) > 0
    error_message = "Supply at least one administrative SSH public key."
  }
}

variable "vlan_bridge" {
  type    = string
  default = "vmbr1"
}

variable "database_bridge" {
  type    = string
  default = "vmbr2"
  validation {
    condition     = var.database_bridge != "vmbr0"
    error_message = "The database bridge must be internal and separate from Proxmox management."
  }
}

variable "proxy_network" {
  type = object({
    vlan    = number
    cidr    = string
    gateway = string
  })
  validation {
    condition     = can(cidrnetmask(var.proxy_network.cidr)) && can(cidrnetmask("${var.proxy_network.gateway}/32")) && var.proxy_network.vlan >= 1 && var.proxy_network.vlan <= 4094
    error_message = "Supply a tagged VLAN, static IPv4 CIDR and IPv4 gateway for the proxy."
  }
}

variable "app_network" {
  type = object({
    vlan    = number
    cidr    = string
    gateway = string
  })
  validation {
    condition     = can(cidrnetmask(var.app_network.cidr)) && can(cidrnetmask("${var.app_network.gateway}/32")) && var.app_network.vlan >= 1 && var.app_network.vlan <= 4094
    error_message = "Supply a tagged VLAN, static IPv4 CIDR and IPv4 gateway for the application."
  }
}

variable "app_database_cidr" {
  type = string
  validation {
    condition     = can(cidrnetmask(var.app_database_cidr))
    error_message = "Supply a static IPv4 CIDR for the app interface on the private DB bridge."
  }
}

variable "database_cidr" {
  type = string
  validation {
    condition     = can(cidrnetmask(var.database_cidr))
    error_message = "Supply a static IPv4 CIDR for the DB interface on the private DB bridge."
  }
}

variable "flowform_environment" {
  type = string
  validation {
    condition     = contains(["staging", "prod"], var.flowform_environment)
    error_message = "Select the existing staging or prod AWS environment explicitly."
  }
}

variable "aws_region" {
  type = string
  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-[0-9]+$", var.aws_region))
    error_message = "Use a standard AWS region name."
  }
}

variable "vm_sizes" {
  type = map(object({
    cores     = number
    memory_mb = number
    disk_gb   = number
  }))
  default = {
    proxy = { cores = 2, memory_mb = 2048, disk_gb = 24 }
    app   = { cores = 2, memory_mb = 2048, disk_gb = 32 }
    db    = { cores = 2, memory_mb = 4096, disk_gb = 80 }
  }
}
