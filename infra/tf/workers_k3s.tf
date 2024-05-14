data "local_file" "node_token" {
  filename = "${path.module}/node-token"
  depends_on = [
    null_resource.mgr_config_files
  ]
}

resource "null_resource" "workers_k3s" {
  # Apply this to all but the first node (presumably the control node).
  count = length(var.meshdb_ips) - 1

  connection {
    type     = "ssh"
    user     = "${var.meshdb_local_user}"
    private_key = file("${path.module}/meshdb${var.meshdb_env_name}")
    host     = "${var.meshdb_ips[count.index + 1]}"
  }


  provisioner "remote-exec" {
    inline = [
      "curl -sfL https://get.k3s.io>k3s",
      "sudo bash k3s agent --server https://${var.meshdb_ips[0]}:6443 --token ${data.local_file.node_token.content}",
      "sudo apt-get update",
      "sudo apt-get install nfs-common -y"
    ]
  }

  depends_on = [
    proxmox_vm_qemu.meshdbmgr,
    proxmox_vm_qemu.meshdbnode,
    null_resource.mgr_config_files,
  ]
}

