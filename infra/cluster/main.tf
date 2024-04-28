provider "kubernetes" {
  config_path = "/etc/rancher/k3s/k3s.yaml"
}

# Create metallb-system
resource "kubernetes_namespace" "metallb-system-ns" {
  metadata {
    name = "metallb-system"
  }
}

# Create metallb with the manifest
resource "kubernetes_manifest" "metallb" {
  manifest = yamldecode(file("./metallb.yaml"))
  depends_on = [
    kubernetes_namespace.metallb-system-ns
  ]
}

# Create longhorn-system
resource "kubernetes_namespace" "longhorn-system-ns" {
  metadata {
    name = "longhorn-system"
  }
}

# Create longhorn with the manifest
resource "kubernetes_manifest" "longhorn" {
  manifest = yamldecode(file("./longhorn.yaml"))
  depends_on = [
    kubernetes_namespace.longhorn-system-ns
  ]
}
