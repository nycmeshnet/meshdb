resource "proxmox_vm_qemu" "meshdbnode" {
  for_each = {
    "node1" = { name = "1" }
    "node2" = { name = "2" }
    "node3" = { name = "3" }
  }

  name        = "meshdb${var.meshdb_env_name}node${each.value.name}"
  desc        = "node ${each.value.name} for meshdb ${var.meshdb_env_name}"
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

  ipconfig0 = "ip=${var.meshdb_ips[each.value.name]}/${var.meshdb_networkrange},gw=${var.meshdb_gateway}"

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

