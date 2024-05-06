metallb_addr="$1"

cd /opt/meshdb_mgmt/
cd meshdb
git checkout james/infra
cd infra/cluster

sleep 10

terraform init
terraform plan
terraform apply

sed -i -e "s/METALLB_ADDR_RANGE/${metallb_addr}/g" metallb_extra.yaml
terraform init
terraform plan
terraform apply -auto-approve

sleep 30

kubectl apply -f /opt/meshdb_mgmt/meshdb/infra/cluster/metallb_extra.yaml