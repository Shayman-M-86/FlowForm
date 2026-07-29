build {
  name = "flowform-base"
  sources = [
    "source.proxmox-clone.amazon_linux_2023",
    "source.amazon-ebs.amazon_linux_2023_base",
  ]

  provisioner "file" {
    source      = "${var.image_root}/definitions/base/provisioners/lib.sh"
    destination = "/tmp/flowform-image-lib.sh"
  }

  provisioner "shell" {
    execute_command = "chmod +x {{ .Path }}; {{ .Vars }} sudo -E {{ .Path }}"
    scripts         = local.base_scripts
  }

  provisioner "shell" {
    only            = ["proxmox-clone.amazon_linux_2023"]
    execute_command = "chmod +x {{ .Path }}; {{ .Vars }} sudo -E {{ .Path }}"
    scripts         = ["${var.image_root}/packer/provisioners/proxmox/configure-proxmox-guest.sh"]
  }

  provisioner "shell" {
    only            = ["amazon-ebs.amazon_linux_2023_base"]
    execute_command = "chmod +x {{ .Path }}; {{ .Vars }} sudo -E {{ .Path }}"
    scripts = [
      "${var.image_root}/definitions/base/provisioners/aws/configure-ec2.sh",
      "${var.image_root}/definitions/base/provisioners/aws/configure-ssm.sh",
    ]
  }

  provisioner "shell" {
    execute_command = "chmod +x {{ .Path }}; {{ .Vars }} sudo -E {{ .Path }}"
    script          = "${var.image_root}/definitions/base/provisioners/verify-base.sh"
  }

  provisioner "shell" {
    execute_command = "chmod +x {{ .Path }}; {{ .Vars }} sudo -E {{ .Path }}"
    script          = "${var.image_root}/definitions/base/provisioners/cleanup-image.sh"
  }

  post-processor "manifest" {
    output     = "${var.image_root}/packer/manifests/base-manifest.json"
    strip_path = true
    custom_data = {
      architecture  = var.aws_architecture
      image_role    = "base"
      region        = var.aws_region
      source_commit = var.source_commit
    }
  }
}
