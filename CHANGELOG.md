# Changelog

All notable public scientific-core releases of Romanian Monetary Dynamics (RMD) are recorded here.

## Unreleased

### Scientific integrity and reproducibility

- reviewed `debt_service_and_credit_risk → credit_supply_capacity`: NPL/DSTI, prudential capital/funding states and BLS lending standards are related but non-identical dimensions; no scalar credit-supply-capacity measure, exogenous NPL shock or synthetic prudential index is promoted;
- reviewed the `loan_stock → debt_service_and_credit_risk` boundary: outstanding credit is exposure scale, not debt-service burden or NPL state; aggregate NPL and narrower housing-loan DSTI evidence remain non-interchangeable, so the combined risk node stays unresolved and no proxy-based feedback equation is introduced;
- reviewed the bank-credit `credit_flow → loan_stock` boundary on the exact ECB BSI private non-financial credit universe: published financial transactions are not stock first differences, non-transaction adjustments remain required, the loan-stock reference target is frozen to `credit_stock`, and no endogenous stock equation or feedback activation is introduced;
- closed the current government issuance-yield candidate loop at the present evidence boundary: 0/5 links have exact integrated equations, all five nodes remain unresolved, the supply-source path remains trigger-gated with three official acts missing, the tested sovereign-yield form remains FAIL_BEFORE_HOLDOUT, both delays remain TBD, and the loop enters evidence-triggered hold with no active empirical task;
- closed the current government refinancing-interest candidate loop as structurally reviewed but quantitatively blocked: all four links now have explicit boundary decisions, 0/4 have exact integrated equations, all four nodes remain unresolved, the maturity delay and repricing share remain unidentified, and the loop enters evidence-triggered hold with no active empirical task;
- reviewed the government-debt-stock to interest-cost link as a conditional accounting scale relation: Eurostat apparent cost confirms the matched S13 accrued-interest/average-Maastricht-debt boundary, while year-end debt, Ministry portfolio rate and current market yields remain non-substitutable; no new reference mode, parameter, equation activation or behavioural closure is introduced;
- Review the government gross-borrowing/issuance to Maastricht-debt-stock bridge: reject one-to-one accumulation, anchor the 2025 S13 stock change to Eurostat EDP Table 3 stock-flow reconciliation, keep matched net debt transactions unidentified, and preserve inactive feedback/behavioural closure.
- retained all twelve 2025 Ministry monthly public-debt reports and extracted exact provider-published cumulative-YTD financing channels; changing FX-conversion regimes, exchange-operation semantics and non-monotone published lines block month-to-month differencing, so no monthly realized-financing flow series or channel allocation is promoted;
- froze a Ministry realized-financing channel source contract for provider-published cumulative-YTD actual borrowing by instrument/market; raw source retention and exact cumulative extraction are authorized, while monthly differencing, residual channel inference, synthetic allocation shares and cross-vintage FX conversion assumptions remain blocked;
- reviewed the bridge from government financing need to debt issuance as an explicit multi-channel allocation problem: the retained BNR domestic primary-market series remains one channel only, the Ministry 45%/55% split is scoped to deficit financing rather than total GFN, no residual or synthetic channel shares are allowed, and the generic financing-need/debt-issuance link remains unresolved;
- reviewed the government-interest-cost to financing-need boundary as a conditional accounting composition rather than a behavioural equation: headline-deficit GFN forms already include interest, primary-deficit forms include interest exactly once, and no cross-boundary Eurostat/MoF identity or canonical financing-need reference mode is promoted;
- reviewed the sovereign-yield to government-interest-cost boundary and rejected any contemporaneous one-to-one mapping from the ECB 10-year RON yield to portfolio cost or interest expenditure; Ministry portfolio-average rate and Eurostat D41PAY remain distinct observed targets, while the repricing/refinancing transition stays unidentified and feedback remains inactive;
- closed repeated full-2025 announced-supply source retries as an evidence-triggered hold: eight legally identified Ministry orders remain raw-source unavailable because Portal Legislativ transport is not reproducible from GitHub Actions and no exact alternative MF/ANAF raw copy was discovered; no values are imputed, canonical promotion remains blocked, and the next independent issuance-yield task is a structural primary-yield-to-sovereign-yield boundary review;
- retained exact official Ministry/ANAF source PDFs for April, May-base, June and October 2025 and materialised a competitive-only announced-RON reference-auction candidate with six exact final months (January-April, June and October); May remains non-final because OMF 752 is not retained, July-September and November-December remain unavailable, and canonical reference-mode promotion stays blocked;
- reviewed the full-2025 definition of announced RON primary-market supply and found a structural break in SSON information timing: the exact Q1 combined competitive+fixed-SSON pilot remains retained as legacy evidence, while the full-year comparable candidate is narrowed to competitive reference-auction targets only and must preserve May/November/December amendment history before any canonical promotion;
- retained the January-March 2025 Ministry issuance prospectuses and materialised an exact event-level pilot for announced RON domestic primary-market supply: completed-period monthly sums are RON 5,770m, 8,040m and 8,165m; a RON 75m SSON scheduled for 1 April remains a forward event rather than being shifted into March. Canonical reference-mode promotion remains deferred pending the April-December 2025 extension;
- froze the Ministry event-level source contract for the first government-securities supply reference mode: domestic RON discount Treasury-bill auctions, benchmark reference auctions and benchmark SSON targets remain separate source components; monthly aggregation uses each event date, Article 1 totals must reconcile exactly, and no stock denominator, accepted amount, yield-effect estimate or feedback activation is introduced;
- redesigned the unresolved government-securities supply-pressure concept as a structured measurement vector that separates announced RON supply level, announcement surprise, duration supply, auction absorption/bid-to-cover and secondary-market liquidity/capacity context; no scalar composite is selected, and the first recovery priority is the exact announced-RON primary-supply reference mode without a stock denominator;
- probed and retained preregistered ECB denominator candidates for the RON auction supply-load design: the CSEC S1311 domestic-currency debt-securities stock is valid but market-valued, the exact preregistered GFS domestic-currency face-value key returns no series, and the valid GFS face-value series is S13/all-currency context only; no denominator or supply-load ratio is selected;
- reviewed the denominator boundary for the proposed RON primary-market supply-load diagnostic: Ministry nominal RON holdings, ECB CSEC central-government market-value stocks and ECB GFS general-government face-value stocks remain distinct candidates, with no one-to-one auction-universe denominator selected and no pressure ratio materialised;
- retained three exact Ministry of Finance source PDFs for the government-securities supply-pressure probe and verified native PDF-text extractability without OCR: the January auction table supplies exact completed-month announced/borrowed values, while submitted-bid/bid-to-cover chart series and the stock denominator remain explicitly blocked pending exact mapping/boundary reconciliation;
- reviewed the observable boundary for government-securities supply pressure using official Ministry primary/secondary-market reporting: retained a multidimensional candidate design separating ex-ante announced supply load, auction absorption, published bid-to-cover and secondary-market liquidity, while explicitly prohibiting raw issuance, accepted amounts or inverse bid-to-cover from being promoted as a scalar pressure node;
- materialised the retained BNR 2025 domestic-primary-market issue rates by instrument and currency, preserving nil/not-applicable source symbols and distinct yield/interest-rate semantics; no cross-instrument aggregate, generic sovereign-yield mapping, causal issuance-to-yield claim or feedback activation is introduced;
- preregistered the government issuance–yield empirical boundary: retained the qualitative closed candidate topology while explicitly rejecting one-to-one substitution of BNR domestic-primary-market issuance into the generic closed loop; four separate bridges remain required for financing-channel allocation, supply-pressure operationalisation, primary-yield mapping and debt-stock interest-cost propagation;
- retained the exact official BNR December 2025 Monthly Bulletin PDF used by the full-year domestic-primary-market government-securities issuance pilot, with fixed-URL acquisition, repository-retained raw bytes, byte count and SHA-256 provenance; this closes only the raw-source-retention blocker and leaves the generic issuance node unresolved;
- completed a later-vintage BNR revision check for the domestic-primary-market issuance pilot: all 28 Jan-Jul native-currency amount cells are unchanged at published precision, and the reviewed pilot now covers all twelve months of 2025; the retained raw source closes provenance retention while structural narrowing of the issuance-yield path remains a separate gate;
- retained the original reviewed Jan-Jul 2025 BNR domestic-primary-market government-securities pilot lineage with native RON/EUR columns and complete Q1-Q2 aggregation, subsequently extended and revision-checked to full-year 2025 without collapsing the BNR boundary into total government borrowing;
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
