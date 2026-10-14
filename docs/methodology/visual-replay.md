# Replay visual antes/depois

Ferramenta de apresentação: `scripts/record_before_after.py`. Gera vídeos sincronizados de dois
controladores sobre a **mesma** demanda e o **mesmo** instante de simulação. **Não é evidência
inferencial**; todo vídeo oficial traz o aviso *"Visualização ilustrativa — resultados científicos
utilizam múltiplas seeds."*

## Requisitos

- SUMO 1.27.1 com `sumo-gui` (janelas do GUI aparecem durante a captura).
- FFmpeg, resolvido nesta ordem:
  1. variável de ambiente `FFMPEG_BINARY` (caminho do executável);
  2. `ffmpeg` no `PATH` do sistema;
  3. executável embutido no pacote `imageio-ffmpeg`.

  FFmpeg externo é **opcional** quando `imageio-ffmpeg` está instalado. Ele é declarado no grupo
  `dev` do `pyproject.toml` (instalado por `uv sync --frozen`), não no runtime científico.
- Pillow (`pillow`, dependência direta do projeto) e as fontes DejaVu do matplotlib para as
  sobreposições.

Ambiente reproduzível: `uv sync --frozen` instala tudo o que a gravação exige. Validado em um
ambiente novo (sem FFmpeg no `PATH`): resolução via `imageio-ffmpeg`, codificação de MP4 curto e
`comparison.json` gerados.

## Uso

```
python scripts/record_before_after.py --scenario S4_LOCAL_SATURATION --seed 42 \
  --before-controller B2_LOCAL_PRESSURE --after-controller C1_COOPERATIVE_COMPACT \
  --camera a5_center --start-step 600 --end-step 2600 --fps 30 \
  --output artifacts/demos/s4_seed42_b2_vs_c1
```

Opções extras: `--step-delay-ms`, `--keep-frames` (mantém `frames/before|after/000000.png`),
`--reuse-existing-run` (reencoda a partir de frames mantidos, só se entradas e código da simulação
forem idênticos), `--reference-vehicle auto|on|off`, `--overwrite`.

## Semântica

- Seed oficial de demonstração: **42** (`DEMO_SEED`), definida antes da visualização, parte do
  conjunto final. Outra seed só para depuração: a saída é marcada `NÃO OFICIAL`.
- Passos `[start_step, end_step)`. O quadro `k` mostra o estado ao fim do passo `start_step + k`
  (tempo = `(passo + 1) * step_length`). Os dois lados avançam em *lock-step* por passo de
  simulação (nunca por relógio) e a sincronia é verificada a cada passo.
- O SUMO entrega o screenshot ao fim do **próximo** `simulationStep`; por isso o pedido é feito
  antes do passo, e um *gate* espera o arquivo antes de qualquer comando TraCI posterior.
  Validado: com o mesmo controlador nos dois lados, os quadros são idênticos pixel a pixel.

## Justiça (fairness)

Antes de abrir o SUMO, falha imediatamente se qualquer um diferir: seed, rede, rotas, metadados de
rota, conversões, hash **neutro ao controlador** do cenário (`scenario_sha256` não é usado, pois
inclui `controller_id`), plano de fases, modelo de movimentos, população de veículos, aquecimento,
janela de medição e passos totais.

## Câmeras (`config/demo_camera_presets.yaml`)

`whole_grid` (S1), `a5_center` (S4: A5 + A2, A4, A6, A8), `west_to_center` (S2/S3),
`reference_route` (`left1A1 A1B1 B1C1 C1right1`, corredor destacado). Rótulos são sobreposições
(Pillow); a rede SUMO não é alterada.

## Anotações

- Choque S3: banner "CHOQUE DE DEMANDA" por 20 s a partir de `traffic.shock_start_seconds`
  (lido do cenário oficial).
- Veículo de referência (câmera `reference_route`): primeiro veículo por `(depart, id)` cuja rota
  planejada é exatamente a rota de referência e com `depart >= max(início da medição, início da
  gravação)`. Regra independente de resultados; registrada em `comparison.json`.
- `visual_metrics_*.csv` (fila = veículos parados, chegados/partidos acumulados) servem só para a
  anotação; não são métricas científicas.

## Isolamento científico

O `TraCISimulationRunner` é usado sem alterações (mesma sequência controlador/passo/seed/rede/
rotas); apenas argumentos de GUI são adicionados. Screenshots, destaque de veículo e consultas de
métricas visuais só alteram tempo de relógio. `tests/test_replay_sumo.py` compara, passo a passo,
posições, velocidades e fases semafóricas de uma execução headless contra uma com captura.

## Intervalo da demonstração de engenharia (S4)

Passos 600–2600, predeclarado antes de gerar qualquer vídeo. O hotspot do S4 atua em toda a
execução (`full_run`, 0–3900 s), logo não há evento a escolher: o intervalo começa 300 s após o
início da medição (300 s) para a fila central se formar, e cobre 2000 s. Não foi buscado o melhor
momento para o C1.
