# Terraform uploads these rendered cloud-init snippets to Proxmox; the host
# never needs a FlowForm checkout.
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

resource "proxmox_virtual_environment_file" "db_user_data" {
  content_type = "snippets"
  datastore_id = var.proxmox_snippet_storage
  node_name    = var.proxmox_node

  source_raw {
    data      = local.cloud_init_user_data.db
    file_name = "flowform-db.user-data.yaml"
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

    # Static — see proxy_lan_ip in variables.tf for why DHCP is not used here.
    ip_config {
      ipv4 {
        address = var.proxy_lan_ip
        gateway = var.proxy_lan_gateway
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

resource "proxmox_virtual_environment_vm" "db" {
  name      = "flowform-rehearsal-db"
  node_name = var.proxmox_node
  vm_id     = 240
  started   = true

  clone {
    vm_id        = var.db_fixture_template_vmid
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
    user_data_file_id = proxmox_virtual_environment_file.db_user_data.id

    # Deliberately no gateway: the DB host can reach only its local subnet.
    ip_config {
      ipv4 {
        address = "10.10.10.40/24"
      }
    }

    user_account {
      username = "ec2-user"
      keys     = var.ssh_public_keys
    }
  }
}
