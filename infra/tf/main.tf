terraform {
  required_providers {
    proxmox = {
      source  = "telmate/proxmox"
      version = "3.0.1-rc1"
    }
  }
}

provider "proxmox" {
  # Configuration options
  pm_api_url = "https://${var.meshdb_proxmox_host}:8006/api2/json"
  # TODO: Setup cert
  pm_tls_insecure = true
  pm_debug = true
}
