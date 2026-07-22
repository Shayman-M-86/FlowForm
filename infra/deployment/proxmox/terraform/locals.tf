locals {
  cloud_init_template_dir = "${path.module}/../cloud-init/templates"
  database_init_dir       = "${path.module}/../../../database/init"
  database_init_files     = sort(tolist(fileset(local.database_init_dir, "**")))
  database_init_write_files = join("\n", [
    for relative_path in local.database_init_files : join("\n", [
      "  - path: /opt/flowform/db/init/${relative_path}",
      "    encoding: b64",
      "    permissions: '${endswith(relative_path, ".sh") ? "0755" : "0644"}'",
      "    owner: root:root",
      "    content: ${base64encode(file("${local.database_init_dir}/${relative_path}"))}",
    ])
  ])
  ssh_authorized_keys        = indent(2, join("\n", [for key in var.ssh_public_keys : "- ${key}"]))
  runtime_parameter_contract = jsondecode(file("${path.module}/../../config/runtime-parameter-contract.json"))
  # Runtime-parameter seed keys become plaintext SSM parameters. Terraform no
  # longer supplies ANY secret values: real secrets (the Auth0 management secret,
  # the Grafana Cloud token, the application key, both database passwords, and the
  # linkage secret) are held in the root-only Proxmox host bundle and streamed
  # into LocalStack Secrets Manager over SSH at deploy time — never through
  # Terraform variables, state, or cloud-init. The contract's secret_seed_value_keys
  # is now empty, so this union is just the runtime-parameter seed keys.
  required_localstack_seed_keys = toset(concat(
    flatten([
      for group in values(local.runtime_parameter_contract.runtime_groups) : [
        for parameter in values(group.parameters) : parameter.seed_value_key
        if can(parameter.seed_value_key)
      ]
    ]),
    lookup(local.runtime_parameter_contract, "secret_seed_value_keys", [])
  ))

  localstack_seed_values = merge(var.localstack_seed_values, {
    FLOWFORM_AUTH0_DOMAIN      = var.auth0_domain
    FLOWFORM_AUTH0_AUDIENCE    = var.auth0_audience
    FLOWFORM_AUTH0_CLIENT_ID   = var.auth0_client_id
    FLOWFORM_AUTH0_MGMT_DOMAIN = var.auth0_mgmt_domain
    FLOWFORM_AUTH0_MGMT_ID     = var.auth0_mgmt_id
    # No secrets are merged here. The boot seed writes only these non-secret
    # identifiers into SSM; every real secret arrives later via the deploy-time
    # SSH synchronisation step (see `scripts/rehearsal sync`).
  })
  configured_localstack_seed_keys = toset(keys(local.localstack_seed_values))
  localstack_seed_environment = join("\n", concat(
    ["FLOWFORM_SCOPE=nonprod"],
    [for key in sort(keys(local.localstack_seed_values)) : "${key}=${local.localstack_seed_values[key]}"]
  ))

  cloud_init_template_values = {
    REHEARSAL_CA_CRT_B64                = base64encode(file("${path.module}/../../../containers/strategies/rehearsal/services/tls-shim/ca/rehearsal-ca.crt"))
    BOOTSTRAP_APP_SH_B64                = base64encode(file("${path.module}/../../bootstrap/bootstrap-app.sh"))
    AWS_CLI_RETRY_SH_B64                = base64encode(file("${path.module}/../../bootstrap/aws-cli-retry.sh"))
    BOOTSTRAP_COMMON_SH_B64             = base64encode(file("${path.module}/../../bootstrap/bootstrap-common.sh"))
    DOCKER_COMPOSE_APP_B64              = base64encode(file("${path.module}/../../../containers/runtime/compose/app.yml"))
    DOCKER_COMPOSE_APP_REHEARSAL_B64    = base64encode(file("${path.module}/../../../containers/strategies/rehearsal/compose/app.override.yml"))
    CONFIG_ALLOY_APP_B64                = base64encode(file("${path.module}/../../../containers/runtime/services/alloy-app/config.alloy"))
    BOOTSTRAP_DB_SH_B64                 = base64encode(file("${path.module}/../../bootstrap/bootstrap-db.sh"))
    DOCKER_COMPOSE_DB_B64               = base64encode(file("${path.module}/../../../containers/strategies/rehearsal/compose/db.yml"))
    PG_HBA_CONF_B64                     = base64encode(file("${path.module}/../../../database/config/pg_hba.conf"))
    DB_INIT_WRITE_FILES                 = local.database_init_write_files
    BOOTSTRAP_PROXY_SH_B64              = base64encode(file("${path.module}/../../bootstrap/bootstrap-proxy.sh"))
    DOCKER_COMPOSE_PROXY_B64            = base64encode(file("${path.module}/../../../containers/runtime/compose/proxy.yml"))
    CONFIG_ALLOY_B64                    = base64encode(file("${path.module}/../../../containers/runtime/services/alloy/config.alloy"))
    DOCKER_COMPOSE_PROXY_REHEARSAL_B64  = base64encode(file("${path.module}/../../../containers/strategies/rehearsal/compose/proxy.override.yml"))
    CADDYFILE_PROXY_REHEARSAL_B64       = base64encode(file("${path.module}/../../../containers/strategies/rehearsal/services/caddy/Caddyfile.proxy"))
    PROXY_API_CRT_B64                   = base64encode(file("${path.module}/../../../containers/strategies/rehearsal/services/caddy/certs/api.crt"))
    PROXY_API_KEY_B64                   = base64encode(file("${path.module}/../../../containers/strategies/rehearsal/services/caddy/certs/api.key"))
    SQUID_CONF_B64                      = base64encode(file("${path.module}/../../../containers/runtime/services/squid/squid.conf"))
    SQUID_ALLOWED_DOMAINS_REHEARSAL_B64 = base64encode(file("${path.module}/../../../containers/strategies/rehearsal/services/squid/allowed-domains.txt"))
    DOCKER_COMPOSE_LOCALSTACK_B64       = base64encode(file("${path.module}/../../../containers/strategies/rehearsal/fixtures/compose.localstack.yml"))
    LOCALSTACK_SEED_SH_B64              = base64encode(file("${path.module}/../../../containers/strategies/rehearsal/services/localstack/seed-localstack.sh"))
    LOCALSTACK_SYNC_SECRETS_SH_B64      = base64encode(file("${path.module}/../../../containers/strategies/rehearsal/services/localstack/sync-secrets-into-localstack.sh"))
    RUNTIME_PARAMETER_CONTRACT_B64      = base64encode(file("${path.module}/../../config/runtime-parameter-contract.json"))
    DOCKER_COMPOSE_REGISTRY_B64         = base64encode(file("${path.module}/../../../containers/strategies/rehearsal/fixtures/compose.registry.yml"))
    DOCKER_COMPOSE_TLS_SHIM_B64         = base64encode(file("${path.module}/../../../containers/strategies/rehearsal/fixtures/compose.tls-shim.yml"))
    TLS_SHIM_CADDYFILE_B64              = base64encode(file("${path.module}/../../../containers/strategies/rehearsal/services/tls-shim/Caddyfile"))
    LOCALSTACK_CRT_B64                  = base64encode(file("${path.module}/../../../containers/strategies/rehearsal/services/tls-shim/ca/localstack.crt"))
    LOCALSTACK_KEY_B64                  = base64encode(file("${path.module}/../../../containers/strategies/rehearsal/services/tls-shim/ca/localstack.key"))
    LOCALSTACK_SEED_ENV_TERRAFORM       = base64encode("${local.localstack_seed_environment}\n")
  }

  rendered_cloud_init = {
    proxy      = templatefile("${local.cloud_init_template_dir}/proxy.yaml.tftpl", local.cloud_init_template_values)
    app        = templatefile("${local.cloud_init_template_dir}/app.yaml.tftpl", local.cloud_init_template_values)
    db         = templatefile("${local.cloud_init_template_dir}/db.yaml.tftpl", local.cloud_init_template_values)
    localstack = templatefile("${local.cloud_init_template_dir}/localstack.yaml.tftpl", local.cloud_init_template_values)
  }

  cloud_init_user_data = {
    for name, rendered in local.rendered_cloud_init : name => <<-EOT
      #cloud-config
      ssh_authorized_keys:
      ${local.ssh_authorized_keys}

      ${rendered}
    EOT
  }
}

check "localstack_seed_values_match_contract" {
  assert {
    condition = (
      length(setsubtract(local.required_localstack_seed_keys, local.configured_localstack_seed_keys)) == 0 &&
      length(setsubtract(local.configured_localstack_seed_keys, local.required_localstack_seed_keys)) == 0
    )
    error_message = "localstack_seed_values keys must exactly match seed_value_key entries in infra/deployment/config/runtime-parameter-contract.json."
  }
}
