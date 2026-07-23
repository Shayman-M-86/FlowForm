output "proxy_lan_ip" {
  description = "Static LAN address of the operator-facing proxy VM, without its CIDR suffix."
  value       = split("/", var.proxy_lan_ip)[0]
}

output "rehearsal_vm_ids" {
  description = "Proxmox VM IDs for the Terraform-managed rehearsal topology."
  value = {
    proxy      = proxmox_virtual_environment_vm.proxy.vm_id
    app        = proxmox_virtual_environment_vm.app.vm_id
    localstack = proxmox_virtual_environment_vm.localstack.vm_id
    db         = proxmox_virtual_environment_vm.db.vm_id
  }
}
