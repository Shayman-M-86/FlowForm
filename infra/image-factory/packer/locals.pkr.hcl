locals {
  build_timestamp = formatdate("YYYYMMDDhhmmss", timestamp())
  common_scripts = [
    "../provisioners/common/install-base.sh",
    "../provisioners/common/install-docker.sh",
    "../provisioners/common/install-aws-cli.sh",
    "../provisioners/common/configure-host.sh",
    "../provisioners/common/verify-image.sh",
  ]
  common_tags = {
    project       = "flowform"
    image_role    = var.image_role
    operating_sys = var.os_name
    source_commit = var.source_commit
    managed_by    = "packer"
  }
}
