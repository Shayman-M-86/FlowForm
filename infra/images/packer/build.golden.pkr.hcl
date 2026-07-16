build {
  name = "flowform-golden"
  sources = [
    "source.proxmox-clone.amazon_linux_2023",
    "source.amazon-ebs.amazon_linux_2023",
  ]

  provisioner "file" {
    source      = "../common/build-steps/lib.sh"
    destination = "/tmp/flowform-image-lib.sh"
  }

  provisioner "shell" {
    execute_command = "chmod +x {{ .Path }}; {{ .Vars }} sudo -E {{ .Path }}"
    scripts         = local.common_scripts
  }

  provisioner "shell" {
    only            = ["proxmox-clone.amazon_linux_2023"]
    execute_command = "chmod +x {{ .Path }}; {{ .Vars }} sudo -E {{ .Path }}"
    scripts         = ["../proxmox/build-steps/install-qemu-agent.sh", "../proxmox/build-steps/configure-proxmox-guest.sh"]
  }

  provisioner "shell" {
    only            = ["amazon-ebs.amazon_linux_2023"]
    execute_command = "chmod +x {{ .Path }}; {{ .Vars }} sudo -E {{ .Path }}"
    scripts         = ["../aws/build-steps/configure-ec2.sh", "../aws/build-steps/configure-ssm.sh"]
  }

  provisioner "shell" {
    execute_command = "chmod +x {{ .Path }}; {{ .Vars }} sudo -E {{ .Path }}"
    script          = "../common/build-steps/cleanup-image.sh"
  }

  post-processor "manifest" {
    output     = "../common/manifests/packer-manifest.json"
    strip_path = true
  }
}
