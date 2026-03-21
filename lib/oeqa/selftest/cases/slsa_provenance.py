#
# Copyright Konsulko Group
#
# SPDX-License-Identifier: MIT
#

import json
import os
import textwrap
from oeqa.selftest.case import OESelftestTestCase
from oeqa.utils.commands import bitbake, get_bb_vars


class SLSAProvenanceBase(object):
    """Base class for SLSA provenance tests."""

    def _get_config(self, extra=""):
        return textwrap.dedent("""\
            INHERIT += "slsa-provenance"
            SLSA_PROVENANCE_PRETTY = "1"
        """) + textwrap.dedent(extra)

    def _build_and_get_build_provenance(self, target="core-image-minimal", extra_conf=""):
        self.write_config(self._get_config(extra_conf))
        bitbake(target)

        bb_vars = get_bb_vars(
            ["DEPLOY_DIR_SLSA", "IMAGE_LINK_NAME"],
            target,
        )
        deploy_dir = bb_vars["DEPLOY_DIR_SLSA"]
        link_name = bb_vars["IMAGE_LINK_NAME"]

        provenance_path = os.path.join(
            deploy_dir, link_name + ".slsa-build.json"
        )
        self.assertExists(provenance_path)

        with open(provenance_path, "r") as f:
            return json.load(f)

    # Backward-compatible alias used by existing tests
    _build_and_get_provenance = _build_and_get_build_provenance

    def _get_source_provenance(self, target="core-image-minimal", extra_conf=""):
        self.write_config(self._get_config(extra_conf))
        bitbake(target)

        bb_vars = get_bb_vars(
            ["DEPLOY_DIR_SLSA", "IMAGE_LINK_NAME"],
            target,
        )
        deploy_dir = bb_vars["DEPLOY_DIR_SLSA"]
        link_name = bb_vars["IMAGE_LINK_NAME"]

        source_path = os.path.join(
            deploy_dir, link_name + ".slsa-source.json"
        )
        self.assertExists(source_path)

        with open(source_path, "r") as f:
            return json.load(f)


