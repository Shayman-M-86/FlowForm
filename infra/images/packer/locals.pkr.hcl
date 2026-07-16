locals {
  build_timestamp = formatdate("YYYYMMDDhhmmss", timestamp())
  common_scripts = [
    "../common/build-steps/install-base.sh",
    "../common/build-steps/install-docker.sh",
    "../common/build-steps/install-aws-cli.sh",
    "../common/build-steps/configure-host.sh",
    "../common/build-steps/verify-image.sh",
  ]
  common_tags = {
    project       = "flowform"
    image_role    = var.image_role
    operating_sys = var.os_name
    source_commit = var.source_commit
    managed_by    = "packer"
  }
}
