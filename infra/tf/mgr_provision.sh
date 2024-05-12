#!/bin/bash

set -e

# Setup k3s
curl -sfL https://get.k3s.io | sh -s - server --cluster-init --disable servicelb

# Persist our preferences
echo "cluster-init: true" >> /etc/rancher/k3s/config.yaml
echo "disable: servicelb" >> /etc/rancher/k3s/config.yaml

# FIXME (willnilges): Jank as fuck
cp /etc/rancher/k3s/k3s.yaml /var/lib/rancher/k3s/server/node-token /tmp
chown -R debian:debian /tmp/k3s.yaml
chown -R debian:debian /tmp/node-token
