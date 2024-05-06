variable "meshdb_proxmox_host" {
  type        = string
  description = "ip/domain of the proxmox server"
}

variable "meshdb_proxmox_token_id" {
  type        = string
  description = "proxmox server token id"
}

variable "meshdb_proxmox_token_secret" {
  type        = string
  description = "proxmox server token secret"
}

variable "meshdb_proxmox_node" {
  type        = string
  description = "target node on the proxmox server"
  default     = "jon"
}

variable "meshdb_proxmox_template_image" {
  type        = string
  description = "name of the template you have already setup in proxmox"
  default     = "ubuntu-cloud"
}

variable "meshdb_proxmox_storage_location" {
  type        = string
  description = "target resource pool on the proxmox server"
  default     = "local-lvm"
}

variable "meshdb_env_name" {
  type        = string
  description = "name of the environment(dev0, dev1, stage, prod)"
}

variable "meshdb_local_user" {
  type        = string
  description = "local user username"
  default     = "ubuntu"
}

variable "meshdb_local_password" {
  type        = string
  description = "password for the local user"
  sensitive   = true
}

variable "meshdb_ips" {
  description  = "static IPs to use for nodes"
}

variable "meshdb_gateway" {
  description  = "default gateway to use for nodes"
  default      = "10.70.90.1"
}

variable "meshdb_networkrange" {
  description  = "network range to use for nodes"
  default      = "24"
}

variable "meshdb_metallb_range" {
  type         = string
  description  = "ip range for metallb"
}
