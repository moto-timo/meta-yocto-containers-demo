#
# Copyright Konsulko Group
#
# SPDX-License-Identifier: MIT
#
# SLSA provenance task implementation
#

import json
import os

import bb.fetch2
import bb.utils
import oe.buildcfg
import oe.slsa
import oe.packagedata

from pathlib import Path


def collect_recipe_sources(d):
    """
    Collect resolved source URIs and digests for the current recipe.
    Called per-recipe during do_collect_slsa_sources. Writes a JSON file
    with an array of source descriptors.
    """
    import oe.spdx_common

    pn = d.getVar("PN")
    src_uri = d.getVar("SRC_URI")
    if not src_uri:
        return

    urls = src_uri.split()
    if not urls:
        return

    sources = []

    try:
        fetch = bb.fetch2.Fetch(urls, d)
    except bb.fetch2.BBFetchException as e:
        bb.warn("SLSA provenance: unable to create fetcher for %s: %s" % (pn, str(e)))
        return

    for src_uri_str in urls:
        fd = fetch.ud[src_uri_str]

        # Skip local file:// sources (patches, config fragments, etc.)
        if fd.type == "file":
            continue

        entry = {
            "name": pn,
        }

        # Get normalized URI
        try:
            entry["uri"] = oe.spdx_common.fetch_data_to_uri(fd, fd.name)
        except Exception:
            # Fall back to raw URI without parameters
            entry["uri"] = src_uri_str.split(";")[0]

        # Collect digests
        digest = {}
        if fd.method.supports_srcrev():
            revision = getattr(fd, "revision", None)
            if revision and revision not in ("INVALID", "AUTOINC"):
                digest["gitCommit"] = revision

        if fd.method.supports_checksum(fd):
            sha256 = getattr(fd, "sha256_expected", None)
            if sha256:
                digest["sha256"] = sha256

        if digest:
            entry["digest"] = digest

        sources.append(entry)

    if not sources:
        return

    deploy_dir = d.getVar("SLSA_DEPLOY")
    bb.utils.mkdirhier(deploy_dir)

    output_path = os.path.join(deploy_dir, "sources-%s.json" % pn)
    with open(output_path, "w") as f:
        json.dump(sources, f)


def collect_image_subjects(d):
    """
    Read the IMAGE_OUTPUT_MANIFEST and compute sha256 digests
    for each image artifact. Returns a list of ResourceDescriptor.
    """
    manifest_path = d.getVar("IMAGE_OUTPUT_MANIFEST")
    image_deploy_dir = d.getVar("IMGDEPLOYDIR")
    subjects = []

    if not manifest_path or not os.path.exists(manifest_path):
        bb.warn("SLSA provenance: IMAGE_OUTPUT_MANIFEST not found: %s" % manifest_path)
        return subjects

    with open(manifest_path, "r") as f:
        manifest = json.load(f)

    for task_entry in manifest:
        for image_info in task_entry.get("images", []):
            filename = image_info["filename"]
            filepath = os.path.join(image_deploy_dir, filename)

            if not os.path.exists(filepath):
                bb.warn("SLSA provenance: image file not found: %s" % filepath)
                continue

            if os.path.isdir(filepath):
                bb.debug(1, "SLSA provenance: skipping directory artifact: %s" % filename)
                continue

            sha256 = bb.utils.sha256_file(filepath)
            subjects.append(oe.slsa.ResourceDescriptor(
                name=filename,
                digest={"sha256": sha256},
            ))

    return subjects


def collect_layer_dependencies(d):
    """
    Collect OE/Yocto layer revisions as resolvedDependencies.
    Each layer becomes a ResourceDescriptor with its git commit as digest
    and the remote URL (if available) as the URI.
    """
    deps = []
    revisions = oe.buildcfg.get_layer_revisions(d)

    for layer_path, layer_name, branch, revision, modified in revisions:
        digest = {}
        uri = None
        annotations = {}

        if revision and revision != "<unknown>":
            digest["gitCommit"] = revision

        # Try to get the remote URL for this layer
        remotes = oe.buildcfg.get_metadata_git_remotes(layer_path)
        if remotes:
            remote_name = "origin" if "origin" in remotes else remotes[0]
            remote_url = oe.buildcfg.get_metadata_git_remote_url(
                layer_path, remote_name
            )
            if remote_url:
                uri = remote_url

        if branch and branch != "<unknown>":
            annotations["branch"] = branch

        if modified:  # non-empty string means layer has uncommitted changes
            annotations["modified"] = True

        dep = oe.slsa.ResourceDescriptor(
            name=layer_name,
            digest=digest,
            uri=uri,
            annotations=annotations if annotations else None,
        )
        deps.append(dep)

    return deps


def collect_recipe_source_dependencies(d):
    """
    Collect per-recipe source metadata from the JSON files written by
    do_collect_slsa_sources. Maps installed packages to recipes and reads
    each recipe's source descriptor.
    """
    deps = []
    seen_recipes = set()

    rootfs_packages_file = d.getVar("SLSA_ROOTFS_PACKAGES")
    if not rootfs_packages_file or not os.path.exists(rootfs_packages_file):
        bb.warn("SLSA provenance: rootfs packages file not found, "
                "skipping recipe source collection")
        return deps

    with open(rootfs_packages_file, "r") as f:
        packages = json.load(f)

    if not packages:
        return deps

    deploy_dir_slsa = d.getVar("DEPLOY_DIR_SLSA")
    if not deploy_dir_slsa:
        return deps

    pkg_map = oe.packagedata.pkgmap(d)

    for pkg in sorted(packages.keys() if isinstance(packages, dict) else packages):
        recipe = pkg_map.get(pkg) or oe.packagedata.recipename(pkg, d)
        if not recipe or recipe in seen_recipes:
            continue
        seen_recipes.add(recipe)

        # Look for the source descriptor JSON written by do_collect_slsa_sources
        # The files are organized by architecture under DEPLOY_DIR_SLSA
        source_file = _find_recipe_sources_file(deploy_dir_slsa, recipe)
        if not source_file:
            continue

        try:
            with open(source_file, "r") as f:
                sources = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            bb.debug(1, "SLSA provenance: error reading %s: %s" % (source_file, str(e)))
            continue

        for src in sources:
            dep = oe.slsa.ResourceDescriptor(
                name=src.get("name", recipe),
                uri=src.get("uri"),
                digest=src.get("digest", {}),
            )
            deps.append(dep)

    return deps


