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
  description = "Packer-built golden template VMID cloned by the proxy and app VMs."
  type        = number
  default     = 9000
}

variable "localstack_fixture_template_vmid" {
  description = "Packer-built LocalStack fixture template VMID cloned by the isolated LocalStack VM."
  type        = number
  default     = 9001
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

variable "localstack_seed_values" {
  description = "Non-secret rehearsal values written to LocalStack by the fixture VM after boot. Keys are validated against the shared runtime parameter contract."
  type        = map(string)
  default = {
    API_DOMAIN                  = "api.localstack.test"
    AWS_REGION                  = "ap-southeast-2"
    BACKEND_IMAGE               = "10.10.10.30:5000/flowform-backend:rehearsal"
    CADDY_IMAGE                 = "caddy:2-alpine"
    DATABASE_CORE_APP_USER      = "flowform_core_app"
    DATABASE_CORE_HOST          = "core-db"
    DATABASE_CORE_NAME          = "flowform_core"
    DATABASE_RESPONSE_APP_USER  = "flowform_response_app"
    DATABASE_RESPONSE_HOST      = "response-db"
    DATABASE_RESPONSE_NAME      = "flowform_response"
    FLOWFORM_AUTH0_AUDIENCE     = "https://flowform.auth.api"
    FLOWFORM_AUTH0_CLIENT_ID    = "rehearsalClientId0000000000000000"
    FLOWFORM_AUTH0_DOMAIN       = "dev-rehearsal.au.auth0.com"
    FLOWFORM_AUTH0_MGMT_DOMAIN  = "dev-rehearsal.au.auth0.com"
    FLOWFORM_AUTH0_MGMT_ID      = "rehearsalMgmtId000000000000000000"
    FLOWFORM_EMAIL_FROM_ADDRESS = "no-reply@rehearsal.test"
    FLOWFORM_ENV                = "prod"
    FLOWFORM_LOGGING_LEVEL      = "INFO"
    FLOWFORM_LOGGING_LOG_JSON   = "true"
  }

  validation {
    condition     = alltrue([for value in values(var.localstack_seed_values) : length(trimspace(value)) > 0 && !can(regex("[\r\n]", value))])
    error_message = "LocalStack seed values must be non-empty single-line strings."
  }
}
