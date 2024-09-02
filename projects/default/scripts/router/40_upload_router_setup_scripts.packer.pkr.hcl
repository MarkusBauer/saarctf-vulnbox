provisioner "file" {
    source      = "${var.base}/resources/router-setup-scripts/"
    destination = "/root/"
}
