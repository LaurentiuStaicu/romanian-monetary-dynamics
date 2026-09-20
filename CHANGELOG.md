# Changelog

All notable public scientific-core releases of Romanian Monetary Dynamics (RMD) are recorded here.

## Unreleased

### Scientific integrity and reproducibility

- screened official BNR and Ministry of Finance issuance/borrowing sources and identified `government_debt_issuance` as semantically overloaded across the two government feedback loops; froze separate domestic-primary-market and all-market borrowing materialisation paths while keeping the generic node unresolved;
- added a government F3 holder-composition and net-incurrence diagnostic for 2025, explicitly distinguishing financial-account net incurrence from gross issuance/refinancing need and keeping holder absorption separate from the unresolved securities-supply-pressure feedback node;
- added deterministic F3 observed behavior-over-time diagnostics for 2025, decomposing sector and bilateral Q1-Q4 stock changes into Q2-Q4 financial transactions plus combined non-transaction changes while explicitly preserving the 9/10 partial sectoral-financial-positions reference-mode boundary;
- added a deterministic F3-only quarterly empirical replay for 2025-Q2..Q4 using retained QSA stocks and transactions plus an explicitly non-causal combined non-transaction residual; the replay closes 105 bilateral transitions exactly at published precision without changing full-RMD accounting readiness;
- added a machine-checked 14-criterion activation matrix for every registered feedback structure; only explicit `PASS` counts, leaving all five structures quantitatively blocked under the current evidence boundary;
- implemented the exact frozen household-housing delta-policy monetary candidate as a target-specific executable form while preserving CANDIDATE status and keeping the generic monetary-credit feedback link quantitatively inactive;
- froze behavioural parameter sign semantics for current executable forms: sensitivity betas are non-negative magnitudes and equation operators own causal signs, with runtime rejection of silent negative-coefficient sign reversals;
- added an evidence gate for all seven candidate delays; timing distributions, survey cadence, lag windows, average maturity and average re-fixing are explicitly prevented from being reused as scalar `tau` values without exact validation;
- added exact link-level feedback readiness and a per-loop activation matrix; all 22 registered path links and all five feedback structures remain quantitatively blocked rather than treating related mechanisms or qualitative topology as integrated equations;
- added form-level behavioural extreme-condition and structural-sensitivity tests while explicitly keeping integrated extreme-condition validation and empirical sensitivity execution blocked;
- added an executable feedback-variable boundary gate covering every qualitative loop/chain node and preventing topology or observed-target availability from silently implying endogeneity;
- added an executable behavioural dimensional-consistency gate that separates symbolic unit validity from unfrozen empirical measurement scales and blocks activation without inventing transforms;
- added executable behavioural-implementation governance so retained exploratory equations cannot be mistaken for currently admitted mechanism implementations;
- completed scientific-baseline consolidation and integration with executable cross-registry consistency checks;
- retained exact source vintages and strengthened offline provenance verification so accepted historical evidence does not depend on future provider availability;
- completed the fiscal structural-primary real-time source adjudication and preserved the reviewed AMECO raw source vintage without later refetch;
- returned the fiscal mechanism to `DEFERRED` after the source-only reopen, without estimation, target-family substitution or final-evaluation inspection;
- added post-closure reopen-trigger monitoring and a trigger-aware monitoring horizon that prevents repeated unchanged-source probing from being treated as scientific progress;
- preserved the Evidence-Triggered Baseline Hold, inactive behavioural closure and zero validated reference behavioural mechanisms.

### Accounting and reference-mode recovery

- strengthened Accounting Spine readiness and retained instrument-specific rank/materialization boundaries;
- completed current-public-source recovery screening for the remaining sectoral-financial-position reference-mode blocker;
- retained explicit reopen conditions instead of using synthetic allocations or relaxed source boundaries.

### Repository governance

- added a review-gated RMD social-preview design brief using GitHub's 1280x640 recommendation, suite grayscale identity and explicit scientific non-claim constraints; no social-preview image is published by this change;
- added PR-only workflow concurrency so superseded Scientific CI runs on the same pull-request branch are canceled while main/manual runs retain unique execution groups;
- added RMD community-health governance with contribution/support guidance, structured bug and scientific issue forms, and a pull-request scientific-integrity checklist; security policy and code-of-conduct adoption remain explicitly deferred pending private-reporting/enforcement decisions;
- defined a professional scientific-model README design contract and a canonical-state-checked RMD landing-page preview, without replacing the public README before review;
- added a light/dark, accessibility-checked RMD conceptual-structure diagram preview that shows the institutional boundary and accounting/evidence/dynamics/activation layers without implying validated causal links or complete bilateral coverage;
- prepared the professional RMD first-page implementation with compact suite-consistent header, canonical scientific-status panel, responsive concept diagram, reproduction path, provenance rules, repository map and reader routing; publication remains review-gated;
- added an atomic release/versioning contract and release checklist;
- future version changes must synchronize package metadata, README badge, citation metadata, changelog, release contract, Git tag and GitHub Release.


## 0.1.0 - 2026-09-18

Initial public scientific-core baseline.

### Included

- accounting spine and structural dynamic-core contracts;
- empirical-dynamics and mechanism/evidence registries;
- source and processed data with provenance;
- validation-recovery selection, holdout and disposition artifacts;
- government repricing ledger contract and assessment;
- Python scientific/reference implementation;
- reproducibility and empirical-recovery scripts;
- standardized RMD project identity and release metadata.

### Scientific status

The model is in Validation Recovery / Empirical Basis Expansion. The canonical disposition records zero validated reference behavioural mechanisms. Monetary pass-through forms remain candidates or fail selection gates, and the government repricing mechanism remains deferred because the required boundary-matched structure is not point-identifiable from the current public data.

### Scope boundary

The release is a scientific model core, not a calibrated macroeconomic forecast, production policy simulator, or end-user application.
