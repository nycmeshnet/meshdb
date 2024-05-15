resource "null_resource" "ssh_key" {
  provisioner "local-exec" {
    command = "bash ${path.module}/gen_ssh_key.sh ${var.meshdb_env_name}"
  }
}

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

  depends_on = [
    null_resource.ssh_key
  ]
}

# resource "null_resource" "mgr_config_files" {
#   connection {
#     type     = "ssh"
#     user     = "${var.meshdb_local_user}"
#     private_key = file("${path.module}/meshdb${var.meshdb_env_name}")
#     host     = "${var.meshdb_ips[0]}"
#   }
# 
#   # Copy over scripts
#   provisioner "file" {
#     source      = "${path.module}/mgr_provision.sh"
#     destination = "/home/${var.meshdb_local_user}/mgr_provision.sh"
#   }
# 
#   /*
#   provisioner "file" {
#     source      = "${path.module}/setup_node.sh"
#     destination = "/home/${var.meshdb_local_user}/setup_node.sh"
#   }
# 
#   # Copy local SSH Key to manager so it can configure the workers later
#   # FIXME (willnilges): We should configure the workers from the laptop. Will
#   # still be brittle, but maybe less confusing
#   provisioner "file" {
#     source      = "${path.module}/meshdb${var.meshdb_env_name}"
#     destination = "/home/${var.meshdb_local_user}/.ssh/id_rsa"
#   }
# 
#   provisioner "file" {
#     source      = "${path.module}/meshdb${var.meshdb_env_name}.pub"
#     destination = "/home/${var.meshdb_local_user}/.ssh/id_rsa.pub"
#   }
#   */
# 
#   # Do some configuration (mostly just set up k3s)
#   provisioner "remote-exec" {
#     inline = [
#       "sudo bash /home/${var.meshdb_local_user}/mgr_provision.sh"
#     ]
#   }
# 
#   # Copy KUBECONFIG and NODETOKEN to our local machine for later
#   # FIXME (willnilges): This is super brittle
#   provisioner "local-exec" {
#     command = "scp -o StrictHostKeyChecking=no -i ${path.module}/meshdb${var.meshdb_env_name} ${var.meshdb_local_user}@${var.meshdb_ips[0]}:/tmp/k3s.yaml ${path.module}/"
#   }
# 
#   provisioner "local-exec" {
#     command = "scp -o StrictHostKeyChecking=no -i ${path.module}/meshdb${var.meshdb_env_name} ${var.meshdb_local_user}@${var.meshdb_ips[0]}:/tmp/node-token ${path.module}/"
#   }
# 
#   /*
#   # Configure the worker machines from manager machine
#   provisioner "remote-exec" {
#     inline = [<<EOT
#       %{ for ip in slice(var.meshdb_ips, 1, 4) ~}
#       bash /home/${var.meshdb_local_user}/setup_node.sh ${ip} ${var.meshdb_local_user}
#       %{ endfor ~}
#       EOT
#     ]
#   }
#   */
# 
#   depends_on = [
#     proxmox_vm_qemu.meshdbmgr,
#     proxmox_vm_qemu.meshdbnode
#   ]
# }
