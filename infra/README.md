# Meshdb Environment Setup

1. Configure a user for the [proxmox provider](https://registry.terraform.io/providers/Telmate/proxmox/latest/docs) and setup env vars.
2. Setup tfvars + ssh keys
3. `terraform plan --var-file=your.tfvars`
4. `terraform apply --var-file=your.tfvars`
5. Login via serial and figure out the IPs that were recieved from DHCP
6. SSH into the master node and setup
```
curl -sfL https://get.k3s.io | sh -s - server --cluster-init --disable servicelb

echo "cluster-init: true" >> /etc/rancher/k3s/config.yaml
echo "disable: servicelb" >> /etc/rancher/k3s/config.yaml
```

7. Install metallb on master node

```
IP_RANGE="10.70.90.71/32"
cat <<EOF > /var/lib/rancher/k3s/server/manifests/metallb.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: metallb-system
---
apiVersion: helm.cattle.io/v1
kind: HelmChart
metadata:
  name: metallb
  namespace: metallb-system
spec:
  repo: https://metallb.github.io/metallb
  chart: metallb
  targetNamespace: metallb-system

---
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: pool-1
  namespace: metallb-system
spec:
  addresses:
  - $IP_RANGE

---
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata:
  name: k3s-l2
  namespace: metallb-system
spec:
  ipAddressPools:
  - pool-1
EOF

```

8. Setup each node (from the manager)

`bash setup_node.sh <NODE IP>`

```
#!/bin/bash
# setup_node.sh
MASTER_IP="$(ip addr show eth0 | grep "inet\b" | awk '{print $2}' | cut -d/ -f1)"
NODE_TOKEN="$(cat /var/lib/rancher/k3s/server/node-token)"

target_host="$1"

ssh -t ubuntu@$target_host "curl -sfL https://get.k3s.io>k3s; sudo bash k3s --server https://${MASTER_IP}:6443 --token $NODE_TOKEN"
```

9. Install helm chart...