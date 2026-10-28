# IoT Edge Gateway distro configuration snippet
#
# Include this from your distro conf or local.conf:
#   require conf/distro/include/iot-gateway.inc
#
# It enables the necessary DISTRO_FEATURES and selects Podman as the
# container engine via the meta-virtualization container profile.

# --- Container runtime selection -----------------------------------------
# The podman profile pulls in: podman + crun + netavark + aardvark-dns
CONTAINER_PROFILE = "podman"

# Pin crun as the OCI runtime so dnf does not try to co-install runc
PREFERRED_PROVIDER_virtual-runc = "crun"

# --- Required distro features -------------------------------------------
DISTRO_FEATURES:append = " virtualization systemd seccomp ipv6"

# Use systemd as init manager (required for Quadlet)
INIT_MANAGER = "systemd"

# --- QEMU networking -----------------------------------------------------
#
# Option A: TAP networking (recommended, requires root/sudo)
#
#   runqemu nographic iot-gateway-image
#
#   The guest gets a routable IP on a bridge (typically 192.168.7.2).
#   Connect directly — no port forwarding required:
#
#     Dashboard : http://192.168.7.2:8080
#     MQTT      : mosquitto_sub -h 192.168.7.2 -t 'sensors/#' -v
#     WebSocket : ws://192.168.7.2:9001/mqtt
#
# Option B: SLIRP / user-mode networking (no root needed)
#
#   Add to local.conf:
#     QB_SLIRP_OPT = "-netdev user,id=net0,hostfwd=tcp::1883-:1883,hostfwd=tcp::9001-:9001,hostfwd=tcp::8080-:8080"
#
#   Then launch with:
#     runqemu slirp nographic iot-gateway-image
#
#   Connect via localhost on the forwarded ports:
#
#     Dashboard : http://localhost:8080
#     MQTT      : mosquitto_sub -h localhost -t 'sensors/#' -v
#     WebSocket : ws://localhost:9001/mqtt

# Security profile: debug (default), nonroot or hardened. See README.
IOT_GATEWAY_PROFILE ??= "debug"

# Dashboard web server: "nginx" or "caddy"
IOT_GATEWAY_WEBSERVER ??= "nginx"
