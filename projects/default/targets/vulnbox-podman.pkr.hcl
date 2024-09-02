packer {
    required_plugins {
        # Current online version of packer plugin is bugged.
        # Fixes are on master, but no release has been created.
        # Please clone https://github.com/Polpetta/packer-plugin-podman, then run:
        #   go build . && cp packer-plugin-podman ~/.packer.d/plugins/packer-plugin-podman
        #podman = {
        #    version = ">= 0.1.1"
        #    source  = "github.com/Polpetta/podman"
        #}
    }
}

variable "project_name" {
    type    = string
    default = "saarCTF"
}

variable "project_version" {
    type    = string
    default = "0.0.1"
}

variable "project_output_dir" {
    type    = string
}

variable "target_name" {
    type    = string
    default = "vulnbox"
}

variable "base" {
    type = string
}

source "podman" "vulnbox" {
    image       = "debian"
    export_path = "vulnbox.tar.gz"
    # commit      = true
    changes     = [
        "EXPOSE 22",
        "CMD [\"/sbin/init\"]"
    ]
}

build {
    sources = ["source.podman.vulnbox"]

    vulnbuild "actions" {}
}
