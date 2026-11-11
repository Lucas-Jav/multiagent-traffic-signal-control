> **Proveniencia (copia versionada).**
> Fonte: `artifacts/experiments/pilot_v2/s4-teleport-audit.md` (git-ignorado) | Experimento: `pilot_v2` |
> Git SHA do codigo que gerou as runs: `7fffb4efff9ad98498c81cc0d829911ad44baa46` | Git SHA no empacotamento: `0215e852603cb56a2c1ebd2ddd615b94c50b95ad` |
> Data de empacotamento: 2026-10-13 | Tipo: **derived** | Conteudo copiado abaixo (texto traduzido para português, sem alteração de números ou conclusões).

# Auditoria de teleportes do SUMO no S4 (Prompt 46.9, parte B)

Nenhum arquivo de repositório ou de cenário foi alterado; Pilot V2 não foi re-executado; nenhum ranking de controladores. Dados: `s4-teleport-table.csv` (17 eventos), `artifacts/calibration/pilot_v2-diagnostic/` (`s4_analysis.json`, `s4_per_run.csv`, `diag_runs.json`, logs do SUMO das execuções `CALIBRATION_DIAGNOSTIC` apenas com B0).

## B1. Política de teleporte realmente usada pelo Pilot V2

- O executor do projeto monta o comando do SUMO apenas com `--net-file --route-files --step-length --seed --no-step-log --quit-on-end --tripinfo-output --tripinfo-output.write-unfinished --statistic-output`. **Nenhuma opção de teleporte é definida**, portanto todo valor é o padrão do SUMO 1.27.1: `--time-to-teleport 300` (um veículo que esperou 300 s é teleportado; valor não positivo desativa), `--time-to-teleport.highways` padrão (inativo nestas vias de 13,9 m/s), `--time-to-teleport.disconnected` padrão, sem `--max-num-teleports`.
- Os avisos ("Teleporting vehicle ...") foram para o stderr do SUMO e só foram capturados no log do lote `artifacts/pilot_v2_stderr.log`, não por execução; por execução há apenas a contagem em `sumo/statistics.xml` (`<teleports total/jam/yield/wrongLane>`). As linhas do log do lote foram atribuídas às execuções pela ordem de execução e pelas contagens por execução (17 linhas = 17 teleportes contados, tempos monotônicos dentro de cada execução e <= 3900 s: mapeamento consistente).

## B2. Quantificação (25 execuções S4)

- Eventos: 17 no total (15 `jam`, 2 `yield`), em 6 das 25 execuções S4. Nenhum teleporte em S1/S2/S3 (75 execuções).
- Por controlador: `B0_FIXED` 14 (em 5/5 seeds), `B2_LOCAL_PRESSURE` 3 (1/5 seeds, seed 5791), `B1_LOCAL_ADAPTIVE`, `C1_COOPERATIVE_COMPACT`, `C2_COOPERATIVE_EXPANDED` 0. Por seed: 42 -> 2, 2027 -> 2, 3253 -> 4, 4517 -> 2, 5791 -> 7.
- Por localização (junção a jusante, rótulos do projeto): A1 11 (lane `B2A2_0` 10, `left2A2_0` 1), A3 4 (`right2C2_0`), A9 2 (`right0C0_0`, `bottom2C0_0`). **Nenhum em A5 nem em A2/A4/A6/A8**: os teleportes ocorrem em aproximações de canto e em lanes de entrada de borda, não no hotspot. Grupos: base 8, hotspot 9.
- Tempo de simulação: 1012..3867 s (eventos no piloto: mín 1221, mediana 2582, máx 3867).
- Filas extremas: a fila da rede no evento é 1,08x a média da execução e 0,92x o máximo da execução; correlação da contagem de teleportes por execução com a fila máxima da rede -0,0005, com a fila média 0,17, com a razão de partida 0,47 (n = 25). Não concentrados em filas extremas.
- Conclusão: concentrados em lugares diferentes de A5, **dependentes do controlador** (apenas B0 e uma execução B2), sem relação com filas extremas da rede.
- As seeds `CALIBRATION_DIAGNOSTIC` apenas com B0 (política padrão) mostram o mesmo padrão: 2, 0, 3, 3, 5 teleportes, principalmente a lane `B2A2_0` mais as lanes de entrada `right0C0_0`/`right2C2_0`.

## B3. Efeito nas métricas científicas (a partir dos artefatos reais do SUMO)

