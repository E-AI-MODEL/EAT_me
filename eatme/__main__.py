from __future__ import annotations

import argparse
import json
from pathlib import Path

from .metrics import compute_metrics
from .migration import migrate_directory, migrate_file
from .validator import EATValidator


def cmd_validate(args: argparse.Namespace) -> int:
    validator = EATValidator()
    issues = validator.validate_path(args.path)
    if issues:
        for issue in issues:
            print(f"ERROR {issue.path}: {issue.message}")
        return 1
    print(f"OK: validated {args.path}")
    return 0


def cmd_migrate(args: argparse.Namespace) -> int:
    p = Path(args.path)
    if p.is_dir():
        changed = migrate_directory(p)
        print(f"Migrated {len(changed)} rubrics")
    else:
        migrate_file(p)
        print(f"Migrated {p}")
    return 0


def cmd_metrics(args: argparse.Namespace) -> int:
    out = compute_metrics(args.trace)
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="eatme",
        description="EAT_me CLI for JSON-based .eat v2 rubrics (no YAML dependency).",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_validate = sub.add_parser("validate", help="Validate JSON-based .eat v2 rubric file or directory")
    p_validate.add_argument("path")
    p_validate.set_defaults(func=cmd_validate)

    p_migrate = sub.add_parser("migrate", help="Migrate legacy rubric text into JSON-based .eat v2 format")
    p_migrate.add_argument("path")
    p_migrate.set_defaults(func=cmd_migrate)

    p_metrics = sub.add_parser("metrics", help="Compute metrics from JSONL trace logs")
    p_metrics.add_argument("trace")
    p_metrics.set_defaults(func=cmd_metrics)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
