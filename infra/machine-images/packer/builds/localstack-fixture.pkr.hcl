build {
  name    = "flowform-localstack-fixture"
  sources = ["source.proxmox-clone.localstack_fixture"]

  provisioner "file" {
    source      = "${var.image_root}/definitions/base/provisioners/lib.sh"
    destination = "/tmp/flowform-image-lib.sh"
  }

  provisioner "shell" {
    execute_command = "chmod +x {{ .Path }}; {{ .Vars }} sudo -E {{ .Path }}"
    inline          = ["install -d -m 0755 -o ${var.ssh_username} -g ${var.ssh_username} /tmp/flowform-fixture-compose"]
  }

  provisioner "file" {
    sources = [
      "${var.repo_root}/infra/containers/runtime/proxmox/rehearsal/fixtures/compose.localstack.yml",
      "${var.repo_root}/infra/containers/runtime/proxmox/rehearsal/fixtures/compose.registry.yml",
      "${var.repo_root}/infra/containers/runtime/proxmox/rehearsal/fixtures/compose.tls-shim.yml",
    ]
    destination = "/tmp/flowform-fixture-compose/"
  }

  provisioner "shell" {
    execute_command = "chmod +x {{ .Path }}; {{ .Vars }} sudo -E {{ .Path }}"
    script          = "${var.image_root}/packer/provisioners/proxmox/localstack/preload-images.sh"
  }

  provisioner "shell" {
    execute_command = "chmod +x {{ .Path }}; {{ .Vars }} sudo -E {{ .Path }}"
    script          = "${var.image_root}/definitions/base/provisioners/cleanup-image.sh"
  }

  post-processor "manifest" {
    output     = "${var.image_root}/packer/manifests/localstack-fixture-manifest.json"
    strip_path = true
  }
}
