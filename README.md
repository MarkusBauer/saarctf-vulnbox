saarCTF Vulnbox Build Tool
==========================

Vulnbox images are automatically generated by [Packer](https://www.packer.io/) and based on [VirtualBox](https://www.virtualbox.org/). 

Images are based on [Debian 11 (Bullseye)](https://packages.debian.org/bullseye/).

Subsequent builds can be speed up by installing *apt-cacher-ng* on the host: `apt-get install -y apt-cacher-ng`.



What is here
------------
- Scripts to build a vulnbox including services that follow the [saarCTF service template](https://github.com/MarkusBauer/saarctf-gamelib)
- Scripts to build a testbox (similar to vulnbox but with a simple test service only)
- Scripts to build a "router VM"
- Scripts to convert any of there .ova VM images to a .tar.xz cloud bundle (see below)



How to build the vulnbox
------------------------

- **Step 0:** Download and install [Packer](https://www.packer.io/), [Docker](https://www.docker.com/) and [VirtualBox](https://www.virtualbox.org/).

- **Step 1:** Prepare services
    
    Clone all services into the `services` directory. They must be structured following [these guidelines](https://github.com/MarkusBauer/saarctf-gamelib) 

- **Step 2:** Build the vulnbox

    `./vulnbuild.py build`



Vulnbuild Tool
--------------
In a first step, a plain debian image is built. In a second step, services are built. 
In a third final step, vulnbox is built, based on the plain debian image and the service builds.

- `./vulnbuild.py prepare [--rebuild]`  Build all services. 
- `./vulnbuild.py prepare <service> [--rebuild]`  Build service `<service>`.
- `./vulnbuild.py prepare-debian [--rebuild]`  Build plain debian image.  
- `./vulnbuild.py clean [<service>|debian]`  Clean cached build from service, all services or plain image.   
- `./vulnbuild.py pull [<service>]`  Update git repositories containing one or all services.   
- `./vulnbuild.py build`  Build the final vulnbox.   
- `./vulnbuild.py build [testbox|router]`  Build other boxes.



Customizing the vulnbox
-----------------------
- In any case you should create a **new SSH key** and move it to `ssh/saarctf[.pub]`. 
- The greeting frontpage can be edited in `/frontpage` and `/frontpage-testbox`.
- The general structure of build steps is in `vulnbox.yaml` and can be modified.
- Meta information of all VMs are in `/*.yaml`. 



Cloud builds
------------
We can convert any of these VMs into a `.tar.xz` bundle that is suited for cloud hosting. 
These bundles are our hacky way to get cloud images, which we came up with due to the COVID-19 outbreak. 
Please read the [setup instructions on ctf.saarland](https://ctf.saarland/setup#setupCloud) to get an idea what these bundles are.

To build a bundle from an existing ova VM image, run: 

`sudo ./cloudbuild.py <ova-file> <output-archive> [<password>]`

Conversion requires root, `libguestfs-tools` must be installed and all VirtualBox VMs must be powered off.
If a password is given, the archive is encrypted using GnuPG.   



Orga-hosted cloud images
------------------------
Building a cloud-image for orga-hosted Hetzner Cloud is easy.

1. First build the regular vulnbox and the cloud bundle as described above.
2. `HCLOUD_TOKEN=... packer build vulnbox-cloud.json`


### The manual way (deprecated)
If you (optionally) host vulnboxes as organizer, we provide Hetzner cloud images. 
These cloud images come with OpenVPN preinstalled that connects to the game network.
Use cloudinit to provide SSH keys, root password and `/etc/openvpn/vulnbox.conf`.
Include `sed '/^root/s/:0:0:99999:/:1:0:99999:/' -i /etc/shadow` in cloudinit's `runcmd` to get rid of some "password reset" issues. 

1. First build the regular vulnbox and the cloud bundle as described above.
2. Create a new Hetzner Cloud Server (Debian), boot it into rescue mode.
3. Upload the cloud bundle archive and the scripts from `/cloudhosting-scripts` to `/dev/shm` on that machine.
4. Run `/dev/shm/install_bundle_for_orgahosted_cloud.sh <uploaded-archive.tar.xz>`
5. Shutdown the server and take a snapshot. This snapshot is your image. 

