provider "kubernetes" {
  config_path = "${path.module}/../tf/k3s.yaml"
}

# Create meshdb
resource "kubernetes_namespace" "meshdb-ns" {
  metadata {
    name = "meshdb"
  }
}

# Generate the chart
#resource "null_resource" "generate_meshdb_chart" {
#  provisioner "local-exec" {
#    command = "cd ${path.module}/../helm/meshdb/; helm tempate . -f values.yaml -f secret.values.yaml > meshdb.yaml"
#  }
#}

# TODO: template version
resource "null_resource" "package_meshdb_chart" {
  provisioner "local-exec" {
    command = "cd ${path.module}/../helm/; helm package meshdb; mv ${path.module}/../helm/meshdb-0.1.0.tgz ${path.module}/../meshdb/"
  }
}

# Create meshdb with the manifest
resource "kubernetes_manifest" "meshdb" {
  manifest = yamldecode(file("${path.module}/meshdb.yaml"))
  depends_on = [
    kubernetes_namespace.meshdb-ns,
    null_resource.package_meshdb_chart
  ]
}