- Todo veículo teleportado está presente em `tripinfo.xml` (17/17); 11/17 têm `arrival` (continuam na rota após o salto e passam a contar como **chegados**, e contam no throughput se a chegada está dentro da janela); 6/17 não haviam chegado ao fim da execução (contados como não finalizados). Nenhum foi removido/vaporizado e nenhum foi reinserido.
- O tempo de viagem, o tempo de espera e a perda de tempo **não são truncados**: os veículos teleportados carregam espera de 443-2680 s e perda de tempo de 473-3210 s (espera média da execução ~580 s), então a longa espera permanece na métrica.
- Alívio de fila: o teleporte remove o veículo bloqueado da sua lane; a fila da lane caiu de 7,8 (média) para 6,1 (média) 60 s após o evento (variações por evento de 0 a -6). Uma lane por vez, nas aproximações de canto/entrada, não no hotspot.
- Magnitude: no máximo 4 eventos em uma execução (B0) ou 3 (B2) contra cerca de 3588 ofertados (<= 0,11%); a contribuição dos veículos teleportados que chegaram para o tempo médio de espera de uma execução é <= cerca de 0,4% (ex.: B0 seed 5791: (1717 + 993) s / ~1300 concluídos = 2,1 s de ~580 s); efeito no throughput <= 0,3%; `internal_lane_persistence_events` é calculado a partir da ocupação das lanes da junção e não é alterado diretamente.
- Classificação de impacto:

| métrica | impacto |
| --- | --- |
| throughput | BAIXO |
| razão de conclusão | BAIXO |
| tempo de viagem | BAIXO |
| tempo de espera | BAIXO |
| perda de tempo | BAIXO |
| fila da rede | BAIXO |
| internal_lane_persistence_events | NENHUM |

- Ressalva: teleportes são sintomas de um veículo preso à frente da lane por 300 s, e apenas B0 e B2 na seed 5791 os apresentam. A execução B2 S4 seed 5791 (3 teleportes) também tem a menor razão de partida entre as execuções B2 S4 (0,332 vs 0,408-0,423) e a maior fila média; não se pode provar que os teleportes causem ou aliviem isso. Essa execução é 1 dos 20 pares B2-vs-C1.

## B4. Contrafactual de zero teleportes (apenas B0, seeds de calibração 3011, 4021, 5039, 6043, 7057, S4 nos níveis calibrados)

Política padrão vs `--time-to-teleport -1` (adicionado apenas na subclasse do executor de diagnóstico; executor do repositório intocado):

| seed | teleportes padrão / desativado | razão de partida | fila média da rede | fila nos últimos 600 s | throughput | intervalos de 300 s sem chegadas | tempo de relógio (s) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 3011 | 2 / 0 | 0.493 / 0.493 | 323 / 323 | 341 / 344 | 1559 / 1554 | 0 / 0 | 88 / 87 |
| 4021 | 0 / 0 | 0.484 / 0.484 | 316 / 316 | 330 / 330 | 1556 / 1556 | 0 / 0 | 88 / 87 |
| 5039 | 3 / 0 | 0.491 / 0.489 | 316 / 315 | 328 / 326 | 1569 / 1569 | 0 / 0 | 87 / 87 |
| 6043 | 3 / 0 | 0.486 / 0.485 | 325 / 327 | 342 / 353 | 1541 / 1526 | 0 / 0 | 87 / 79 |
| 7057 | 5 / 0 | 0.485 / 0.486 | 316 / 320 | 328 / 345 | 1554 / 1546 | 0 / 0 | 87 / 79 |

- Desativar os teleportes resulta em simulação normal e contínua: congestão severa mas ativa, 3900 passos concluídos, todo intervalo de 300 s tem chegadas (115-141), sem gridlock, sem backlog ilimitado além da sobrecarga pretendida, mesmo hotspot em A5 e mesma propagação, tempo de execução inalterado (79-88 s). As diferenças de métricas são <= 1% no throughput e <= 3% na fila ao fim da execução.
- Limite: apenas B0. Os controladores adaptativos não foram executados sem teleportes (proibido nesta tarefa), portanto seu comportamento com teleportes desativados não foi testado.

## B5. Recomendação

**S4_TELEPORT_POLICY = ALLOW_AND_MEASURE**

- Os teleportes são raros (17 eventos, 6/25 execuções S4, <= 0,11% da coorte de uma execução), localizados longe de A5, mantêm a espera/perda de tempo nas métricas, e sua remoção altera as métricas agregadas em <= cerca de 1%. Desativá-los muda quase nada para o B0, então desativar não traria muito e exigiria re-executar o S4 para todos os controladores com um comportamento adaptativo não testado.
- Condições para manter a integridade científica: reportar `sumo_teleports_total` (já registrado por execução) junto a todo resultado do S4 e executar a comparação B2-vs-C1 com uma verificação de sensibilidade excluindo o par da seed 5791 do S4 (o único par com teleportes no B2).
- Se o responsável preferir zero alívio oculto nos experimentos FINAIS, `DISABLE_FOR_FINAL_EXPERIMENTS` é tecnicamente seguro para o B0 (B4), mas deve ser validado primeiro para B1/B2/C1/C2 (novas execuções, decisão separada).

```
S4_TELEPORT_POLICY = ALLOW_AND_MEASURE
S4_TELEPORTS_AFFECT_VALIDITY = NO
S4_REQUIRES_SIMULATION_CONFIG_CHANGE = NO
S4_REQUIRES_RECALIBRATION = NO
S4_REQUIRES_PILOT_RERUN = NO
```
