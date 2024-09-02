provisioner "file" {
    source      = "${var.base}/resources/frontpage-testbox/"
    destination = "/var/www/html/"
}

provisioner "file" {
    source      = "${var.base}/resources/setup-scripts/"
    destination = "/root/"
}
