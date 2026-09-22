# Release and versioning policy

Romanian Monetary Dynamics (RMD) uses Semantic Versioning-compatible version identifiers for public scientific-core artifacts. The current public release is **v0.3.0**. The scientific maturity of the model is tracked separately from the software/artifact version: a new version does not by itself mean that behavioural mechanisms are validated, the model is calibrated, or behavioural closure is active.

## Current release state

- Current public release: **v0.3.0**
- Release date: **2026-09-21**
- Exact release commit: `33c11b7e10e7e837097da5b34a9251c7bedb3f2c`
- Release notes: **releases/v0.3.0.md**
- Publication record: **model/registries/v0_3_0_release_publication_record_2026_09_21.json**
- One-shot publication authorization: **consumed / inactive**
- Default next substantive milestone candidate: **v0.4.0**
- A narrowly scoped corrective release may use **v0.3.1** when appropriate.

The published v0.1.0, v0.2.0 and v0.3.0 tags/releases are historical identities and must not be moved or rewritten.

## Atomic version bump checklist

When a new public version is prepared, update these repository surfaces in the same release change:

1. `pyproject.toml` → `project.version`
2. `src/romania_macro_financial_dynamics/__init__.py` → `__version__`
3. `README.md` → version badge
4. `CITATION.cff` → `version`
5. `CITATION.cff` → `date-released`
6. `CHANGELOG.md` → move released material from **Unreleased** to the new version/date heading
7. `model/registries/release_versioning_contract.json` → advance current release/version fields and the next candidate
8. create `releases/v<version>.md` with the version-specific scientific status, included changes and non-claims

Before publication, the exact release commit must pass Scientific CI and the required accounting/materialization audits.

After repository metadata is synchronized:

9. create tag `v<version>` at the exact reviewed release commit;
10. create the GitHub Release from that same tag;
11. use the versioned `releases/v<version>.md` content as the reviewed release-note source or verify semantic equivalence;
12. ensure release notes describe the actual scientific maturity and current non-claims;
13. verify the tag, GitHub Release, package metadata, README, citation metadata, changelog and versioned release-note file all identify the same version.

## Version selection during 0.x development

RMD remains in initial development. Substantive public scientific-core milestones should normally advance the minor version, for example `0.1.0 → 0.2.0`. A patch increment is reserved for a narrowly scoped corrective release where that classification accurately describes the public artifact.

The version number communicates the released artifact identity. It must not be used to imply causal identification, validated behavioural closure, calibration quality or policy-simulation readiness.

## Scientific invariants during release work

Release preparation must not, by itself, authorize:

- estimation or refitting;
- model selection;
- final-holdout or reserved-response inspection;
- target-family substitution;
- activation of System Dynamics feedbacks;
- behavioural closure;
- claims of model completion.

Those states remain governed by their scientific contracts and evidence gates.
