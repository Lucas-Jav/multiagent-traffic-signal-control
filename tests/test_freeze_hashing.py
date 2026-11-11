from __future__ import annotations

import ast
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from traffic_agents.experiments import final_freeze as ff
from traffic_agents.experiments.freeze_hashing import (
    FileHashes,
    FreezeHashingError,
    FreezePreconditions,
    GitCommitSource,
    ScientificSpec,
    TreeRoot,
    WorkingTreeSource,
    canonical_sha256,
    check_freeze_preconditions,
    compute_scientific_tree,
    diff_trees,
    fingerprint_entries,
    hash_file_bytes,
    is_text_path,
    raw_byte_sha256,
    semantic_metadata_sha256,
)

REPO = Path(__file__).resolve().parents[1]
SCENARIO_DIR = REPO / "scenarios" / "grid_3x3"


def _crlf(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")


def _lf(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


# --- hash de texto canônico -----------------------------------------------------------------------
def test_lf_and_crlf_have_different_raw_but_equal_canonical_hashes() -> None:
    lf = b"a: 1\nb: 2\n"
    crlf = b"a: 1\r\nb: 2\r\n"
    assert raw_byte_sha256(lf) != raw_byte_sha256(crlf)
    assert canonical_sha256(lf) == canonical_sha256(crlf)


def test_lone_cr_is_normalised() -> None:
    assert canonical_sha256(b"a\rb\n") == canonical_sha256(b"a\nb\n")


def test_content_change_changes_canonical_hash() -> None:
    assert canonical_sha256(b"a: 1\n") != canonical_sha256(b"a: 2\n")


@pytest.mark.parametrize(
    ("original", "changed"),
    [
        (b"a: 1\n", b"a: 1 \n"),  # espaço no fim é conteúdo
        (b"a: 1\n", b"a: 1"),  # nova linha final é conteúdo
        (b"a:\n  b: 1\n", b"a:\n    b: 1\n"),  # indentação é conteúdo
        (b"a: 1\n\nb: 2\n", b"a: 1\nb: 2\n"),  # linhas em branco são conteúdo
    ],
)
def test_only_line_endings_are_normalised(original: bytes, changed: bytes) -> None:
    assert canonical_sha256(original) != canonical_sha256(changed)


def test_utf8_bom_is_ignored_and_other_characters_preserved() -> None:
    text = "descrição: ônibus\n".encode()
    assert canonical_sha256(b"\xef\xbb\xbf" + text) == canonical_sha256(text)
    assert canonical_sha256(text) != canonical_sha256(b"descricao: onibus\n")


def test_invalid_utf8_text_is_rejected() -> None:
    with pytest.raises(FreezeHashingError, match="UTF-8"):
        canonical_sha256(b"\xff\xfe\x00bad")


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("scenarios/grid_3x3/network.net.xml", True),
        ("scenarios/grid_3x3/routes_s1_seed_42.rou.xml", True),
        ("scenarios/grid_3x3/routes_s1_seed_42.metadata.json", True),
        ("experiments/configs/final_main.yaml", True),
        ("pyproject.toml", True),
        ("uv.lock", True),
        ("docs/x.md", True),
        ("a.csv", True),
        ("notes.txt", True),
        ("src/x.py", True),
        ("movie.mp4", False),
        ("frame.png", False),
        ("blob.bin", False),
        ("noextension", False),
    ],
)
def test_text_file_policy(path: str, expected: bool) -> None:
    assert is_text_path(path) is expected


def test_binary_files_use_raw_hash_only() -> None:
    hashes = hash_file_bytes("frame.png", b"\x89PNG\r\n\x1a\n\x00")
    assert (hashes.mode, hashes.canonical_sha256, hashes.semantic_sha256) == ("raw", None, None)
    assert hashes.authoritative == hashes.raw_byte_sha256


def test_text_files_keep_both_hashes() -> None:
    hashes = hash_file_bytes("a.yaml", b"a: 1\r\n")
    assert hashes.mode == "canonical"
    assert hashes.raw_byte_sha256 != hashes.canonical_sha256
    assert hashes.authoritative == hashes.canonical_sha256


