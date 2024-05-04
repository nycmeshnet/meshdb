#!/bin/bash

# Create meshdb_mgmt directory
MGMT_DIR="/opt/meshdb_mgmt"
mkdir -p $MGMT_DIR
cd $MGMT_DIR

# Clone the repo
apt-get update && apt-get install -y git unzip
git clone https://github.com/nycmeshnet/meshdb.git

# Install tf
wget https://releases.hashicorp.com/terraform/1.8.2/terraform_1.8.2_linux_amd64.zip
unzip terraform_*
mv terraform /usr/bin/

# Setup secret files (will need to be modified)
cp meshdb/infra/helm/meshdb/secret.values.yaml ./secret.values.yaml
cp meshdb/infra/helm/meshdb/values.yaml ./values.yaml

# Setup k3s
curl -sfL https://get.k3s.io | sh -s - server --cluster-init --disable servicelb

echo "cluster-init: true" >> /etc/rancher/k3s/config.yaml
echo "disable: servicelb" >> /etc/rancher/k3s/config.yaml
