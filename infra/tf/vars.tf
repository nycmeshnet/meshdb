variable "meshdb_proxmox_host" {
  type        = string
  description = "ip/domain of the proxmox server"
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