# --- arquivos reais: cópias LF <-> CRLF -----------------------------------------------------------
REAL_FILES = [
    SCENARIO_DIR / "network.net.xml",
    SCENARIO_DIR / "routes_s4_seed_42.rou.xml",
    SCENARIO_DIR / "routes_s4_seed_42.metadata.json",
    REPO / "experiments" / "fixed_time" / "b0_fixed_calibrated.json",
    REPO / "experiments" / "configs" / "final_main.yaml",
    REPO / "experiments" / "configs" / "final_s5_packet_loss.yaml",
]


@pytest.mark.parametrize("path", REAL_FILES, ids=lambda p: p.name)
def test_real_files_are_line_ending_invariant(path: Path, tmp_path: Path) -> None:
    original = path.read_bytes()
    lf_copy = tmp_path / ("lf_" + path.name)
    crlf_copy = tmp_path / ("crlf_" + path.name)
    lf_copy.write_bytes(_lf(original))
    crlf_copy.write_bytes(_crlf(original))
    lf, crlf = lf_copy.read_bytes(), crlf_copy.read_bytes()
    assert raw_byte_sha256(lf) != raw_byte_sha256(crlf)
    assert canonical_sha256(lf) == canonical_sha256(crlf) == canonical_sha256(original)


def test_b0_plan_hashes_are_exposed_and_content_is_unchanged() -> None:
    path = REPO / ff.B0_PLAN_RELATIVE_PATH
    data = path.read_bytes()
    assert canonical_sha256(data) == ff.B0_CANONICAL_SHA256
    assert canonical_sha256(_crlf(data)) == canonical_sha256(_lf(data)) == ff.B0_CANONICAL_SHA256
    assert raw_byte_sha256(data) in {raw_byte_sha256(_crlf(data)), raw_byte_sha256(_lf(data))}


# --- hash semântico de metadados ------------------------------------------------------------------
def _metadata_bytes() -> bytes:
    return (SCENARIO_DIR / "routes_s3_seed_6841.metadata.json").read_bytes()


def test_semantic_hash_ignores_only_generated_at() -> None:
    payload = json.loads(_metadata_bytes())
    changed = dict(payload, generated_at="1999-01-01T00:00:00Z")
    a = json.dumps(payload, indent=2).encode()
    b = json.dumps(changed, indent=4).encode()  # formatação diferente também
    assert raw_byte_sha256(a) != raw_byte_sha256(b)
    assert semantic_metadata_sha256(a) == semantic_metadata_sha256(b)
    removed = {k: v for k, v in payload.items() if k != "generated_at"}
    assert semantic_metadata_sha256(json.dumps(removed).encode()) == semantic_metadata_sha256(a)


@pytest.mark.parametrize(
    "field",
    [
        "seed",
        "demand_level",
        "demand_profile",
        "shock_start_seconds",
        "turning_ratios",
        "offered",
        "entries",
        "scenario_id",
        "route_hash",
        "network_hash",
        "generator_version",
    ],
)
def test_every_scientific_metadata_field_changes_the_semantic_hash(field: str) -> None:
    payload = json.loads(_metadata_bytes())
    original = semantic_metadata_sha256(json.dumps(payload).encode())
    altered = json.loads(json.dumps(payload))
    value = altered[field]
    if isinstance(value, bool):
        altered[field] = not value
    elif isinstance(value, int | float):
        altered[field] = value + 1
    elif isinstance(value, str):
        altered[field] = value + "x"
    elif isinstance(value, list):
        altered[field] = [*value, "extra"]
    elif isinstance(value, dict):
        altered[field] = {**value, "extra": 1}
    else:
        altered[field] = "changed"
    assert semantic_metadata_sha256(json.dumps(altered).encode()) != original


def test_nested_generated_at_is_not_removed() -> None:
    base = {"seed": 1, "generated_at": "x", "inner": {"generated_at": "a"}}
    other = {"seed": 1, "generated_at": "y", "inner": {"generated_at": "b"}}
    assert semantic_metadata_sha256(json.dumps(base).encode()) != semantic_metadata_sha256(
        json.dumps(other).encode()
    )


def test_unknown_timestamp_like_fields_are_not_removed() -> None:
    base = {"seed": 1, "created_at": "x"}
    other = {"seed": 1, "created_at": "y"}
    assert semantic_metadata_sha256(json.dumps(base).encode()) != semantic_metadata_sha256(
        json.dumps(other).encode()
    )


