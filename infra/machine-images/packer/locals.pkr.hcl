locals {
  build_timestamp = formatdate("YYYYMMDDhhmmss", timestamp())
  base_scripts = [
    "${var.image_root}/definitions/base/provisioners/install-base.sh",
    "${var.image_root}/definitions/base/provisioners/install-docker.sh",
    "${var.image_root}/definitions/base/provisioners/install-aws-cli.sh",
    "${var.image_root}/definitions/base/provisioners/configure-host.sh",
  ]
  common_tags = {
    project       = "flowform"
    image_role    = var.image_role
    operating_sys = var.os_name
    source_commit = var.source_commit
    managed_by    = "packer"
  }
}
