from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class LiveSourceRefreshWorkflowTests(unittest.TestCase):
    def test_live_provider_refreshes_are_manual_only(self) -> None:
        manual_only = [
            ".github/workflows/f2-source-structure-audit.yml",
            ".github/workflows/corporate-investment-financing-rate-screening.yml",
            ".github/workflows/corporate-investment-source-materialisation.yml",
            ".github/workflows/corporate-investment-supplemental-materialisation.yml",
            ".github/workflows/accounting-coverage-audit.yml",
            ".github/workflows/bps-f2-sector-structure-audit.yml",
            ".github/workflows/eurostat-f2-sector-detail-audit.yml",
            ".github/workflows/f21-bpm6-esa-concept-bridge-audit.yml",
            ".github/workflows/f21-currency-coverage-audit.yml",
            ".github/workflows/f21-f2-external-bridge-audit.yml",
            ".github/workflows/f2m-deposit-coverage-audit.yml",
            ".github/workflows/f2m-external-identity-audit.yml",
            ".github/workflows/f4-loans-coverage-audit.yml",
            ".github/workflows/f5-bilateral-component-issuer-audit.yml",
            ".github/workflows/f5-equity-fund-coverage-audit.yml",
            ".github/workflows/f6-bilateral-component-coverage-audit.yml",
            ".github/workflows/f6-insurance-pensions-coverage-audit.yml",
            ".github/workflows/f8-bilateral-component-bridge-audit.yml",
            ".github/workflows/private-credit-reference-audit.yml",
            ".github/workflows/government-interest-burden-reference-audit.yml",
            ".github/workflows/government-debt-stock-reference-audit.yml",
            ".github/workflows/sovereign-yield-quarterly-materialisation.yml",
            ".github/workflows/fiscal-primary-balance-materialisation.yml",
            ".github/workflows/bank-credit-prudential-coverage-audit.yml",
            ".github/workflows/provenance-audit.yml",
            ".github/workflows/f4-exact-complement-rank-audit.yml",
            ".github/workflows/f5-equity-subcomponent-bridge-audit.yml",
            ".github/workflows/f7-financial-derivatives-coverage-audit.yml",
            ".github/workflows/f8-other-accounts-coverage-audit.yml",
            ".github/workflows/sectoral-financial-positions-reference-audit.yml",
            ".github/workflows/sectoral-financial-positions-aggregate-identity-audit.yml",
            ".github/workflows/sectoral-financial-positions-rounding-consistency-audit.yml",
            ".github/workflows/sectoral-financial-positions-source-discrepancy-audit.yml",
            ".github/workflows/sectoral-financial-positions-esa-f1-applicability-reaudit.yml",
            ".github/workflows/sectoral-financial-positions-esa-f1-semantics-diagnostic.yml",
            ".github/workflows/sectoral-financial-positions-s1n-boundary-diagnostic.yml",
        ]
        for relative in manual_only:
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("workflow_dispatch:", text, relative)
            self.assertNotIn("pull_request:", text, relative)
            lowered = text.lower()
            self.assertIn("refresh", lowered, relative)
            self.assertTrue(
                "live" in lowered or "provider" in lowered,
                relative,
            )



    def test_f2_source_structure_probe_requires_explicit_live_refetch(self) -> None:
        workflow_path = ROOT / ".github/workflows/f2-source-structure-audit.yml"
        workflow = workflow_path.read_text(encoding="utf-8")
        self.assertIn(
            "python scripts/probe_qsa_f2_structure.py --allow-live-refetch",
            workflow,
        )

        process = subprocess.run(
            [sys.executable, str(ROOT / "scripts/probe_qsa_f2_structure.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(process.returncode, 2)
        self.assertIn("--allow-live-refetch", process.stderr)
        self.assertIn("disabled by default", process.stderr)


    def test_frozen_corporate_source_clis_require_explicit_live_refetch(self) -> None:
        scripts = (
            "scripts/audit_corporate_investment_financing_rate_source_screening.py",
            "scripts/audit_corporate_investment_source_materialisation.py",
            "scripts/audit_corporate_investment_supplemental_materialisation.py",
        )
        for relative in scripts:
            process = subprocess.run(
                [sys.executable, str(ROOT / relative)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(process.returncode, 2, relative)
            self.assertIn("--allow-live-refetch", process.stderr, relative)
            self.assertIn("disabled by default", process.stderr, relative)

    def test_sectoral_position_has_no_parallel_phase_aliases(self) -> None:
        forbidden_paths = [
            ".github/workflows/sectoral-financial-positions-phase-b-audit.yml",
            "scripts/audit_ecb_sectoral_financial_positions_phase_b.py",
            "model/dynamics/sectoral_financial_positions_phase_b_assessment.json",
            ".github/workflows/sectoral-financial-positions-phase-c-diagnostic.yml",
            "scripts/audit_ecb_sectoral_financial_positions_phase_c.py",
            "model/dynamics/sectoral_financial_positions_phase_c_diagnostic_contract.json",
            "tests/test_sectoral_financial_positions_phase_c_diagnostic_contract.py",
        ]
        for relative in forbidden_paths:
            self.assertFalse((ROOT / relative).exists(), relative)

        registry = (
            ROOT / "model" / "dynamics" / "reference_modes.json"
        ).read_text(encoding="utf-8")
        self.assertNotIn('"phase_b_assessment"', registry)
        self.assertIn(
            '"historical_phase_b_assessment": '
            '"model/dynamics/sectoral_financial_positions_aggregate_identity_assessment.json"',
            registry,
        )


    def test_offline_reproduction_workflows_remain_automatic(self) -> None:
        offline_automatic = [
            ".github/workflows/f4-partial-materialization-audit.yml",
            ".github/workflows/f5-component-aware-rank-audit.yml",
            ".github/workflows/f6-aggregate-rank-audit.yml",
            ".github/workflows/f7-aggregate-rank-audit.yml",
            ".github/workflows/f8-aggregate-rank-audit.yml",
        ]
        for relative in offline_automatic:
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("pull_request:", text, relative)
            self.assertIn("workflow_dispatch:", text, relative)

    def test_scientific_ci_does_not_call_live_source_audits(self) -> None:
        text = (
            ROOT / ".github" / "workflows" / "scientific-ci.yml"
        ).read_text(encoding="utf-8")
        forbidden = [
            "audit_ecb_private_credit_reference.py",
            "audit_eurostat_government_interest_burden_reference.py",
            "audit_eurostat_government_debt_stock_reference.py",
            "audit_sovereign_yield_quarterly_materialisation.py",
            "audit_fiscal_primary_balance_materialisation.py",
            "audit_ecb_bank_credit_prudential_coverage.py",
            "audit_qsa_f4_loans_coverage.py",
            "audit_qsa_f5_equity_subcomponents.py",
            "audit_qsa_f7_financial_derivatives_coverage.py",
            "audit_qsa_f8_other_accounts_coverage.py",
            "audit_ecb_sectoral_financial_positions_reference.py",
            "audit_ecb_sectoral_financial_positions_aggregate_identity.py",
            "audit_ecb_sectoral_financial_positions_rounding_consistency.py",
            "audit_ecb_sectoral_financial_positions_source_discrepancy.py",
            "audit_ecb_sectoral_financial_positions_esa_f1_applicability_reaudit.py",
            "audit_ecb_sectoral_financial_positions_esa_f1_semantics_diagnostic.py",
            "audit_ecb_sectoral_financial_positions_s1n_boundary.py",
        ]
        for script in forbidden:
            self.assertNotIn(script, text)

    def test_offline_reproduction_is_still_covered_by_scientific_ci(self) -> None:
        text = (
            ROOT / ".github" / "workflows" / "scientific-ci.yml"
        ).read_text(encoding="utf-8")
        self.assertIn("python -m unittest discover -s tests -v", text)
        self.assertIn("python scripts/audit_accounting_readiness.py", text)
        self.assertIn("python scripts/audit_system_dynamics_conformity.py", text)
        self.assertIn(
            "python scripts/verify_validation_recovery_provenance.py",
            text,
        )


if __name__ == "__main__":
    unittest.main()
