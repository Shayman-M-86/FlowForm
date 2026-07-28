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

  # Host convergence assets, staged for install-runtime-assets.sh. The trailing
  # "/." on each source copies the directory's contents into the matching
  # subdirectory, preserving the repository layout the bootstrap scripts
  # resolve their own paths against.
  provisioner "shell" {
    inline = [
      "mkdir -p /tmp/flowform-runtime-assets/infra/deployment",
      "mkdir -p /tmp/flowform-runtime-assets/infra/containers/runtime",
      "mkdir -p /tmp/flowform-runtime-assets/infra/containers/strategies",
    ]
  }

  provisioner "file" {
    source      = "${var.repo_root}/infra/deployment/bootstrap"
    destination = "/tmp/flowform-runtime-assets/infra/deployment/"
  }

  provisioner "file" {
    source      = "${var.repo_root}/infra/containers/runtime/compose"
    destination = "/tmp/flowform-runtime-assets/infra/containers/runtime/"
  }

  provisioner "file" {
    source      = "${var.repo_root}/infra/containers/runtime/services"
    destination = "/tmp/flowform-runtime-assets/infra/containers/runtime/"
  }

  provisioner "file" {
    source      = "${var.repo_root}/infra/containers/strategies/aws"
    destination = "/tmp/flowform-runtime-assets/infra/containers/strategies/"
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
