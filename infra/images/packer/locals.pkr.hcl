locals {
  build_timestamp = formatdate("YYYYMMDDhhmmss", timestamp())
  common_scripts = [
    "../provisioning/common/install-base.sh",
    "../provisioning/common/install-docker.sh",
    "../provisioning/common/install-aws-cli.sh",
    "../provisioning/common/configure-host.sh",
    "../provisioning/common/verify-image.sh",
  ]
  common_tags = {
    project       = "flowform"
    image_role    = var.image_role
    operating_sys = var.os_name
    source_commit = var.source_commit
    managed_by    = "packer"
  }
}
