#!/bin/sh
# First-boot import of the bundled upstream OCI images into podman storage.
# Reads the container-bundle payload the iot-gateway-bundle package left in the
# rootfs and imports each image under its short ref (e.g. localhost/nginx:1.30).
set -e

BASE=/usr/share/container-bundles
MARKER=/var/lib/iot-gateway/.imported

[ -f "$MARKER" ] && exit 0

# The bundle stores OCI dirs under a runtime subdir (docker/ or podman/,
# depending on CONTAINER_PROFILE). The OCI layout is identical either way and
# we import with native skopeo, so just take whichever refs file(s) exist.
found=0
for refs in "$BASE"/*/*.refs; do
    [ -f "$refs" ] || continue
    found=1
    rt_dir=$(dirname "$refs")
    # Each line: <oci_dir_name>:<image>:<tag>   e.g.  nginx_1.30:nginx:1.30
    while IFS=: read -r oci_name image_ref; do
        [ -z "$oci_name" ] && continue
        dir="$rt_dir/oci/$oci_name"
        [ -d "$dir" ] || continue
        echo "iot-image-import: $dir -> $image_ref"
        skopeo copy "oci:$dir" "containers-storage:$image_ref"
    done < "$refs"
done

if [ "$found" -eq 0 ]; then
    echo "iot-image-import: no bundle payload under $BASE" >&2
    exit 0
fi

mkdir -p "$(dirname "$MARKER")"
touch "$MARKER"
echo "iot-image-import: done"
