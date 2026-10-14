> **Proveniencia (copia versionada).**
> Fonte: `artifacts/experiments/pilot_v2/pilot-v2-methodological-decision.md` (git-ignorado) | Experimento: `pilot_v2` |
> Git SHA do codigo que gerou as runs: `7fffb4efff9ad98498c81cc0d829911ad44baa46` | Git SHA no empacotamento: `0215e852603cb56a2c1ebd2ddd615b94c50b95ad` |
> Data de empacotamento: 2026-10-13 | Tipo: **derived** | Conteudo copiado sem alteracao abaixo.

# Decisão metodológica do Pilot V2: gate S3 e política S4

- Escopo: `campaign_role: PILOT` (Pilot V2). Esta decisão não altera código, cenários, controladores nem limiares numéricos herdados. Nenhuma simulação nova.
- Origem: Prompt 47, com base em `s3-stability-adjudication.md`, `s3-stability-table.csv`, `s4-teleport-audit.md` e `s4-teleport-table.csv` (Prompt 46.9).
- Status: o gate S3 **ainda não foi reavaliado**. Este documento só formaliza as regras. A reavaliação usa apenas a telemetria já existente e é um passo seguinte, separado.

## 1. Decisões registradas

```
S3_FAILURE_CLASS          = STOCHASTIC_GATE_SENSITIVITY
S3_GATE_UPDATED           = YES
S3_NEW_GATE_TYPE          = COMPOSITE_GATE
S4_TELEPORT_POLICY        = ALLOW_AND_MEASURE
S4_TELEPORTS_AFFECT_VALIDITY = NO
S4_REQUIRES_SIMULATION_CONFIG_CHANGE = NO
S4_REQUIRES_RECALIBRATION = NO
S4_REQUIRES_PILOT_RERUN   = NO
NEW_SIMULATION_RUNS_REQUIRED = NO
```

## 2. Por que o gate anterior de 360 s era sensível demais

Regra anterior (congelada na calibração): ajuste linear da fila de rede nos últimos 20% da medição pré-choque (360 s); estável se `variação projetada <= 0,10 x max(fila média da janela, 5)`.

Evidência da auditoria 46.9, com tráfego B0 sem backlog em todas as observações:

- Em 18 observações independentes (5 seeds do piloto, 3 de calibração, 10 diagnósticas), 14 passaram e 4 falharam: taxa de falso-fail de cerca de 22% por seed.
- Em janelas deslizantes de 360 s sobre tráfego estável, 14% (105 de 735) das janelas pré-choque e 17% (93 de 545) das janelas do S1 reprovam.
- O limite de 0,10 fica apenas 0,73 desvio-padrão acima da média do slope normalizado (média 0,020, desvio 0,109; n = 15). Com 22% de falso-fail por seed, a chance de 5 seeds de um cenário estável passarem todas é cerca de 29%.
- A janela de 360 s é curta frente ao ciclo semafórico de 98 s e à oscilação da fila (mín 33 a máx 60 veículos em janelas de 360 s). O slope de uma janela assim mede flutuação, não tendência.

Conclusão: o gate binário de 360 s não discrimina regime estável de instável com a confiabilidade necessária; ele reprova tráfego estável com frequência alta.

## 3. Por que a falha da seed 4517 não invalida o S3

- A primeira metade do S3 é idêntica à do S1 (mesmos veículos, rotas e partidas). As séries de fila de S3 e S1 coincidem nos passos 0 a 2099 (diferença máxima 0,0 veículo). A mesma janela também reprova no S1 seed 4517. O choque, que começa em 2100 s, não participa da janela.
- Na seed 4517: 900 oferecidos, 900 partiram, 0 nunca inseridos, `departure_ratio` 1,000, atraso de inserção máximo 1 s, saturação de faixa 0, fila máxima por faixa 9.
- A margem foi pequena (projetado 6,51 contra limite 5,00) e a seed está perto do limite, não isolada: as margens das outras seeds vão de +2,2 a +8,9.
- A mesma seed passa no critério agregado de 1800 s (normalizado 0,031) e o S1 seed 4517 passa na sua janela final (−0,114).
- Conclusão: a falha é flutuação local da fila medida por um critério ruidoso (LOCAL_STOCHASTIC_FLUCTUATION dentro de STOCHASTIC_GATE_SENSITIVITY), não instabilidade estrutural do cenário nem efeito da adaptação.

## 4. Por que a janela de 1800 s passa a ser a janela decisória principal

- A janela de 1800 s cobre toda a fase pré-choque (300 a 2100 s), cerca de 18 ciclos semafóricos, e mede a tendência do regime em vez da flutuação de ciclos individuais.
- É a janela que corresponde à pergunta do gate: a primeira metade do S3 é um regime estável equivalente ao S1?
- Nos 15 casos pilot e diagnósticos o critério de 1800 s teve 0 falhas (slope normalizado máximo 0,060, contra limite 0,100); os diagnósticos de calibração (10 seeds) não usam seeds do piloto.
- Transparência: a escolha da janela foi feita após observar os dados da auditoria 46.9. O limiar 0,10 e o piso de 5 veículos **não foram alterados**; só a janela mudou, e a decisão se apoia na taxa de falso-fail medida nas seeds de calibração, não na seed 4517. O risco residual (janela escolhida depois do dado) é registrado como limitação.
- A janela de 360 s continua sendo **calculada e reportada como diagnóstico**; deixa de ser critério decisório isolado.

## 5. Gate composto oficial do S3

Os critérios principais (por seed, avaliados no B0 de referência, como nas demais validades):

