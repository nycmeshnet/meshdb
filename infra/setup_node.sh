#!/bin/bash
# setup_node.sh
MASTER_IP="$(ip addr show eth0 | grep "inet\b" | awk '{print $2}' | cut -d/ -f1)"
NODE_TOKEN="$(cat /var/lib/rancher/k3s/server/node-token)"

target_host="$1"

ssh -t ubuntu@$target_host "curl -sfL https://get.k3s.io>k3s; sudo bash k3s --server https://${MASTER_IP}:6443 --token $NODE_TOKEN;sudo apt-get update && sudo apt-get install nfs-common -y"0
