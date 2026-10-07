SUMMARY = "IoT Edge Gateway container bundle (upstream reference images)"
DESCRIPTION = "Bundles the upstream Yocto Project reference containers \
(mosquitto, nginx, python) from registry.yocto.io/library into the target \
image's container storage.  Configuration is overlaid at runtime by the \
iot-gateway-assets Quadlet units, so these images are used unmodified."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COREBASE}/meta/COPYING.MIT;md5=3da9cfbcb788c80a0384361b4de20420"

inherit container-bundle

# Upstream reference containers, pulled by pinned digest (reproducible).
CONTAINER_BUNDLES = "\
    registry.yocto.io/library/mosquitto:2 \
    registry.yocto.io/library/nginx:1.30 \
    registry.yocto.io/library/python:3 \
"

# REQUIRED: digests must be pinned. Get each with, e.g.:
#   skopeo inspect docker://registry.yocto.io/library/nginx:1.30 | jq -r '.Digest'
# Key = image ref with '/' and ':' replaced by '_'.
CONTAINER_DIGESTS[registry.yocto.io_library_mosquitto_2]  = "sha256:42114dd8744228f4085a9b3918a645e842c7ef51db276cacf8825b800eb81f13"
CONTAINER_DIGESTS[registry.yocto.io_library_nginx_1.30]   = "sha256:e45cacce5716dcc93b4451506bc5584219d867b47ab40c806846dc4ba9da8b64"
CONTAINER_DIGESTS[registry.yocto.io_library_python_3]     = "sha256:8bf7d869b34e246fc69719b69efd707ba29e09587b5c0c1930c8c9a27f9db33c"

# Runtime follows CONTAINER_PROFILE (podman) automatically; no autostart here
# because the assets recipe ships custom Quadlet units with mounts/ports.

# container-bundle couples do_compile to the vruntime multiconfig initramfs
# images (vdkr/vpdmn) via mcdepends. Those are only needed for the build-time
# container-cross-install import, which we do NOT use (we import at first boot
# with the target's own skopeo). Drop the mcdepends so the demo doesn't drag in
# — and fail on — those images' do_sbom_cve_check. do_compile here only copies
# the fetched OCI dirs, so it needs nothing from the multiconfig.
# Runs after the class's __anonymous, so it wins.
python __anonymous() {
    d.delVarFlag('do_compile', 'mcdepends')
}

# NOTE: You need to accept licenses for the registry.yocto.io containers
# A good place to do this is conf/local.conf
# CONTAINER_FLAGS_ACCEPTED:pn-iot-gateway-bundle += "registry.yocto.io/library/mosquitto"
# CONTAINER_FLAGS_ACCEPTED:pn-iot-gateway-bundle += "registry.yocto.io/library/nginx"
# CONTAINER_FLAGS_ACCEPTED:pn-iot-gateway-bundle += "registry.yocto.io/library/python"
