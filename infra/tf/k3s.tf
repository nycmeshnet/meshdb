module "k3s" {
  source = "xunleii/k3s/module"

  depends_on_    = [
    proxmox_vm_qemu.meshdbmgr,
    proxmox_vm_qemu.meshdbnode,
  ]
  k3s_version    = "latest"
  cluster_domain = "cluster.local"
  cidr = {
    pods     = "10.42.0.0/16"
    services = "10.43.0.0/16"
  }
  drain_timeout  = "30s"
  managed_fields = ["label", "taint"] // ignore annotations

  global_flags = [
    "--disable servicelb"
    #"--flannel-iface ens10",
    #"--kubelet-arg cloud-provider=external" // required to use https://github.com/hetznercloud/hcloud-cloud-controller-manager
  ]

  servers = {
    for i in range(length(proxmox_vm_qemu.meshdbmgr)) :
    proxmox_vm_qemu.meshdbmgr[i].name => {
      ip = proxmox_vm_qemu.meshdbmgr[i].default_ipv4_address
      connection = {
        host        = proxmox_vm_qemu.meshdbmgr[i].default_ipv4_address
        # TODO: Try to use tls_private_key?
        #private_key = trimspace(tls_private_key.ed25519_provisioning.private_key_pem)
        private_key = file("${path.module}/meshdb${var.meshdb_env_name}")
      }
      flags = [
        #"--disable-cloud-controller",
        #"--tls-san ${hcloud_server.control_planes[0].ipv4_address}",
      ]
      annotations = { "server_id" : i } // theses annotations will not be managed by this module
    }
  }

  agents = {
    for i in range(length(proxmox_vm_qemu.meshdbnode)) :
    "${proxmox_vm_qemu.meshdbnode[i].name}_node" => {
      name = proxmox_vm_qemu.meshdbnode[i].name
      ip   = hcloud_server_network.agents_network[i].ip
      connection = {
        host        = proxmox_vm_qemu.meshdbnode[i].default_ipv4_address
        # TODO: Try to use tls_private_key?
        #private_key = trimspace(tls_private_key.ed25519_provisioning.private_key_pem)
        private_key = file("${path.module}/meshdb${var.meshdb_env_name}")
      }

      #labels = { "node.kubernetes.io/pool" = proxmox_vm_qemu.meshdbnode[i].labels.nodepool }
      #taints = { "dedicated" : proxmox_vm_qemu.meshdbnode[i].labels.nodepool == "gpu" ? "gpu:NoSchedule" : null }
    }
  }
}
