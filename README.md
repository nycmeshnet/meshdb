# meshdb

## The Premiere NYCMesh Member/Install Database

Welcome to the `nth` attempt at making an API! This was started out of hatred for our current solution for tracking installs/buildings/requests, the **New Node Form**.

This project aims to provide a convenient, stable, and sane API for use with robots and humans. 
For more information, [check the wiki](http://wiki.mesh.nycmesh.net/books/software-services/page/meshdb)

## Setup

```
git clone https://github.com/andybaumgar/nycmesh-database

docker-compose up
```

## Tests

```
podman build --tag meshdb_integration -f ./tests/Dockerfile . && podman run --rm -it meshdb_integration
```

or

```
cd tests
podman-compose up # Podman-compose profiles support should be coming soon™
```