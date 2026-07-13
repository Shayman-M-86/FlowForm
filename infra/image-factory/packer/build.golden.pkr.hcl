build {
  name = "flowform-golden"
  sources = [
    "source.proxmox-clone.amazon_linux_2023",
    "source.amazon-ebs.amazon_linux_2023",
  ]

  provisioner "file" {
    source      = "../provisioning/common/lib.sh"
    destination = "/tmp/flowform-image-lib.sh"
  }

  provisioner "shell" {
    execute_command = "chmod +x {{ .Path }}; {{ .Vars }} sudo -E {{ .Path }}"
    scripts         = local.common_scripts
  }

  provisioner "shell" {
    only            = ["proxmox-clone.amazon_linux_2023"]
    execute_command = "chmod +x {{ .Path }}; {{ .Vars }} sudo -E {{ .Path }}"
    scripts         = ["../provisioning/proxmox/install-qemu-agent.sh", "../provisioning/proxmox/configure-proxmox-guest.sh"]
  }

  provisioner "shell" {
    only            = ["amazon-ebs.amazon_linux_2023"]
    execute_command = "chmod +x {{ .Path }}; {{ .Vars }} sudo -E {{ .Path }}"
    scripts         = ["../provisioning/aws/configure-ec2.sh", "../provisioning/aws/configure-ssm.sh"]
  }

  provisioner "shell" {
    execute_command = "chmod +x {{ .Path }}; {{ .Vars }} sudo -E {{ .Path }}"
    script          = "../provisioning/common/cleanup-image.sh"
  }

  post-processor "manifest" {
    output     = "../manifests/packer-manifest.json"
    strip_path = true
  }
}
