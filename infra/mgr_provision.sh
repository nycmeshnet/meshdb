#!/bin/bash

# Create meshdb_mgmt directory
MGMT_DIR="/opt/meshdb_mgmt"
mkdir -p $MGMT_DIR
cd $MGMT_DIR

# Clone the repo
apt-get update && apt-get install -y git
git clone https://github.com/nycmeshnet/meshdb.git

# JBO TODO REMOVE DEBUG
cd meshdb
git checkout james/infra_updates
cd ..
# END DEBUG

# Setup secret files (will need to be modified)
cp meshdb/infra/helm/meshdb/secret.values.yaml ./secret.values.yaml
cp meshdb/infra/helm/meshdb/values.yaml ./values.yaml
cp meshdb/infra/tf/example.tfvars ./local.tfvars
cp meshdb/infra/cluster/cluster_example.tfvars ./cluster_local.tfvars

# Setup k3s
curl -sfL https://get.k3s.io | sh -s - server --cluster-init --disable servicelb

echo "cluster-init: true" >> /etc/rancher/k3s/config.yaml
echo "disable: servicelb" >> /etc/rancher/k3s/config.yaml