1. Sem backlog estrutural pré-choque: `departure_ratio` pré-choque >= 0,98 e atraso médio de inserção pré-choque <= 5 s.
2. Sem não inseridos relevantes: fração de nunca inseridos <= 0,02 na coorte pré-choque.
3. Sem saturação estrutural de faixa: fração de amostras faixa-passo com fila >= 0,8 da capacidade <= 0,02 na fase pré-choque.
4. Janela agregada de 1800 s pré-choque (passos 300 a 2099): mesma regra congelada (`variação projetada <= 0,10 x max(média da janela, 5)`), aplicada à janela de 1800 s.

Agregação entre seeds: o S3 é válido se **pelo menos 4 de 5 seeds** passarem nos critérios 1 a 4 (seeds 42, 2027, 3253, 4517, 5791).

Inalterado e exigido nas 5 seeds (verificações determinísticas ou já aprovadas no Pilot V2, que a decisão não relaxa): base igual à do S1; primeira metade idêntica à do S1; choque em 2100 s (ponto médio da medição); origem só nas bordas oeste declaradas; veículos do choque passando pelo A5; resposta visível após o choque (razão de fila >= 1,25 e latência <= 600 s); sem backlog de inserção de milhares de segundos; AUC pós-choque conforme a definição congelada.

Diagnóstico reportado (não decisório): a regra de 360 s (por seed e passagem/falha), a regra de 720 s, a distribuição de slopes normalizados e a taxa de falso-fail observada.

Todos os limiares (0,98; 5 s; 0,02; 0,8; 0,10; piso 5) são herdados do que já estava predeclarado. Nenhum limiar foi relaxado.

## 6. Por que a regra de 4 de 5 seeds é metodologicamente aceitável

- Os critérios 1 a 4 medem propriedades estocásticas do regime (fila, inserção, saturação) sobre uma realização de tráfego; uma seed isolada pode desviar por flutuação sem que o cenário seja inválido.
- Tolerar uma seed em cinco reconhece esse ruído e ainda exige que a maioria clara (80%) mostre o regime estável. Uma segunda falha reprova o cenário.
- A regra não afrouxa as verificações estruturais (Seção 5, "Inalterado"), que são determinísticas e não sujeitas a essa flutuação.
- O gate composto não depende de uma única janela ruidosa: combina ausência de backlog, inserção, saturação e tendência de 1800 s.
- Limitação: com 5 seeds, 4 de 5 é grosseiro. A regra é adequada ao piloto e deve ser revisitada, com mais seeds, para a campanha final.

## 7. Por que novas simulações não são necessárias agora

- A reavaliação de S3 depende de quantidades já gravadas na telemetria canônica (`lane_telemetry.parquet`, `tripinfo.xml`, `run_metrics.json`) das 100 runs do Pilot V2.
- O critério de 1800 s, as frações de inserção/backlog e a saturação de faixa já foram calculados na auditoria 46.9 (15 observações B0, incluindo 10 seeds de calibração-diagnóstico).
- Mudar o gate não muda as simulações: o tráfego é o mesmo. Rodar de novo só reproduziria os mesmos dados (B0 é determinístico).

## 8. Por que S4 foi aceito como ALLOW_AND_MEASURE

Evidência da auditoria 46.9:

- Política real: nenhuma opção de teleport definida; vale o default do SUMO 1.27.1 (`time-to-teleport` 300 s).
- Quantidade: 17 teleports em 6 das 25 runs do S4 (B0: 14 nas 5 seeds; B2: 3 na seed 5791; B1, C1, C2: 0); nenhum nos cenários S1, S2, S3.
- Localização: nenhum em A5 nem em A2/A4/A6/A8; concentrados no canto A1 (11, faixa `B2A2_0`), A3 (4) e A9 (2). Sem correlação com fila extrema.
- Efeito nas métricas: os veículos teleportados continuam em `tripinfo`, contam como chegados quando chegam (11 de 17) e mantêm espera e time loss sem truncamento. Impacto LOW em throughput, conclusão, tempos e fila, e NONE em `internal_lane_persistence_events` (<= 0,1% da coorte; <= 0,4% da espera média).
- Contrafactual B0 sem teleport (5 seeds de calibração): simulação normal, sem gridlock, métricas dentro de ~1%, mesmo tempo de execução.

Consequências da política:

- `sumo_teleports_total` (já gravado por run) é **métrica auxiliar obrigatória** nos relatórios do S4. Teleports não bloqueiam a validade do S4.
- Sensibilidade a reportar no comparativo B2 vs C1: repetir a análise sem a dupla S4 seed 5791 (única com teleports no B2).
- Limite conhecido: o contrafactual sem teleport só foi testado com B0; o comportamento dos adaptativos sem teleport não é conhecido. Se a campanha final optar por desligar teleports, isso exige validação separada dos demais controladores e é decisão futura.

## 9. Bloqueios restantes antes da reavaliação do S3

- Nenhum bloqueio metodológico: regras e limiares estão definidos nesta decisão.
- Pendente (passo seguinte, não feito aqui): executar a reavaliação do S3 com o gate composto sobre a telemetria existente e registrar o resultado; só então decidir se a comparação B2 vs C1 pode ser liberada.
- Risco a declarar no relatório da reavaliação: a janela de 1800 s foi escolhida depois de observar os dados da auditoria (Seção 4).

> **Status update (final audit, Prompt 52).** The re-evaluation left pending in section 9 was executed in Prompt 48: S3 passes the composite gate with 5/5 valid seeds (seed 4517 `VALID_WITH_DIAGNOSTIC_WARNING`). No blocker remains.
