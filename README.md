# Multi-Agent Traffic Signal Control

Bootstrap Python para um projeto de controle semaforico multiagente.

Este repositorio ainda nao implementa integracao com SUMO. O objetivo inicial e manter uma
base pequena, validavel e pronta para evoluir com experimentos reprodutiveis.

## Requisitos

- Python 3.12
- uv

## Setup

```powershell
uv sync
```

## Execucao

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
uv run ruff check .
uv run mypy src
```

## Configuracao

As configuracoes iniciais sao lidas de variaveis de ambiente ou de um arquivo `.env` local:

- `APP_ENV`
- `LOG_LEVEL`
- `SUMO_BINARY`
- `SUMO_HOME`
- `ARTIFACTS_DIR`
- `DEFAULT_SEED`
