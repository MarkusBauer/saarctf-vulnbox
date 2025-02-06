packer {
    required_plugins {
        virtualbox = {
            source  = "github.com/hashicorp/virtualbox"
            version = "~> 1"
        }
    }
}

variable "project_name" {
    type    = string
    default = "saarCTF"
}

variable "project_version" {
    type    = string
    default = "0.0.2"
}

variable "project_output_dir" {
    type    = string
}

variable "target_name" {
    type    = string
    default = "router"
}

variable "base" {
    type = string
}

variable "debian_ova_file" {
    type = string
}

variable "physical_interface" {
    type = string
}

source "virtualbox-ovf" "router" {
    boot_command = ["<enter>"]
    export_opts  = [
        "--manifest", "--vsys", "0",
        "--description", "${var.project_name} ${var.target_name} (powered by saarsec)",
        "--version", "${var.project_version}"
    ]
    format               = "ova"
    guest_additions_mode = "disable"
    headless             = true
    keep_registered      = false
    output_directory     = "output-router"
    shutdown_command     = "echo 'packer' | shutdown -P now"
    source_path          = "${var.debian_ova_file}"
    ssh_password         = "123456789"
    ssh_username         = "root"
    vboxmanage           = [
        ["modifyvm", "{{.Name}}", "--memory", "1024"],
        ["modifyvm", "{{.Name}}", "--vram", "16"],
        ["modifyvm", "{{.Name}}", "--cpus", "1"],
        ["modifyvm", "{{.Name}}", "--nic1", "nat"],
        ["modifyvm", "{{.Name}}", "--nic2", "bridged"],
        ["modifyvm", "{{.Name}}", "--bridgeadapter2", "${var.physical_interface}"],
        ["modifyvm", "{{.Name}}", "--natpf1", "ssh,tcp,127.0.0.1,22222,,22"],
        ["modifyvm", "{{.Name}}", "--natpf1", "OpenVPN for Team-Members,udp,0.0.0.0,1194,,1194"],
        ["modifyvm", "{{.Name}}", "--natpf1", "Wireguard for Team-Members,udp,0.0.0.0,51820,,51820"],
    ]
    vm_name = "saarctf-${var.target_name}"
}

build {
    sources = ["source.virtualbox-ovf.router"]

    vulnbuild "actions" {}
}
