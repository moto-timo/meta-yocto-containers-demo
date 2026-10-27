SUMMARY = "IoT Edge Gateway host image"
DESCRIPTION = "QEMU image that boots with Podman and three upstream Yocto \
reference containers (mosquitto, nginx, python) preloaded into storage. \
Our mosquitto.conf, dashboard, and sensor app are overlaid at runtime via \
Podman Quadlet bind-mounts; all three start automatically on boot."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COREBASE}/meta/COPYING.MIT;md5=3da9cfbcb788c80a0384361b4de20420"

inherit core-image container-cross-install

# --- Distro integration --------------------------------------------------
# The iot-gateway.inc sets CONTAINER_PROFILE, DISTRO_FEATURES, and QEMU
# port forwarding.  Include it in local.conf or your distro conf:
#
#   require conf/distro/include/iot-gateway.inc

# --- Image contents ------------------------------------------------------
# Core
IMAGE_INSTALL = " \
    packagegroup-core-boot \
    packagegroup-base-extended \
"

# Container runtime (crun, netavark, aardvark-dns pulled via podman RDEPENDS)
IMAGE_INSTALL:append = " \
    podman \
    netavark \
    aardvark-dns \
    container-host-config \
"

# Trust the usual certificate authorities, for TLS from the gateway, for
# example "podman pull" from a registry. The clock is set by
# systemd-timesyncd, which is part of systemd.
IMAGE_INSTALL:append = " ca-certificates"

# Upstream container images (bundle) + runtime overlay assets & Quadlet units.
# container-cross-install imports the bundle into podman storage at build time.
IMAGE_INSTALL:append = " iot-gateway-bundle iot-gateway-assets"

# Debugging / demo convenience
IMAGE_INSTALL:append = " \
    mosquitto-clients \
    htop \
    less \
"

# Allow root login for the demo (disable for production)
IMAGE_FEATURES:append = " allow-empty-password allow-root-login empty-root-password"

# Enough room for container storage
IMAGE_ROOTFS_EXTRA_SPACE = "1048576"

# Image type — ext4.zst is what runqemu expects by default
IMAGE_FSTYPES = "ext4.zst tar.bz2"
IMAGE_FSTYPES:append = " wic.qcow2"
