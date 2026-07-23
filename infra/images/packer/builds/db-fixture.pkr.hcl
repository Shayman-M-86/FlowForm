build {
  name    = "flowform-db-fixture"
  sources = ["source.proxmox-clone.db_fixture"]

  provisioner "file" {
    source      = "${var.image_root}/packer/provisioners/common/lib.sh"
    destination = "/tmp/flowform-image-lib.sh"
  }

  provisioner "file" {
    source      = "${var.image_root}/../containers/strategies/rehearsal/compose/db.yml"
    destination = "/tmp/flowform-db-compose.yml"
  }

  provisioner "shell" {
    execute_command = "chmod +x {{ .Path }}; {{ .Vars }} sudo -E {{ .Path }}"
    script          = "${var.image_root}/packer/provisioners/proxmox/db/preload-image.sh"
  }

  provisioner "shell" {
    execute_command = "chmod +x {{ .Path }}; {{ .Vars }} sudo -E {{ .Path }}"
    script          = "${var.image_root}/packer/provisioners/common/cleanup-image.sh"
  }

  post-processor "manifest" {
    output     = "${var.image_root}/packer/manifests/db-fixture-manifest.json"
    strip_path = true
  }
}
