import json
import subprocess
import sys
import unittest
import zipfile
from pathlib import Path

from eatme.evaluator import GatekeeperOrchestrator
from eatme.models import GatekeeperConfig, Mode
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

        self.assertEqual(observe.action_taken.value, 'PASS')
        self.assertEqual(nudge.global_decision.value, 'NUDGE')
        self.assertEqual(correct.global_decision.value, 'REWRITE')
        self.assertEqual(gate.global_decision.value, 'BLOCK')


if __name__ == '__main__':
    unittest.main()
