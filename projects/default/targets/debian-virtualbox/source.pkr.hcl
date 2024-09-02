packer {
	required_plugins {
		virtualbox = {
			version = "~> 1"
			source  = "github.com/hashicorp/virtualbox"
		}
	}
}

variable "debian_version" {
	type    = string
	default = "12.2.0"
}

source "virtualbox-iso" "vulnbox-debian" {
	boot_command = [
		"<esc><wait>",
		"install <wait>",
		"preseed/url=http://{{ .HTTPIP }}:{{ .HTTPPort }}/preseed.cfg <wait>",
		"debian-installer=en_US <wait>",
		"auto <wait>",
		"locale=en_US <wait>",
		"kbd-chooser/method=us <wait>",
		"keyboard-configuration/xkb-keymap=us <wait>",
		"netcfg/get_hostname=saarctf-vulnbox <wait>",
		"netcfg/get_domain=saarctf <wait>",
		"netcfg/hostname=saarctf-vulnbox <wait>",
		"netcfg/domain=saarctf <wait>",
		"<enter><wait>"
	]
	boot_wait            = "10s"
	disk_size            = 51200
	format               = "ova"
	guest_additions_mode = "disable"
	guest_os_type        = "Debian_64"
	hard_drive_interface = "sata"
	headless             = true
	http_directory       = "."
	iso_checksum         = "file:https://cdimage.debian.org/cdimage/release/${var.debian_version}/amd64/iso-cd/SHA512SUMS"
	iso_url              = "https://cdimage.debian.org/cdimage/release/${var.debian_version}/amd64/iso-cd/debian-${var.debian_version}-amd64-netinst.iso"
	keep_registered      = false
	output_directory     = "output"
	shutdown_command     = "echo 'packer'|/sbin/shutdown -hP now"
	ssh_password         = "123456789"
	ssh_port             = 22
	ssh_username         = "root"
	ssh_wait_timeout     = "10000s"
	vboxmanage           = [
		["modifyvm", "{{ .Name }}", "--memory", "2048"], ["modifyvm", "{{ .Name }}", "--vram", "16"], ["modifyvm", "{{ .Name }}", "--cpus", "4"],
		["modifyvm", "{{ .Name }}", "--audio", "none"], ["modifyvm", "{{ .Name }}", "--rtcuseutc", "on"]
	]
	vm_name = "saarctf-vulnbox-base"
}

build {
	sources = ["source.virtualbox-iso.vulnbox-debian"]

	provisioner "file" {
		destination = "/dev/shm/test-and-configure-aptcache.sh"
		source      = "./test-and-configure-aptcache.sh"
	}

	provisioner "shell" {
		scripts = ["./initial_setup.sh"]
	}

}
