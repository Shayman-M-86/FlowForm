build {
  name = "flowform-golden"
  sources = [
    "source.proxmox-clone.amazon_linux_2023",
    "source.amazon-ebs.amazon_linux_2023",
  ]

  provisioner "file" {
    source      = "${var.image_root}/packer/provisioners/common/lib.sh"
    destination = "/tmp/flowform-image-lib.sh"
  }

  provisioner "shell" {
    execute_command = "chmod +x {{ .Path }}; {{ .Vars }} sudo -E {{ .Path }}"
    scripts         = local.common_scripts
  }

  provisioner "shell" {
    only            = ["proxmox-clone.amazon_linux_2023"]
    execute_command = "chmod +x {{ .Path }}; {{ .Vars }} sudo -E {{ .Path }}"
    scripts         = ["${var.image_root}/packer/provisioners/proxmox/configure-proxmox-guest.sh"]
  }

  provisioner "shell" {
    only            = ["amazon-ebs.amazon_linux_2023"]
    execute_command = "chmod +x {{ .Path }}; {{ .Vars }} sudo -E {{ .Path }}"
    scripts         = ["${var.image_root}/packer/provisioners/aws/configure-ec2.sh", "${var.image_root}/packer/provisioners/aws/configure-ssm.sh"]
  }

  provisioner "shell" {
    execute_command = "chmod +x {{ .Path }}; {{ .Vars }} sudo -E {{ .Path }}"
    script          = "${var.image_root}/packer/provisioners/common/cleanup-image.sh"
  }

  post-processor "manifest" {
    output     = "${var.image_root}/packer/manifests/packer-manifest.json"
    strip_path = true
  }
}
