#!/usr/bin/env bash

export DEBIAN_FRONTEND=noninteractive

apt-get install -y nginx

# Disable nginx logging
sed -i 's/access_log /# access_log /' /etc/nginx/nginx.conf
