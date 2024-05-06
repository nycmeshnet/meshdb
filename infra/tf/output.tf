output "mgr_ip" {
    description = "IP address of the managment node"
    value       = proxmox_vm_qemu.meshdbdevmgr.default_ipv4_address
}

output "worker_ips" {
    value = {
        for k, meshdbnode in proxmox_vm_qemu.meshdbnode : k => meshdbnode.default_ipv4_address
  }
}