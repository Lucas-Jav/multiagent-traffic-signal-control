"""Deriva a tabela legada hash bruto -> hash canônico usada na validação de artefatos de rota.

Os metadados históricos de rota registram hashes de BYTES BRUTOS dos arquivos de rota/rede. Eles
dependem das quebras de linha do checkout, de modo que em outra plataforma o hash bruto deixa de
coincidir embora o conteúdo seja idêntico. Esta ferramenta registra, para cada artefato commitado,
o hash CANÔNICO esperado, indexado pelo hash bruto que os metadados já contêm. A validação aceita
uma divergência bruta apenas quando o hash canônico do arquivo é igual ao valor da tabela para o
hash bruto escrito nos metadados, de modo que um arquivo adulterado (ou metadados adulterados)
ainda é rejeitado.

As entradas são verificadas antes de serem confiáveis: o hash bruto atual do arquivo deve ser
igual ao hash bruto dos metadados, e o hash canônico do arquivo da árvore de trabalho deve ser
igual ao hash canônico do blob git commitado. Execute a partir da raiz do repositório:

    python scripts/build_legacy_route_hash_table.py            # reescreve o módulo
    python scripts/build_legacy_route_hash_table.py --check    # falha se o módulo estiver desatualizado
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from traffic_agents.experiments.text_hashing import canonical_sha256, raw_byte_sha256

REPO_ROOT = Path(__file__).resolve().parents[1]
SCENARIO_DIR = REPO_ROOT / "scenarios" / "grid_3x3"
TARGET = REPO_ROOT / "src" / "traffic_agents" / "experiments" / "legacy_artifact_hashes.py"

HEADER = '''"""Identidades de artefatos legados: hash BRUTO registrado -> hash CANÔNICO esperado.

GERADO por ``scripts/build_legacy_route_hash_table.py`` a partir dos artefatos de rota/rede
commitados. Não edite manualmente. Veja ``route_artifacts.py`` para saber como a tabela é usada:
uma divergência de hash bruto só é aceita quando o hash canônico do arquivo é igual ao valor
listado aqui para o hash bruto registrado nos metadados de rota (prova de que só as quebras de
linha diferem).
"""

# ruff: noqa: E501
from __future__ import annotations

from collections.abc import Mapping

'''


def _metadata_path(route_path: Path) -> Path:
    return route_path.with_name(route_path.name.replace(".rou.xml", ".metadata.json"))


def _committed_canonical(relative: str) -> str | None:
    completed = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "show", f"HEAD:{relative}"],
        capture_output=True,
        check=False,
    )
    return canonical_sha256(completed.stdout) if completed.returncode == 0 else None


def _verified(path: Path, recorded_raw: str) -> str:
    data = path.read_bytes()
    relative = path.relative_to(REPO_ROOT).as_posix()
    if raw_byte_sha256(data) != recorded_raw:
        msg = f"{relative}: current raw hash differs from the metadata raw hash"
        raise SystemExit(msg)
    canonical = canonical_sha256(data)
    committed = _committed_canonical(relative)
    if committed is not None and committed != canonical:
        msg = f"{relative}: working tree content differs from the committed blob"
        raise SystemExit(msg)
    return canonical


def build_tables() -> tuple[dict[str, str], dict[str, str]]:
    routes: dict[str, str] = {}
    networks: dict[str, str] = {}
    for route_path in sorted(SCENARIO_DIR.glob("routes_*.rou.xml")):
        metadata = json.loads(_metadata_path(route_path).read_text(encoding="utf-8"))
        routes[str(metadata["route_hash"])] = _verified(route_path, str(metadata["route_hash"]))
        network_hash = metadata.get("network_hash")
        if network_hash is not None:
            network_path = SCENARIO_DIR / "network.net.xml"
            networks[str(network_hash)] = _verified(network_path, str(network_hash))
    return routes, networks


def render(routes: dict[str, str], networks: dict[str, str]) -> str:
    def block(name: str, table: dict[str, str]) -> str:
        lines = [f"{name}: Mapping[str, str] = {{"]
        lines += [f'    "{raw}": "{canonical}",' for raw, canonical in sorted(table.items())]
        lines.append("}")
        return "\n".join(lines)

    return (
        HEADER
        + block("LEGACY_ROUTE_CANONICAL_BY_RAW", routes)
        + "\n\n"
        + block("LEGACY_NETWORK_CANONICAL_BY_RAW", networks)
        + "\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", maxsplit=1)[0])
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    routes, networks = build_tables()
    text = render(routes, networks)
    if args.check:
        stale = TARGET.read_text(encoding="utf-8").replace("\r\n", "\n") != text
        print("legacy hash table:", "STALE" if stale else "OK")
        return 1 if stale else 0
    TARGET.write_text(text, encoding="utf-8", newline="\n")
    print(f"routes={len(routes)} networks={len(networks)} -> {TARGET.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
