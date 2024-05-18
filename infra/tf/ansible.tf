# declare your groups here
resource "ansible_group" "mgrs" {
  name = "mgrs"
  variables = {
    ansible_user = var.meshdb_local_user 
  }
}

resource "ansible_group" "workers" {
  name = "workers"
  variables = {
    ansible_user = var.meshdb_local_user 
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
