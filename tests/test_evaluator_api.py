import unittest
from pathlib import Path

from engine import EATRuntimeGatekeeper
from eatme.models import GatekeeperConfig, Mode


class EvaluatorApiTests(unittest.TestCase):
    def test_evaluator_report_shape(self):
        gate = EATRuntimeGatekeeper(rubric_dir='.', config=GatekeeperConfig(mode=Mode.NUDGE), trace_path='trace/test_trace.jsonl')
        transcript = [
            {"role": "user", "text": "Kun je uitleggen wat fotosynthese is?"},
            {"role": "assistant", "text": "Zeker, wat weet je al?"},
        ]
        report = gate.evaluate_turn(
            session_id='s1',
            turn_id='t1',
            transcript_window=transcript,
            candidate_reply='1. Fotosynthese zet licht om in energie. Begrijp je dit?',
            sources=[{"type": "docstore", "title": "Biologie samenvatting", "snippet": "..."}],
        )
        self.assertIn('global_decision', report)
        self.assertIn('per_rubric', report)
        self.assertTrue(len(report['per_rubric']) >= 1)


if __name__ == '__main__':
    unittest.main()
