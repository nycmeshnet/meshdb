# Meshdb Environment Setup

These instructions will set up a 4 node k3s cluster on proxmox.
- 1 "manager" node for control plane and to be used for deployments.
- 3 "agent" nodes to run services.

1. Clone this repository
2. Set up tfvars. See [proxmox provider](https://registry.terraform.io/providers/Telmate/proxmox/latest/docs). Create an API key in Proxmox, and disable Privilege Separation.
```
cd meshdb/infra/tf/
cp example.tfvars your_env.tfvars
# Modify your_env.tfvars to meet your needs
```
3. Create the VMs that will host k3s
```
terraform init --var-file=your_env.tfvars
terraform plan --var-file=your_env.tfvars
terraform apply --var-file=your_env.tfvars
```
4. SSH into the manager node
5. Update values + secrets in `/opt/meshdb_mgmt/values.yaml` and `/opt/meshdb_mgmt/secret.values.yaml`

6. Deploy helm chart. Create the namespace you indicated in `/opt/meshdb_mgmt/values.yaml`

```
your_ns="meshdbdev0"
cd /opt/meshdb_mgmt/meshdb/infra/helm/meshdb/
kubectl create namespace $your_ns
helm template . -f ../../../../values.yaml -f ../../../../secret.values.yaml | kubectl apply -f -
kubectl get all -n $your_ns
```

7. If you need a superuser: `kubectl exec -it -n meshdbdev0 service/meshdb-meshweb bash` and `python manage.py createsuperuser`
