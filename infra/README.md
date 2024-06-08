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
bash gen_ssh_key.sh dev0
```

3. Create the k3s cluster
```
terraform init -var-file=your_env.tfvars
terraform plan -var-file=your_env.tfvars
terraform apply -var-file=your_env.tfvars
```

4. Setup ansible, build the inventory, run the playbook using the keyfile generated in 2.
```
cd meshdb/infra/ansible
ansible-galaxy collection install cloud.terraform
ansible-playbook -i inventory.yaml install_packages.yaml -v --key-file ../tf/meshdbdev0
ansible-playbook -i inventory.yaml k8s_lb.yaml -v --key-file ../tf/meshdbdev0
```

<!-- 5. Install the `meshdb-cluster` chart.

```
cd meshdb/infra/helm/meshdb-cluster
# Modify values.yaml to meet your needs
helm template . -f values.yaml > meshdb-cluster.yaml
kubectl apply -f meshdb-cluster.yaml
``` -->

5. Create and update values + secrets in `values.yaml` and `secret.values.yaml`


```
cd meshdb/infra/helm/meshdb/
cp example.secret.values.yaml secret.values.yaml
cp example.values.yaml values.yaml
nano secret.values.yaml
nano values.yaml
```

6. Render the helm chart

<!--TODO: Use helm install for everything-->
<!-- helm install --kubeconfig='../../tf/k3s.yaml' -f values.yaml -f secret.values.yaml meshdb ./ -->

```
cd meshdb/infra/helm/meshdb
helm template . -f values.yaml -f secret.values.yaml > meshdb.yaml
```

<!--TODO: Have helm create NS and update instns to kubectl apply file-->

7. Deploy MeshDB!

```
cd meshdb/infra/meshdb
terraform init
terraform apply
```

8. If you need a superuser: `kubectl exec -it -n meshdbdev0 service/meshdb-meshweb bash` and `python manage.py createsuperuser`
