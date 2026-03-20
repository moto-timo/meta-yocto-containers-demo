#
# SLSA provenance image tasks
#
# Copyright Konsulko Group
#
# SPDX-License-Identifier: MIT
#

# Deploy directory for provenance files (separate from IMGDEPLOYDIR to
# avoid sstate conflicts with do_image_complete)
SLSA_PROVENANCE_DEPLOY_DIR = "${WORKDIR}/slsa-deploy"

# Saved rootfs package list for recipe source mapping
SLSA_ROOTFS_PACKAGES = "${SLSA_DIR}/rootfs-packages.json"

# === Collect installed packages list during rootfs creation ===
# Save the package list while packaging metadata is still available.

python slsa_collect_rootfs_packages() {
    import json
    from pathlib import Path
    from oe.rootfs import image_list_installed_packages

    root_packages_file = Path(d.getVar("SLSA_ROOTFS_PACKAGES"))

    packages = image_list_installed_packages(d)
    if not packages:
        packages = {}

    root_packages_file.parent.mkdir(parents=True, exist_ok=True)
    with root_packages_file.open("w") as f:
        json.dump(packages, f)
}

ROOTFS_POSTUNINSTALL_COMMAND =+ "slsa_collect_rootfs_packages"
ROOTFS_POSTUNINSTALL_COMMAND[vardepvalueexclude] .= "| slsa_collect_rootfs_packages"
ROOTFS_POSTUNINSTALL_COMMAND[vardepsexclude] += "slsa_collect_rootfs_packages"

# === Main provenance generation task ===

python do_create_slsa_provenance() {
    import oe.slsa_tasks
    oe.slsa_tasks.create_image_provenance(d)
}

addtask do_create_slsa_provenance after do_image_complete before do_build

SSTATETASKS += "do_create_slsa_provenance"
SSTATE_SKIP_CREATION:task-create-slsa-provenance = "1"
do_create_slsa_provenance[sstate-inputdirs] = "${SLSA_PROVENANCE_DEPLOY_DIR}"
do_create_slsa_provenance[sstate-outputdirs] = "${DEPLOY_DIR_SLSA}"
do_create_slsa_provenance[stamp-extra-info] = "${MACHINE_ARCH}"
do_create_slsa_provenance[cleandirs] = "${SLSA_PROVENANCE_DEPLOY_DIR}"
do_create_slsa_provenance[dirs] = "${SLSA_PROVENANCE_DEPLOY_DIR}"
do_create_slsa_provenance[recrdeptask] += "do_collect_slsa_sources"
do_create_slsa_provenance[file-checksums] += "${SLSA_DEP_FILES}"
do_create_slsa_provenance[vardeps] += "\
    SLSA_PROVENANCE_BUILDER_ID \
    SLSA_PROVENANCE_BUILD_TYPE \
    SLSA_PROVENANCE_INCLUDE_TIMESTAMPS \
    SLSA_PROVENANCE_INVOCATION_ID \
    "

python do_create_slsa_provenance_setscene() {
    sstate_setscene(d)
}
addtask do_create_slsa_provenance_setscene
