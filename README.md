# meshdb

## The Premiere NYCMesh Member/Install Database

Welcome to the `nth` attempt at making an API! This was started out of hatred for our current solution for tracking installs/buildings/requests, the **New Node Form**.

This project aims to provide a convenient, stable, and sane API for use with robots and humans. 
For more information, [check the wiki](http://wiki.mesh.nycmesh.net/books/software-services/page/meshdb)

## Setup

To run a local copy from source code, first clone the package with git and create the expected
`.env` file (or otherwise configure the environment variables specified in `.env.sample` as 
appropriate to your environment).
```sh
git clone https://github.com/andybaumgar/nycmesh-database

cp .env.sample .env
nano .env # Fill in any missing values
```

Finally, start the application and database servers using `docker compose`
```sh
docker compose up
```

After a few minutes for image download & database setup, the development server should be 
available at `127.0.0.1:8080`:
```sh
# Should return "[]" since the database is empty
curl http://127.0.0.1:8080/getMembers
```


