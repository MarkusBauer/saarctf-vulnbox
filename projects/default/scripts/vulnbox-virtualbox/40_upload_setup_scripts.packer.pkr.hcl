provisioner "file" {
    source      = "${var.base}/resources/setup-scripts/"
    destination = "/root/"
}
