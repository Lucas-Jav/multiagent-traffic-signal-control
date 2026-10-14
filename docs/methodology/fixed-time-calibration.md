# Calibração do Baseline de Tempo Fixo (`B0_FIXED_CALIBRATED`)

Status: calibração concluída e validada (Prompt 55.5). Papel dos dados: `BASELINE_CALIBRATION`;
**os resultados desta calibração não são resultados científicos finais** e não substituem o Pilot V2.

```text
CALIBRATION_METHOD                 = EMPIRICAL_FIXED_TIME (busca em grade predeclarada; Webster NÃO reivindicado)
CALIBRATION_USED_ONLY_B0           = YES
CONTROLLER_RESULTS_USED_FOR_TUNING = NO
FINAL_FIXED_PLAN_SELECTED          = YES  (fx_c84_demand_proportional_alternate)
VALIDATION_PASS                    = YES
```

## 1. Por que a calibração foi necessária

O orientador apontou que um baseline de tempo fixo artificialmente fraco pode inflar os ganhos
aparentes dos controladores adaptativos. O B0 do Pilot V2 é um plano **estático de engenharia**
(defaults do `netgenerate`, não calibrado por demanda). Para a campanha final é preciso um baseline
de tempo fixo calibrado de forma explícita, defensável e independente dos controladores comparados.

## 2. Nomes e preservação do B0 histórico

| Nome | Significado | `controller_id` | Uso |
|---|---|---|---|
| `B0_FIXED_STATIC` (artefatos do Pilot V2: `B0_FIXED_STATIC_V2`) | Plano estático de 98 s do `tlLogic` da rede (verdes 18/20/20/20, amarelo 3, all-red 2, offsets em escada de 10 s) | `B0_FIXED` (inalterado) | **Histórico**: Pilot V2 e referência numérica desta calibração |
| `B0_FIXED_CALIBRATED` | Plano de tempo fixo calibrado, instalado via TraCI uma única vez | `B0_FIXED_CALIBRATED` | **Campanha final** |

O `controller_id` `B0_FIXED` e seus metadados de manifest **não foram alterados**; os artefatos do
Pilot V2 permanecem intactos. O nome "Webster" não é usado.

## 3. Método escolhido e por quê

**Webster não foi usado.** A fórmula de Webster exige fluxos de saturação e razões de fluxo crítico
por movimento, e foi concebida para uma demanda estacionária **de um regime**. Aqui os fluxos de
saturação do SUMO não estão formalmente modelados e é exigido **um plano comum** para quatro regimes
muito diferentes (balanceado, direcional, choque, saturação localizada). Usá-lo seria fingir uma
base teórica que o modelo não sustenta.

Foi usada uma **busca em grade predeclarada** (`EMPIRICAL_FIXED_TIME`) sobre ciclo, divisão de verde e
offset, com avaliação exclusiva por execuções B0. Um dos eixos reaproveita a **regra de divisão de
Webster sob fluxos de saturação iguais** (verde proporcional à parcela de demanda da aproximação), que
vale aqui porque todas as aproximações são idênticas (uma faixa, mesma geometria); isso é uma regra de
repartição, não um cálculo de Webster completo.

**Plano comum, não por cenário.** Um único plano de uso geral foi calibrado para S1-S4, sem planos por
cenário (calibrar separadamente "para vencer" cada cenário seria otimizar contra o teste). Decisão
por simplicidade e por defensabilidade no TCC.

## 4. Predeclaração (congelada antes de qualquer candidato)

Arquivo congelado: `calibration-plan.json` (SHA-256
`3aea5ff507020bd8046595f73b7a921abf4ccf585375f901b3660b99d7c5f0de`, gerado por
`scripts/calibrate_fixed_time.py plan` antes de simular qualquer candidato; cópia em
`docs/evidencias/fixed-time-calibration/`).

### Espaço de busca

- Ciclos: `68, 84, 100, 116, 132` s. Escolhidos para que `(ciclo - 20)` seja divisível por 4
  (verdes iguais de 12/16/20/24/28 s). 20 s é o tempo perdido por ciclo (4 x (3 + 2)).
