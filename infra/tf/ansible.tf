# declare your groups here
resource "ansible_group" "mgrs" {
  name = "mgrs"
  variables = {
    ansible_user                 = var.meshdb_local_user
    ansible_ssh_private_key_file = "../tf/${path.module}/meshdb${var.meshdb_env_name}"
    ansible_ssh_common_args      = "-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no"
  }
}

resource "ansible_group" "workers" {
  name = "workers"
  variables = {
    ansible_user                 = var.meshdb_local_user
    ansible_ssh_private_key_file = "../tf/${path.module}/meshdb${var.meshdb_env_name}"
    ansible_ssh_common_args      = "-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no"
  }
}

resource "ansible_group" "lb" {
  name = "lb"
  variables = {
    ansible_user                 = var.meshdb_local_user
    ansible_ssh_private_key_file = "../tf/${path.module}/meshdb${var.meshdb_env_name}"
    ansible_ssh_common_args      = "-o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no"
    EXTERNAL_LISTEN_IP           = var.meshdb_external_ip
    LB_HOSTNAME                  = "k8s-lb-${var.meshdb_env_name}"
    INTERNAL_NETWORK_BLOCK       = format("%s/%s", var.meshdb_net_block, var.meshdb_networkrange)
    INTERNAL_NETWORK_RANGE       = var.meshdb_networkrange
    NODE_IP_1                    = var.meshdb_ips[0]
    NODE_IP_2                    = var.meshdb_ips[1]
    NODE_IP_3                    = var.meshdb_ips[2]
    NODE_PORT                    = "30303"
    MESHDB_FQDN                  = var.meshdb_fqdn
  }
}

# declare your hosts here
resource "ansible_host" "meshdbmgr" {
  count  = 1
  name   = var.meshdb_mgr_ips[count.index]
  groups = [ansible_group.mgrs.name]
}

resource "ansible_host" "meshdbnode" {
  count  = 3
  name   = var.meshdb_ips[count.index]
  groups = [ansible_group.workers.name]
}

resource "ansible_host" "k8slb" {
  name   = var.meshdb_lb_ip
  groups = [ansible_group.lb.name]
}