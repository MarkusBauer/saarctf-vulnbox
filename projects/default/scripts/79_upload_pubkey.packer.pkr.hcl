provisioner "file" {
    source      = "${var.project_output_dir}/saarctf_vulnbox.pub"
    destination = "/tmp/saarctf.pub"
}
