source "proxmox-clone" "amazon_linux_2023" {
  proxmox_url              = var.proxmox_api_url
  node                     = var.proxmox_node
  username                 = var.proxmox_token_id
  token                    = var.proxmox_token_secret
  insecure_skip_tls_verify = var.proxmox_insecure_skip_tls_verify

  clone_vm             = var.proxmox_source_template
  full_clone           = true
  vm_id                = var.proxmox_vm_id
  vm_name              = var.proxmox_template_name
  template_name        = var.proxmox_template_name
  template_description = "FlowForm ${var.image_role} ${var.os_name} template built by Packer"

  cores           = var.proxmox_cpu
  memory          = var.proxmox_memory
  os              = "l26"
  qemu_agent      = true
  scsi_controller = "virtio-scsi-single"

  network_adapters {
    bridge = var.proxmox_network_bridge
    model  = "virtio"
  }

  cloud_init              = true
  cloud_init_storage_pool = var.proxmox_storage_pool
  ssh_username            = var.ssh_username
  ssh_private_key_file    = var.proxmox_ssh_private_key_file
  ssh_timeout             = "45m"
}
