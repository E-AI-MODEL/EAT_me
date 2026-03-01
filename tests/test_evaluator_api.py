import json
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
        self.assertIn('rewrite_required', report)
        self.assertTrue(len(report['per_rubric']) >= 1)

    def test_trace_contains_observe_and_rewrite_fields(self):
        trace_path = Path('trace/test_trace_extended.jsonl')
        if trace_path.exists():
            trace_path.unlink()

        observe_gate = EATRuntimeGatekeeper(
            rubric_dir='.',
            config=GatekeeperConfig(mode=Mode.OBSERVE),
            trace_path=str(trace_path),
        )
        observe_gate.evaluate_turn(
            session_id='s-observe',
            turn_id='t1',
            transcript_window=[{"role": "user", "text": "Controleer feiten"}],
            candidate_reply='Bron: nergens in 2024.',
            sources=[],
        )

        def rewrite_func(candidate_reply, rewrite_instructions, context):
            return 'Ik heb geen bron; ik geef liever een veilige samenvatting.'

        correct_gate = EATRuntimeGatekeeper(
            rubric_dir='.',
            config=GatekeeperConfig(mode=Mode.CORRECT),
            trace_path=str(trace_path),
            rewrite_func=rewrite_func,
        )
        correct_gate.evaluate_turn(
            session_id='s-correct',
            turn_id='t2',
            transcript_window=[{"role": "user", "text": "Geef antwoord"}],
            candidate_reply='Bron: nergens in 2024.',
            sources=[],
        )

        lines = [json.loads(l) for l in trace_path.read_text(encoding='utf-8').splitlines()]
        observe_entry = next(e for e in lines if e['session_id'] == 's-observe')
        correct_entry = next(e for e in lines if e['session_id'] == 's-correct')

        self.assertIn('would_have_decided', observe_entry)
        self.assertIn('evidence_snippets', observe_entry['rubrics'][0])
        self.assertIn('rewrite_required', correct_entry)
        self.assertIn('final_reply', correct_entry)


if __name__ == '__main__':
    unittest.main()