def test_semantic_hash_is_only_for_metadata_json() -> None:
    with pytest.raises(FreezeHashingError):
        hash_file_bytes("config.yaml", b"a: 1\n", semantic=True)
    with pytest.raises(FreezeHashingError):
        hash_file_bytes("blob.bin", b"1", semantic=True)
    with pytest.raises(FreezeHashingError, match="JSON"):
        semantic_metadata_sha256(b"[1, 2]")


def test_semantic_hash_is_stable_across_line_endings() -> None:
    data = _metadata_bytes()
    assert semantic_metadata_sha256(_crlf(data)) == semantic_metadata_sha256(_lf(data))
    hashes = hash_file_bytes("routes_s3_seed_6841.metadata.json", data, semantic=True)
    assert hashes.mode == "semantic"
    assert hashes.authoritative == hashes.semantic_sha256
    assert hashes.raw_byte_sha256 and hashes.canonical_sha256


def test_regenerated_extension_seed_metadata_differs_only_by_generated_at(tmp_path: Path) -> None:
    """Regenera em um diretório temporário (nunca no repositório) e compara com os arquivos
    commitados.
    """

    sys.path.insert(0, str(REPO / "scripts"))
    try:
        import generate_scenarios  # type: ignore[import-not-found]
    finally:
        sys.path.pop(0)
    for name in ("scenario.yaml", "network.net.xml", "metadata.json"):
        shutil.copy(SCENARIO_DIR / name, tmp_path / name)
    generate_scenarios.generate(tmp_path, seeds=tuple(ff.EXTENSION_SEEDS), write_base_files=False)
    compared = 0
    for scenario in ff.MAIN_SCENARIOS:
        for seed in ff.EXTENSION_SEEDS:
            name = ff.route_metadata_file_name(scenario, seed)
            committed = (SCENARIO_DIR / name).read_bytes()
            regenerated = (tmp_path / name).read_bytes()
            # o gerador agora também registra hashes brutos/canônicos de artefatos (Prompt 59.1C);
            # fora
            # esses campos e os hashes brutos dependentes de quebra de linha, a identidade é igual
            ignored = {
                "route_hash",
                "network_hash",
                "route_raw_sha256",
                "route_canonical_sha256",
                "network_raw_sha256",
                "network_canonical_sha256",
            }
            comparable = [
                json.dumps({k: v for k, v in json.loads(data).items() if k not in ignored}).encode()
                for data in (committed, regenerated)
            ]
            assert semantic_metadata_sha256(comparable[0]) == semantic_metadata_sha256(
                comparable[1]
            ), name
            assert json.loads(committed)["generated_at"] != json.loads(regenerated)["generated_at"]
            # os próprios arquivos científicos de rota são idênticos
            route = ff.route_file_name(scenario, seed)
            assert canonical_sha256((SCENARIO_DIR / route).read_bytes()) == canonical_sha256(
                (tmp_path / route).read_bytes()
            )
            compared += 1
    assert compared == 20


# --- árvore científica ----------------------------------------------------------------------------
def _entry(path: str, content: bytes = b"x\n") -> FileHashes:
    return hash_file_bytes(path, content)


def test_tree_fingerprint_is_order_independent_and_path_normalised() -> None:
    a, b = _entry("src/a.py"), _entry("src/b.py", b"y\n")
    assert fingerprint_entries([a, b]) == fingerprint_entries([b, a])
    backslashed = hash_file_bytes("src\\a.py", b"x\n")
    assert backslashed.path == "src/a.py"
    assert fingerprint_entries([backslashed, b]) == fingerprint_entries([a, b])


def test_tree_fingerprint_follows_the_documented_record_format() -> None:
    import hashlib

    a, b = _entry("z/b.py", b"y\n"), _entry("a/a.yaml", b"k: 1\n")
    expected = (
        f"a/a.yaml\tcanonical\t{b.canonical_sha256}\nz/b.py\tcanonical\t{a.canonical_sha256}\n"
    )
    assert fingerprint_entries([a, b]) == hashlib.sha256(expected.encode()).hexdigest()


