locals {
  rendered_cloud_init_dir    = "${path.module}/cloud-init"
  ssh_authorized_keys        = indent(2, join("\n", [for key in var.ssh_public_keys : "- ${key}"]))
  runtime_parameter_contract = jsondecode(file("${path.module}/../../config/runtime-parameter-contract.json"))
  required_localstack_seed_keys = toset(flatten([
    for group in values(local.runtime_parameter_contract.runtime_groups) : [
      for parameter in values(group.parameters) : parameter.seed_value_key
      if can(parameter.seed_value_key)
    ]
  ]))
  configured_localstack_seed_keys = toset(keys(var.localstack_seed_values))
  localstack_seed_environment = join("\n", concat(
    ["FLOWFORM_SCOPE=nonprod"],
    [for key in sort(keys(var.localstack_seed_values)) : "${key}=${var.localstack_seed_values[key]}"]
  ))
  localstack_rendered_user_data = replace(
    file("${local.rendered_cloud_init_dir}/localstack.user-data.rendered.yaml"),
    "__LOCALSTACK_SEED_ENV_TERRAFORM__",
    base64encode("${local.localstack_seed_environment}\n")
  )

  # Proxmox treats a custom user-data file as a replacement for its generated
  # cloud-init user data. Include the SSH keys in each custom payload instead
  # of relying on initialization.user_account to merge them.
  cloud_init_user_data = {
    proxy      = <<-EOT
      #cloud-config
      ssh_authorized_keys:
      ${local.ssh_authorized_keys}

      ${file("${local.rendered_cloud_init_dir}/proxy.user-data.rendered.yaml")}
    EOT
    app        = <<-EOT
      #cloud-config
      ssh_authorized_keys:
      ${local.ssh_authorized_keys}

      ${file("${local.rendered_cloud_init_dir}/app.user-data.rendered.yaml")}
    EOT
    localstack = <<-EOT
      #cloud-config
      ssh_authorized_keys:
      ${local.ssh_authorized_keys}

      ${local.localstack_rendered_user_data}
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

# These files are rendered locally from the real repository inputs before
# Terraform plans or applies. Terraform then uploads only the resulting
# cloud-init snippets to Proxmox; it never requires a repository checkout on
# the Proxmox host.
resource "proxmox_virtual_environment_file" "proxy_user_data" {
  content_type = "snippets"
  datastore_id = var.proxmox_snippet_storage
  node_name    = var.proxmox_node

  source_raw {
    data      = local.cloud_init_user_data.proxy
    file_name = "flowform-proxy.user-data.yaml"
  }
}

resource "proxmox_virtual_environment_file" "app_user_data" {
  content_type = "snippets"
  datastore_id = var.proxmox_snippet_storage
  node_name    = var.proxmox_node

  source_raw {
    data      = local.cloud_init_user_data.app
    file_name = "flowform-app.user-data.yaml"
  }
}

resource "proxmox_virtual_environment_file" "localstack_user_data" {
  content_type = "snippets"
  datastore_id = var.proxmox_snippet_storage
  node_name    = var.proxmox_node

  source_raw {
    data      = local.cloud_init_user_data.localstack
    file_name = "flowform-localstack.user-data.yaml"
  }
}

resource "proxmox_virtual_environment_vm" "proxy" {
  name      = "flowform-rehearsal-proxy"
  node_name = var.proxmox_node
  vm_id     = 210
  started   = true

  clone {
    vm_id        = var.golden_template_vmid
    full         = true
    datastore_id = var.proxmox_storage_pool
  }

  cpu {
    cores = 2
    type  = var.proxmox_cpu_type
  }

  memory {
    dedicated = 2048
  }

  network_device {
    bridge = "vmbr0"
  }

  network_device {
    bridge = "vmbr10"
  }

  initialization {
    datastore_id      = var.proxmox_storage_pool
    user_data_file_id = proxmox_virtual_environment_file.proxy_user_data.id

    ip_config {
      ipv4 {
        address = "dhcp"
      }
    }

    ip_config {
      ipv4 {
        address = "10.10.10.10/24"
      }
    }

    user_account {
      username = "ec2-user"
      keys     = var.ssh_public_keys
    }
  }
}

resource "proxmox_virtual_environment_vm" "app" {
  name      = "flowform-rehearsal-app"
  node_name = var.proxmox_node
  vm_id     = 220
  started   = true

  clone {
    vm_id        = var.golden_template_vmid
    full         = true
    datastore_id = var.proxmox_storage_pool
  }

  cpu {
    cores = 2
    type  = var.proxmox_cpu_type
  }

  memory {
    dedicated = 2048
  }

  network_device {
    bridge = "vmbr10"
  }

  initialization {
    datastore_id      = var.proxmox_storage_pool
    user_data_file_id = proxmox_virtual_environment_file.app_user_data.id

    ip_config {
      ipv4 {
        address = "10.10.10.20/24"
      }
    }

    user_account {
      username = "ec2-user"
      keys     = var.ssh_public_keys
    }
  }
}

resource "proxmox_virtual_environment_vm" "localstack" {
  name      = "flowform-rehearsal-localstack"
  node_name = var.proxmox_node
  vm_id     = 230
  started   = true

  clone {
    vm_id        = var.localstack_fixture_template_vmid
    full         = true
    datastore_id = var.proxmox_storage_pool
  }

  cpu {
    cores = 2
    type  = var.proxmox_cpu_type
  }

  memory {
    dedicated = 2048
  }

  network_device {
    bridge = "vmbr10"
  }

  initialization {
    datastore_id      = var.proxmox_storage_pool
    user_data_file_id = proxmox_virtual_environment_file.localstack_user_data.id

    ip_config {
      ipv4 {
        address = "10.10.10.30/24"
      }
    }

    user_account {
      username = "ec2-user"
      keys     = var.ssh_public_keys
    }
  }
}
