# Remove the node-token and k3s.yaml from /tmp for safety™

# This is what happens when you have a lot of remote-execs. It stops being
# declarative and starts being imperitive. We now have a chain of
# mgr -> workers -> workers_k3s -> cleanup

resource "null_resource" "cleanup_secrets" {
  connection {
    type     = "ssh"
    user     = "${var.meshdb_local_user}"
    private_key = file("${path.module}/meshdb${var.meshdb_env_name}")
    host     = "${var.meshdb_ips[0]}"
  }

  provisioner "remote-exec" {
    inline = [
      "rm /tmp/k3s.yaml || echo nothing to clean; /tmp/node-token || echo nothing to clean"
    ]
  }

  depends_on = [
    null_resource.workers_k3s,
  ]
}
