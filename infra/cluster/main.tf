provider "kubernetes" {
  config_path = "/etc/rancher/k3s/k3s.yaml"
}

# Read metallb yaml
data "local_file" "yaml_file" {
  filename = "./metallb.yaml"
}

# Parse the Kubernetes config file
data "yamldecode" "metallb_kubernetes_config" {
  # swap a single variable (IP range)
  input = replace(data.local_file.yaml_file.content, "CHANGE_ME_IP_RANGE", var.metallb_ip_address_range)
}

# Create metallb with the manifest
resource "kubernetes_manifest" "metallb" {
  manifest = data.yamldecode.metallb_kubernetes_config
}

# Read longhorn yaml
data "local_file" "longhorn_yaml_file" {
  filename = "./longhorn.yaml"
}

# Parse the Kubernetes config file
data "yamldecode" "longhorn_kubernetes_config" {
  input = data.local_file.longhorn_yaml_file.content
}

# Create longhorn with the manifest
resource "kubernetes_manifest" "longhorn" {
  manifest = data.yamldecode.longhorn_kubernetes_config
}
