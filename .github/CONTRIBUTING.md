# Contributing to Romanian Monetary Dynamics (RMD)

Thank you for considering a contribution to RMD.

RMD is a scientific model repository, so contributions are reviewed on two dimensions at the same time:

1. **software/repository quality** — correctness, reproducibility, tests, documentation;
2. **scientific integrity** — accounting consistency, source provenance, dimensional consistency, evidence boundaries and model-governance rules.

A change that is convenient in code but weakens the scientific boundary should not be merged.

## Before you open an issue or pull request

Please read:

- [README.md](../README.md) for the model overview;
- [STATUS.md](../STATUS.md) for the exact current scientific state;
- [model/registries/model_contract.json](../model/registries/model_contract.json) for the canonical model/repository contract;
- [model/registries/scientific_baseline_manifest.json](../model/registries/scientific_baseline_manifest.json) for the cross-registry baseline;
- [releases/README.md](../releases/README.md) for version/release rules.

## Contribution types

Useful contributions include:

- documentation and presentation improvements;
- reproducibility, build or test fixes;
- source/provenance corrections;
- accounting or dimensional-consistency fixes;
- reference-mode or measurement evidence;
- well-specified behavioural or System Dynamics proposals.

## Scientific invariants

Unless a governing scientific contract is deliberately revised and revalidated, contributions must preserve these rules:

- **missing / TBD is not zero**;
- **partial evidence is not canonical completion**;
- **aggregate evidence is not a bilateral allocation**;
- **provider/access failure is not negative scientific evidence**;
- **missing bilateral positions must not be invented to close a matrix**;
- behavioural mechanisms and feedback loops are not activated merely because code or equations exist;
- reserved holdout/prospective outcomes remain closed until their contract permits inspection;
- changes to canonical scientific state must update the relevant registries and tests together.

## Development workflow

Use a branch and pull request rather than committing scientific changes directly to `main`.

For local verification, use Python 3.12+ and run the same core checks described in the README. At minimum:

```bash
python -m unittest discover -s tests -v
python scripts/audit_accounting_readiness.py
python scripts/audit_dimensional_consistency.py
python scripts/audit_system_dynamics_conformity.py
python scripts/audit_scientific_baseline_manifest.py
python scripts/verify_validation_recovery_provenance.py
```

A pull request should explain:

- what changed;
- why the change is needed;
- the evidence/source boundary;
- whether the change affects accounting, data, reference modes, behavioural structure or only repository/documentation surfaces;
- which tests/audits were run;
- whether the canonical scientific state changes.

## Data and source contributions

For new or corrected data:

- identify the official/reproducible source;
- specify sector, instrument, frequency, units and transformation;
- retain or reference source provenance where permitted;
- distinguish observed values from derived values;
- document missingness explicitly;
- do not silently substitute a related series for the declared target.

## Behavioural / System Dynamics proposals

A new equation, delay or feedback proposal is not automatically an active mechanism.

Such contributions should include, as applicable:

- problem statement and mechanism rationale;
- source/evidence basis;
- endogenous/exogenous boundary;
- units and dimensional checks;
- expected sign/polarity;
- delay assumptions;
- nonlinearities;
- identification strategy;
- extreme-condition and sensitivity considerations;
- validation design.

Activation remains governed by RMD's scientific gates.

## Release/version changes

Do not bump the version as part of an unrelated change.

When a public release is actually prepared, follow the atomic release process in [releases/README.md](../releases/README.md) and [model/registries/release_versioning_contract.json](../model/registries/release_versioning_contract.json).

## Reporting problems

For reproducible software or documentation problems, use the repository issue forms.

For scientific/data/model concerns, use the dedicated scientific issue form and include the affected boundary and evidence.

Do **not** publish sensitive security-vulnerability details in a normal public issue.
