meshdb_proxmox_host             = "10.70.90.52"
meshdb_proxmox_node             = "jon"
meshdb_proxmox_template_image   = "debian-cloud"
meshdb_proxmox_storage_location = "local-lvm"
meshdb_env_name                 = "dev1"
meshdb_local_user               = "debian"
meshdb_local_password           = "MeshMesh9999"
meshdb_proxmox_token_id         = "meshdbdev-terraform-prov@pve!james-test"
meshdb_proxmox_token_secret     = ""
meshdb_mgr_ips                  = [
  "10.70.90.X",
]
meshdb_ips                      = [
  "10.70.90.Y",
  "10.70.90.Z",
  "10.70.90.A",
]
meshdb_metallb_range            = "10.70.90.80/29"
