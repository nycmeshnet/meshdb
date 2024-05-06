#!/bin/bash
# setup_node.sh
MASTER_IP="$(ip addr show eth0 | grep "inet\b" | awk '{print $2}' | cut -d/ -f1)"
NODE_TOKEN="$(sudo cat /var/lib/rancher/k3s/server/node-token)"

ssh_target="$1"

chmod 600 ~/.ssh/id_rsa
chmod 600 ~/.ssh/id_rsa.pub

ssh -t $ssh_target  -o "StrictHostKeyChecking no" "curl -sfL https://get.k3s.io>k3s; sudo bash k3s agent --server https://${MASTER_IP}:6443 --token $NODE_TOKEN;sudo apt-get update && sudo apt-get install nfs-common -y"
