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
  ]

  servers = {
    for instance in proxmox_vm_qemu.meshdbmgr :
    instance.name => {
      ip = instance.default_ipv4_address
      connection = {
        host        = instance.default_ipv4_address
        # TODO: Try to use tls_private_key?
        #private_key = trimspace(tls_private_key.ed25519_provisioning.private_key_pem)
        private_key = file("${path.module}/meshdb${var.meshdb_env_name}")
        user     = "debian"
      }
      flags = [
        "--disable servicelb",
        "--write-kubeconfig-mode 644",
      ]
    }
  }

  agents = {
    for instance in proxmox_vm_qemu.meshdbnode :
    instance.name => {
      name = instance.name
      ip   = instance.default_ipv4_address
      connection = {
        host        = instance.default_ipv4_address
        # TODO: Try to use tls_private_key?
        #private_key = trimspace(tls_private_key.ed25519_provisioning.private_key_pem)
        private_key = file("${path.module}/meshdb${var.meshdb_env_name}")
        user     = "debian"
      }
    }
  }
}

