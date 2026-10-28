SUMMARY = "IoT Edge Gateway config overlays, dashboard, app + Quadlet units"
DESCRIPTION = "Runtime overlay assets for the upstream reference containers: \
mosquitto.conf, the dashboard index.html, the sensor-processor app (plus a \
vendored pure-python paho-mqtt), and the Podman Quadlet units that bind-mount \
them into the stock mosquitto/nginx/python containers."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COREBASE}/meta/COPYING.MIT;md5=3da9cfbcb788c80a0384361b4de20420"

SRC_URI = " \
    file://mosquitto.conf \
    file://www/index.html \
    file://www/dashboard.js \
    file://default.conf \
    file://nginx.conf \
    file://caddy/Caddyfile \
    file://caddy/iot-caddy.container \
    file://sensor-processor.py \
    file://mosquitto.container \
    file://nginx.container \
    file://dataproc.container \
    ${@bb.utils.contains('PACKAGECONFIG', 'mqtt-auth', '${MQTT_AUTH_SRC}', '', d)} \
    https://unpkg.com/mqtt@5.16.1/dist/mqtt.min.js;name=mqttjs;downloadfilename=mqtt-5.16.1.min.js \
    https://files.pythonhosted.org/packages/39/15/0a6214e76d4d32e7f663b109cf71fb22561c2be0f701d67f93950cd40542/paho_mqtt-2.1.0.tar.gz;name=paho \
"
# mqtt.js (MIT), served locally so the browser loads no remote code
SRC_URI[mqttjs.sha256sum] = "75873d04a6400bbbac093b3602caf06f44ed92ee032925e1f4f21c03eba05a4e"
SRC_URI[paho.sha256sum] = "12d6e7511d4137555a3f6ea167ae846af2c7357b10bc6fa4f7c3968fc1723834"

S = "${UNPACKDIR}"

# mqtt-auth: HTTPS dashboard with a login, MQTT logins, ACLs and TLS;
# secrets made on first boot. See README, "Profiles".
# Set by IOT_GATEWAY_PROFILE "hardened".
IOT_GATEWAY_PROFILE ??= "debug"
PACKAGECONFIG ??= "${@'mqtt-auth' if d.getVar('IOT_GATEWAY_PROFILE') == 'hardened' else ''}"

# "nginx" or "caddy"
IOT_GATEWAY_WEBSERVER ??= "nginx"
WEB = "${IOT_GATEWAY_WEBSERVER}"
PACKAGECONFIG[mqtt-auth] = ",,,openssl-bin"
MQTT_AUTH_SRC = " \
    file://mqtt-auth/mosquitto.conf \
    file://mqtt-auth/mosquitto.acl \
    file://mqtt-auth/default.conf \
    file://mqtt-auth/iot-gateway-secrets \
    file://mqtt-auth/iot-gateway-secrets.service \
    file://mqtt-auth/mosquitto-auth.conf \
    file://mqtt-auth/nginx-auth.conf \
    file://mqtt-auth/Caddyfile \
    file://mqtt-auth/caddy-auth.conf \
    file://mqtt-auth/dataproc-auth.conf \
"

GWDIR = "${datadir}/iot-gateway"

do_install() {
    # --- Overlay config + dashboard --------------------------------------
    install -d ${D}${GWDIR}
    install -m 0644 ${UNPACKDIR}/mosquitto.conf ${D}${GWDIR}/mosquitto.conf
    install -d ${D}${GWDIR}/www
    install -m 0644 ${UNPACKDIR}/www/index.html     ${D}${GWDIR}/www/index.html
    install -m 0644 ${UNPACKDIR}/www/dashboard.js   ${D}${GWDIR}/www/dashboard.js
    install -m 0644 ${UNPACKDIR}/mqtt-5.16.1.min.js ${D}${GWDIR}/www/mqtt.min.js
    if [ "${WEB}" = caddy ]; then
        install -m 0644 ${UNPACKDIR}/caddy/Caddyfile ${D}${GWDIR}/Caddyfile
    else
        install -m 0644 ${UNPACKDIR}/default.conf ${D}${GWDIR}/default.conf
        install -m 0644 ${UNPACKDIR}/nginx.conf   ${D}${GWDIR}/nginx.conf
    fi

    # --- Sensor app + vendored pure-python paho-mqtt ---------------------
    install -d ${D}${GWDIR}/app
    install -m 0644 ${UNPACKDIR}/sensor-processor.py ${D}${GWDIR}/app/sensor-processor.py
    cp -R --no-preserve=ownership,mode ${UNPACKDIR}/paho_mqtt-2.1.0/src/paho ${D}${GWDIR}/app/paho
    chmod -R u+rwX,go+rX ${D}${GWDIR}/app/paho

    # --- Podman Quadlet units --------------------------------------------
    install -d ${D}${sysconfdir}/containers/systemd
    install -m 0644 ${UNPACKDIR}/mosquitto.container ${D}${sysconfdir}/containers/systemd/iot-mosquitto.container
    if [ "${WEB}" = caddy ]; then
        install -m 0644 ${UNPACKDIR}/caddy/iot-caddy.container ${D}${sysconfdir}/containers/systemd/iot-caddy.container
    else
        install -m 0644 ${UNPACKDIR}/nginx.container ${D}${sysconfdir}/containers/systemd/iot-nginx.container
    fi
    install -m 0644 ${UNPACKDIR}/dataproc.container  ${D}${sysconfdir}/containers/systemd/iot-dataproc.container

    # --- PACKAGECONFIG mqtt-auth -------------------------------------------
    if ${@bb.utils.contains('PACKAGECONFIG', 'mqtt-auth', 'true', 'false', d)}; then
        a=${UNPACKDIR}/mqtt-auth
        install -m 0644 $a/mosquitto.conf ${D}${GWDIR}/mosquitto.conf
        if [ "${WEB}" = caddy ]; then
            install -m 0644 $a/Caddyfile    ${D}${GWDIR}/Caddyfile
        else
            install -m 0644 $a/default.conf ${D}${GWDIR}/default.conf
        fi
        install -m 0644 $a/mosquitto.acl  ${D}${GWDIR}/mosquitto.acl
        for unit in mosquitto ${WEB} dataproc; do
            install -d ${D}${sysconfdir}/containers/systemd/iot-$unit.container.d
            install -m 0644 $a/$unit-auth.conf \
                ${D}${sysconfdir}/containers/systemd/iot-$unit.container.d/mqtt-auth.conf
        done
        install -D -m 0755 $a/iot-gateway-secrets ${D}${libexecdir}/iot-gateway-secrets
        install -D -m 0644 $a/iot-gateway-secrets.service \
            ${D}${systemd_system_unitdir}/iot-gateway-secrets.service
    fi
}

FILES:${PN} = " \
    ${GWDIR} \
    ${sysconfdir}/containers/systemd \
    ${libexecdir}/iot-gateway-secrets \
    ${systemd_system_unitdir}/iot-gateway-secrets.service \
"

# Pure-python payload, not for the host's python — skip host dep scanning.
INSANE_SKIP:${PN} += "file-rdeps"

# The bundle's images are imported into podman storage at build time by
# container-cross-install in the image; the Quadlets here run them.
RDEPENDS:${PN} = "iot-gateway-bundle podman"

python () {
    if d.getVar('IOT_GATEWAY_WEBSERVER') not in ('nginx', 'caddy'):
        bb.fatal("IOT_GATEWAY_WEBSERVER must be nginx or caddy, not %r" % d.getVar('IOT_GATEWAY_WEBSERVER'))
}
