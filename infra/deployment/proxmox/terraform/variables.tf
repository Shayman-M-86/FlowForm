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

variable "db_fixture_template_vmid" {
  description = "Packer-built PostgreSQL fixture template VMID cloned by the isolated rehearsal database VM."
  type        = number
  default     = 9002
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

# Static, not DHCP: the proxy's LAN address is the one thing operators, docs,
# and hosts files all name, and a DHCP lease does not survive VM recreation —
# every rebuild minted a new MAC/DUID and the stack came up healthy on a NEW
# address while everything pointing at the old one looked dead. (MAC pinning
# alone was tried first and does not fix it: networkd identifies to DHCP by a
# machine-id-derived DUID, which also changes on rebuild.) Keep this address
# excluded from the router's DHCP pool to rule out a future collision.
variable "proxy_lan_ip" {
  description = "Static LAN address (CIDR) for the proxy VM on vmbr0 — the operator-facing entry point named in docs and hosts files."
  type        = string
  default     = "192.168.70.63/22"

  validation {
    condition     = can(cidrhost(var.proxy_lan_ip, 0))
    error_message = "proxy_lan_ip must be an address in CIDR notation, e.g. 192.168.70.63/22."
  }
}

variable "proxy_lan_gateway" {
  description = "Default gateway for the proxy VM's LAN interface."
  type        = string
  default     = "192.168.68.1"
}

variable "ssh_public_keys" {
  description = "SSH public keys embedded in the custom cloud-init user-data for ec2-user."
  type        = list(string)

  validation {
    condition     = length(var.ssh_public_keys) > 0
    error_message = "At least one SSH public key is required for guest access."
  }
}

# Auth0 is the one dependency the rehearsal does not fake: it validates tokens
# against the REAL tenant (hence auth.flow-form.com.au on the Squid allow-list),
# so these must match whatever the Studio front end logs in against or every
# authenticated request fails signature validation.
#
# They have no defaults on purpose — a committed default is a second copy that
# drifts the moment either side changes tenant. Supply them from the dev backend
# env, which is gitignored and already the source of truth for the dev stack:
#
#   infra/deployment/proxmox/scripts/rehearsal terraform plan
#
# (that wrapper exports these as TF_VAR_*), or export TF_VAR_auth0_domain etc.
# yourself. Terraform prompts for any that are missing.
#
# All five are non-secret identifiers. NO real secret is a Terraform variable any
# more: the Auth0 management client secret and the Grafana Cloud token — like the
# application key, database passwords, and linkage secret — live in the root-only
# Proxmox host bundle and are streamed into LocalStack Secrets Manager over SSH at
# deploy time by `scripts/rehearsal sync`. Terraform (config, state, and
# rendered cloud-init) is secret-free.

# These are merged into localstack_seed_values (see locals.tf), so they carry the
# same non-empty/single-line rule its own validation applies to the defaulted
# keys — a blank or newline-bearing value would otherwise reach the seed file.
# A bare hostname is required, not a URL: the seed script writes it straight to
# the runtime parameter the backend builds https://<domain>/ from.

variable "auth0_domain" {
  description = "Auth0 issuer domain the backend validates tokens against, e.g. auth.flow-form.com.au. Set via TF_VAR_auth0_domain."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9.-]+\\.[a-z]{2,}$", var.auth0_domain))
    error_message = "auth0_domain must be a bare hostname, e.g. auth.flow-form.com.au (no scheme, no path)."
  }
}

variable "auth0_audience" {
  description = "Auth0 API audience the access token must carry. Set via TF_VAR_auth0_audience."
  type        = string

  validation {
    condition     = length(trimspace(var.auth0_audience)) > 0 && !can(regex("[\r\n]", var.auth0_audience))
    error_message = "auth0_audience must be a non-empty single-line string."
  }
}

variable "auth0_client_id" {
  description = "Auth0 SPA client id the Studio front end logs in with. Set via TF_VAR_auth0_client_id."
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z0-9]{16,}$", var.auth0_client_id))
    error_message = "auth0_client_id must be an Auth0 client id (alphanumeric, 16+ chars)."
  }
}

variable "auth0_mgmt_domain" {
  description = "Canonical Auth0 tenant domain serving /api/v2 (custom domains do not). Set via TF_VAR_auth0_mgmt_domain."
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9.-]+\\.auth0\\.com$", var.auth0_mgmt_domain))
    error_message = "auth0_mgmt_domain must be the canonical tenant domain (*.auth0.com) — Auth0 does not serve /api/v2 on custom domains."
  }
}

