provisioner "file" {
    source      = "${var.project_output_dir}/ssh_vulnbox.pub"
    destination = "/tmp/saarctf.pub"
}
