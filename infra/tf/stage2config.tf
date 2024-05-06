resource "null_resource" "mgr_stage_two" {
  connection {
    type     = "ssh"
    user     = "${var.meshdb_local_user}"
    private_key = file("${path.module}/meshdb${var.meshdb_env_name}")
    host     = "${var.meshdb_ips[0]}"
  }

  provisioner "file" {
    source      = "${path.module}/stage2.sh"
    destination = "/home/${var.meshdb_local_user}/stage2.sh"
  }

  provisioner "remote-exec" {
    inline = [
      format("sudo bash /home/%s/stage2.sh \"%s\"", var.meshdb_local_user, replace(var.meshdb_metallb_range, "/","\\/"))
    ]
  }

  depends_on = [
    proxmox_vm_qemu.meshdbdevmgr,
    proxmox_vm_qemu.meshdbnode,
    null_resource.mgr_config_files
  ]
}
