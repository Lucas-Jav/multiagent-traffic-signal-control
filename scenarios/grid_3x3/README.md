# grid_3x3

Rede sintetica 3x3 gerada com `netgenerate`, ferramenta oficial do Eclipse SUMO.

Layout logico dos nove semaforos:

```text
A1 A2 A3
A4 A5 A6
A7 A8 A9
```

Os rotulos `A1` a `A9` sao identificadores estaveis do projeto. O arquivo
`metadata.json` mapeia esses rotulos para os IDs reais dos semaforos no XML gerado pelo
SUMO.

## Geracao

```powershell
uv run python scripts/generate_grid.py
```

A geracao e idempotente: o script sobrescreve `network.net.xml` e `metadata.json` com
conteudo derivado dos mesmos parametros.

## Parametros

- 3 intersecoes por 3 intersecoes.
- Vias bidirecionais.
- 1 faixa por via.
- Comprimento de aresta de 250 m.
- Extensoes de borda de 100 m.
- Intersecoes semaforizadas.

O script tambem executa uma validacao smoke com `netcheck.py`.

## Demanda S1_BALANCED

```powershell
uv run python scripts/generate_routes.py scenarios/grid_3x3/scenario.yaml
```

O perfil inicial `S1_BALANCED` cria fluxos sinteticos semelhantes nos dois eixos
principais da malha:

- oeste -> leste no eixo central;
- leste -> oeste no eixo central;
- norte -> sul no eixo central;
- sul -> norte no eixo central.

Os niveis `LOW`, `MEDIUM` e `HIGH` ficam registrados em `scenario.yaml`. O arquivo
`routes_s1_seed_42.metadata.json` registra `seed`, `flows`, `generated_at` e
`config_hash` da geracao.