def test_tree_fingerprint_changes_with_content_path_and_mode() -> None:
    base = fingerprint_entries([_entry("a.py")])
    assert fingerprint_entries([_entry("a.py", b"changed\n")]) != base
    assert fingerprint_entries([_entry("b.py")]) != base
    metadata = hash_file_bytes("m.metadata.json", b'{"seed": 1}\n', semantic=True)
    plain = hash_file_bytes("m.metadata.json", b'{"seed": 1}\n')
    assert fingerprint_entries([metadata]) != fingerprint_entries([plain])


def test_spec_includes_science_and_excludes_tooling_and_replay() -> None:
    spec = ff.scientific_spec()
    paths = spec.paths(WorkingTreeSource(REPO))
    assert "experiments/configs/final_main.yaml" in paths
    assert "experiments/configs/final_s5_packet_loss.yaml" in paths
    assert "experiments/fixed_time/b0_fixed_calibrated.json" in paths
    assert "scenarios/grid_3x3/network.net.xml" in paths
    assert "src/traffic_agents/experiments/metric_definitions.py" in paths
    assert "src/traffic_agents/controllers/cooperative_compact.py" in paths
    assert "analysis/statistics.py" in paths
    assert "uv.lock" in paths
    assert not any(path.startswith("src/traffic_agents/replay/") for path in paths)
    assert not any(path.startswith(("tests/", "docs/", "artifacts/")) for path in paths)
    for tooling in ff.FREEZE_TOOLING_FILES:
        assert tooling not in paths
    assert "scenarios/grid_3x3/viewsettings.xml" not in paths
    assert len(spec.semantic_files) == 40
    assert all(path in paths for path in spec.semantic_files)
    scenario_yaml = [p for p in paths if "/scenario_" in p]
    assert len(scenario_yaml) == 40
    assert paths == sorted(paths)


def test_scientific_modules_never_import_freeze_or_replay_tooling() -> None:
    forbidden = ("final_freeze", "freeze_hashing", "replay")
    spec = ff.scientific_spec()
    for path in spec.paths(WorkingTreeSource(REPO)):
        if not path.endswith(".py"):
            continue
        tree = ast.parse((REPO / path).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or "", *(alias.name for alias in node.names)]
            for name in names:
                assert not any(part in forbidden for part in name.split(".")), (path, name)


def test_scientific_tree_of_the_working_tree_is_deterministic() -> None:
    spec = ff.scientific_spec()
    first = compute_scientific_tree(spec, WorkingTreeSource(REPO))
    second = compute_scientific_tree(spec, WorkingTreeSource(REPO))
    assert first.sha256 == second.sha256 and first.entries == second.entries


def test_experiment_freeze_module_belongs_to_the_scientific_tree() -> None:
    """freeze.py roda dentro do ExperimentRunner (validação + campos do manifesto de execução): é
    código de execução, então pela regra documentada faz parte da árvore científica, ao contrário
    das ferramentas de freeze."""

    paths = ff.scientific_spec().paths(WorkingTreeSource(REPO))
    assert "src/traffic_agents/experiments/freeze.py" in paths
    assert "src/traffic_agents/experiments/text_hashing.py" in paths
    assert "src/traffic_agents/experiments/legacy_artifact_hashes.py" in paths
    assert "src/traffic_agents/experiments/freeze_hashing.py" not in paths
    assert "src/traffic_agents/experiments/final_freeze.py" not in paths


# --- pré-condições do git em um repositório descartável -------------------------------------------
def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        [
            "git",
            "-c",
            "user.name=t",
            "-c",
            "user.email=t@example.com",
            "-c",
            "commit.gpgsign=false",
            "-C",
            str(repo),
            *args,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout.strip()


@pytest.fixture
def mini_repo(tmp_path: Path) -> tuple[Path, ScientificSpec, str]:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "tools").mkdir()
    (repo / "src" / "science.py").write_text("VALUE = 1\n", encoding="utf-8", newline="\n")
    (repo / "src" / "meta.metadata.json").write_text(
        '{"seed": 1, "generated_at": "t0"}\n', encoding="utf-8", newline="\n"
    )
    (repo / "config.yaml").write_text("a: 1\n", encoding="utf-8", newline="\n")
    (repo / "tools" / "freeze_tool.py").write_text("T = 1\n", encoding="utf-8", newline="\n")
    _git(repo.parent, "init", str(repo))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "source")
    spec = ScientificSpec(
        tree_roots=(TreeRoot("src", (".py",)),),
        fixed_files=("config.yaml",),
        semantic_files=("src/meta.metadata.json",),
    )
    return repo, spec, _git(repo, "rev-parse", "HEAD")


