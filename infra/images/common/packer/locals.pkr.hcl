locals {
  build_timestamp = formatdate("YYYYMMDDhhmmss", timestamp())
  common_scripts = [
    "../build-steps/install-base.sh",
    "../build-steps/install-docker.sh",
    "../build-steps/install-aws-cli.sh",
    "../build-steps/configure-host.sh",
    "../build-steps/verify-image.sh",
  ]
  common_tags = {
    project       = "flowform"
    image_role    = var.image_role
    operating_sys = var.os_name
    source_commit = var.source_commit
    managed_by    = "packer"
  }
}
