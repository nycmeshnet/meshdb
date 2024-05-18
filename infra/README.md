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

3. Create the k3s cluster
```
terraform init -var-file=your_env.tfvars
terraform plan -var-file=your_env.tfvars
terraform apply -var-file=your_env.tfvars
```

<!--ansible-galaxy collection install cloud.terraform-->

4. Apply supporting infrastructure (metallb and longhorn)
```
cd meshdb/infra/cluster
terraform init
terraform apply
```

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
