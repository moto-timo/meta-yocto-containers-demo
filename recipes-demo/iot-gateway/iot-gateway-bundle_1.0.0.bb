SUMMARY = "IoT Edge Gateway container bundle (upstream reference images)"
DESCRIPTION = "Bundles the upstream Yocto Project reference containers \
(mosquitto, nginx, python) from registry.yocto.io/library into the target \
image's container storage.  Configuration is overlaid at runtime by the \
iot-gateway-assets Quadlet units, so these images are used unmodified."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COREBASE}/meta/COPYING.MIT;md5=3da9cfbcb788c80a0384361b4de20420"

inherit container-bundle

# Upstream reference containers, pulled by pinned digest (reproducible).
# Web server image follows IOT_GATEWAY_WEBSERVER
IOT_GATEWAY_WEBSERVER ??= "nginx"
WEB_IMAGE = "${@'quay.io/ticotimo/caddy:2.11' if d.getVar('IOT_GATEWAY_WEBSERVER') == 'caddy' else 'registry.yocto.io/library/nginx:1.30'}"
CONTAINER_BUNDLES = "\
    registry.yocto.io/library/mosquitto:2 \
    ${WEB_IMAGE} \
    registry.yocto.io/library/python:3 \
"

# REQUIRED: digests must be pinned. Get each with, e.g.:
#   skopeo inspect docker://registry.yocto.io/library/nginx:1.30 | jq -r '.Digest'
# Key = image ref with '/' and ':' replaced by '_'.
CONTAINER_DIGESTS[registry.yocto.io_library_mosquitto_2]  = "sha256:42114dd8744228f4085a9b3918a645e842c7ef51db276cacf8825b800eb81f13"
CONTAINER_DIGESTS[registry.yocto.io_library_nginx_1.30]   = "sha256:3dea95116f44b2513b6f7fda52c866793a2c15198a975926015769c4100c5ae8"
CONTAINER_DIGESTS[quay.io_ticotimo_caddy_2.11]            = "sha256:03ac076f291be2dae935d8e12ba57cc037611626e4f9e080e6f43b349cac3291"
CONTAINER_DIGESTS[registry.yocto.io_library_python_3]     = "sha256:8bf7d869b34e246fc69719b69efd707ba29e09587b5c0c1930c8c9a27f9db33c"

# Public images: fetch without credentials. Otherwise skopeo reads
# /run/containers/$UID/auth.json and fails if root owns /run/containers.
export REGISTRY_AUTH_FILE = "${WORKDIR}/no-registry-auth.json"

# Runtime follows CONTAINER_PROFILE (podman) automatically; no autostart here
# because the assets recipe ships custom Quadlet units with mounts/ports.

# NOTE: You need to accept licenses for the registry.yocto.io containers
# A good place to do this is conf/local.conf
# CONTAINER_FLAGS_ACCEPTED:pn-iot-gateway-bundle += "registry.yocto.io/library/mosquitto"
# CONTAINER_FLAGS_ACCEPTED:pn-iot-gateway-bundle += "registry.yocto.io/library/nginx"
# CONTAINER_FLAGS_ACCEPTED:pn-iot-gateway-bundle += "registry.yocto.io/library/python"
# CONTAINER_FLAGS_ACCEPTED:pn-iot-gateway-bundle += "quay.io/ticotimo/caddy"
