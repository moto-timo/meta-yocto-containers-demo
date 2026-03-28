SUMMARY = "A comprehensive and versatile security scanner"
DESCRIPTION = "Trivy is a comprehensive security scanner for vulnerabilities, \
misconfigurations, secrets, and SBOM in containers, Kubernetes, code \
repositories, clouds, and more."
HOMEPAGE = "https://github.com/aquasecurity/trivy"
LICENSE = "Apache-2.0"
LIC_FILES_CHKSUM = "file://src/${GO_IMPORT}/LICENSE;md5=3b83ef96387f14655fc854ddc3c6bd57"

GO_IMPORT = "github.com/aquasecurity/trivy"
GO_INSTALL = "${GO_IMPORT}/cmd/trivy"
SRC_URI = "git://${GO_IMPORT};protocol=https;nobranch=1;destsuffix=${GO_SRCURI_DESTSUFFIX}"
PV = "0.69.3+git"
SRCREV = "6fb20c8edd70745d6b34bff0387b53b03c8a760a"

require ${BPN}-licenses.inc
require ${BPN}-go-mods.inc

inherit go-mod go-mod-update-modules

CGO_ENABLED = "0"

export GOEXPERIMENT = "jsonv2"

GO_EXTRA_LDFLAGS = "-s -w -X ${GO_IMPORT}/pkg/version/app.ver=${PV}"

BBCLASSEXTEND = "native nativesdk"
