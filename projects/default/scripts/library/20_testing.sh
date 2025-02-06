#!/usr/bin/env bash

# Configure Debian Buster (testing) as an additional package source.
# Packages from Stretch (stable) are preferred, but future installations can 
# use "-t testing" to install a more recent version of a package.

export DEBIAN_FRONTEND=noninteractive

mv /etc/apt/sources.list /etc/apt/sources.list.d/stable.list
sed -i '/deb-src /d' /etc/apt/sources.list.d/stable.list
sed -e s/bullseye/trixie/g /etc/apt/sources.list.d/stable.list > /etc/apt/sources.list.d/testing.list

echo 'Package: *'             >  /etc/apt/preferences.d/stable.pref
echo 'Pin: release a=stable'  >> /etc/apt/preferences.d/stable.pref
echo 'Pin-Priority: 900'      >> /etc/apt/preferences.d/stable.pref
echo 'Package: *'             >  /etc/apt/preferences.d/testing.pref
echo 'Pin: release a=testing' >> /etc/apt/preferences.d/testing.pref
echo 'Pin-Priority: 1'        >> /etc/apt/preferences.d/testing.pref

apt-get update
