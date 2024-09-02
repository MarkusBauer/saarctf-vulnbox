#!/usr/bin/env bash

set -eu

if [ $# -le 2 ]; then
    echo "USAGE: $0 <ova-file> <vm-name> <network>"
    echo "network can be:"
    echo " - vboxnetX   // host-only network"
    echo " - intXYZ     // internal network"
    echo " - ethX       // bridge to physical adapter"
    exit 1
fi

OVA_FILE=$1
VMNAME=$2
NETWORK=$3
if echo "$OVA_FILE" | grep -q 'router'; then
	echo "Router image detected."
	NIC=2
else
	NIC=1
fi

vboxmanage import "$OVA_FILE" --vsys 0 --vmname "$VMNAME" --options keepallmacs
vboxmanage modifyvm "$VMNAME" --defaultfrontend headless

# Configure network interface
if [[ $NETWORK == vboxnet* ]]; then
	vboxmanage modifyvm "$VMNAME" --nic$NIC hostonly
	vboxmanage modifyvm "$VMNAME" --hostonlyadapter$NIC "$NETWORK"
elif [[ $NETWORK == int* ]]; then
	vboxmanage modifyvm "$VMNAME" --nic$NIC intnet
	vboxmanage modifyvm "$VMNAME" --intnet$NIC "$NETWORK"
else
	vboxmanage modifyvm "$VMNAME" --nic$NIC bridged
	vboxmanage modifyvm "$VMNAME" --bridgeadapter$NIC "$NETWORK"
fi
echo "VM $VMNAME imported."

# Change CPU cores
vboxmanage showvminfo "$VMNAME" | grep "Number of CPU"
echo -n "Enter new CPU count (or press Enter to keep default): "
read CPUCOUNT
test -z $CPUCOUNT || vboxmanage modifyvm "$VMNAME" --cpus "$CPUCOUNT"

# Change RAM
vboxmanage showvminfo "$VMNAME" | grep "Memory"
echo -n "Enter new RAM amount in MB (or press Enter to keep default): "
read MEMORY
test -z $MEMORY || vboxmanage modifyvm "$VMNAME" --memory "$MEMORY"

# If router - change NAT port
if echo "$OVA_FILE" | grep -q 'router'; then
	echo -n "Enter the port you want to expose SSH on your host (default 22222): "
	read PORT
	test -z $PORT || vboxmanage modifyvm "$VMNAME" --natpf1 delete ssh 2>/dev/null || true
	test -z $PORT || vboxmanage modifyvm "$VMNAME" --natpf1 "ssh,tcp,127.0.0.1,$PORT,,22"
fi

# Start VM?
read -p "Start the VM (y/n)? " -n 1 -r
echo    # (optional) move to a new line
if [[ $REPLY =~ ^[Yy]$ ]]; then
    vboxmanage startvm "$VMNAME" --type headless
fi
