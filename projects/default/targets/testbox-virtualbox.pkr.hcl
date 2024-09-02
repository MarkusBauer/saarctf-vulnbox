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

variable "target_name" {
    type    = string
    default = "testbox"
}

variable "project_version" {
    type    = string
    default = "0.0.1"
}

variable "project_output_dir" {
    type    = string
}

variable "base" {
    type = string
}

variable "debian_ova_file" {
    type = string
}

source "virtualbox-ovf" "testbox" {
    boot_command = ["<enter>"]
    export_opts  = [
        "--manifest", "--vsys", "0",
        "--description", "${var.project_name} ${var.target_name} (powered by saarsec)",
        "--version", "${var.project_version}"
    ]
    format               = "ova"
    guest_additions_mode = "disable"
    headless             = true
    keep_registered      = true
    output_directory     = "output-testbox"
    shutdown_command     = "echo 'packer' | shutdown -P now"
    source_path          = "${var.debian_ova_file}"
    ssh_password         = "123456789"
    ssh_username         = "root"
    vboxmanage           = [
        ["modifyvm", "{{ .Name }}", "--memory", "2048"],
        ["modifyvm", "{{ .Name }}", "--vram", "16"],
        ["modifyvm", "{{ .Name }}", "--cpus", "2"],
        ["modifyvm", "{{ .Name }}", "--nic1", "nat"]
    ]
    vboxmanage_post = [
        ["modifyvm", "{{ .Name }}", "--nic1", "bridged"],
        ["modifyvm", "{{ .Name }}", "--bridgeadapter1", "none"],
        ["modifyvm", "{{ .Name }}", "--macaddress1", "0A00273D6303"]
    ]
    vm_name = "saarctf-${var.target_name}"
}

build {
    sources = ["source.virtualbox-ovf.testbox"]

    vulnbuild "actions" {}
}
