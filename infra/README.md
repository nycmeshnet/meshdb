# Meshdb Environment Setup

These instructions will set up a 4 node k3s cluster on proxmox.
- 1 "manager" node for control plane and to be used for deployments.
- 3 "agent" nodes to run services.

1. Setup a new cluster via [nycmeshnet/k8s-infra](https://github.com/nycmeshnet/k8s-infra). Get the ssh key of the mgr node via ssh-keyscan.

2. Create a new "environment" in this repo and add the required secrets to the "environment":

| Name    | Description |
| -------- | ------- |
| `ACCESS_KEY_ID` | Access key ID for s3 backups |
| `SECRET_ACCESS_KEY` | Secret access key for s3 backups |
| `BACKUP_S3_BUCKET_NAME` | Name of the s3 bucket to store backups |
| `DJANGO_SECRET_KEY` | Django secret key |
| `GH_TOKEN` | Github token for pulling down panoramas |
| `NN_ASSIGN_PSK` | Legacy node number assign password |
| `PG_PASSWORD` | meshdb postgres database password |
| `QUERY_PSK` | Legacy query password |
| `SSH_KNOWN_HOSTS`  |  Copy paste from `ssh-keyscan <mgr node IP>`  |
| `SSH_PRIVATE_KEY`  | SSH key for the mgr node.   |
| `SSH_TARGET_IP`  |  Mgr node IP  |
| `SSH_USER`  | Mgr username for ssh   |
| `UISP_PSK` | UISP readonly password |
| `UISP_USER` | UISP readonly username |
| `WIREGUARD_ENDPOINT`  | IP and port of the wireguard server for deployment in the format `<IP>:<Port>`   |
| `WIREGUARD_OVERLAY_NETWORK_IP`  | Overlay network IP for wireguard server used for deployment   |
| `WIREGUARD_PEER_PUBLIC_KEY`  | Public key of the wireguard server for deployment   |
| `WIREGUARD_PRIVATE_KEY`  |  Private key for connecting to wireguard for deployment  |

3. Create a new environment in `.github/workflows/publish-and-deploy.yaml`

4. Run the deployment.

5. If you need a superuser, ssh into the mgr node and: `kubectl exec -it -n meshdb service/meshdb-meshweb python manage.py createsuperuser`

6. If you need to import data: `cat meshdb_export.sql | kubectl exec -it --tty -n meshdb pod/meshdb-postgres-.... -- psql -U meshdb -d meshdb`
