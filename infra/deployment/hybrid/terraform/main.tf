provider "proxmox" {
  endpoint = var.proxmox_endpoint
  insecure = false
  # PROXMOX_VE_API_TOKEN is read by the provider.
}

locals {
  roles = {
    proxy = {
      vm_id = 310
      nics  = [merge(var.proxy_network, { bridge = var.vlan_bridge })]
    }
    app = {
      vm_id = 320
      nics = [
        merge(var.app_network, { bridge = var.vlan_bridge }),
        { bridge = var.database_bridge, vlan = null, cidr = var.app_database_cidr, gateway = null },
      ]
    }
    db = {
      vm_id = 330
      nics  = [{ bridge = var.database_bridge, vlan = null, cidr = var.database_cidr, gateway = null }]
    }
  }
}

resource "proxmox_virtual_environment_vm" "role" {
  for_each  = local.roles
  name      = "flowform-hybrid-${each.key}"
  node_name = var.proxmox_node
  vm_id     = each.value.vm_id
  # The operator starts new guests after their firewall policies are installed.
  started = false
  on_boot = false

  # The database is persistent. Require deliberate maintenance to delete or
  # replace any role VM through this state.
  protection = each.key == "db"

  lifecycle {
    prevent_destroy = true
    ignore_changes  = [started, on_boot]

    precondition {
      condition     = var.database_bridge != var.vlan_bridge && var.proxy_network.vlan != var.app_network.vlan
      error_message = "Use separate ingress and application VLANs and an independent internal DB bridge."
    }
    precondition {
      condition     = split("/", var.app_database_cidr)[0] != split("/", var.database_cidr)[0] && cidrhost(var.app_database_cidr, 0) == cidrhost(var.database_cidr, 0) && cidrnetmask(var.app_database_cidr) == cidrnetmask(var.database_cidr)
      error_message = "Assign distinct app and DB addresses in the same private subnet."
    }
  }

  clone {
    vm_id        = 9100
    full         = true
    datastore_id = var.storage_pool
  }

  cpu {
    cores = var.vm_sizes[each.key].cores
    type  = "x86-64-v2-AES"
  }

  memory {
    dedicated = var.vm_sizes[each.key].memory_mb
  }

  scsi_hardware = "virtio-scsi-single"

  disk {
    interface    = "scsi0"
    datastore_id = var.storage_pool
    size         = var.vm_sizes[each.key].disk_gb
  }

  dynamic "network_device" {
    for_each = each.value.nics
    content {
      bridge   = network_device.value.bridge
      vlan_id  = network_device.value.vlan
      firewall = true
    }
  }

  initialization {
    datastore_id = var.storage_pool

    dynamic "dns" {
      for_each = each.key == "db" ? [] : [each.value.nics[0].gateway]
      content {
        servers = [dns.value]
      }
    }

    dynamic "ip_config" {
      for_each = each.value.nics
      content {
        ipv4 {
          address = ip_config.value.cidr
          gateway = ip_config.value.gateway
        }
      }
    }

    user_account {
      username = "ec2-user"
      keys     = var.ssh_public_keys
    }
  }
}

output "addresses" {
  value = {
    proxy  = local.role_ips.proxy
    app    = local.role_ips.app
    app_db = local.role_ips.app_db
    db     = local.role_ips.db
  }
  depends_on = [proxmox_virtual_environment_firewall_options.guest]
}

output "aws" {
  value = {
    environment = var.flowform_environment
    region      = var.aws_region
  }
}
