from __future__ import annotations

import copy
import json
import math
import unittest
from pathlib import Path

from romania_macro_financial_dynamics.dynamics import (
    DEFAULT_DT_YEARS, first_order_delay_timestep_is_adequate,
    simulate_first_order_delay_euler,
)
from scripts.audit_numerical_integration import (
    audit_numerical_integration, simulate_constant_rate_partition,
)

ROOT=Path(__file__).resolve().parents[1]
def load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))

class NumericalIntegrationGateTests(unittest.TestCase):
    def setUp(self):
        self.c=load("model/dynamics/numerical_integration_contract.json")
        self.core=load("model/dynamics/core_contract.json")
        self.d=load("model/dynamics/delay_evidence_registry.json")
        self.m=load("model/registries/model_contract.json")
        self.r=load("model/dynamics/feedback_link_readiness_registry.json")

    def audit(self,c=None,d=None):
        return audit_numerical_integration(c or self.c,self.core,d or self.d,self.m,self.r)

    def test_current_contract_passes(self):
        self.assertEqual(self.audit(),[])

    def test_constant_rate_partition_invariance(self):
        values=[simulate_constant_rate_partition(
            opening=1000.0,transaction_rate=100.0,revaluation_rate=-20.0,
            other_change_rate=5.0,horizon_years=1.0,dt_years=dt
        ) for dt in (1.0,0.5,0.25,0.125)]
        self.assertTrue(all(abs(x-1085.0)<1e-10 for x in values))

    def test_first_order_delay_converges_under_halving(self):
        exact=1-math.exp(-1)
        values=[simulate_first_order_delay_euler(
            initial=0,input_value=1,tau_years=1,horizon_years=1,dt_years=dt
        ) for dt in (0.25,0.125,0.0625,0.03125)]
        errors=[abs(x-exact) for x in values]
        self.assertTrue(all(b<a for a,b in zip(errors,errors[1:])))

    def test_default_quarterly_dt_strict_threshold(self):
        self.assertEqual(DEFAULT_DT_YEARS,0.25)
        self.assertFalse(first_order_delay_timestep_is_adequate(0.25,0.75))
        self.assertTrue(first_order_delay_timestep_is_adequate(0.25,0.750001))

    def test_one_third_is_adequacy_not_stability_claim(self):
        rule=self.c["structural_primitives"]["first_order_delay"]["explicit_euler_time_step_rule"]
        self.assertEqual(rule["rule_type"],"CONSERVATIVE_SYSTEM_DYNAMICS_ADEQUACY_RULE_NOT_STABILITY_LIMIT")

    def test_current_delays_remain_unparameterized(self):
        self.assertEqual(self.d["current_summary"]["registered_delay_candidates"],7)
        self.assertEqual(self.d["current_summary"]["scalar_tau_identified_and_validated"],0)
        self.assertEqual(self.d["current_summary"]["active_delay_candidates"],0)

    def test_stale_tau_implication_detected(self):
        x=copy.deepcopy(self.c)
        x["structural_primitives"]["first_order_delay"]["explicit_euler_time_step_rule"]["implied_tau_requirement_at_default_dt"]="tau_years >= 0.75"
        self.assertTrue(any("tau implication" in e for e in self.audit(c=x)))

    def test_numerical_pass_cannot_activate_model(self):
        x=copy.deepcopy(self.c)
        x["current_summary"]["model_activation_authorized"]=True
        self.assertTrue(any("model activation" in e for e in self.audit(c=x)))

if __name__=="__main__": unittest.main()
