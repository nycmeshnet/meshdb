# Meshdb Environment Setup

1. Configure a user for the [proxmox provider](https://registry.terraform.io/providers/Telmate/proxmox/latest/docs) and setup env vars.
2. Setup tfvars + ssh keys
3. `terraform plan --var-file=your.tfvars`
4. `terraform apply --var-file=your.tfvars`
5. Login via serial and figure out the IPs that were recieved from DHCP
6. One time provisioning for the master node

```
target_host="<MGR IP>"
scp infra/mgr_provision.sh ubuntu@$target_host:/home/ubuntu/mgr_provision.sh
ssh -t ubuntu@$target_host "sudo bash /home/ubuntu/mgr_provision.sh"
```

7. Set the IP range for metallb, such as `10.70.90.80/29`, in `/opt/meshdb_mgmt/cluster_local.tfvars` and then deploy metallb and longhorn from the manager
```
cd /opt/meshdb_mgmt/meshdb/infra/cluster/
cat ../../cluster_local.tfvars
terraform init
terraform plan --var-file=../../cluster_local.tfvars
terraform apply --var-file=../../cluster_local.tfvars
```

8. Setup each node (from the manager)

```
cd /opt/meshdb_mgmt/meshdb/infra/
declare -a target_nodes=("10.70.90.XX" "10.70.90.YY" "10.70.90.ZZ")

for n in "${target_nodes[@]}"
do
  bash setup_node.sh $n
done
```

10. `kubectl create namespace meshdbdev0 && helm template . -f values.yaml -f secret.values.yaml | kubectl apply -f -`

11. If you need a superuser: `kubectl exec -it -n meshdbdev0 service/meshdb-meshweb bash` and `python manage.py createsuperuser`
