variable "image_role" {
  type    = string
  default = "base"

  validation {
    condition     = contains(["base", "app", "proxy"], var.image_role)
    error_message = "Image role must be base, app, or proxy."
  }
}

variable "os_name" {
  type    = string
  default = "amazon-linux-2023"
}

variable "ssh_username" {
  type    = string
  default = "ec2-user"
}

variable "source_commit" {
  type    = string
  default = "unknown"
}

variable "image_root" {
  type        = string
  description = "Absolute path to infra/machine-images, supplied by the build scripts"
}

variable "repo_root" {
  type        = string
  description = "Absolute path to the repository root, supplied by the build scripts"
}
