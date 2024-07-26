# Meshdb Environment Setup

These instructions will set up a 4 node k3s cluster on proxmox.
- 1 "manager" node for control plane and to be used for deployments.
- 3 "agent" nodes to run services.

1. Setup a new cluster via [nycmeshnet/k8s-infra](https://github.com/nycmeshnet/k8s-infra). Get the ssh key of the mgr node via ssh-keyscan.

2. Create a new "environment" in this repo and add the required secrets to the "environment":

| Name    | Description |
| -------- | ------- |
| `PROJECT_PATH`  |  Absolute file system path to the clone of meshdb, likely `/root/meshdb`  |
| `SSH_KNOWN_HOSTS`  |  Copy paste from `ssh-keyscan <mgr node IP>`  |
| `SSH_PRIVATE_KEY`  | SSH key for the mgr node.   |
| `SSH_TARGET_IP`  |  Mgr node IP  |
| `SSH_USER`  | Mgr username for ssh   |
| `WIREGUARD_ENDPOINT`  | IP and port of the wireguard server for deployment in the format `<IP>:<Port>`   |
| `WIREGUARD_OVERLAY_NETWORK_IP`  | Overlay network IP for wireguard server used for deployment   |
| `WIREGUARD_PEER_PUBLIC_KEY`  | Public key of the wireguard server for deployment   |
| `WIREGUARD_PRIVATE_KEY`  |  Private key for connecting to wireguard for deployment  |

3. Create a new environment specific deployment workflow similar to `.github/workflows/deploy_prod1.yaml`

4. Set variables in `values.yaml` and `secret.values.yaml` on the manager server in `/root/` (one directory above `PROJECT_PATH`)

5. Run the deployment.

6. If you need a superuser, ssh into the mgr node and: `kubectl exec -it -n meshdbdev3 service/meshdb-meshweb bash` and then `python manage.py createsuperuser`
