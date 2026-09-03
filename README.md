# Multi-Agent Traffic Signal Control

[![CI](https://github.com/Lucas-Jav/multiagent-traffic-signal-control/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Lucas-Jav/multiagent-traffic-signal-control/actions/workflows/ci.yml)

Bootstrap Python para um projeto de controle semaforico multiagente.

O projeto ja possui uma primeira execucao real com Eclipse SUMO, usando uma rede
sintetica 3x3 e demanda sintetica reproduzivel. O baseline `B0_FIXED` formaliza a
execucao fixed-time: ele nao aplica ajustes adaptativos e deixa as fases definidas no
arquivo SUMO.

## Requisitos

- Python 3.12
- uv
- Eclipse SUMO 1.27.1

No Windows, se o comando `uv` nao for encontrado, adicione o diretorio do executavel ao
`PATH` do usuario:

```powershell
$uvPath = "$env:APPDATA\Python\Python313\Scripts"
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")

if ($userPath -notlike "*$uvPath*") {
    [Environment]::SetEnvironmentVariable("Path", "$uvPath;$userPath", "User")
}
```

Depois feche e abra o terminal novamente.

## Setup Inicial

```powershell
uv sync
```

Confira se o SUMO esperado esta disponivel:

```powershell
uv run python scripts/check_sumo.py
```

Saida esperada:

```text
SUMO detected
version=1.27.1
binary=<path>
```

## Gerar Artefatos Do Cenario

A rede 3x3 e as rotas ja estao versionadas, mas podem ser regeneradas de forma
idempotente.

Gerar rede:

```powershell
uv run python scripts/generate_grid.py
```

Gerar demanda sintetica `S1_BALANCED`:

```powershell
uv run python scripts/generate_routes.py scenarios/grid_3x3/scenario.yaml
```

Validar o YAML do cenario:

```powershell
uv run python scripts/validate_scenario.py scenarios/grid_3x3/scenario.yaml
```

## Executar Simulacao

Execucao headless:

```powershell
uv run python scripts/run_simulation.py --scenario scenarios/grid_3x3/scenario.yaml
```

Smoke explicito do baseline inicial:

```powershell
uv run python scripts/run_simulation.py --scenario scenarios/grid_3x3/scenario.yaml --controller-id B0_FIXED --max-steps 300
```

Execucao visual com `sumo-gui`:

```powershell
uv run python scripts/run_simulation.py --scenario scenarios/grid_3x3/scenario.yaml --gui --step-delay-ms 40 --max-steps 900
```

Use `--step-delay-ms` para desacelerar a visualizacao e `--max-steps` para limitar uma
execucao curta. Para rodar o cenario inteiro no GUI, remova `--max-steps`.

Cada execucao grava `artifacts/runs/<run_id>/manifest.json`, exceto quando usada a flag
`--no-manifest`.

## Container Headless

O container usa a imagem oficial versionada do Eclipse SUMO `ghcr.io/eclipse-sumo/sumo:v1_27_1`
e instala as dependencias Python a partir de `pyproject.toml` e `uv.lock`.

Build:

```powershell
docker compose build
```

Verificar SUMO:

```powershell
docker compose run --rm simulator sumo --version
```

Smoke:

```powershell
docker compose run --rm simulator traffic-agents simulation run --scenario scenarios/grid_3x3/scenario.yaml --controller B0_FIXED --seed 42 --max-steps 300
```

Experimento MVP:

```powershell
docker compose run --rm simulator traffic-agents experiment run --config experiments/configs/mvp1.yaml
```

Os volumes `scenarios`, `experiments` e `artifacts` sao montados no container; `docs` e montado
como somente leitura. A imagem roda com usuario nao-root.

## Execucao Do Package

```powershell
uv run python -m traffic_agents
```

Saida esperada:

```text
Traffic Multi-Agent Control
environment=development
```

## Validacao

```powershell
uv run pytest
uv run pytest -m "not sumo"
uv run ruff check .
uv run mypy src
```

O teste de integracao real com SUMO fica marcado com `sumo`:

```powershell
uv run pytest -m sumo
```

## Configuracao

As configuracoes iniciais sao lidas de variaveis de ambiente ou de um arquivo `.env` local:

- `APP_ENV`
- `LOG_LEVEL`
- `SUMO_BINARY`
- `SUMO_HOME`
- `ARTIFACTS_DIR`
- `DEFAULT_SEED`
