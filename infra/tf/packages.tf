# Both the mgrs and workers install the same pagkages for now

locals {
  packages = "open-iscsi"
  # Kind of kludgy, but will attempt to install packages several times before failing.
  command = "for i in {0..12}; do echo install packages...; sleep 10; sudo apt -o DPkg::Lock::Timeout=180 update && sudo apt -o DPkg::Lock::Timeout=180 install -y ${local.packages} && break; done"
}

resource "null_resource" "mgr_packages" {
  for_each = {
    for ip in var.meshdb_mgr_ips : ip => ip
  }

  depends_on = [
    proxmox_vm_qemu.meshdbmgr,
  ]

  connection {
    type     = "ssh"
    user     = "${var.meshdb_local_user}"
    private_key = file("${path.module}/meshdb${var.meshdb_env_name}")
    host     = each.value
  }

  # set hostname
  provisioner "remote-exec" {
    inline = [
      local.command,
    ]
  }
}

resource "null_resource" "worker_packages" {
  for_each = {
    for ip in var.meshdb_ips : ip => ip
  }

  depends_on = [
    proxmox_vm_qemu.meshdbnode,
  ]

  connection {
    type     = "ssh"
    user     = "${var.meshdb_local_user}"
    private_key = file("${path.module}/meshdb${var.meshdb_env_name}")
    host     = each.value
  }

  # set hostname
  provisioner "remote-exec" {
    inline = [
        local.command,
    ]
  }
}
