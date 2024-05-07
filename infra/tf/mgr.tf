resource "null_resource" "ssh_key" {
  provisioner "local-exec" {
    command = "bash ${path.module}/gen_ssh_key.sh ${var.meshdb_env_name}"
  }
}

resource "proxmox_vm_qemu" "meshdbdevmgr" {
  name        = "meshdb${var.meshdb_env_name}mgr"
  desc        = "managment server for meshdb ${var.meshdb_env_name}"
  target_node = var.meshdb_proxmox_node

  clone = var.meshdb_proxmox_template_image

  cores   = 2
  sockets = 1
  memory  = 2560
  os_type = "cloud-init"
  agent = 1
  cloudinit_cdrom_storage = var.meshdb_proxmox_storage_location
  ciuser = "${var.meshdb_local_user}"
  cipassword = "${var.meshdb_local_password}"

  scsihw = "virtio-scsi-pci"

  disks {
    scsi {
      scsi0 {
        disk {
          backup = false
          size = 50
          storage = var.meshdb_proxmox_storage_location

        }
      }
    }
  }

  network {
    bridge = "vmbr0"
    model = "virtio"
  }

  ipconfig0 = "ip=${var.meshdb_ips[0]}/${var.meshdb_networkrange},gw=${var.meshdb_gateway}"

  ssh_user = "root"
  ssh_private_key = file("${path.module}/meshdb${var.meshdb_env_name}")

  sshkeys = file("${path.module}/meshdb${var.meshdb_env_name}.pub")

  serial {
    id   = 0
    type = "socket"
  }
  
  tags = "meshdb${var.meshdb_env_name}"

  depends_on = [
    null_resource.ssh_key
  ]
}

resource "null_resource" "mgr_config_files" {
  connection {
    type     = "ssh"
    user     = "${var.meshdb_local_user}"
    private_key = file("${path.module}/meshdb${var.meshdb_env_name}")
    host     = "${var.meshdb_ips[0]}"
  }

  provisioner "file" {
    source      = "${path.module}/mgr_provision.sh"
    destination = "/home/${var.meshdb_local_user}/mgr_provision.sh"
  }

  provisioner "file" {
    source      = "${path.module}/setup_node.sh"
    destination = "/home/${var.meshdb_local_user}/setup_node.sh"
  }

  provisioner "file" {
    source      = "${path.module}/meshdb${var.meshdb_env_name}"
    destination = "/home/${var.meshdb_local_user}/.ssh/id_rsa"
  }

  provisioner "file" {
    source      = "${path.module}/meshdb${var.meshdb_env_name}.pub"
    destination = "/home/${var.meshdb_local_user}/.ssh/id_rsa.pub"
  }

  provisioner "remote-exec" {
    inline = [
      "sudo bash /home/${var.meshdb_local_user}/mgr_provision.sh"
    ]
  }

  provisioner "remote-exec" {
    inline = [<<EOT
      %{ for ip in slice(var.meshdb_ips, 1, 4) ~}
      bash /home/${var.meshdb_local_user}/setup_node.sh ${ip} ${var.meshdb_local_user}
      %{ endfor ~}
      EOT
    ]
  }

  depends_on = [
    proxmox_vm_qemu.meshdbdevmgr,
    proxmox_vm_qemu.meshdbnode
  ]
}
