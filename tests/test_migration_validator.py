import json
import tempfile
import unittest
from pathlib import Path

from eatme.migration import migrate_rubric, parse_legacy_rubric_text
from eatme.validator import EATValidator


LEGACY = """rubric:
  rubric_id: E_Test
  name: Test
  dimension: dim
  version: 9.3
  language: nl
  goal: \"Doel\"

bands:
  band 0.1-0.29:
    label: L1
    description: \"Desc1\"
    learner_obs:
      - A
    ai_obs:
      - B
    flag: F1
    fix: \"Fix1\"
  band 0.3-0.49:
    label: L2
    description: \"Desc2\"
    learner_obs:
      - C
    ai_obs:
      - D
    flag: F2
    fix: \"Fix2\"
  band 0.5-0.69:
    label: L3
    description: \"Desc3\"
    learner_obs:
      - E
    ai_obs:
      - F
    flag: F3
    fix: \"Fix3\"
  band 0.7-0.89:
    label: L4
    description: \"Desc4\"
    learner_obs:
      - G
    ai_obs:
      - H
    flag: F4
    fix: \"Fix4\"
  band 0.9-1.0:
    label: L5
    description: \"Desc5\"
    learner_obs:
      - I
    ai_obs:
      - J
    flag: F5
    fix: \"Fix5\"
"""


class MigrationValidatorTests(unittest.TestCase):
    def test_migration_converts_band_and_version(self):
        data = parse_legacy_rubric_text(LEGACY)
        migrated = migrate_rubric(data)
        self.assertEqual(migrated["meta"]["version"], 2.0)
        self.assertIn("rubric_version", migrated["rubric"])
        self.assertEqual(migrated["rubric"]["rubric_version"], "9.3")
        self.assertEqual(migrated["bands"][0]["score_min"], 0.1)
        self.assertEqual(migrated["bands"][0]["learner_obs"][0], "A")

    def test_validator_fails_missing_meta(self):
        v = EATValidator()
        issues = v.validate({"rubric": {}, "bands": []}, source="x")
        self.assertTrue(any("meta" in i.path for i in issues))

    def test_validator_fails_bad_ranges(self):
        rubric = {
            "meta": {"version": 2.0, "locked": True},
            "rubric": {
                "rubric_id": "R",
                "name": "N",
                "dimension": "D",
                "rubric_version": "9.3",
                "language": "nl",
                "goal": "g",
            },
            "bands": [
                {"score_min": 0.0, "score_max": 0.5, "label": "a", "description": "", "learner_obs": ["x"], "ai_obs": ["y"], "flag": "f", "fix": "z"},
                {"score_min": 0.6, "score_max": 1.0, "label": "b", "description": "", "learner_obs": ["x"], "ai_obs": ["y"], "flag": "f", "fix": "z"},
            ],
        }
        issues = EATValidator().validate(rubric, source="x")
        self.assertTrue(any("gap" in i.message for i in issues))

    def test_all_root_rubrics_validate(self):
        issues = EATValidator(tolerance=0.02).validate_path(Path("."))
        self.assertEqual([], issues)


if __name__ == "__main__":
    unittest.main()