class SLSAProvenanceTest(SLSAProvenanceBase, OESelftestTestCase):

    def test_provenance_basic_structure(self):
        """Verify in-toto Statement v1 structure."""
        stmt = self._build_and_get_provenance()

        self.assertEqual(stmt["_type"], "https://in-toto.io/Statement/v1")
        self.assertEqual(stmt["predicateType"], "https://slsa.dev/provenance/v1")
        self.assertIn("subject", stmt)
        self.assertIn("predicate", stmt)
        self.assertIn("buildDefinition", stmt["predicate"])
        self.assertIn("runDetails", stmt["predicate"])

    def test_provenance_subjects_have_sha256(self):
        """Every subject must have a name and sha256 digest."""
        stmt = self._build_and_get_provenance()

        self.assertTrue(len(stmt["subject"]) > 0, "Must have at least one subject")
        for subject in stmt["subject"]:
            self.assertIn("name", subject)
            self.assertIn("digest", subject)
            self.assertIn("sha256", subject["digest"])
            # sha256 hex digest is 64 characters
            self.assertEqual(len(subject["digest"]["sha256"]), 64)

    def test_provenance_build_definition(self):
        """Verify buildDefinition has required fields."""
        stmt = self._build_and_get_provenance()
        build_def = stmt["predicate"]["buildDefinition"]

        self.assertIn("buildType", build_def)
        self.assertEqual(
            build_def["buildType"],
            "https://openembedded.org/slsa/image-build/v1",
        )
        self.assertIn("externalParameters", build_def)

        ext_params = build_def["externalParameters"]
        self.assertIn("image", ext_params)
        self.assertIn("machine", ext_params)
        self.assertIn("distro", ext_params)

    def test_provenance_resolved_dependencies_layers(self):
        """Verify layer revisions appear in resolvedDependencies."""
        stmt = self._build_and_get_provenance()
        build_def = stmt["predicate"]["buildDefinition"]

        self.assertIn("resolvedDependencies", build_def)
        deps = build_def["resolvedDependencies"]
        self.assertTrue(len(deps) > 0, "Must have at least one dependency")

        # At minimum, the meta layer should be present
        layer_names = [d["name"] for d in deps]
        self.assertIn("meta", layer_names)

        # Layer entries should have gitCommit digests
        meta_dep = next(d for d in deps if d["name"] == "meta")
        self.assertIn("digest", meta_dep)
        self.assertIn("gitCommit", meta_dep["digest"])
        # Git commit is 40-char hex
        self.assertEqual(len(meta_dep["digest"]["gitCommit"]), 40)

    def test_provenance_builder_id_default(self):
        """Verify default builder ID."""
        stmt = self._build_and_get_provenance()
        builder = stmt["predicate"]["runDetails"]["builder"]
        self.assertEqual(builder["id"], "https://openembedded.org/local-build")

    def test_provenance_builder_id_custom(self):
        """Verify custom builder ID is configurable."""
        stmt = self._build_and_get_provenance(
            extra_conf='SLSA_PROVENANCE_BUILDER_ID = "https://ci.example.com/builder"'
        )
        builder = stmt["predicate"]["runDetails"]["builder"]
        self.assertEqual(builder["id"], "https://ci.example.com/builder")

    def test_provenance_custom_build_type(self):
        """Verify custom build type URI."""
        stmt = self._build_and_get_provenance(
            extra_conf='SLSA_PROVENANCE_BUILD_TYPE = "https://example.com/custom-build/v1"'
        )
        self.assertEqual(
            stmt["predicate"]["buildDefinition"]["buildType"],
            "https://example.com/custom-build/v1",
        )

    def test_provenance_recipe_sources(self):
        """Verify recipe source URIs appear in resolvedDependencies."""
        stmt = self._build_and_get_provenance()
        build_def = stmt["predicate"]["buildDefinition"]

        deps = build_def.get("resolvedDependencies", [])
        # With sources enabled, we should have entries with uri fields
        # that are not layer revisions (layer entries have annotations.branch)
        source_deps = [
            d for d in deps
            if d.get("uri") and not (d.get("annotations") or {}).get("branch")
        ]
        self.assertTrue(
            len(source_deps) > 0,
            "Should have at least one recipe source dependency",
        )

    def test_provenance_internal_parameters(self):
        """Verify internalParameters are present."""
        stmt = self._build_and_get_provenance()
        build_def = stmt["predicate"]["buildDefinition"]

        self.assertIn("internalParameters", build_def)
        internal = build_def["internalParameters"]
        self.assertIn("target_arch", internal)

    # --- SLSA Build L3 tests ---

    def test_provenance_builder_version_present(self):
        """L3: builder.version must be populated with tool versions."""
        stmt = self._build_and_get_provenance()
        builder = stmt["predicate"]["runDetails"]["builder"]

        self.assertIn("version", builder,
                      "builder.version is required for SLSA Build L3")
        version = builder["version"]
        self.assertIsInstance(version, dict)
        self.assertIn("bitbake", version,
                      "builder.version must include the bitbake version")
        # BitBake version should be a non-empty string like "2.8.0"
        self.assertTrue(len(version["bitbake"]) > 0)

    def test_provenance_deploy_dir_is_slsa(self):
        """L3: build provenance must land in DEPLOY_DIR_SLSA, not DEPLOY_DIR_IMAGE."""
        self.write_config(self._get_config())
        bitbake("core-image-minimal")

        bb_vars = get_bb_vars(
            ["DEPLOY_DIR_SLSA", "DEPLOY_DIR_IMAGE", "IMAGE_LINK_NAME"],
            "core-image-minimal",
        )
        slsa_dir = bb_vars["DEPLOY_DIR_SLSA"]
        image_dir = bb_vars["DEPLOY_DIR_IMAGE"]
        link_name = bb_vars["IMAGE_LINK_NAME"]

        slsa_path = os.path.join(slsa_dir, link_name + ".slsa-build.json")
        image_path = os.path.join(image_dir, link_name + ".slsa-build.json")

        self.assertExists(slsa_path,
                          "Build provenance must be in DEPLOY_DIR_SLSA")
        self.assertFalse(os.path.exists(image_path),
                         "Build provenance must NOT be placed in DEPLOY_DIR_IMAGE")


