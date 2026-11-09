locals {
  role_ips = {
    proxy  = split("/", var.proxy_network.cidr)[0]
    app    = split("/", var.app_network.cidr)[0]
    app_db = split("/", var.app_database_cidr)[0]
    db     = split("/", var.database_cidr)[0]
  }
  service_rules = {
    proxy = [{
      source  = local.role_ips.app
      ports   = "3128,3500,4317"
      comment = "Squid and Alloy from the app"
    }]
    app = [{
      source  = local.role_ips.proxy
      ports   = "5000"
      comment = "Gunicorn from the ingress proxy"
    }]
    db = [
      {
        source  = local.role_ips.app_db
        ports   = "5432"
        comment = "PostgreSQL from the app DB interface"
      },
      {
        source  = local.role_ips.app_db
        ports   = "22"
        comment = "SSH via the restricted app jump path"
      }
    ]
  }
  guest_nics = merge([
    for role, config in local.roles : {
      for index, nic in config.nics : "${role}-${index}" => {
        role = role
        name = "ipfilter-net${index}"
        ip   = split("/", nic.cidr)[0]
      }
    }
  ]...)
}

resource "proxmox_virtual_environment_cluster_firewall_security_group" "guest_ssh" {
  # Proxmox limits security group names to 18 characters.
  name    = "ff-hybrid-ssh"
  comment = "Trusted deployment workstation access to ingress and app"

  rule {
    type   = "in"
    action = "ACCEPT"
    proto  = "tcp"
    dport  = "22"
    source = "${var.admin_ipv4}/32"
  }
}

resource "proxmox_virtual_environment_firewall_rules" "guest" {
  for_each  = local.service_rules
  node_name = var.proxmox_node
  vm_id     = proxmox_virtual_environment_vm.role[each.key].vm_id

  dynamic "rule" {
    for_each = each.key == "db" ? [] : [proxmox_virtual_environment_cluster_firewall_security_group.guest_ssh.name]
    content {
      security_group = rule.value
      iface          = "net0"
    }
  }

  dynamic "rule" {
    for_each = each.value
    content {
      type    = "in"
      action  = "ACCEPT"
      iface   = "net0"
      proto   = "tcp"
      source  = "${rule.value.source}/32"
      dest    = "${local.role_ips[each.key]}/32"
      dport   = rule.value.ports
      comment = rule.value.comment
    }
  }
}

resource "proxmox_virtual_environment_firewall_ipset" "guest_nic" {
  for_each  = local.guest_nics
  node_name = var.proxmox_node
  vm_id     = proxmox_virtual_environment_vm.role[each.value.role].vm_id
  name      = each.value.name
  comment   = "Static address for this guest NIC"

  cidr {
    # Proxmox stores single-host IP set entries without /32; matching that
    # form keeps later plans from replacing the set.
    name = each.value.ip
  }
}

resource "proxmox_virtual_environment_firewall_options" "guest" {
  for_each  = local.roles
  node_name = var.proxmox_node
  vm_id     = proxmox_virtual_environment_vm.role[each.key].vm_id

  enabled       = true
  input_policy  = "DROP"
  output_policy = each.key == "db" ? "DROP" : "ACCEPT"
  ipfilter      = true
  macfilter     = true
  dhcp          = false
  ndp           = false
  radv          = false

  depends_on = [
    proxmox_virtual_environment_firewall_rules.guest,
    proxmox_virtual_environment_firewall_ipset.guest_nic,
  ]
}
