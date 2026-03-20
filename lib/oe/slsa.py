#
# Copyright Konsolko Group
#
# SPDX-License-Identifier: MIT
#
# In-toto Statement v1 and SLSA Provenance v1 data model
# Reference: https://slsa.dev/provenance/v1
# Reference: https://in-toto.io/Statement/v1

import json
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timezone


INTOTO_STATEMENT_TYPE = "https://in-toto.io/Statement/v1"
SLSA_PROVENANCE_PREDICATE_TYPE = "https://slsa.dev/provenance/v1"
SLSA_SOURCE_PROVENANCE_PREDICATE_TYPE = "https://slsa.dev/source_provenance/v1"

# Default build type URI for OpenEmbedded/Yocto image builds
OE_BUILD_TYPE = "https://openembedded.org/slsa/image-build/v1"


def now_rfc3339():
    """Return current UTC time as RFC3339 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class ResourceDescriptor:
    """
    Represents a resource descriptor per SLSA/in-toto spec.
    Used for both subjects and resolvedDependencies.
    """
    name: str
    digest: dict = field(default_factory=dict)
    uri: Optional[str] = None
    annotations: Optional[dict] = None

    def to_dict(self):
        d = {"name": self.name}
        if self.digest:
            d["digest"] = self.digest
        if self.uri is not None:
            d["uri"] = self.uri
        if self.annotations is not None:
            d["annotations"] = self.annotations
        return d


@dataclass
class Builder:
    """The builder identity."""
    id: str
    version: Optional[dict] = None

    def to_dict(self):
        d = {"id": self.id}
        if self.version:
            d["version"] = self.version
        return d


@dataclass
class BuildMetadata:
    """Optional metadata about the build invocation."""
    invocationId: Optional[str] = None
    startedOn: Optional[str] = None
    finishedOn: Optional[str] = None

    def to_dict(self):
        d = {}
        if self.invocationId is not None:
            d["invocationId"] = self.invocationId
        if self.startedOn is not None:
            d["startedOn"] = self.startedOn
        if self.finishedOn is not None:
            d["finishedOn"] = self.finishedOn
        return d


@dataclass
class RunDetails:
    """Run details: builder identity and build metadata."""
    builder: Builder
    metadata: Optional[BuildMetadata] = None

    def to_dict(self):
        d = {"builder": self.builder.to_dict()}
        if self.metadata is not None:
            md = self.metadata.to_dict()
            if md:
                d["metadata"] = md
        return d


@dataclass
class BuildDefinition:
    """The build definition: what was built and with what parameters."""
    buildType: str
    externalParameters: dict = field(default_factory=dict)
    internalParameters: Optional[dict] = None
    resolvedDependencies: list = field(default_factory=list)

    def to_dict(self):
        d = {
            "buildType": self.buildType,
            "externalParameters": self.externalParameters,
        }
        if self.internalParameters:
            d["internalParameters"] = self.internalParameters
        if self.resolvedDependencies:
            d["resolvedDependencies"] = [
                rd.to_dict() for rd in self.resolvedDependencies
            ]
        return d


@dataclass
class SLSAProvenance:
    """SLSA Provenance v1 predicate."""
    buildDefinition: BuildDefinition
    runDetails: RunDetails

    def to_dict(self):
        return {
            "buildDefinition": self.buildDefinition.to_dict(),
            "runDetails": self.runDetails.to_dict(),
        }


@dataclass
class SourceActor:
    """The actor that created or published the source."""
    id: str

    def to_dict(self):
        return {"id": self.id}


@dataclass
class SourceActivity:
    """
    Describes the activity that produced the source attestation.
    Maps to the SLSA source_provenance/v1 'activity' field.
    """
    id: Optional[str] = None
    actor: Optional[SourceActor] = None
    context: Optional[dict] = None

    def to_dict(self):
        d = {}
        if self.id is not None:
            d["id"] = self.id
        if self.actor is not None:
            d["actor"] = self.actor.to_dict()
        if self.context is not None:
            d["context"] = self.context
        return d


@dataclass
class SLSASourceProvenance:
    """
    SLSA Source Provenance v1 predicate.
    Reference: https://slsa.dev/source-requirements
    """
    activity: SourceActivity

    def to_dict(self):
        return {"activity": self.activity.to_dict()}


@dataclass
class InTotoStatement:
    """In-toto Statement v1 envelope wrapping a SLSA provenance predicate."""
    subject: list
    predicate: object  # SLSAProvenance or SLSASourceProvenance
    _type: str = INTOTO_STATEMENT_TYPE
    predicateType: str = SLSA_PROVENANCE_PREDICATE_TYPE

    def to_dict(self):
        return {
            "_type": self._type,
            "subject": [s.to_dict() for s in self.subject],
            "predicateType": self.predicateType,
            "predicate": self.predicate.to_dict(),
        }

    def to_json(self, indent=2):
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False)
