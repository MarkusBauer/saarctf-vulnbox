packer {
    required_plugins {
        docker = {
            version = ">= 1.0.9"
            source  = "github.com/hashicorp/docker"
        }
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
    type = string
}

variable "target_name" {
    type    = string
    default = "vulnbox"
}

variable "base" {
    type = string
}

source "docker" "vulnbox" {
    image       = "debian"
    export_path = "vulnbox.tar.gz"
    # commit      = true
    changes     = [
        "EXPOSE 22",
        "CMD [\"/sbin/init\"]"
    ]
}

build {
    sources = ["source.docker.vulnbox"]

    vulnbuild "actions" {}
}