- Divisão de verde:
  - `EQUAL`: verdes iguais por aproximação.
  - `DEMAND_PROPORTIONAL`: verde proporcional à parcela de demanda de cada aproximação, com
    mínimo de 10 s por fase e máximo de 60 s, repartição por maior resto. A parcela vem **dos
    arquivos de rotas das seeds de calibração**, pela média igual dos quatro cenários S1-S4
    (nenhum resultado de simulação).
- Offsets:
  - `ZERO`: todos 0.
  - `STAGGER`: escada do plano histórico, `((índice lógico - 1) x 10) mod ciclo`.
  - `ALTERNATE`: xadrez, `((coluna + linha) mod 2) x ciclo/2`.
- Total: 5 x 2 x 3 = **30 candidatos**, mais a **referência** estática de 98 s avaliada nativamente.
- Amarelo = 3 s e all-red = 2 s (inalterados). Verde mínimo 10 s e máximo 60 s (mesmos limites de
  segurança dos adaptativos).

### Função objetivo (menor é melhor; a referência vale exatamente 1,0)

```text
J_run = 1 - 0.40*dC + 0.35*dQ + 0.25*dL
  dC = (c - c_ref)/c_ref   c = completion_ratio_offered   (vazão/conclusão)
  dQ = (q - q_ref)/q_ref   q = mean_network_queue_vehicles (fila da rede)
  dL = (l - l_ref)/l_ref   l = mean_time_loss               (perda de tempo)
  *_ref = mesma cenário e seed sob o plano estático histórico

J_plano = média sobre os 4 cenários da média sobre seeds de J_run
```

Guardas, por cenário e na média sobre seeds, para evitar otimizar uma métrica em detrimento de outra
ou aceitar backlog estrutural:

- `completion_ratio_offered >= 0,95 x referência`;
- `departure_ratio >= 0,95 x referência` (sem backlog de inserção);
- `mean_network_queue_vehicles <= 1,25 x referência`;
- `mean_time_loss <= 1,25 x referência`.

Seleção: menor `J_plano` entre os candidatos que passam todos os guardas em todos os cenários.
Desempate (J dentro de 0,005 do mínimo): maior conclusão média, depois ciclo menor. Validação: o plano
escolhido deve ter `J <= 1,0` e passar os guardas em seeds intocadas.

A referência estática serve apenas como denominador de normalização. **Nenhum resultado de B1, B2, C1
ou C2 foi lido ou usado.**

## 5. Seeds

| Papel | Seeds | Observação |
|---|---|---|
| Calibração | `101, 1009, 2029` | Seeds exclusivas de calibração, as mesmas que calibraram os níveis de demanda do Pilot V2 (papel `CALIBRATION`); fora do Pilot V2 e do pool final |
| Validação | `3011, 4021, 5003` | **Intocadas** até a validação |
| Proibidas | `42, 2027, 3253, 4517, 5791` (Pilot V2) e `6841, 8089, 10007, 12011, 16001` (pool final reservado) | Não usadas |

`campaign_role = BASELINE_CALIBRATION`. Demandas: níveis já fixados do Pilot V2 (`gen.CALIBRATED`);
nenhum cenário foi modificado. Total de execuções: 31 planos x 4 cenários x 3 seeds = **372** de
calibração e 2 planos x 4 cenários x 3 seeds = **24** de validação.

## 6. Resultados da calibração

Todos os 31 candidatos foram registrados (`calibration-candidates.csv`), não apenas o vencedor.
13 dos 31 passam todos os guardas. Top 5 (J menor é melhor):

| Posição | Plano | J | Guardas |
|---|---|---|---|
| 1 | `fx_c84_demand_proportional_alternate` | 0,8525 | passa |
| 2 | `fx_c68_demand_proportional_alternate` | 0,8860 | reprova |
| 3 | `fx_c100_demand_proportional_alternate` | 0,8923 | passa |
| 4 | `fx_c84_demand_proportional_stagger` | 0,9212 | reprova |
| 5 | `fx_c68_equal_alternate` | 0,9263 | reprova |

