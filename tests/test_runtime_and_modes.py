import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from engine import EATRuntimeGatekeeper
from eatme.evaluator import GatekeeperOrchestrator, extract_features, quick_score_for_rubric
from eatme.models import Decision, GatekeeperConfig, Mode
from eatme.parser import load_eat


class RuntimeAndModesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rubrics = [load_eat(p) for p in sorted(Path('.').glob('*.eat'))]

    def test_runtime_zip_has_real_rubrics(self):
        zip_path = Path('dist/EAT_v2_runtime_ready_FULL.zip')
        if not zip_path.exists():
            subprocess.run([sys.executable, 'scripts/build_runtime_bundle.py'], check=True)
        z = zipfile.ZipFile(zip_path)
        names = z.namelist()
        self.assertIn('rubrics/index.eat', names)
        for n in names:
            if n.endswith('.eat') and n != 'rubrics/index.eat':
                content = z.read(n).decode('utf-8')
                self.assertNotIn('[content already defined in previous message]', content)

    def test_index_refs_existing_files(self):
        index = json.loads(Path('rubrics/index.eat').read_text(encoding='utf-8'))
        for f in index['index']['files']:
            self.assertTrue((Path('rubrics') / f).exists())

    def test_mode_behavior(self):
        transcript = [{"role": "user", "text": "Wat is de hoofdstad van Frankrijk?"}]
        candidate = "Volgens bron: https://example.com is het Parijs in 2024."
        sources = []

        observe = GatekeeperOrchestrator(self.rubrics, GatekeeperConfig(mode=Mode.OBSERVE)).evaluate(transcript, candidate, sources)
        nudge = GatekeeperOrchestrator(self.rubrics, GatekeeperConfig(mode=Mode.NUDGE)).evaluate(transcript, candidate, sources)
        correct = GatekeeperOrchestrator(self.rubrics, GatekeeperConfig(mode=Mode.CORRECT)).evaluate(transcript, candidate, sources)
        gate = GatekeeperOrchestrator(self.rubrics, GatekeeperConfig(mode=Mode.GATEKEEP)).evaluate(transcript, candidate, sources)

        self.assertEqual(observe.global_decision.value, 'PASS')
        self.assertEqual(observe.action_taken.value, 'PASS')
        self.assertEqual(observe.would_have_decided.value, 'BLOCK')
        self.assertEqual(nudge.global_decision.value, 'NUDGE')
        self.assertEqual(correct.global_decision.value, 'REWRITE')
        self.assertEqual(gate.global_decision.value, 'BLOCK')

    def test_index_order_and_selection_respected(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            first = td_path / 'B_BiasCorrectieFairness.eat'
            second = td_path / 'C_CoRegulatie.eat'
            first.write_text(Path('rubrics/B_BiasCorrectieFairness.eat').read_text(encoding='utf-8'), encoding='utf-8')
            second.write_text(Path('rubrics/C_CoRegulatie.eat').read_text(encoding='utf-8'), encoding='utf-8')
            extra = td_path / 'E_EpistemischeBetrouwbaarheid.eat'
            extra.write_text(Path('rubrics/E_EpistemischeBetrouwbaarheid.eat').read_text(encoding='utf-8'), encoding='utf-8')
            index = {
                'meta': {'version': 2.0, 'mode': 'runtime', 'locked': True},
                'index': {'order': ['C_CoRegulatie', 'B_BiasCorrectieFairness'], 'files': ['C_CoRegulatie.eat', 'B_BiasCorrectieFairness.eat']},
            }
            (td_path / 'index.eat').write_text(json.dumps(index), encoding='utf-8')

            gate = EATRuntimeGatekeeper(rubric_dir=td)
            loaded_ids = [r['rubric']['rubric_id'] for r in gate.rubrics]
            self.assertEqual(loaded_ids, ['C_CoRegulatie', 'B_BiasCorrectieFairness'])

    def test_index_missing_file_fails_with_clear_message(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            index = {
                'meta': {'version': 2.0, 'mode': 'runtime', 'locked': True},
                'index': {'order': ['C_CoRegulatie'], 'files': ['C_CoRegulatie.eat']},
            }
            (td_path / 'index.eat').write_text(json.dumps(index), encoding='utf-8')
            with self.assertRaises(ValueError) as ctx:
                EATRuntimeGatekeeper(rubric_dir=td)
            self.assertIn("referenced rubric 'C_CoRegulatie.eat' does not exist", str(ctx.exception))

    def test_evidence_detection_weak_attribution_no_misleading(self):
        features = extract_features([], 'Volgens mij is het ongeveer 30 in 2024.', [])
        hard_flags = []
        if features['explicit_source_claim'] and features['sources_count'] == 0:
            hard_flags.append('MISLEADING_SOURCES')
        self.assertNotIn('MISLEADING_SOURCES', hard_flags)

    def test_evidence_detection_explicit_claims_trigger_misleading(self):
        for text in ['Bron: klimaatrapport', 'Zie https://example.com/data']:
            features = extract_features([], text, [])
            hard_flags = []
            if features['explicit_source_claim'] and features['sources_count'] == 0:
                hard_flags.append('MISLEADING_SOURCES')
            self.assertIn('MISLEADING_SOURCES', hard_flags)

    def test_uncertain_numeric_claim_has_smaller_penalty(self):
        no_uncertain = extract_features([], 'Het is 33 in 2024.', [])
        uncertain = extract_features([], 'Het is mogelijk 33 in 2024, volgens mij.', [])

        score_no_uncertain = quick_score_for_rubric('E_EpistemischeBetrouwbaarheid', no_uncertain, ['UNGROUNDED_CLAIMS'])
        score_uncertain = quick_score_for_rubric('E_EpistemischeBetrouwbaarheid', uncertain, ['UNGROUNDED_CLAIMS'])
        self.assertGreater(score_uncertain, score_no_uncertain)

    def test_correct_mode_rewrite_without_hook_sets_required(self):
        gate = EATRuntimeGatekeeper(rubric_dir='.', config=GatekeeperConfig(mode=Mode.CORRECT), trace_path='trace/test_trace.jsonl')
        report = gate.evaluate_turn(
            session_id='s-rewrite-none',
            turn_id='t1',
            transcript_window=[{"role": "user", "text": "Geef bron"}],
            candidate_reply='Bron: onbekend in 2024.',
            sources=[],
        )
        self.assertEqual(report['global_decision'], 'REWRITE')
        self.assertTrue(report['rewrite_required'])
        self.assertEqual(report['rewrite_iterations'], 0)

    def test_correct_mode_rewrite_with_hook_can_pass(self):
        def rewrite_func(candidate_reply, rewrite_instructions, context):
            return 'Ik weet het niet zeker; zonder bron kan ik geen claim doen. Wil je dat ik een zoekstrategie geef?'

        gate = EATRuntimeGatekeeper(
            rubric_dir='.',
            config=GatekeeperConfig(mode=Mode.CORRECT, max_rewrite_iterations=2),
            trace_path='trace/test_trace.jsonl',
            rewrite_func=rewrite_func,
        )
        report = gate.evaluate_turn(
            session_id='s-rewrite',
            turn_id='t1',
            transcript_window=[{"role": "user", "text": "Vertel feiten"}],
            candidate_reply='Bron: onbekend in 2024.',
            sources=[],
        )
        self.assertIn(report['global_decision'], ['PASS', 'NUDGE'])
        self.assertLessEqual(report['rewrite_iterations'], 2)
        self.assertIn('final_reply', report)


    def test_observe_would_have_decided_rewrite_without_critical_fail(self):
        observe = GatekeeperOrchestrator(
            self.rubrics,
            GatekeeperConfig(mode=Mode.OBSERVE, critical_rubrics=[]),
        ).evaluate(
            [{"role": "user", "text": "Geef bron"}],
            'Bron: onbekend in 2024.',
            [],
        )
        self.assertEqual(observe.global_decision.value, 'PASS')
        self.assertEqual(observe.action_taken.value, 'PASS')
        self.assertEqual(observe.would_have_decided.value, 'REWRITE')

    def test_index_order_files_mismatch_collects_warning(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            (td_path / 'C_CoRegulatie.eat').write_text(Path('rubrics/C_CoRegulatie.eat').read_text(encoding='utf-8'), encoding='utf-8')
            index = {
                'meta': {'version': 2.0, 'mode': 'runtime', 'locked': True},
                'index': {'order': ['B_BiasCorrectieFairness'], 'files': ['C_CoRegulatie.eat']},
            }
            (td_path / 'index.eat').write_text(json.dumps(index), encoding='utf-8')
            gate = EATRuntimeGatekeeper(rubric_dir=td)
            self.assertTrue(any('index.order and index.files' in w for w in gate.index_warnings))

    def test_gatekeep_critical_fail_blocks_with_guidance(self):
        gate = GatekeeperOrchestrator(self.rubrics, GatekeeperConfig(mode=Mode.GATEKEEP))
        report = gate.evaluate([{"role": "user", "text": "fact check"}], 'Bron: niet-bestaand 2024', [])
        self.assertEqual(report.global_decision, Decision.BLOCK)
        self.assertTrue(len(report.rewrite_instructions) > 0)

    def test_keyword_calibration_agency_boosts_coregulatie(self):
        base = extract_features([], 'We kunnen verder.', [{"type": "doc"}])
        agency = extract_features([], 'Jij bepaalt welke optie je kiest en waarom.', [{"type": "doc"}])
        base_score = quick_score_for_rubric('C_CoRegulatie', base, [])
        agency_score = quick_score_for_rubric('C_CoRegulatie', agency, [])
        self.assertGreater(agency_score, base_score)

    def test_keyword_calibration_answer_is_penalizes_taakdichtheid(self):
        neutral = extract_features([], 'Laten we stap voor stap werken met een hint.', [])
        dominant = extract_features([], 'Het antwoord is 42, dus het is opgelost.', [])
        neutral_score = quick_score_for_rubric('TD_Taakdichtheid', neutral, [])
        dominant_score = quick_score_for_rubric('TD_Taakdichtheid', dominant, [])
        self.assertLess(dominant_score, neutral_score)


if __name__ == '__main__':
    unittest.main()
