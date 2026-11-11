"""Gera ou verifica o freeze definitivo da campanha final (nenhuma simulação é executada).

    python scripts/build_final_freeze.py --scientific-source-sha <SHA> --check
    python scripts/build_final_freeze.py --scientific-source-sha <SHA>          # gera
    python scripts/build_final_freeze.py --verify [--scientific-source-sha <SHA>]

O SHA do commit-fonte científico nunca é fixado no código: não pode ser conhecido antes de esse
commit existir, então é informado explicitamente e validado. Deve existir, ser ancestral de HEAD
(o próprio HEAD é válido, assim como um descendente posterior que só tenha evidências) e sua árvore
científica deve ser igual à atual; a árvore de trabalho deve estar limpa. As configs congeladas
nunca são reescritas.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

from traffic_agents.experiments.final_freeze import (
    FREEZE_DOCS_DIR,
    MANIFEST_FILE_NAME,
    FinalFreezeError,
    generate_definitive_freeze,
    scientific_spec,
    validate_final_campaign,
    verify_freeze_manifest,
)
from traffic_agents.experiments.freeze_hashing import (
    FreezeHashingError,
    check_freeze_preconditions,
    manifest_file_sha256,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", maxsplit=1)[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Check preconditions only.")
    mode.add_argument("--verify", action="store_true", help="Verify the committed manifest.")
    parser.add_argument(
        "--scientific-source-sha",
        default=None,
        help="Commit that contains the scientific source (required except for --verify).",
    )
    args = parser.parse_args(argv)

    try:
        return _run(args)
    except (FinalFreezeError, FreezeHashingError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _run(args: argparse.Namespace) -> int:
    if args.verify:
        problems = verify_freeze_manifest(
            REPO_ROOT, scientific_source_sha=args.scientific_source_sha
        )
        for problem in problems:
            print(f"MISMATCH {problem}", file=sys.stderr)
        print("freeze verification:", "FAILED" if problems else "OK")
        return 1 if problems else 0

    if not args.scientific_source_sha:
        print("error: --scientific-source-sha is required", file=sys.stderr)
        return 2

    if args.check:
        pre = check_freeze_preconditions(REPO_ROOT, scientific_spec(), args.scientific_source_sha)
        print(f"head={pre.head_sha}")
        print(f"scientific_source_git_sha={pre.scientific_source_git_sha}")
        print(f"source_exists={pre.source_exists}")
        print(f"working_tree_dirty={pre.working_tree_dirty_at_input_inspection}")
        print(f"source_is_ancestor_of_head={pre.source_is_ancestor_of_head}")
        print(f"scientific_tree_sha256={pre.scientific_tree_sha256}")
        print(f"source_scientific_tree_sha256={pre.source_scientific_tree_sha256}")
        for failure in pre.failures():
            print(f"FAIL {failure}", file=sys.stderr)
        return 0 if pre.ok else 1

    generated_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    written, pre = generate_definitive_freeze(
        REPO_ROOT,
        generated_at=generated_at,
        scientific_source_sha=args.scientific_source_sha,
    )
    report = validate_final_campaign(REPO_ROOT)
    for path in written:
        print(path.relative_to(REPO_ROOT).as_posix())
    manifest = REPO_ROOT / FREEZE_DOCS_DIR / MANIFEST_FILE_NAME
    print(f"scientific_source_git_sha={pre.scientific_source_git_sha}")
    print(f"scientific_tree_sha256={pre.scientific_tree_sha256}")
    print(f"FREEZE_MANIFEST_SHA256={manifest_file_sha256(manifest)}")
    print(f"runs={report['total_run_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
