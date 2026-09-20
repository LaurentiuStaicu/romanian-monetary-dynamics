from __future__ import annotations

import inspect
import json
import unittest
from pathlib import Path

import romania_macro_financial_dynamics.behavioural as behavioural

ROOT = Path(__file__).resolve().parents[1]


class BehaviouralImplementationGovernanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = json.loads(
            (ROOT / "model" / "empirical_dynamics" / "mechanism_registry.json").read_text(
                encoding="utf-8"
            )
        )
        self.contract = json.loads(
            (ROOT / "model" / "empirical_dynamics" / "contract.json").read_text(
                encoding="utf-8"
            )
        )

    def public_behavioural_functions(self) -> set[str]:
        return {
            name
            for name, value in inspect.getmembers(behavioural, inspect.isfunction)
            if value.__module__ == behavioural.__name__ and not name.startswith("_")
        }

    def current_implementations(self) -> set[str]:
        return {
            mechanism["implementation"]
            for mechanism in self.registry["mechanisms"]
            if mechanism.get("implementation") is not None
        }

    def retained_noncanonical_forms(self) -> set[str]:
        return {
            item["function"]
            for item in self.registry["implementation_governance"]["retained_noncanonical_forms"]
        }

    def test_every_public_behavioural_function_has_explicit_governance(self) -> None:
        governed = self.current_implementations() | self.retained_noncanonical_forms()
        self.assertEqual(self.public_behavioural_functions(), governed)

    def test_retained_noncanonical_forms_cannot_be_current_implementations(self) -> None:
        self.assertTrue(
            self.current_implementations().isdisjoint(self.retained_noncanonical_forms())
        )

    def test_every_current_implementation_exists_in_code(self) -> None:
        missing = sorted(
            self.current_implementations() - self.public_behavioural_functions()
        )
        self.assertEqual(missing, [])

    def test_no_admitted_form_statement_requires_null_implementation(self) -> None:
        governance = self.registry["implementation_governance"]
        self.assertTrue(governance["no_admitted_form_requires_null_implementation"])
        offenders = [
            mechanism["id"]
            for mechanism in self.registry["mechanisms"]
            if mechanism.get("functional_form", "").startswith("No admitted")
            and mechanism.get("implementation") is not None
        ]
        self.assertEqual(offenders, [])

    def test_closed_calibration_cycle_has_no_activated_implementation(self) -> None:
        self.assertEqual(self.contract["activated_mechanisms"], [])
        activated = [
            mechanism["id"]
            for mechanism in self.registry["mechanisms"]
            if mechanism["classification"] == "ACTIVATED"
        ]
        self.assertEqual(activated, [])

    def test_activated_semantics_do_not_imply_sd_activation(self) -> None:
        semantics = self.registry["status_semantics"]["ACTIVATED"]
        self.assertIn("currently open calibration/validation cycle", semantics)
        self.assertIn("does not activate a System Dynamics feedback loop", semantics)
        self.assertIn("behavioural closure", semantics)


if __name__ == "__main__":
    unittest.main()
