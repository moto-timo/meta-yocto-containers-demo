SUMMARY = "A vulnerability scanner for container images and filesystems"
DESCRIPTION = "Grype is a vulnerability scanner for container images and \
filesystems. It scans container images, filesystems, and SBOMs for known \
vulnerabilities using multiple vulnerability database sources."
HOMEPAGE = "https://github.com/anchore/grype"
LICENSE = "Apache-2.0"
LIC_FILES_CHKSUM = "file://src/${GO_IMPORT}/LICENSE;md5=86d3f3a95c324c9479bd8986968f4327"

GO_IMPORT = "github.com/anchore/grype"
GO_INSTALL = "${GO_IMPORT}/cmd/grype"
SRC_URI = "git://${GO_IMPORT};protocol=https;nobranch=1;destsuffix=${GO_SRCURI_DESTSUFFIX}"
PV = "0.121.0"
SRCREV = "afe2742527d98d822da06c9f32eed86fe3d193e0"

require ${BPN}-licenses.inc
require ${BPN}-go-mods.inc

inherit go-mod go-mod-update-modules

CGO_ENABLED = "0"
# -linkshared needs cgo, so link statically on every architecture
GO_LINKSHARED = ""

GO_EXTRA_LDFLAGS = "-X main.version=${PV}"

BBCLASSEXTEND = "native nativesdk"