class SLSASourceProvenanceTest(SLSAProvenanceBase, OESelftestTestCase):
    """Tests for the SLSA source provenance (slsa.dev/source_provenance/v1)."""

    def test_source_provenance_basic_structure(self):
        """Verify in-toto Statement v1 wraps source_provenance/v1 predicate."""
        stmt = self._get_source_provenance()

        self.assertEqual(stmt["_type"], "https://in-toto.io/Statement/v1")
        self.assertEqual(stmt["predicateType"],
                         "https://slsa.dev/source_provenance/v1")
        self.assertIn("subject", stmt)
        self.assertIn("predicate", stmt)
        self.assertIn("activity", stmt["predicate"])

    def test_source_provenance_subjects_are_layers(self):
        """Subjects must be layer entries with gitCommit digests."""
        stmt = self._get_source_provenance()

        subjects = stmt["subject"]
        self.assertTrue(len(subjects) > 0,
                        "Source provenance must have at least one layer subject")

        for subj in subjects:
            self.assertIn("name", subj)
            self.assertIn("digest", subj)
            self.assertIn("gitCommit", subj["digest"],
                          "Layer subject must carry a gitCommit digest")
            self.assertEqual(len(subj["digest"]["gitCommit"]), 40,
                             "gitCommit must be a 40-char hex SHA1")

        # The 'meta' layer must always be present
        layer_names = [s["name"] for s in subjects]
        self.assertIn("meta", layer_names)

    def test_source_provenance_activity_actor(self):
        """Activity must contain an actor with the builder ID."""
        stmt = self._get_source_provenance()
        activity = stmt["predicate"]["activity"]

        self.assertIn("actor", activity)
        self.assertIn("id", activity["actor"])
        # Default builder ID
        self.assertEqual(activity["actor"]["id"],
                         "https://openembedded.org/local-build")

    def test_source_provenance_activity_context(self):
        """Activity context must include image and machine values."""
        stmt = self._get_source_provenance()
        activity = stmt["predicate"]["activity"]

        self.assertIn("context", activity)
        ctx = activity["context"]
        self.assertIn("type", ctx)
        self.assertIn("values", ctx)
        self.assertIn("image", ctx["values"])
        self.assertIn("machine", ctx["values"])

    def test_source_provenance_custom_builder_id(self):
        """Custom SLSA_PROVENANCE_BUILDER_ID must appear in source activity actor."""
        stmt = self._get_source_provenance(
            extra_conf='SLSA_PROVENANCE_BUILDER_ID = "https://ci.example.com/builder"'
        )
        actor_id = stmt["predicate"]["activity"]["actor"]["id"]
        self.assertEqual(actor_id, "https://ci.example.com/builder")

    def test_source_provenance_invocation_id(self):
        """SLSA_PROVENANCE_INVOCATION_ID must appear as activity.id."""
        stmt = self._get_source_provenance(
            extra_conf='SLSA_PROVENANCE_INVOCATION_ID = "https://ci.example.com/runs/42"'
        )
        activity = stmt["predicate"]["activity"]
        self.assertIn("id", activity)
        self.assertEqual(activity["id"], "https://ci.example.com/runs/42")