def test_preconditions_pass_on_clean_source_commit(
    mini_repo: tuple[Path, ScientificSpec, str],
) -> None:
    repo, spec, source = mini_repo
    pre = check_freeze_preconditions(repo, spec, source)
    assert pre.ok and not pre.working_tree_dirty_at_input_inspection
    assert pre.source_is_ancestor_of_head and pre.failures() == []


def test_tooling_only_commit_is_allowed(mini_repo: tuple[Path, ScientificSpec, str]) -> None:
    repo, spec, source = mini_repo
    (repo / "tools" / "freeze_tool.py").write_text("T = 2\n", encoding="utf-8", newline="\n")
    (repo / "docs.md").write_text("freeze evidence\n", encoding="utf-8", newline="\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "tooling")
    pre = check_freeze_preconditions(repo, spec, source)
    assert pre.head_sha != source
    assert pre.ok and pre.scientific_changes_since_source == ()
    assert pre.scientific_tree_sha256 == pre.source_scientific_tree_sha256


def test_line_ending_only_change_is_not_a_scientific_change(
    mini_repo: tuple[Path, ScientificSpec, str],
) -> None:
    repo, spec, source = mini_repo
    (repo / "config.yaml").write_bytes(b"a: 1\r\n")
    (repo / "src" / "science.py").write_bytes(b"VALUE = 1\r\n")
    _git(repo, "-c", "core.autocrlf=false", "add", "-A")
    _git(repo, "-c", "core.autocrlf=false", "commit", "-m", "crlf")
    pre = check_freeze_preconditions(repo, spec, source)
    assert pre.ok and pre.scientific_changes_since_source == ()


def test_generated_at_only_change_is_not_a_scientific_change(
    mini_repo: tuple[Path, ScientificSpec, str],
) -> None:
    repo, spec, source = mini_repo
    (repo / "src" / "meta.metadata.json").write_text(
        '{"seed": 1, "generated_at": "t1"}\n', encoding="utf-8", newline="\n"
    )
    _git(repo, "commit", "-am", "regenerate metadata")
    assert check_freeze_preconditions(repo, spec, source).ok


@pytest.mark.parametrize(
    ("relative", "content", "expected"),
    [
        ("src/science.py", "VALUE = 2\n", "changed: src/science.py"),
        ("config.yaml", "a: 2\n", "changed: config.yaml"),
        ("src/meta.metadata.json", '{"seed": 2, "generated_at": "t0"}\n', "changed: src/meta"),
        ("src/new_controller.py", "X = 1\n", "added: src/new_controller.py"),
    ],
)
def test_scientific_change_after_source_is_detected(
    mini_repo: tuple[Path, ScientificSpec, str], relative: str, content: str, expected: str
) -> None:
    repo, spec, source = mini_repo
    (repo / relative).write_text(content, encoding="utf-8", newline="\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "science changed")
    pre = check_freeze_preconditions(repo, spec, source)
    assert not pre.ok
    assert any(change.startswith(expected) for change in pre.scientific_changes_since_source)
    assert any("scientific input changed" in failure for failure in pre.failures())


def test_removed_scientific_file_is_detected(mini_repo: tuple[Path, ScientificSpec, str]) -> None:
    repo, spec, source = mini_repo
    (repo / "src" / "science.py").unlink()
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "remove")
    pre = check_freeze_preconditions(repo, spec, source)
    assert "removed: src/science.py" in pre.scientific_changes_since_source


def test_dirty_working_tree_fails_the_preconditions(
    mini_repo: tuple[Path, ScientificSpec, str],
) -> None:
    repo, spec, source = mini_repo
    (repo / "untracked.txt").write_text("x", encoding="utf-8")
    pre = check_freeze_preconditions(repo, spec, source)
    assert pre.working_tree_dirty_at_input_inspection and not pre.ok
    assert "working tree is not clean" in pre.failures()


def test_source_must_be_an_ancestor_of_head(mini_repo: tuple[Path, ScientificSpec, str]) -> None:
    repo, spec, source = mini_repo
    _git(repo, "checkout", "--orphan", "other")
    (repo / "unrelated.txt").write_text("x\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "unrelated history")
    pre = check_freeze_preconditions(repo, spec, source)
    assert not pre.source_is_ancestor_of_head and not pre.ok


def test_git_commit_source_reads_blobs_not_the_working_tree(
    mini_repo: tuple[Path, ScientificSpec, str],
) -> None:
    repo, spec, source = mini_repo
    (repo / "src" / "science.py").write_text("VALUE = 99\n", encoding="utf-8")
    committed = compute_scientific_tree(spec, GitCommitSource(repo, source))
    working = compute_scientific_tree(spec, WorkingTreeSource(repo))
    assert diff_trees(committed, working) == ["changed: src/science.py"]


def test_missing_required_scientific_file_is_an_error(tmp_path: Path) -> None:
    spec = ScientificSpec(tree_roots=(), fixed_files=("missing.yaml",))
    with pytest.raises(FreezeHashingError, match="missing"):
        compute_scientific_tree(spec, WorkingTreeSource(tmp_path))


# --- fluxo de geração definitivo -----------------------------------------------------------------
def _preconditions(**overrides: object) -> FreezePreconditions:
    tree = compute_scientific_tree(ff.scientific_spec(), WorkingTreeSource(REPO))
    values: dict[str, object] = {
        "head_sha": "6" * 40,
        "scientific_source_git_sha": "5" * 40,
        "working_tree_dirty_at_input_inspection": False,
        "source_is_ancestor_of_head": True,
        "source_exists": True,
        "scientific_tree_sha256": tree.sha256,
        "source_scientific_tree_sha256": tree.sha256,
        "scientific_changes_since_source": (),
        "tree": tree,
    }
    values.update(overrides)
    return FreezePreconditions(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"working_tree_dirty_at_input_inspection": True}, "working tree is not clean"),
        ({"source_exists": False, "source_is_ancestor_of_head": False}, "does not exist"),
        ({"source_is_ancestor_of_head": False}, "not an ancestor"),
        (
            {"scientific_changes_since_source": ("changed: src/traffic_agents/controllers/x.py",)},
            "scientific input changed",
        ),
    ],
)
def test_generation_refuses_and_writes_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, overrides: dict[str, object], message: str
) -> None:
    refused = _preconditions(**overrides)
    monkeypatch.setattr(ff, "check_freeze_preconditions", lambda *args, **kwargs: refused)
    with pytest.raises(ff.FreezePreconditionError, match=message):
        ff.generate_definitive_freeze(
            tmp_path, generated_at="2026-01-01T00:00:00Z", scientific_source_sha="5" * 40
        )
    assert list(tmp_path.iterdir()) == []


