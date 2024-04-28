# meshdb

A Helm chart for Kubernetes

## Values

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| autoscaling.enabled | bool | `false` |  |
| autoscaling.maxReplicas | int | `100` |  |
| autoscaling.minReplicas | int | `1` |  |
| autoscaling.targetCPUUtilizationPercentage | int | `80` |  |
| aws.access_key_id | string | `"the_real_value"` | AWS access key id for S3 |
| aws.secret_access_key | string | `"the_real_value"` | AWS secret access key for S3 |
| fullnameOverride | string | `"meshdb"` | App name |
| image.pullPolicy | string | `"Always"` | pullPolicy for all images, should be `Always` |
| map.base_url | string | `"http://admin-map.grandsvc.mesh.nycmesh.net"` | Map url |
| meshdb_app_namespace | string | `"meshdbdev0"` | K8s namespace used for all resources |
| meshweb.affinity | object | `{}` |  |
| meshweb.backup_s3_base_folder | string | `"meshdb-backups/development/"` | Base folder for django postgres backups |
| meshweb.backup_s3_bucket_name | string | `"meshdb-data-backups"` | Bucket used for django postgres backups |
| meshweb.disable_pano_edits | string | `"True"` | Feature flag for disabling panorama edits |
| meshweb.disable_profiling | string | `"True"` | Disable profiling in meshweb |
| meshweb.django_secret_key | string | `"the_real_value"` | Django secret key |
| meshweb.enable_debug | string | `"False"` | Enable `DEBUG` in meshweb |
| meshweb.image.repository | string | `"willnilges/meshdb"` | Docker image repo for meshweb |
| meshweb.image.tag | string | `"main"` | Docker image tag for meshweb |
| meshweb.liveness_probe | string | `"true"` | Enable liveness probe with `true` all other values will disable it |
| meshweb.nn_assign_psk | string | `"the_real_value"` | Legacy NN assign form password |
| meshweb.nodeSelector | object | `{}` |  |
| meshweb.pano_github_token | string | `"the_real_value"` | Github token for downloading panorama |
| meshweb.podSecurityContext | object | `{}` |  |
| meshweb.port | int | `8081` | Port used by meshweb (internally) |
| meshweb.query_psk | string | `"the_real_value"` | Legacy query form password |
| meshweb.resources | object | `{}` |  |
| meshweb.securityContext | object | `{}` |  |
| meshweb.static_pvc_name | string | `"meshdb-static-pvc"` | Name of the PVC for static content |
| meshweb.static_pvc_size | string | `"1Gi"` | Size of the PVC for static content |
| meshweb.tolerations | list | `[]` |  |
| nameOverride | string | `""` |  |
| nginx.affinity | object | `{}` |  |
| nginx.nodeSelector | object | `{}` |  |
| nginx.podSecurityContext | object | `{}` |  |
| nginx.port | int | `80` | Nginx port |
| nginx.resources | object | `{}` |  |
| nginx.securityContext | object | `{}` |  |
| nginx.server_name | string | `"db.nycmesh.net"` | `server_name` used by nginx |
| nginx.tolerations | list | `[]` |  |
| pelias.affinity | object | `{}` |  |
| pelias.nodeSelector | object | `{}` |  |
| pelias.podSecurityContext | object | `{}` |  |
| pelias.port | int | `6800` | Pelias port (internal) |
| pelias.resources | object | `{}` |  |
| pelias.securityContext | object | `{}` |  |
| pelias.tolerations | list | `[]` |  |
| pg.affinity | object | `{}` |  |
| pg.dbname | string | `"meshdb"` | Postgres database name |
| pg.liveness_probe | string | `"true"` | Enable liveness probe with `true` all other values will disable it |
| pg.nodeSelector | object | `{}` |  |
| pg.password | string | `"the_real_value"` | Password for postgres |
| pg.podSecurityContext | object | `{}` |  |
| pg.port | string | `"5432"` | Postgres port (internal) |
| pg.pvc_name | string | `"meshdb-postgres-pvc"` | Name of the PVC for postgres |
| pg.pvc_size | string | `"20Gi"` | Size of the PVC for postgres |
| pg.resources | object | `{}` |  |
| pg.securityContext | object | `{}` |  |
| pg.tolerations | list | `[]` |  |
| pg.user | string | `"meshdb"` | Postgres user |
| podAnnotations | object | `{}` |  |
| podLabels | object | `{}` |  |
| redis.affinity | object | `{}` |  |
| redis.liveness_probe | string | `"true"` | Enable liveness probe with `true` all other values will disable it |
| redis.nodeSelector | object | `{}` |  |
| redis.podSecurityContext | object | `{}` |  |
| redis.port | int | `6379` | Redis port (internal) |
| redis.resources | object | `{}` |  |
| redis.securityContext | object | `{}` |  |
| redis.tolerations | list | `[]` |  |
| uisp.psk | string | `"the_real_value"` | Password for UISP |
| uisp.url | string | `"https://uisp.mesh.nycmesh.net/nms"` | UISP url |
| uisp.user | string | `"nycmesh_readonly"` | Username for UISP |

----------------------------------------------
