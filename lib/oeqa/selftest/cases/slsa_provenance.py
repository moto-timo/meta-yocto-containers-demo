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

    def _build_and_get_provenance(self, target="core-image-minimal", extra_conf=""):
        self.write_config(self._get_config(extra_conf))
        bitbake(target)

        bb_vars = get_bb_vars(
            ["DEPLOY_DIR_IMAGE", "IMAGE_LINK_NAME"],
            target,
        )
        deploy_dir = bb_vars["DEPLOY_DIR_IMAGE"]
        link_name = bb_vars["IMAGE_LINK_NAME"]

        provenance_path = os.path.join(
            deploy_dir, link_name + ".slsa-provenance.json"
        )
        self.assertExists(provenance_path)

        with open(provenance_path, "r") as f:
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
