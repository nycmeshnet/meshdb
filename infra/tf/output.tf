output "mgr_ip" {
    description = "IP address of the managment node"
    value = {
        for k, mgr in proxmox_vm_qemu.meshdbmgr : k => mgr.default_ipv4_address
    }
}

output "worker_ips" {
    description = "IP address of the worker node"
    value = {
        for k, node in proxmox_vm_qemu.meshdbnode : k => node.default_ipv4_address
    }
}
