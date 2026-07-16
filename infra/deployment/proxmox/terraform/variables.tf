variable "proxmox_endpoint" {
  description = "Proxmox API endpoint, for example https://pve.example.lan:8006/api2/json."
  type        = string
}

variable "proxmox_api_token" {
  description = "Proxmox API token in user@realm!token=secret form."
  type        = string
  sensitive   = true
}

variable "proxmox_insecure_skip_tls_verify" {
  description = "Whether to skip TLS certificate verification for the Proxmox API."
  type        = bool
  default     = false
}

variable "proxmox_node" {
  description = "Proxmox node that hosts the golden template and rehearsal VMs."
  type        = string
}

variable "golden_template_vmid" {
  description = "Packer-built golden template VMID to clone."
  type        = number
  default     = 9000
}

variable "proxmox_storage_pool" {
  description = "Storage pool for cloned disks and cloud-init disks."
  type        = string
}

variable "proxmox_snippet_storage" {
  description = "Storage configured with the Proxmox snippets content type."
  type        = string
  default     = "local"
}

variable "proxmox_cpu_type" {
  description = "QEMU CPU model used by the Packer template and its clones."
  type        = string
  default     = "x86-64-v2-AES"
}

variable "ssh_public_keys" {
  description = "SSH public keys embedded in the custom cloud-init user-data for ec2-user."
  type        = list(string)

  validation {
    condition     = length(var.ssh_public_keys) > 0
    error_message = "At least one SSH public key is required for guest access."
  }
}
