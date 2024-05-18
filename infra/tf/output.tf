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

#locals {
#    concatenated_ips = concat(
#        [for mgr in proxmox_vm_qemu.meshdbmgr : mgr.default_ipv4_address],
#        [for node in proxmox_vm_qemu.meshdbnode : node.default_ipv4_address]
#    )
#    multiline_ips   = join("\n", local.concatenated_ips)
#}
#
#resource "local_file" "inventory" {
#    content = local.multiline_ips
#    filename = "${path.module}/../ansible/inventory.ini"
#}

resource "local_file" "kubeconfig" {
    content = module.k3s.kube_config
    filename = "${path.module}/k3s.yaml"
}
