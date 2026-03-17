SUMMARY = "Base python3 container image for development"
DESCRIPTION = "Python3 base image with 'pip' to allow developers to simply \
run 'pip install' on top of this container.\
Not advised for production/hardened use."
LICENSE = "MIT"

OCI_LAYER_MODE = "multi"
OCI_LAYERS = "\
    base:packages:base-files+base-passwd+netbase \
    python:packages:python3+python3-pip \
"
IMAGE_INSTALL = "base-files base-passwd netbase python3 python3-pip"