J médio por fator, sobre todos os candidatos: ciclo `84 -> 0,994`, `68 -> 1,011`, `100 -> 1,017`,
`116 -> 1,044`, `132 -> 1,076`; divisão `DEMAND_PROPORTIONAL 0,995` contra `EQUAL 1,061`; offset
`ALTERNATE 0,952`, `STAGGER 1,010`, `ZERO 1,122`. Ou seja, o offset alternado e a divisão por demanda
são os fatores mais influentes.

A diferença do vencedor para o 2º colocado (0,034) é maior que a tolerância de desempate (0,005); o
desempate não foi acionado.

## 7. Plano selecionado

```text
plan_id            = fx_c84_demand_proportional_alternate
cycle_seconds      = 84
yellow / all-red   = 3 s / 2 s   (preservados)
offset strategy    = ALTERNATE (xadrez, meio ciclo = 42 s)
split strategy     = DEMAND_PROPORTIONAL (mín. 10 s, máx. 60 s)
plan sha256        = e1d04e9c50fe12655c5b49dda98fc93cef7f5e48e84b2884a556f160ee498b40
arquivo            = experiments/fixed_time/b0_fixed_calibrated.json
```

Verdes (s) por aproximação, na ordem das fases da rede (soma = 64, ciclo = 64 + 20 = 84), e offset:

| SUMO | Lógico | Verdes | Offset (s) |
|---|---|---|---|
| A0 | A7 | 15 / 14 / 15 / 20 | 0 |
| A1 | A4 | 15 / 16 / 15 / 18 | 42 |
| A2 | A1 | 15 / 14 / 15 / 20 | 0 |
| B0 | A8 | 17 / 15 / 14 / 18 | 42 |
| B1 | A5 | 15 / 15 / 15 / 19 | 0 |
| B2 | A2 | 15 / 14 / 17 / 18 | 42 |
| C0 | A9 | 15 / 16 / 16 / 17 | 0 |
| C1 | A6 | 15 / 14 / 15 / 20 | 42 |
| C2 | A3 | 16 / 16 / 15 / 17 | 0 |

(Offsets alternados: interseções de borda `A1, B0, B2, C1` com 42 s; cantos e centro com 0.)

## 8. Validação (seeds intocadas 3011, 4021, 5003)

`J = 0,8486` (calibração: 0,8525), guardas passam em todos os cenários: **VALIDATION_PASS = YES**.
O plano não é artefato de uma seed.

| Cenário | J calibração | J validação | Conclusão cal./val. (ref. cal.) | Fila da rede cal./val. (ref. cal.) | Perda de tempo cal./val. (ref. cal.) |
|---|---|---|---|---|---|
| S1 | 0,785 | 0,783 | 0,967 / 0,967 (0,957) | 29,2 / 28,9 (47,3) | 78,0 / 77,5 (112,4) |
| S2 | 0,774 | 0,770 | 0,969 / 0,973 (0,956) | 18,9 / 19,4 (31,8) | 77,6 / 79,4 (113,6) |
| S3 | 0,767 | 0,768 | 0,934 / 0,936 (0,899) | 40,9 / 40,6 (67,5) | 92,5 / 92,3 (135,6) |
| S4 | **1,084** | **1,074** | 0,356 / 0,350 (0,366) | 343,7 / 332,5 (317,5) | 810,7 / 799,4 (691,1) |

### Leitura honesta dos resultados

- **S1-S3**: o plano calibrado é bem melhor que o estático de 98 s (J ≈ 0,77-0,79: fila da rede de
  38% a 41% menor, perda de tempo 31% a 32% menor, conclusão maior). **O B0 final é um baseline
  muito mais forte que o B0 histórico** nesses regimes. Isso significa que ganhos de controladores
  adaptativos sobre o B0 do Pilot V2 nesses cenários não podem ser extrapolados para o B0 final.
- **S4 (saturação localizada)**: o plano calibrado é **ligeiramente pior** que o estático (J = 1,08;
  conclusão 0,356 contra 0,366; fila e perda de tempo maiores). É um custo do plano comum: foi
  otimizado para o conjunto, e o S4 é sobrecarga intencional (cerca de metade da demanda não entra).
  O plano passa os guardas (dentro de 1,25 x), mas esse efeito deve ser reportado e **não** ajustado
  retroativamente. Nenhum plano por cenário foi criado.
