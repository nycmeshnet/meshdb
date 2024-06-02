resource "proxmox_vm_qemu" "meshdbmgr" {
  count       = 1

  name        = "meshdb${var.meshdb_env_name}mgr${count.index}"
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

  ipconfig0 = "ip=${var.meshdb_mgr_ips[0]}/${var.meshdb_networkrange},gw=${var.meshdb_gateway}"

  ssh_user = "root"
  ssh_private_key = file("${path.module}/meshdb${var.meshdb_env_name}")

  sshkeys = file("${path.module}/meshdb${var.meshdb_env_name}.pub")

  serial {
    id   = 0
    type = "socket"
  }
  
  tags = "meshdb${var.meshdb_env_name}"
}
