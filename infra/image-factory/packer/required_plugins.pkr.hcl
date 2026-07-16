packer {
  required_version = ">= 1.10.0"

  required_plugins {
    proxmox = {
      version = "= 1.1.8"
      source  = "github.com/hashicorp/proxmox"
    }
    amazon = {
      version = "= 1.3.3"
      source  = "github.com/hashicorp/amazon"
    }
  }
}
