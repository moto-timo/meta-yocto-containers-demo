SUMMARY = "A comprehensive and versatile security scanner"
DESCRIPTION = "Trivy is a comprehensive security scanner for vulnerabilities, \
misconfigurations, secrets, and SBOM in containers, Kubernetes, code \
repositories, clouds, and more."
HOMEPAGE = "https://github.com/aquasecurity/trivy"
LICENSE = "Apache-2.0"
LIC_FILES_CHKSUM = "file://src/${GO_IMPORT}/LICENSE;md5=86d3f3a95c324c9479bd8986968f4327"

GO_IMPORT = "github.com/aquasecurity/trivy"
GO_INSTALL = "${GO_IMPORT}/cmd/trivy"
SRC_URI = "git://${GO_IMPORT};protocol=https;nobranch=1;destsuffix=${GO_SRCURI_DESTSUFFIX}"
PV = "0.76.1"
SRCREV = "e713f67f7d54decdcd9b3132c9751833dcced698"

require ${BPN}-licenses.inc
require ${BPN}-go-mods.inc

inherit go-mod go-mod-update-modules

CGO_ENABLED = "0"
# -linkshared needs cgo, so link statically on every architecture
GO_LINKSHARED = ""

export GOEXPERIMENT = "jsonv2"

GO_EXTRA_LDFLAGS = "-X ${GO_IMPORT}/pkg/version/app.ver=${PV}"

BBCLASSEXTEND = "native nativesdk"

# The sources in ${PN}-dev include bash scripts
RDEPENDS:${PN}-dev += "bash"
