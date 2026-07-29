build {
  name    = "flowform-proxy"
  sources = ["source.amazon-ebs.flowform_role"]

  provisioner "file" {
    source      = "${var.image_root}/definitions/base/provisioners/lib.sh"
    destination = "/tmp/flowform-image-lib.sh"
  }

  provisioner "shell" {
    inline = [
      "mkdir -p /tmp/flowform-role-assets/shared-host",
      "mkdir -p /tmp/flowform-role-assets/role-host",
      "mkdir -p /tmp/flowform-role-assets/runtime-common",
      "mkdir -p /tmp/flowform-role-assets/runtime-compose",
    ]
  }

  provisioner "file" {
    source      = "${var.image_root}/shared/host-assets/."
    destination = "/tmp/flowform-role-assets/shared-host/"
  }

  provisioner "file" {
    source      = "${var.image_root}/definitions/proxy/host-assets/."
    destination = "/tmp/flowform-role-assets/role-host/"
  }

  provisioner "file" {
    source      = "${var.repo_root}/infra/containers/runtime/common/."
    destination = "/tmp/flowform-role-assets/runtime-common/"
  }

  provisioner "file" {
    source      = "${var.repo_root}/infra/containers/runtime/aws/common/compose/proxy.yml"
    destination = "/tmp/flowform-role-assets/runtime-compose/proxy.yml"
  }

  provisioner "shell" {
    environment_vars = ["FLOWFORM_IMAGE_ROLE=proxy"]
    execute_command  = "chmod +x {{ .Path }}; {{ .Vars }} sudo -E {{ .Path }}"
    script           = "${var.image_root}/shared/provisioners/install-role-assets.sh"
  }

  provisioner "shell" {
    environment_vars = ["FLOWFORM_IMAGE_ROLE=proxy"]
    execute_command  = "chmod +x {{ .Path }}; {{ .Vars }} sudo -E {{ .Path }}"
    script           = "${var.image_root}/shared/provisioners/verify-role.sh"
  }

  provisioner "shell" {
    execute_command = "chmod +x {{ .Path }}; {{ .Vars }} sudo -E {{ .Path }}"
    script          = "${var.image_root}/definitions/base/provisioners/cleanup-image.sh"
  }

  post-processor "manifest" {
    output     = "${var.image_root}/packer/manifests/proxy-manifest.json"
    strip_path = true
    custom_data = {
      architecture  = var.aws_architecture
      image_role    = "proxy"
      parent_ami_id = var.aws_base_ami_id
      region        = var.aws_region
      source_commit = var.source_commit
    }
  }
}
