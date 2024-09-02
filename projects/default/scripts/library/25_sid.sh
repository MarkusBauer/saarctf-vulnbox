#!/usr/bin/env bash

# Configure Debian SID as an additional package source.
# Packages from Buster (stable) are preferred, but future installations can 
# use "-t sid" to install a more recent version of a package.

export DEBIAN_FRONTEND=noninteractive

sed -i '/deb-src /d' /etc/apt/sources.list
mv /etc/apt/sources.list /etc/apt/sources.list.d/stable.list
echo 'deb http://http.us.debian.org/debian sid main' > /etc/apt/sources.list.d/sid.list

echo 'Package: *'             >  /etc/apt/preferences.d/stable.pref
echo 'Pin: release a=stable'  >> /etc/apt/preferences.d/stable.pref
echo 'Pin-Priority: 900'      >> /etc/apt/preferences.d/stable.pref
echo 'Package: *'             >  /etc/apt/preferences.d/sid.pref
echo 'Pin: release a=sid'     >> /etc/apt/preferences.d/sid.pref
echo 'Pin-Priority: 1'        >> /etc/apt/preferences.d/sid.pref

apt-get update
