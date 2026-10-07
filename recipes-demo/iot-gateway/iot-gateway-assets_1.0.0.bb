SUMMARY = "IoT Edge Gateway config overlays, dashboard, app + Quadlet units"
DESCRIPTION = "Runtime overlay assets for the upstream reference containers: \
mosquitto.conf, the dashboard index.html, the sensor-processor app (plus a \
vendored pure-python paho-mqtt), and the Podman Quadlet units that bind-mount \
them into the stock mosquitto/nginx/python containers."
LICENSE = "MIT"
LIC_FILES_CHKSUM = "file://${COREBASE}/meta/COPYING.MIT;md5=3da9cfbcb788c80a0384361b4de20420"

SRC_URI = " \
    file://mosquitto.conf \
    file://index.html \
    file://default.conf \
    file://nginx.conf \
    file://sensor-processor.py \
    file://mosquitto.container \
    file://nginx.container \
    file://dataproc.container \
    file://iot-image-import.sh \
    file://iot-image-import.service \
    https://files.pythonhosted.org/packages/39/15/0a6214e76d4d32e7f663b109cf71fb22561c2be0f701d67f93950cd40542/paho_mqtt-2.1.0.tar.gz;name=paho \
"
SRC_URI[paho.sha256sum] = "12d6e7511d4137555a3f6ea167ae846af2c7357b10bc6fa4f7c3968fc1723834"

S = "${UNPACKDIR}"

inherit systemd
SYSTEMD_SERVICE:${PN} = "iot-image-import.service"
SYSTEMD_AUTO_ENABLE:${PN} = "enable"

GWDIR = "${datadir}/iot-gateway"

do_install() {
    # --- Overlay config + dashboard --------------------------------------
    install -d ${D}${GWDIR}
    install -m 0644 ${UNPACKDIR}/mosquitto.conf ${D}${GWDIR}/mosquitto.conf
    install -m 0644 ${UNPACKDIR}/index.html     ${D}${GWDIR}/index.html
    install -m 0644 ${UNPACKDIR}/default.conf   ${D}${GWDIR}/default.conf
    install -m 0644 ${UNPACKDIR}/nginx.conf     ${D}${GWDIR}/nginx.conf

    # --- Sensor app + vendored pure-python paho-mqtt ---------------------
    install -d ${D}${GWDIR}/app
    install -m 0644 ${UNPACKDIR}/sensor-processor.py ${D}${GWDIR}/app/sensor-processor.py
    cp -R --no-preserve=ownership,mode ${UNPACKDIR}/paho_mqtt-2.1.0/src/paho ${D}${GWDIR}/app/paho
    chmod -R u+rwX,go+rX ${D}${GWDIR}/app/paho

    # --- First-boot image import (native skopeo) -------------------------
    install -d ${D}${bindir}
    install -m 0755 ${UNPACKDIR}/iot-image-import.sh ${D}${bindir}/iot-image-import.sh
    install -d ${D}${systemd_system_unitdir}
    install -m 0644 ${UNPACKDIR}/iot-image-import.service \
        ${D}${systemd_system_unitdir}/iot-image-import.service
    install -d ${D}${localstatedir}/lib/iot-gateway

    # --- Podman Quadlet units --------------------------------------------
    install -d ${D}${sysconfdir}/containers/systemd
    install -m 0644 ${UNPACKDIR}/mosquitto.container ${D}${sysconfdir}/containers/systemd/iot-mosquitto.container
    install -m 0644 ${UNPACKDIR}/nginx.container     ${D}${sysconfdir}/containers/systemd/iot-nginx.container
    install -m 0644 ${UNPACKDIR}/dataproc.container  ${D}${sysconfdir}/containers/systemd/iot-dataproc.container
}

FILES:${PN} = " \
    ${GWDIR} \
    ${bindir}/iot-image-import.sh \
    ${systemd_system_unitdir}/iot-image-import.service \
    ${localstatedir}/lib/iot-gateway \
    ${sysconfdir}/containers/systemd \
"

# Pure-python payload, not for the host's python — skip host dep scanning.
INSANE_SKIP:${PN} += "file-rdeps"

# Bundle provides the OCI payload; skopeo/podman perform the first-boot import.
RDEPENDS:${PN} = "iot-gateway-bundle skopeo podman"
