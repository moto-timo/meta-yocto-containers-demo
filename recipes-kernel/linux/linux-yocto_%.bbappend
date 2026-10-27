FILESEXTRAPATHS:prepend := "${THISDIR}/linux-yocto:"

SRC_URI:append:aarch64 = " file://rtc-efi.cfg"
