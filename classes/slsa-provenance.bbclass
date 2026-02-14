#
# Generates SLSA Build L2 v1.0 provenance attestation for image builds.
#
# The provenance is an in-toto Statement v1 JSON document with a SLSA
# Provenance v1 predicate, written as a sidecar file next to image
# artifacts in DEPLOY_DIR_IMAGE.
#
# Usage: add INHERIT += "slsa-provenance" to your conf file
#
# Copyright Konsulko Group
#
# SPDX-License-Identifier: MIT
#

# === Configuration Variables ===

# URI identifying the build platform. CI systems should override this.
SLSA_PROVENANCE_BUILDER_ID ??= "https://openembedded.org/local-build"
SLSA_PROVENANCE_BUILDER_ID[doc] = "URI identifying the build platform for SLSA \
    provenance. Set this to your CI system's identity URI."

# URI identifying the build template/type.
SLSA_PROVENANCE_BUILD_TYPE ??= "https://openembedded.org/slsa/image-build/v1"
SLSA_PROVENANCE_BUILD_TYPE[doc] = "URI identifying the build process template."

# Whether to include timestamps. Enabling makes output non-reproducible.
SLSA_PROVENANCE_INCLUDE_TIMESTAMPS ??= "0"
SLSA_PROVENANCE_INCLUDE_TIMESTAMPS[doc] = "If set to '1', build timestamps \
    are included in the provenance metadata. This makes the output \
    non-reproducible across builds."

# Optional invocation ID (e.g. CI job URL or run ID)
SLSA_PROVENANCE_INVOCATION_ID ??= ""
SLSA_PROVENANCE_INVOCATION_ID[doc] = "Unique identifier for this build invocation. \
    Typically a CI job URL or run ID."

# Pretty-print the JSON output
SLSA_PROVENANCE_PRETTY ??= "0"

# === Deploy directories ===

DEPLOY_DIR_SLSA ??= "${DEPLOY_DIR}/slsa"
SLSA_DIR ??= "${WORKDIR}/slsa"
SLSA_DEPLOY = "${SLSA_DIR}/deploy"

# === File checksum dependencies ===

SLSA_DEP_FILES = "\
    ${COREBASE}/meta/lib/oe/slsa.py:True \
    ${COREBASE}/meta/lib/oe/slsa_tasks.py:True \
    "

# === Per-recipe source collection task ===

python do_collect_slsa_sources() {
    import oe.slsa_tasks
    oe.slsa_tasks.collect_recipe_sources(d)
}

addtask do_collect_slsa_sources after do_fetch before do_build do_rm_work

SSTATETASKS += "do_collect_slsa_sources"
do_collect_slsa_sources[sstate-inputdirs] = "${SLSA_DEPLOY}"
do_collect_slsa_sources[sstate-outputdirs] = "${DEPLOY_DIR_SLSA}"
do_collect_slsa_sources[dirs] = "${SLSA_DIR}"
do_collect_slsa_sources[cleandirs] = "${SLSA_DEPLOY}"
do_collect_slsa_sources[file-checksums] += "${SLSA_DEP_FILES}"

python do_collect_slsa_sources_setscene() {
    sstate_setscene(d)
}
addtask do_collect_slsa_sources_setscene

# === Image class ===

IMAGE_CLASSES:append = " slsa-provenance-image"
