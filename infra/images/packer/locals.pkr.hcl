locals {
  build_timestamp = formatdate("YYYYMMDDhhmmss", timestamp())
  common_scripts = [
    "${var.image_root}/packer/provisioners/common/install-base.sh",
    "${var.image_root}/packer/provisioners/common/install-docker.sh",
    "${var.image_root}/packer/provisioners/common/install-aws-cli.sh",
    "${var.image_root}/packer/provisioners/common/configure-host.sh",
    "${var.image_root}/packer/provisioners/common/verify-image.sh",
  ]
  common_tags = {
    project       = "flowform"
    image_role    = var.image_role
    operating_sys = var.os_name
    source_commit = var.source_commit
    managed_by    = "packer"
  }
}