def _find_recipe_sources_file(deploy_dir_slsa, recipe):
    """
    Search for the sources-<recipe>.json file under DEPLOY_DIR_SLSA.
    The sstate mechanism places files under architecture subdirectories.
    """
    deploy_path = Path(deploy_dir_slsa)
    if not deploy_path.exists():
        return None

    # Direct location (no arch subdirs)
    direct = deploy_path / ("sources-%s.json" % recipe)
    if direct.exists():
        return str(direct)

    # Search recursively under arch subdirs
    for match in deploy_path.rglob("sources-%s.json" % recipe):
        return str(match)

    return None


def collect_external_parameters(d):
    """
    Collect user-controlled external build parameters.
    """
    params = {}

    params["image"] = d.getVar("IMAGE_BASENAME") or ""
    params["machine"] = d.getVar("MACHINE") or ""
    params["distro"] = d.getVar("DISTRO") or ""
    params["distro_version"] = d.getVar("DISTRO_VERSION") or ""

    image_features = d.getVar("IMAGE_FEATURES") or ""
    if image_features.strip():
        params["image_features"] = image_features.split()

    image_install = d.getVar("IMAGE_INSTALL") or ""
    if image_install.strip():
        params["image_install"] = image_install.split()

    image_fstypes = d.getVar("IMAGE_FSTYPES") or ""
    if image_fstypes.strip():
        params["image_fstypes"] = image_fstypes.split()

    return params


def collect_internal_parameters(d):
    """
    Collect builder-controlled internal parameters relevant for reproducibility.
    """
    params = {}

    for var in ("TCLIBC", "TARGET_ARCH", "TARGET_OS", "TUNE_PKGARCH"):
        val = d.getVar(var)
        if val:
            params[var.lower()] = val

    return params


def create_image_provenance(d):
    """
    Main entry point: generates the SLSA provenance in-toto statement
    for an image build.
    """
    image_name = d.getVar("IMAGE_NAME")
    image_link_name = d.getVar("IMAGE_LINK_NAME")
    provenance_deploy_dir = d.getVar("SLSA_PROVENANCE_DEPLOY_DIR")

    # 1. Collect subjects (image artifacts with sha256)
    subjects = collect_image_subjects(d)

    if not subjects:
        bb.warn("SLSA provenance: no image subjects found, "
                "skipping provenance generation")
        return

    # 2. Collect resolvedDependencies
    resolved_deps = collect_layer_dependencies(d)
    resolved_deps.extend(collect_recipe_source_dependencies(d))

    # 3. Build the provenance
    build_type = d.getVar("SLSA_PROVENANCE_BUILD_TYPE") or oe.slsa.OE_BUILD_TYPE
    builder_id = d.getVar("SLSA_PROVENANCE_BUILDER_ID") or \
        "https://openembedded.org/local-build"

    build_def = oe.slsa.BuildDefinition(
        buildType=build_type,
        externalParameters=collect_external_parameters(d),
        internalParameters=collect_internal_parameters(d),
        resolvedDependencies=resolved_deps,
    )

    # Build metadata
    metadata = oe.slsa.BuildMetadata()
    has_metadata = False

    if d.getVar("SLSA_PROVENANCE_INCLUDE_TIMESTAMPS") == "1":
        metadata.finishedOn = oe.slsa.now_rfc3339()
        has_metadata = True

    invocation_id = d.getVar("SLSA_PROVENANCE_INVOCATION_ID")
    if invocation_id:
        metadata.invocationId = invocation_id
        has_metadata = True

    builder = oe.slsa.Builder(id=builder_id)

    run_details = oe.slsa.RunDetails(
        builder=builder,
        metadata=metadata if has_metadata else None,
    )

    provenance = oe.slsa.SLSAProvenance(
        buildDefinition=build_def,
        runDetails=run_details,
    )

    statement = oe.slsa.InTotoStatement(
        subject=subjects,
        predicate=provenance,
    )

    # 4. Write the provenance file
    bb.utils.mkdirhier(provenance_deploy_dir)

    provenance_filename = "%s.slsa-build.json" % image_name
    provenance_path = os.path.join(provenance_deploy_dir, provenance_filename)

    pretty = d.getVar("SLSA_PROVENANCE_PRETTY") == "1"
    indent = 2 if pretty else None

    with open(provenance_path, "w") as f:
        json.dump(statement.to_dict(), f, indent=indent, sort_keys=False)

    bb.note("SLSA provenance written to: %s" % provenance_path)

    # 5. Create symlink with IMAGE_LINK_NAME
    if image_link_name:
        link_name = "%s.slsa-build.json" % image_link_name
        link_path = os.path.join(provenance_deploy_dir, link_name)
        if os.path.islink(link_path) or os.path.exists(link_path):
            os.remove(link_path)
        if link_path != provenance_path:
            os.symlink(
                os.path.relpath(provenance_path, os.path.dirname(link_path)),
                link_path,
            )