def test_generation_passes_the_supplied_sha_to_the_preconditions(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    seen: list[str] = []

    def fake(root: Path, spec: ScientificSpec, sha: str) -> FreezePreconditions:
        seen.append(sha)
        return _preconditions(working_tree_dirty_at_input_inspection=True)

    monkeypatch.setattr(ff, "check_freeze_preconditions", fake)
    with pytest.raises(ff.FreezePreconditionError):
        ff.generate_definitive_freeze(
            tmp_path, generated_at="2026-01-01T00:00:00Z", scientific_source_sha="abc1234"
        )
    assert seen == ["abc1234"]


# --- validação do SHA-fonte (repositórios descartáveis) -------------------------------------------
def test_nonexistent_source_sha_is_rejected(mini_repo: tuple[Path, ScientificSpec, str]) -> None:
    repo, spec, _ = mini_repo
    for bogus in ("deadbeef" * 5, "abc1234", "not-a-sha", "HEAD", "--help", ""):
        pre = check_freeze_preconditions(repo, spec, bogus)
        assert not pre.source_exists and not pre.ok
        assert any("does not exist" in failure for failure in pre.failures())


def test_abbreviated_source_sha_is_resolved_to_the_full_sha(
    mini_repo: tuple[Path, ScientificSpec, str],
) -> None:
    repo, spec, source = mini_repo
    pre = check_freeze_preconditions(repo, spec, source[:10])
    assert pre.ok and pre.scientific_source_git_sha == source


def test_head_equal_to_source_is_valid_before_the_freeze_commit(
    mini_repo: tuple[Path, ScientificSpec, str],
) -> None:
    repo, spec, source = mini_repo
    pre = check_freeze_preconditions(repo, spec, source)
    assert pre.head_sha == source and pre.ok


def test_evidence_only_descendant_is_valid_after_the_freeze_commit(
    mini_repo: tuple[Path, ScientificSpec, str],
) -> None:
    repo, spec, source = mini_repo
    evidence = repo / "docs" / "evidencias"
    evidence.mkdir(parents=True)
    (evidence / "manifest.json").write_text("{}\n", encoding="utf-8", newline="\n")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "freeze record")
    pre = check_freeze_preconditions(repo, spec, source)
    assert pre.head_sha != source and pre.ok
    assert pre.scientific_tree_sha256 == pre.source_scientific_tree_sha256


