FROM docker.io/library/debian

# Configure apt-cacher-ng
COPY ./podman/test-and-configure-aptcache.sh /tmp/test-and-configure-aptcache.sh
RUN export DEBIAN_FRONTEND=noninteractive && \
	(timeout 2 /tmp/test-and-configure-aptcache.sh || timeout 2 /tmp/test-and-configure-aptcache.sh 127.0.0.1 || echo "No cache.")

RUN apt-get update && \
	apt-get install -y openssh-server sudo nano htop wget openvpn && \
	apt-get clean && \
	systemctl enable ssh && \
	echo "PermitRootLogin yes" >> /etc/ssh/sshd_config


COPY ./scripts/10_basics.sh /tmp/10_basics.sh
RUN /tmp/10_basics.sh

COPY ./scripts/15_nginx.sh /tmp/15_nginx.sh
RUN /tmp/15_nginx.sh

COPY ./scripts/20_vulnbox_utils.sh /tmp/20_vulnbox_utils.sh
RUN /tmp/20_vulnbox_utils.sh

COPY ./scripts/35_append_only.sh /tmp/35_append_only.sh
RUN /tmp/35_append_only.sh


# PATCH services


COPY ./ssh/saarctf.pub /tmp/saarctf.pub

COPY ./scripts/80_system_config.sh /tmp/80_system_config.sh
RUN /tmp/80_system_config.sh

COPY ./scripts/81_podman_config.sh /tmp/81_podman_config.sh
RUN /tmp/81_podman_config.sh

COPY ./scripts/90_cleanup.sh /tmp/90_cleanup.sh
RUN /tmp/90_cleanup.sh

EXPOSE 22
CMD ["/sbin/init"]