- Teleports do SUMO (`sumo_teleports_total`, soma sobre S1-S4): calibração estático 14 contra
  calibrado 5; validação estático 3 contra calibrado 10. Não há tendência clara; reportar ao lado de
  todo resultado do S4 (`ALLOW_AND_MEASURE`).

## 9. Equidade e identidade

O `B0_FIXED_CALIBRATED` usa a **mesma rede** (hash idêntico ao do Pilot V2:
`46953c48351b0fde...`), os mesmos movimentos legais, as mesmas rotas e os mesmos cenários que os demais
controladores. Só muda o tempo dos programas já existentes: os estados das fases, a ordem das fases, o
amarelo e o all-red são preservados; os verdes ficam em `[10, 60]` s. O controlador **não é responsivo
ao tráfego**: instala o plano uma vez antes do primeiro passo e depois não lê observações nem altera
fases. O manifest da run registra `controller_id = B0_FIXED_CALIBRATED`, `fixed_time_plan_id`,
`fixed_time_plan_sha256`, `fixed_time_cycle_seconds`, `traffic_responsive = false`.

A semântica de offset segue a do atributo `offset` do `tlLogic` (tempo de programa = `(t - offset)
mod ciclo`), verificada contra o programa nativo: instalando o plano estático de 98 s pelo novo
controlador, os estados dos semáforos coincidem nos 600 primeiros passos para as 9 interseções.

## 10. Regras do Pilot V2

- Os artefatos do Pilot V2 **não foram alterados**.
- A comparação primária do Pilot V2, **B2 vs C1**, permanece válida: o B0 não participa do isolamento
  do efeito da cooperação.
- Qualquer afirmação "B0 vs adaptativo" do Pilot V2 deve ser rotulada como usando o **B0 histórico
  `B0_FIXED_STATIC`**.
- As comparações finais com B0 devem usar `B0_FIXED_CALIBRATED`.

## 11. Limitações

1. **Plano comum**: um único plano para quatro regimes. Prejudica o S4 (ver acima). Planos por
   cenário ou por horário não foram considerados.
2. **Espaço de busca pequeno** (30 candidatos): não é um ótimo global; não há Webster, otimização
   contínua nem coordenação de onda verde. É calibração defensável, não otimização exaustiva.
3. **Seeds de calibração** (`101, 1009, 2029`) coincidem com as seeds que fixaram os níveis de demanda
   do Pilot V2 (papel de calibração, não finais). Há 3 seeds de calibração e 3 de validação:
   amostra pequena.
4. **Divisão por demanda** usa a média igual dos 4 cenários, o que embute a mistura de regimes escolhida
   (inclusive o hotspot do S4 e a demanda oeste de S2/S3).
5. **Pesos do objetivo** (0,40/0,35/0,25) são escolhas de projeto predeclaradas, não derivadas.
6. **Condicionalidade**: `mean_time_loss` só cobre viagens concluídas; a conclusão entra no objetivo
   para penalizar o abandono.
7. **Infraestrutura**: um evento de corrida de leitura do `tripinfo.xml` sob paralelismo (`traci.close`
   sem esperar) foi tratado com retry do job; a simulação é determinística e a retentativa não altera
   resultados. Uma sessão interrompida foi retomada reaproveitando as runs já finalizadas em disco
   (determinísticas).
8. **Rótulo do código**: a execução dos resultados ocorreu com a árvore de trabalho com alterações
   ainda não commitadas (SHA base `0215e85`).
9. O plano final é calibrado nos níveis de demanda atuais (`gen.CALIBRATED`); se os níveis de demanda
   mudarem, a calibração deve ser refeita.

## 12. Artefatos

- Plano final: `experiments/fixed_time/b0_fixed_calibrated.json`.
- Código: `src/traffic_agents/controllers/fixed_time_plan.py`; script `scripts/calibrate_fixed_time.py`;
  testes `tests/test_fixed_time_plan.py`.
- Evidências versionadas (leves): [`../evidencias/fixed-time-calibration/`](../evidencias/fixed-time-calibration/)
  (predeclaração e SHA, tabela de candidatos, runs de calibração e validação, seleção, validação e
  manifest). Traces brutos: `artifacts/calibration/fixed_time_b0/` (git-ignorado).
