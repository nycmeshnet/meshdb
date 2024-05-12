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
resource "null_resource" "generate_meshdb_chart" {
  provisioner "local-exec" {
    command = "cd ${path.module}/../helm/meshdb/; helm tempate . -f values.yaml -f secret.values.yaml > meshdb.yaml"
  }
}

# Create meshdb with the manifest
resource "kubernetes_manifest" "meshdb" {
  manifest = yamldecode(file("${path.module}/../helm/meshdb/meshdb.yaml"))
  depends_on = [
    kubernetes_namespace.meshdb-ns,
    null_resource.generate_meshdb_chart
  ]
}
