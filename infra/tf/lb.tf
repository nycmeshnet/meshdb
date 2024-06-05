resource "proxmox_vm_qemu" "k8s-lb" {
  name        = "k8s-lb"
  desc        = "router and lb for k8s"
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
          size = 10
          storage = var.meshdb_proxmox_storage_location

        }
      }
    }
  }

  network {
    bridge = "vmbr0"
    model = "virtio"
  }

  ipconfig0 = "ip=${var.meshdb_lb_ip}/${var.meshdb_networkrange},gw=${var.meshdb_gateway}"

  ssh_user = "root"
  ssh_private_key = file("${path.module}/meshdb${var.meshdb_env_name}")

  sshkeys = file("${path.module}/meshdb${var.meshdb_env_name}.pub")

  serial {
    id   = 0
    type = "socket"
  }
  
  tags = "meshdb${var.meshdb_env_name}"
}