class SLSADepsProvenanceTest(SLSAProvenanceBase, OESelftestTestCase):
    """Tests for the in-toto Link deps provenance (in-toto.io/attestation/link/v0.3)."""

    def _get_deps_provenance(self, target="core-image-minimal", extra_conf=""):
        self.write_config(self._get_config(extra_conf))
        bitbake(target)

        bb_vars = get_bb_vars(
            ["DEPLOY_DIR_SLSA", "IMAGE_LINK_NAME"],
            target,
        )
        deploy_dir = bb_vars["DEPLOY_DIR_SLSA"]
        link_name = bb_vars["IMAGE_LINK_NAME"]

        deps_path = os.path.join(
            deploy_dir, link_name + ".slsa-deps.json"
        )
        self.assertExists(deps_path)

        with open(deps_path, "r") as f:
            return json.load(f)

    def test_deps_provenance_basic_structure(self):
        """Verify in-toto Statement v1 wraps link/v0.3 predicate."""
        stmt = self._get_deps_provenance()

        self.assertEqual(stmt["_type"], "https://in-toto.io/Statement/v1")
        self.assertEqual(stmt["predicateType"],
                         "https://in-toto.io/attestation/link/v0.3")
        self.assertIn("subject", stmt)
        self.assertIn("predicate", stmt)

    def test_deps_provenance_link_required_fields(self):
        """Link predicate must have name, command, and materials."""
        stmt = self._get_deps_provenance()
        predicate = stmt["predicate"]

        self.assertIn("name", predicate)
        self.assertIn("command", predicate)
        self.assertIn("materials", predicate)

    def test_deps_provenance_subjects_are_image_artifacts(self):
        """Subjects must be image artifacts with sha256 digests."""
        stmt = self._get_deps_provenance()

        subjects = stmt["subject"]
        self.assertTrue(len(subjects) > 0,
                        "Deps provenance must have at least one image subject")
        for subj in subjects:
            self.assertIn("name", subj)
            self.assertIn("digest", subj)
            self.assertIn("sha256", subj["digest"],
                          "Image artifact subject must carry a sha256 digest")
            self.assertEqual(len(subj["digest"]["sha256"]), 64,
                             "sha256 must be a 64-char hex string")

    def test_deps_provenance_command_contains_bitbake(self):
        """Link command must reference bitbake and the image target."""
        stmt = self._get_deps_provenance()
        command = stmt["predicate"]["command"]

        self.assertIsInstance(command, list)
        self.assertTrue(len(command) > 0, "command must not be empty")
        self.assertEqual(command[0], "bitbake",
                         "first command element must be 'bitbake'")
        # second element should be the image basename
        self.assertTrue(len(command) > 1,
                        "command must include the image target name")

    def test_deps_provenance_materials_include_layers(self):
        """Materials must include layer entries with gitCommit digests."""
        stmt = self._get_deps_provenance()
        materials = stmt["predicate"]["materials"]

        self.assertTrue(len(materials) > 0, "materials must not be empty")

        # At least the 'meta' layer must be present
        layer_names = [m["name"] for m in materials]
        self.assertIn("meta", layer_names,
                      "materials must include the 'meta' layer")

        # Layer entries must carry gitCommit digests
        meta_mat = next(m for m in materials if m["name"] == "meta")
        self.assertIn("digest", meta_mat)
        self.assertIn("gitCommit", meta_mat["digest"],
                      "layer material must carry a gitCommit digest")
        self.assertEqual(len(meta_mat["digest"]["gitCommit"]), 40,
                         "gitCommit must be a 40-char hex SHA1")

    def test_deps_provenance_environment_fields(self):
        """Link environment must include machine and distro keys."""
        stmt = self._get_deps_provenance()
        predicate = stmt["predicate"]

        self.assertIn("environment", predicate)
        env = predicate["environment"]
        self.assertIn("machine", env)
        self.assertIn("distro", env)

    def test_deps_provenance_deploy_dir_is_slsa(self):
        """Deps provenance must land in DEPLOY_DIR_SLSA, not DEPLOY_DIR_IMAGE."""
        self.write_config(self._get_config())
        bitbake("core-image-minimal")

        bb_vars = get_bb_vars(
            ["DEPLOY_DIR_SLSA", "DEPLOY_DIR_IMAGE", "IMAGE_LINK_NAME"],
            "core-image-minimal",
        )
        slsa_dir = bb_vars["DEPLOY_DIR_SLSA"]
        image_dir = bb_vars["DEPLOY_DIR_IMAGE"]
        link_name = bb_vars["IMAGE_LINK_NAME"]

        slsa_path = os.path.join(slsa_dir, link_name + ".slsa-deps.json")
        image_path = os.path.join(image_dir, link_name + ".slsa-deps.json")

        self.assertExists(slsa_path,
                          "Deps provenance must be in DEPLOY_DIR_SLSA")
        self.assertFalse(os.path.exists(image_path),
                         "Deps provenance must NOT be placed in DEPLOY_DIR_IMAGE")
