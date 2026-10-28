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

# --- Login -----------------------------------------------------------------
# nonroot: root locked; "admin" logs in over SSH with IOT_GATEWAY_ADMIN_SSH_KEY
# and has sudo. See README, "Profiles".
PACKAGECONFIG ??= ""
PACKAGECONFIG[nonroot] = ""
IOT_GATEWAY_ADMIN_SSH_KEY ??= ""

IOT_GATEWAY_DEBUG_LOGIN = "allow-empty-password allow-root-login empty-root-password"
IMAGE_FEATURES:append = "${@bb.utils.contains('PACKAGECONFIG', 'nonroot', \
    ' ssh-server-openssh', ' ${IOT_GATEWAY_DEBUG_LOGIN}', d)}"
# Also when EXTRA_IMAGE_FEATURES or the root-login-with-empty-password
# fragment add them.
IMAGE_FEATURES:remove = "${@bb.utils.contains('PACKAGECONFIG', 'nonroot', \
    '${IOT_GATEWAY_DEBUG_LOGIN}', '', d)}"

inherit extrausers

# "*": no password, but unlike "!" the account still accepts SSH keys.
EXTRA_USERS_PARAMS = "${@bb.utils.contains('PACKAGECONFIG', 'nonroot', \
    'groupadd -f wheel; useradd -m -G wheel -s /bin/sh -p \'*\' admin;', '', d)}"

IMAGE_INSTALL:append = "${@bb.utils.contains('PACKAGECONFIG', 'nonroot', ' sudo', '', d)}"
ROOTFS_POSTPROCESS_COMMAND += "${@bb.utils.contains('PACKAGECONFIG', 'nonroot', \
    'iot_gateway_admin', '', d)}"

# admin has no password, so sudo must not ask for one.
iot_gateway_admin () {
    install -d -m 0750 ${IMAGE_ROOTFS}${sysconfdir}/sudoers.d
    echo '%wheel ALL=(ALL:ALL) NOPASSWD: ALL' > ${IMAGE_ROOTFS}${sysconfdir}/sudoers.d/wheel
    chmod 0440 ${IMAGE_ROOTFS}${sysconfdir}/sudoers.d/wheel

    ids=$(awk -F: '$1 == "admin" { print $3 ":" $4 }' ${IMAGE_ROOTFS}${sysconfdir}/passwd)
    install -d -m 0700 ${IMAGE_ROOTFS}/home/admin/.ssh
    echo '${IOT_GATEWAY_ADMIN_SSH_KEY}' > ${IMAGE_ROOTFS}/home/admin/.ssh/authorized_keys
    chmod 0600 ${IMAGE_ROOTFS}/home/admin/.ssh/authorized_keys
    chown -R $ids ${IMAGE_ROOTFS}/home/admin/.ssh
}

python () {
    if bb.utils.contains('PACKAGECONFIG', 'nonroot', True, False, d) \
            and not d.getVar('IOT_GATEWAY_ADMIN_SSH_KEY'):
        bb.fatal("PACKAGECONFIG nonroot needs IOT_GATEWAY_ADMIN_SSH_KEY, the "
                 "public key of admin; make one with 'ssh-keygen -t ed25519'")
}

# Enough room for container storage
IMAGE_ROOTFS_EXTRA_SPACE = "1048576"

# Image type — ext4.zst is what runqemu expects by default
IMAGE_FSTYPES = "ext4.zst tar.bz2"
IMAGE_FSTYPES:append = " wic.qcow2"