variable "auth0_mgmt_id" {
  description = "Auth0 Management API client id. Set via TF_VAR_auth0_mgmt_id."
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z0-9]{16,}$", var.auth0_mgmt_id))
    error_message = "auth0_mgmt_id must be an Auth0 client id (alphanumeric, 16+ chars)."
  }
}

# The Auth0 management client secret and the Grafana Cloud token were once
# Terraform variables merged into the LocalStack seed. They are REAL secrets and
# are no longer supplied through Terraform at all: both now live in the root-only
# Proxmox host bundle (auth0/grafana resolved at deploy time from their
# file/env/AWS sources) and reach LocalStack Secrets Manager via the deploy-time
# SSH sync. Terraform carries no secret variables — see locals.tf.

variable "localstack_seed_values" {
  description = "Non-secret rehearsal values written to LocalStack by the fixture VM after boot. Auth0 keys are merged in from their own variables (see locals.seed_values); the rest default here. Keys are validated against the shared runtime parameter contract."
  type        = map(string)
  default = {
    API_DOMAIN                 = "api.localstack.test"
    AWS_REGION                 = "ap-southeast-2"
    BACKEND_IMAGE              = "registry.localstack.test/flowform-backend:rehearsal"
    BACKEND_ALLOY_IMAGE        = "registry.localstack.test/grafana/alloy:v1.18.0"
    CADDY_IMAGE                = "caddy:2-alpine"
    PROXY_ALLOY_IMAGE          = "grafana/alloy:v1.18.0@sha256:eb21f4c0858edffcdd1b385910ddeef26f692fc2c282f61baa724fc09d274a17"
    SQUID_IMAGE                = "ubuntu/squid:6.6-24.04_edge@sha256:94f844158e12b52f51b4ae996515e37e8fb3e8d85e1c86caba1a297376e4ec4f"
    DATABASE_CORE_APP_USER     = "flowform_core_app"
    DATABASE_CORE_HOST         = "10.10.10.40"
    DATABASE_CORE_NAME         = "flowform_core"
    DATABASE_RESPONSE_APP_USER = "flowform_response_app"
    DATABASE_RESPONSE_HOST     = "10.10.10.40"
    DATABASE_RESPONSE_NAME     = "flowform_response"
    # The rehearsal seeds the REAL mgmt client secret via the deploy-time SSH sync
    # (from the Proxmox host bundle), so startup validation is ON: the app
    # exercises the real Management API at boot and fails loudly if the secret or
    # tenant is wrong. Token validation is unaffected either way.
    FLOWFORM_AUTH0_MGMT_VALIDATE_ON_STARTUP = "true"
    FLOWFORM_EMAIL_FROM_ADDRESS             = "no-reply@flow-form.com.au"
    FLOWFORM_ENV                            = "prod"
    FLOWFORM_LOGGING_LEVEL                  = "INFO"
    FLOWFORM_LOGGING_LOG_JSON               = "true"
    FLOWFORM_TRACING_ENABLED                = "true"
    FLOWFORM_TRACING_OTLP_ENDPOINT          = "http://alloy:4317"
    FLOWFORM_TRACING_SAMPLE_RATIO           = "1.0"
    FLOWFORM_TRACING_SERVICE_NAME           = "backend"
    # Grafana Cloud Loki target for the proxy-box Alloy agent. URL + user id are
    # non-secret and default here. The secret token is NOT a seed value at all: it
    # is delivered as the observability-secrets Secrets Manager entry by the
    # deploy-time SSH sync, never through this map or Terraform. Override the
    # URL/user for a real GC stack via TF_VAR_localstack_seed_values.
    GRAFANA_CLOUD_LOKI_URL       = "https://logs-prod-026.grafana.net/loki/api/v1/push"
    GRAFANA_CLOUD_LOKI_USER      = "1687659"
    GRAFANA_CLOUD_TEMPO_ENDPOINT = "tempo-prod-16-prod-au-southeast-1.grafana.net:443"
    GRAFANA_CLOUD_TEMPO_USER     = "1681960"
  }

  validation {
    condition     = alltrue([for value in values(var.localstack_seed_values) : length(trimspace(value)) > 0 && !can(regex("[\r\n]", value))])
    error_message = "LocalStack seed values must be non-empty single-line strings."
  }
}