def test_new_source_commit_supersedes_the_old_one(
    mini_repo: tuple[Path, ScientificSpec, str],
) -> None:
    """Após uma mudança científica, o SHA ANTIGO é rejeitado e o SHA do NOVO commit é válido."""

    repo, spec, old = mini_repo
    (repo / "src" / "science.py").write_text("VALUE = 2\n", encoding="utf-8", newline="\n")
    _git(repo, "commit", "-am", "scientific change")
    new = _git(repo, "rev-parse", "HEAD")
    assert not check_freeze_preconditions(repo, spec, old).ok
    assert check_freeze_preconditions(repo, spec, new).ok


def test_sha_that_is_not_an_ancestor_is_rejected(
    mini_repo: tuple[Path, ScientificSpec, str],
) -> None:
    repo, spec, source = mini_repo
    _git(repo, "checkout", "--orphan", "other")
    (repo / "unrelated.txt").write_text("x\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "unrelated history")
    pre = check_freeze_preconditions(repo, spec, source)
    assert pre.source_exists and not pre.source_is_ancestor_of_head and not pre.ok


def _build_script() -> object:
    sys.path.insert(0, str(REPO / "scripts"))
    try:
        import build_final_freeze  # type: ignore[import-not-found]
    finally:
        sys.path.pop(0)
    return build_final_freeze


def test_cli_requires_a_source_sha_and_rejects_a_bogus_one(
    capsys: pytest.CaptureFixture[str],
) -> None:
    cli = _build_script()
    assert cli.main(["--check"]) == 2  # type: ignore[attr-defined]
    assert "--scientific-source-sha is required" in capsys.readouterr().err
    assert cli.main(["--check", "--scientific-source-sha", "deadbeef" * 5]) == 1  # type: ignore[attr-defined]
    assert "does not exist" in capsys.readouterr().err
    assert cli.main(["--scientific-source-sha", "deadbeef" * 5]) == 1  # type: ignore[attr-defined]
    assert "does not exist" in capsys.readouterr().err


# --- segurança do B0 histórico --------------------------------------------------------------------
def test_final_comparisons_use_explicit_calibrated_b0() -> None:
    from analysis.statistics import CONTROLLER_ALIASES, DEFAULT_CONTROLLER_PAIRS

    controllers = {controller for pair in DEFAULT_CONTROLLER_PAIRS for controller in pair}
    assert "B0_FIXED_CALIBRATED" in controllers
    assert controllers.isdisjoint({"B0", *ff.HISTORICAL_CONTROLLERS})
    assert tuple(DEFAULT_CONTROLLER_PAIRS) == ff.FINAL_CONTROLLER_PAIRS
    ff.reject_historical_b0(sorted(controllers))
    # o alias histórico ainda existe no código de análise (congelado), daí a salvaguarda abaixo
    assert CONTROLLER_ALIASES["B0"] == "B0_FIXED"


@pytest.mark.parametrize("label", ["B0", "B0_FIXED", "B0_FIXED_STATIC", "B0_FIXED_STATIC_V2"])
def test_historical_b0_labels_are_rejected(label: str) -> None:
    with pytest.raises(ff.FinalFreezeError, match="historical B0"):
        ff.reject_historical_b0(["B2_LOCAL_PRESSURE", label])


def test_final_run_matrix_never_uses_historical_b0() -> None:
    labels = [run.controller_id for run in (*ff.main_runs(), *ff.s5_runs())]
    ff.reject_historical_b0(labels)
    assert "B0_FIXED_CALIBRATED" in labels
