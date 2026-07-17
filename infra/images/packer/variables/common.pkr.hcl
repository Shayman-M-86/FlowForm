variable "image_role" {
  type    = string
  default = "golden"
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
  description = "Absolute path to infra/images, supplied by the build scripts"
}
