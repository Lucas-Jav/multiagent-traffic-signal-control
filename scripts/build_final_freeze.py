"""Generate the frozen final-campaign configs and the freeze manifest (no simulations are run).

python scripts/build_final_freeze.py          # write configs + manifest + evidence
python scripts/build_final_freeze.py --verify # recompute hashes against the committed manifest
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from traffic_agents.experiments.final_freeze import (
    FinalFreezeError,
    build_freeze_manifest,
    validate_final_campaign,
    verify_freeze_manifest,
    write_final_configs,
    write_freeze_evidence,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", maxsplit=1)[0])
    parser.add_argument("--verify", action="store_true", help="Verify the committed manifest.")
    args = parser.parse_args(argv)

    if args.verify:
        problems = verify_freeze_manifest(REPO_ROOT)
        validate_final_campaign(REPO_ROOT)
        for problem in problems:
            print(f"MISMATCH {problem}", file=sys.stderr)
        print("freeze verification:", "FAILED" if problems else "OK")
        return 1 if problems else 0

    write_final_configs(REPO_ROOT)
    try:
        report = validate_final_campaign(REPO_ROOT)
    except FinalFreezeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    generated_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    manifest = build_freeze_manifest(REPO_ROOT, generated_at=generated_at)
    for path in write_freeze_evidence(REPO_ROOT, manifest):
        print(path.relative_to(REPO_ROOT).as_posix())
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
