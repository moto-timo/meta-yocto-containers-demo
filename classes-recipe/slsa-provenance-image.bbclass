#
# SLSA provenance image tasks
#
# Copyright Konsulko Group
#
# SPDX-License-Identifier: MIT
#

# Per-task staging directories for provenance files.
#
# Each provenance task MUST have its own isolated staging directory so
# that sstate can track ownership of output files independently.  Using
# a single shared directory causes "files already exist in manifest"
# sstate conflicts when any two of the three tasks run concurrently
# (they all schedule after do_image_complete with no mutual dependency).
#
# slsa_tasks.py reads SLSA_PROVENANCE_DEPLOY_DIR; each task body calls
# d.setVar() to point that variable at its own staging dir before
# invoking the library function.
SLSA_BUILD_PROV_STAGEDIR = "${WORKDIR}/slsa-build-stage"
SLSA_SOURCE_PROV_STAGEDIR = "${WORKDIR}/slsa-source-stage"
SLSA_DEPS_PROV_STAGEDIR = "${WORKDIR}/slsa-deps-stage"

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
    slsa_ensure_oe_path(d)
    d.setVar("SLSA_PROVENANCE_DEPLOY_DIR", d.getVar("SLSA_BUILD_PROV_STAGEDIR"))
    import oe.slsa_tasks
    oe.slsa_tasks.create_image_provenance(d)
}

addtask do_create_slsa_provenance after do_image_complete before do_build

SSTATETASKS += "do_create_slsa_provenance"
SSTATE_SKIP_CREATION:task-create-slsa-provenance = "1"
do_create_slsa_provenance[sstate-inputdirs] = "${SLSA_BUILD_PROV_STAGEDIR}"
do_create_slsa_provenance[sstate-outputdirs] = "${DEPLOY_DIR_SLSA}"
do_create_slsa_provenance[stamp-extra-info] = "${MACHINE_ARCH}"
do_create_slsa_provenance[cleandirs] = "${SLSA_BUILD_PROV_STAGEDIR}"
do_create_slsa_provenance[dirs] = "${SLSA_BUILD_PROV_STAGEDIR}"
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

# === Source provenance task (SLSA Build L3) ===
# Generates a separate slsa.dev/source_provenance/v1 attestation whose
# subjects are the layer git commits used in this build.  This satisfies
# the L3 requirement for a complete, signed source record that is
# independent of the build provenance.

python do_create_slsa_source_provenance() {
    slsa_ensure_oe_path(d)
    d.setVar("SLSA_PROVENANCE_DEPLOY_DIR", d.getVar("SLSA_SOURCE_PROV_STAGEDIR"))
    import oe.slsa_tasks
    oe.slsa_tasks.create_image_source_provenance(d)
}

addtask do_create_slsa_source_provenance after do_image_complete before do_build

SSTATETASKS += "do_create_slsa_source_provenance"
SSTATE_SKIP_CREATION:task-create-slsa-source-provenance = "1"
do_create_slsa_source_provenance[sstate-inputdirs] = "${SLSA_SOURCE_PROV_STAGEDIR}"
do_create_slsa_source_provenance[sstate-outputdirs] = "${DEPLOY_DIR_SLSA}"
do_create_slsa_source_provenance[stamp-extra-info] = "${MACHINE_ARCH}"
do_create_slsa_source_provenance[cleandirs] = "${SLSA_SOURCE_PROV_STAGEDIR}"
do_create_slsa_source_provenance[dirs] = "${SLSA_SOURCE_PROV_STAGEDIR}"
do_create_slsa_source_provenance[file-checksums] += "${SLSA_DEP_FILES}"
do_create_slsa_source_provenance[vardeps] += "\
    SLSA_PROVENANCE_BUILDER_ID \
    SLSA_PROVENANCE_BUILD_TYPE \
    SLSA_PROVENANCE_INVOCATION_ID \
    "

python do_create_slsa_source_provenance_setscene() {
    sstate_setscene(d)
}
addtask do_create_slsa_source_provenance_setscene

# === Dependency provenance task (SLSA Build L3) ===
# Generates an in-toto Link attestation (in-toto.io/attestation/link/v0.3)
# recording every layer revision and resolved recipe source URI consumed by
# the build.  The image artifacts are the statement subjects, so the signed
# dependency manifest is cryptographically bound to the produced container.

python do_create_slsa_deps_provenance() {
    slsa_ensure_oe_path(d)
    d.setVar("SLSA_PROVENANCE_DEPLOY_DIR", d.getVar("SLSA_DEPS_PROV_STAGEDIR"))
    import oe.slsa_tasks
    oe.slsa_tasks.create_image_deps_provenance(d)
}

addtask do_create_slsa_deps_provenance after do_image_complete before do_build

SSTATETASKS += "do_create_slsa_deps_provenance"
SSTATE_SKIP_CREATION:task-create-slsa-deps-provenance = "1"
do_create_slsa_deps_provenance[sstate-inputdirs] = "${SLSA_DEPS_PROV_STAGEDIR}"
do_create_slsa_deps_provenance[sstate-outputdirs] = "${DEPLOY_DIR_SLSA}"
do_create_slsa_deps_provenance[stamp-extra-info] = "${MACHINE_ARCH}"
do_create_slsa_deps_provenance[cleandirs] = "${SLSA_DEPS_PROV_STAGEDIR}"
do_create_slsa_deps_provenance[dirs] = "${SLSA_DEPS_PROV_STAGEDIR}"
do_create_slsa_deps_provenance[recrdeptask] += "do_collect_slsa_sources"
do_create_slsa_deps_provenance[file-checksums] += "${SLSA_DEP_FILES}"
do_create_slsa_deps_provenance[vardeps] += "\
    SLSA_PROVENANCE_BUILD_TYPE \
    "

python do_create_slsa_deps_provenance_setscene() {
    sstate_setscene(d)
}
addtask do_create_slsa_deps_provenance_setscene
