# Resultados — texto final proposto

> Todos os resultados quantitativos desta seção usam **exclusivamente a evidência final** (FINAL_MAIN
> + FINAL_S5; N = 10 seeds por condição; comparações pareadas por cenário + seed; IC95% por bootstrap
> pareado). O Pilot V2 aparece somente na Seção 6.10, como evidência metodológica. Convenções:
> Δ = tratamento − baseline; "diferença relativa" = diferença média / média do baseline; **o sentido
> favorável depende da métrica** (vazão e conclusão: valores maiores são favoráveis; espera, perda de tempo, fila e
> atraso de partida: valores menores são favoráveis); um efeito só é descrito como favorável a um lado quando o IC95% exclui zero.
> Métricas de tempo são condicionais às viagens concluídas (Seção 3.8).

## 6.1 Visão geral

As tabelas a seguir resumem, para cada cenário, a média ± desvio-padrão entre as 10 seeds (todas as
estatísticas descritivas — N, média, mediana, desvio-padrão, IQR, mínimo e máximo — estão no apêndice de
dados e em `final_controller_summary.csv`). A **Figura 2 (FIG02)** apresenta essas médias em pequenos
múltiplos, e a **Figura 19 (FIG19)** e a **Tabela 3 (TABLE03)** resumem as comparações.

**S1 — balanceado**

| Ctrl | Vazão | Concl. (ofer.) | Razão de partida | Espera (s) | Perda de tempo (s) | Viagem (s) | Fila média | Fila máx. | Teleports |
|---|---|---|---|---|---|---|---|---|---|
| B0 | 1805,0 ± 5,7 | 0,967 ± 0,003 | 1,000 ± 0,000 | 58,6 ± 1,3 | 79,0 ± 1,5 | 132,1 ± 1,9 | 29,5 ± 0,6 | 46,9 ± 1,5 | 0,0 ± 0,0 |
| B1 | 1802,5 ± 7,1 | 0,966 ± 0,002 | 1,000 ± 0,000 | 59,8 ± 1,7 | 79,5 ± 1,8 | 132,5 ± 2,1 | 30,2 ± 0,8 | 47,9 ± 2,8 | 0,0 ± 0,0 |
| B2 | 1810,3 ± 5,6 | 0,969 ± 0,003 | 1,000 ± 0,000 | 49,7 ± 4,9 | 69,0 ± 4,9 | 122,0 ± 4,8 | 25,3 ± 2,4 | 42,3 ± 2,2 | 0,0 ± 0,0 |
| C1 | 1804,2 ± 9,5 | 0,965 ± 0,003 | 1,000 ± 0,000 | 67,1 ± 3,4 | 87,0 ± 3,5 | 140,0 ± 3,4 | 33,9 ± 1,7 | 50,2 ± 2,9 | 0,0 ± 0,0 |
| C2 | 1706,9 ± 28,3 | 0,904 ± 0,017 | 0,998 ± 0,002 | 192,8 ± 17,5 | 220,9 ± 18,9 | 273,5 ± 18,9 | 96,5 ± 8,6 | 156,2 ± 21,1 | 0,0 ± 0,0 |

**S2 — pico direcional**

| Ctrl | Vazão | Concl. (ofer.) | Razão de partida | Espera (s) | Perda de tempo (s) | Viagem (s) | Fila média | Fila máx. | Teleports |
|---|---|---|---|---|---|---|---|---|---|
| B0 | 1200,1 ± 3,4 | 0,970 ± 0,002 | 1,000 ± 0,000 | 56,8 ± 0,5 | 78,0 ± 0,7 | 130,8 ± 1,0 | 19,0 ± 0,2 | 38,9 ± 1,3 | 0,0 ± 0,0 |
| B1 | 1196,8 ± 4,9 | 0,967 ± 0,003 | 1,000 ± 0,000 | 71,8 ± 1,1 | 91,1 ± 1,5 | 143,8 ± 1,8 | 24,2 ± 0,4 | 41,9 ± 2,1 | 0,0 ± 0,0 |
| B2 | 973,0 ± 23,2 | 0,765 ± 0,020 | 0,822 ± 0,022 | 166,0 ± 7,1 | 197,3 ± 7,9 | 249,9 ± 8,0 | 46,1 ± 1,5 | 74,3 ± 4,5 | 0,0 ± 0,0 |
| C1 | 917,4 ± 17,1 | 0,716 ± 0,015 | 0,761 ± 0,013 | 140,8 ± 4,3 | 167,1 ± 4,9 | 219,6 ± 5,2 | 37,7 ± 1,0 | 58,3 ± 3,2 | 0,0 ± 0,0 |
| C2 | 841,4 ± 11,8 | 0,651 ± 0,009 | 0,696 ± 0,010 | 163,6 ± 3,1 | 190,4 ± 3,5 | 242,9 ± 3,8 | 40,2 ± 0,6 | 60,2 ± 1,9 | 0,0 ± 0,0 |

**S3 — mudança de demanda**

| Ctrl | Vazão | Concl. (ofer.) | Razão de partida | Espera (s) | Perda de tempo (s) | Viagem (s) | Fila média | Fila máx. | Teleports |
|---|---|---|---|---|---|---|---|---|---|
| B0 | 1956,4 ± 27,3 | 0,935 ± 0,014 | 0,999 ± 0,002 | 72,3 ± 3,7 | 96,4 ± 4,4 | 150,7 ± 4,2 | 42,8 ± 3,4 | 99,8 ± 19,6 | 0,0 ± 0,0 |
| B1 | 1955,9 ± 8,7 | 0,935 ± 0,004 | 0,997 ± 0,002 | 83,3 ± 2,9 | 108,5 ± 3,3 | 162,9 ± 3,5 | 47,6 ± 1,7 | 96,7 ± 6,1 | 0,0 ± 0,0 |
| B2 | 1944,0 ± 6,3 | 0,927 ± 0,003 | 0,989 ± 0,003 | 78,5 ± 4,7 | 104,3 ± 5,0 | 158,6 ± 4,9 | 45,0 ± 2,5 | 99,1 ± 6,7 | 0,0 ± 0,0 |
| C1 | 1911,1 ± 14,2 | 0,910 ± 0,006 | 0,976 ± 0,003 | 95,3 ± 2,7 | 120,4 ± 3,0 | 174,5 ± 3,1 | 53,3 ± 1,7 | 110,6 ± 7,5 | 0,0 ± 0,0 |
| C2 | 1709,2 ± 32,2 | 0,805 ± 0,014 | 0,907 ± 0,009 | 210,8 ± 16,3 | 241,8 ± 17,6 | 295,2 ± 17,8 | 108,4 ± 7,4 | 189,0 ± 15,3 | 0,0 ± 0,0 |

**S4 — saturação localizada**

| Ctrl | Vazão | Concl. (ofer.) | Razão de partida | Espera (s) | Perda de tempo (s) | Viagem (s) | Fila média | Fila máx. | Teleports |
|---|---|---|---|---|---|---|---|---|---|
| B0 | 1476,3 ± 15,8 | 0,352 ± 0,004 | 0,471 ± 0,006 | 649,8 ± 22,7 | 802,1 ± 29,8 | 861,1 ± 30,1 | 335,1 ± 11,7 | 397,9 ± 10,5 | 2,8 ± 1,6 |
| B1 | 1249,1 ± 18,1 | 0,285 ± 0,005 | 0,428 ± 0,010 | 876,0 ± 24,3 | 1135,0 ± 32,8 | 1198,0 ± 32,6 | 352,0 ± 8,8 | 421,7 ± 7,2 | 0,0 ± 0,0 |
| B2 | 1227,3 ± 101,6 | 0,277 ± 0,028 | 0,411 ± 0,029 | 913,8 ± 43,1 | 1151,5 ± 50,7 | 1215,3 ± 51,3 | 356,4 ± 6,6 | 450,6 ± 13,5 | 0,3 ± 0,9 |
| C1 | 1334,9 ± 20,8 | 0,307 ± 0,005 | 0,414 ± 0,004 | 735,4 ± 25,0 | 890,7 ± 32,7 | 954,3 ± 33,2 | 294,9 ± 6,7 | 356,1 ± 10,8 | 0,0 ± 0,0 |
| C2 | 1364,2 ± 28,2 | 0,310 ± 0,007 | 0,407 ± 0,008 | 613,7 ± 23,4 | 708,1 ± 28,8 | 771,4 ± 29,0 | 254,5 ± 6,7 | 319,0 ± 7,2 | 0,0 ± 0,0 |

A classificação das comparações congeladas, por cenário (regra da Seção 3.11), é:

| Cenário | B2 → C1 (primária) | B0 → B2 | B0 → B1 | C1 → C2 |
|---|---|---|---|---|
| S1 — balanceado | B2 favorecido | B2 favorecido | sem diferença clara | C1 favorecido |
| S2 — pico direcional | trade-off | B0 favorecido | B0 favorecido | C1 favorecido |
| S3 — mudança de demanda | B2 favorecido | B0 favorecido | B0 favorecido | C1 favorecido |
| S4 — saturação localizada | C1 favorecido | B0 favorecido | B0 favorecido | trade-off |

## 6.2 S1 — balanceado

*Figuras 3 e 4 (FIG03, FIG04).*

**Adaptação (B0 → B2).** O B2 teve desempenho melhor que o tempo fixo calibrado: espera −15,2%
IC95% [−19,9%; −9,8%], perda de tempo −12,7% e fila média −14,4%, com vazão praticamente igual
(+0,3%). B0 → B1 não mostrou diferença clara no conjunto das métricas-chave (B1 teve menos paradas).

**Cooperação (B2 → C1).** O C1 teve desempenho **pior** que o B2: espera +35,0% IC95% [+29,2%; +41,0%],
fila média +34,2% IC95% [+28,4%; +40,2%], perda de tempo +26,1% e conclusão −0,5 p.p., com
0/10 seeds favoráveis ao C1 nas métricas de atraso. Em S1, o B2 foi o controlador de melhor
desempenho nas métricas de atraso e fila, e a cooperação não trouxe ganho.

| Métrica | B2 (média) | C1 (média) | Dif. média pareada | Dif. relativa | IC95% (dif.) | Seeds favoráveis ao tratamento | Leitura |
|---|---|---|---|---|---|---|---|
| vazão (veículos concluídos) | 1810,3 | 1804,2 | −6,1 | −0,3% | [−11,2; −0,9] | 3/10 | B2 favorecido |
| razão de conclusão (oferecidos) | 0,969 | 0,965 | −0,005 | −0,5% | [−0,007; −0,002] | 1/10 | B2 favorecido |
| razão de partida | 1,000 | 1,000 | +0,000 | +0,0% | [+0,000; +0,000] | 0/10 | sem diferença clara |
| tempo de espera médio (s) | 49,7 | 67,1 | +17,4 | +35,0% | [+14,5; +20,4] | 0/10 | B2 favorecido |
| perda de tempo média (s) | 69,0 | 87,0 | +18,0 | +26,1% | [+15,0; +21,1] | 0/10 | B2 favorecido |
| tempo de viagem médio (s) | 122,0 | 140,0 | +18,0 | +14,7% | [+15,0; +21,1] | 0/10 | B2 favorecido |
| fila média da rede (veículos) | 25,3 | 33,9 | +8,6 | +34,2% | [+7,2; +10,2] | 0/10 | B2 favorecido |
| fila máxima da rede (veículos) | 42,3 | 50,2 | +7,9 | +18,7% | [+5,2; +10,3] | 0/10 | B2 favorecido |
| atraso de partida médio (s) | 0,5 | 0,5 | +0,0 | +0,0% | [+0,0; +0,0] | 0/10 | sem diferença clara |
| veículos nunca inseridos | 0,0 | 0,0 | +0,0 | n/a | [+0,0; +0,0] | 0/10 | sem diferença clara |
| veículos inacabados na rede | 55,1 | 63,4 | +8,3 | +15,1% | [+3,4; +12,3] | 1/10 | B2 favorecido |
| teleports SUMO | 0,00 | 0,00 | +0,00 | n/a | [+0,00; +0,00] | 0/10 | sem diferença clara |

## 6.3 S2 — pico direcional (trade-off)

*Figuras 4 e 6 (FIG04, FIG06).*

**Cooperação (B2 → C1): compromisso entre métricas.** O C1 reduziu a espera (−15,2% IC95% [−18,6%; −12,2%]),
a perda de tempo (−15,3%), a fila média (−18,3% IC95% [−20,9%; −16,1%]) e a fila máxima
(−21,5%) em 10/10 seeds, mas reduziu a vazão (−5,7% IC95% [−7,8%; −4,0%]), a razão de
partida (−6,1 p.p.) e a conclusão (−4,9 p.p.), e deixou
73,1 veículos a mais nunca inseridos por execução (média B2 211,9; C1 285,0).
**O menor tempo de viagem e de espera do C1 é condicional a menos viagens concluídas** (a fila de entrada
cresce) e, portanto, não pode ser interpretado como melhora isolada. Não se aponta um controlador vencedor.

**Adaptação (B0 → B2, B0 → B1).** O tempo fixo calibrado teve desempenho substancialmente melhor que o B2 e o B1
neste regime: o B2 reduziu a vazão (−18,9%) e a conclusão (−20,5 p.p.) e aumentou a espera
(+192,4%) e a fila média (+142,1%); o B0 não deixou veículos nunca inseridos (média 0,0),
enquanto o B2 deixou 211,9. O B1 teve espera +26,4% e fila +26,9% em relação ao B0, sem diferença clara de vazão.

| Métrica | B2 (média) | C1 (média) | Dif. média pareada | Dif. relativa | IC95% (dif.) | Seeds favoráveis ao tratamento | Leitura |
|---|---|---|---|---|---|---|---|
| vazão (veículos concluídos) | 973,0 | 917,4 | −55,6 | −5,7% | [−75,5; −38,6] | 0/10 | B2 favorecido |
| razão de conclusão (oferecidos) | 0,765 | 0,716 | −0,049 | −6,4% | [−0,066; −0,033] | 0/10 | B2 favorecido |
| razão de partida | 0,822 | 0,761 | −0,061 | −7,5% | [−0,078; −0,044] | 0/10 | B2 favorecido |
| tempo de espera médio (s) | 166,0 | 140,8 | −25,3 | −15,2% | [−30,8; −20,3] | 10/10 | C1 favorecido |
| perda de tempo média (s) | 197,3 | 167,1 | −30,3 | −15,3% | [−36,4; −24,9] | 10/10 | C1 favorecido |
| tempo de viagem médio (s) | 249,9 | 219,6 | −30,3 | −12,1% | [−36,4; −24,9] | 10/10 | C1 favorecido |
| fila média da rede (veículos) | 46,1 | 37,7 | −8,4 | −18,3% | [−9,6; −7,4] | 10/10 | C1 favorecido |
| fila máxima da rede (veículos) | 74,3 | 58,3 | −16,0 | −21,5% | [−18,9; −13,1] | 10/10 | C1 favorecido |
| atraso de partida médio (s) | 271,9 | 294,3 | +22,5 | +8,3% | [+1,7; +46,2] | 4/10 | B2 favorecido |
| veículos nunca inseridos | 211,9 | 285,0 | +73,1 | +34,5% | [+52,4; +93,3] | 0/10 | B2 favorecido |
| veículos inacabados na rede | 67,6 | 52,9 | −14,7 | −21,7% | [−18,3; −11,0] | 10/10 | C1 favorecido |
| teleports SUMO | 0,00 | 0,00 | +0,00 | n/a | [+0,00; +0,00] | 0/10 | sem diferença clara |

## 6.4 S3 — mudança de demanda

*Figuras 4, 7 e 8 (FIG04, FIG07, FIG08); Figura 13 (FIG13) para a comparação com a rota.*

**Cooperação (B2 → C1).** O B2 teve desempenho melhor que o C1 nas métricas-chave: com o C1, espera
+21,4% IC95% [+18,4%; +24,6%], fila média +18,5%, vazão −1,7%, conclusão −1,7 p.p.; a área da
fila pós-choque aumentou +13,5% IC95% [+11,2%; +16,2%] com o C1
(0/10 seeds favoráveis). A **Figura 7** mostra que as filas dos três controladores crescem após o choque
em t = 2100 s; a fila média pós-choque foi de 56,0 veículos no B0, 64,1 no B2 e 72,8 no C1, e as curvas se aproximam ao final da janela.

**Adaptação (B0 → B2).** O B0 teve desempenho melhor que o B2 em conclusão (−0,7 p.p.), razão de partida
(−1,0 p.p.), espera (+8,6%) e fila média (+5,0%); a vazão total não diferiu claramente
(−0,6% IC95% [−1,3%; +0,1%]). A área da fila pós-choque com o B2 foi +14,5% IC95% [+9,5%; +19,7%] em relação ao B0
(B0: 100.739; B2: 115.334; C1: 130.943 veículo·s). O caso de mudança de demanda
**não sustentou superioridade geral da cooperação**.

> **Divulgação metodológica (S3).** O critério composto de validade do S3 foi formalizado após a inspeção
> diagnóstica do Pilot V2 e é um refinamento metodológico *post-hoc*; nenhuma métrica de recuperação nova
> foi criada após ver os resultados finais (a área da fila pós-choque é a métrica congelada da metodologia do S3).

| Métrica | B2 (média) | C1 (média) | Dif. média pareada | Dif. relativa | IC95% (dif.) | Seeds favoráveis ao tratamento | Leitura |
|---|---|---|---|---|---|---|---|
| vazão (veículos concluídos) | 1944,0 | 1911,1 | −32,9 | −1,7% | [−38,7; −27,1] | 0/10 | B2 favorecido |
| razão de conclusão (oferecidos) | 0,927 | 0,910 | −0,017 | −1,9% | [−0,020; −0,015] | 0/10 | B2 favorecido |
| razão de partida | 0,989 | 0,976 | −0,013 | −1,3% | [−0,015; −0,011] | 0/10 | B2 favorecido |
| tempo de espera médio (s) | 78,5 | 95,3 | +16,8 | +21,4% | [+14,4; +19,3] | 0/10 | B2 favorecido |
| perda de tempo média (s) | 104,3 | 120,4 | +16,0 | +15,3% | [+13,4; +18,7] | 0/10 | B2 favorecido |
| fila média da rede (veículos) | 45,0 | 53,3 | +8,3 | +18,5% | [+7,0; +9,7] | 0/10 | B2 favorecido |
| fila máxima da rede (veículos) | 99,1 | 110,6 | +11,5 | +11,6% | [+7,7; +15,0] | 0/10 | B2 favorecido |
| atraso de partida médio (s) | 5,9 | 13,4 | +7,6 | +129,3% | [+5,9; +9,3] | 0/10 | B2 favorecido |
| veículos nunca inseridos | 21,8 | 48,5 | +26,7 | +122,5% | [+22,3; +31,1] | 0/10 | B2 favorecido |
| área da fila pós-choque (veículo·s) | 115334,4 | 130942,6 | +15608,3 | +13,5% | [+12937,6; +18707,5] | 0/10 | B2 favorecido |

## 6.5 S4 — saturação localizada

*Figuras 4, 9 e 10 (FIG04, FIG09, FIG10).*

**Cooperação (B2 → C1): benefício sob saturação localizada.** O C1 teve desempenho melhor que o B2 nas
principais métricas de congestionamento: vazão +8,8% IC95% [+5,6%; +13,8%], espera −19,5% IC95% [−21,5%; −17,4%],
perda de tempo −22,6%, fila média −17,3% IC95% [−18,4%; −16,2%], fila máxima −21,0% e conclusão
+3,0 p.p., em 10/10 seeds. **Por outro lado,** o atraso de partida **piorou** com o C1
(+16,8% IC95% [+12,2%; +22,1%]), a razão de partida não diferiu claramente (+0,2 p.p.) e o número de veículos
nunca inseridos não diferiu claramente (−8,9 veículos por execução). O benefício é, portanto, específico das métricas
de congestionamento e de vazão, e não universal em todas as dimensões.

**Saturação severa e cautela com métricas condicionais.** Em S4, cerca de 65–72% das viagens oferecidas
não concluem (conforme o controlador). As métricas de tempo valem para uma minoria de viagens e devem ser lidas
com a razão de conclusão (0,277–0,352, entre controladores) e os veículos nunca inseridos
(1.899–2.129 por execução).

**Adaptação.** Em S4, o B0 teve desempenho melhor que o B2 e que o B1 em vazão, conclusão e atraso
(B2 vs B0: vazão −16,9%, espera +40,6%). **Teleports do SUMO** (política `ALLOW_AND_MEASURE`;
medidos e mantidos): 11 das 50 execuções do S4 tiveram teleports, num total de 31: B0 28 (em 10/10 execuções),
B2 3 (em 1/10) e B1, C1 e C2 zero; não houve teleports em S1–S3. Nenhuma execução foi excluída
por teleports. Os teleports concentram-se no B0, o controlador de maior vazão em S4, e devem ser lidos junto da severidade da
congestão, e não como falha do experimento.

| Métrica | B2 (média) | C1 (média) | Dif. média pareada | Dif. relativa | IC95% (dif.) | Seeds favoráveis ao tratamento | Leitura |
|---|---|---|---|---|---|---|---|
| vazão (veículos concluídos) | 1227,3 | 1334,9 | +107,6 | +8,8% | [+69,1; +169,8] | 10/10 | C1 favorecido |
| razão de conclusão (oferecidos) | 0,277 | 0,307 | +0,030 | +10,8% | [+0,018; +0,048] | 10/10 | C1 favorecido |
| razão de partida | 0,411 | 0,414 | +0,002 | +0,6% | [−0,010; +0,021] | 4/10 | sem diferença clara |
| tempo de espera médio (s) | 913,8 | 735,4 | −178,4 | −19,5% | [−196,5; −158,7] | 10/10 | C1 favorecido |
| perda de tempo média (s) | 1151,5 | 890,7 | −260,8 | −22,6% | [−281,4; −237,8] | 10/10 | C1 favorecido |
| tempo de viagem médio (s) | 1215,3 | 954,3 | −261,1 | −21,5% | [−281,9; −238,0] | 10/10 | C1 favorecido |
| fila média da rede (veículos) | 356,4 | 294,9 | −61,5 | −17,3% | [−65,6; −57,9] | 10/10 | C1 favorecido |
| fila máxima da rede (veículos) | 450,6 | 356,1 | −94,5 | −21,0% | [−100,9; −87,9] | 10/10 | C1 favorecido |
| atraso de partida médio (s) | 731,8 | 854,5 | +122,7 | +16,8% | [+89,4; +162,0] | 0/10 | B2 favorecido |
| veículos nunca inseridos | 2112,3 | 2103,4 | −8,9 | −0,4% | [−76,8; +35,9] | 4/10 | sem diferença clara |
| veículos inacabados na rede | 482,2 | 383,7 | −98,5 | −20,4% | [−106,9; −89,7] | 10/10 | C1 favorecido |
| teleports SUMO | 0,30 | 0,00 | −0,30 | −100,0% | [−0,90; +0,00] | 1/10 | sem diferença clara |

## 6.6 Síntese das comparações do experimento principal

**Comparação primária B2 → C1.** S1: B2 favorecido; S2: trade-off; S3: B2 favorecido; S4: C1 favorecido sob saturação
localizada. A contribuição da cooperação é, portanto, **dependente do cenário** (Figuras 4, 5 e 19).

**B0 → B2 (efeito da adaptação por pressão local).** O B2 teve melhor desempenho que o B0 apenas em S1; o B0 foi mais forte em S2,
S3 e S4 (Figura 3). **B0 → B1.** Sem diferença clara em S1; B0 mais forte em S2, S3 e S4.
**C1 → C2.** O C1 foi mais forte em S1–S3 (por exemplo, a espera do C2 em relação ao C1 foi +187,4% em S1 e +121,2% em S3);
em S4 houve trade-off (C2: espera −16,5%, fila média −13,7%, vazão +2,2%; porém atraso de partida +16,3%).

*Comparação complementar exploratória (fora da lista congelada).* B0 × C1 foi calculada com o mesmo estimador e
marcada como exploratória no arquivo suplementar da análise: o tempo fixo calibrado teve menor espera e fila em S1, S2 e S3 e, em S2–S4, maior vazão
e conclusão; em S4 teve também menor espera, mas o C1 teve fila média menor. Essa comparação não foi usada para a classificação principal.

## 6.7 Rota de referência (N = 10)

*Figuras 11, 12 e 13 (FIG11, FIG12, FIG13) e Tabela 4 (TABLE04).*

A coorte da rota `left1A1 → A1B1 → B1C1 → C1right1` tem, por execução, em média 52,0 (S1), 108,7 (S2),
113,1 (S3) e 200,2 (S4) veículos oferecidos. As diferenças pareadas e a conclusão são:

| Cenário | B0: viagem / conclusão | B2: viagem / conclusão | C1: viagem / conclusão | B0 → B2 (Δ viagem [IC95%]; Δ conclusão) | B2 → C1 (Δ viagem [IC95%]; Δ conclusão) |
|---|---|---|---|---|---|
| S1 | 129,2 s / 0,977 | 116,7 s / 0,971 | 139,8 s / 0,964 | −12,5 s [−16,9; −8,8]; concl. −0,7 p.p. | +23,2 s [+17,4; +28,9]; concl. −0,6 p.p. |
| S2 | 129,3 s / 0,967 | 322,4 s / 0,673 | 283,0 s / 0,649 | +193,2 s [+182,7; +203,5]; concl. −29,4 p.p. | −39,4 s [−55,5; −22,5]; concl. −2,4 p.p. |
| S3 | 226,7 s / 0,858 | 278,7 s / 0,817 | 232,5 s / 0,826 | +52,0 s [+41,6; +63,1]; concl. −4,1 p.p. | −46,2 s [−54,4; −33,9]; concl. +0,9 p.p. |
| S4 | 370,2 s / 0,899 | 1165,4 s / 0,202 | 779,9 s / 0,293 | +795,2 s [+694,9; +907,5]; concl. −69,7 p.p. | −385,5 s [−489,1; −293,2]; concl. +9,1 p.p. |

**Adaptação (B0 → B2), na rota.** Em S1 o B2 reduziu o tempo de viagem da rota (−12,5 s [−16,9; −8,8]), com conclusão praticamente
igual (−0,7 p.p.). Em S2, S3 e S4 o tempo de viagem condicional **aumentou** (+193,2 s, +52,0 s e +795,2 s) e a conclusão
caiu (−29,4 p.p., −4,1 p.p. e −69,7 p.p.): em S4, a conclusão da rota cai aproximadamente −69,7 p.p. (B0: 0,899; B2: 0,202), o que mostra
que o tempo de viagem do B2 é medido sobre uma fração muito menor da coorte.

**Cooperação (B2 → C1), na rota.** Em S1 o C1 piorou o tempo de viagem da rota (+23,2 s [+17,4; +28,9]). Em S2, S3 e S4 o C1 **reduziu** o tempo de viagem
(−39,4 s, −46,2 s e −385,5 s), com conclusão sem diferença clara em S2 e S3 e maior em S4 (+9,1 p.p.; B2: 0,202; C1: 0,293).
O efeito da adaptação e o da cooperação são interpretados **separadamente**; as conclusões de rota condicionais a
coortes parciais (S2 e S4) devem ser lidas com a conclusão.

**Rede × rota em S3.** Na rede inteira, o B2 teve desempenho melhor que o C1: a diferença no tempo de viagem médio da rede (C1 − B2) foi
+15,9 s (conclusão da rede −1,7 p.p.). Na rota de referência, o C1 **reduziu** o tempo de viagem
em −46,2 s [−54,4; −33,9] em relação ao B2, com conclusão sem diferença clara (+0,9 p.p.). Isso **não é contraditório**: a rede inteira
(cerca de 2.019 veículos oferecidos por execução) e a coorte da rota (cerca de 113,1 veículos) representam populações e escalas diferentes, e os
resultados são reportados em conjunto (Figura 13).

## 6.8 S5 — degradação da comunicação (tráfego S2)

*Figuras 14, 14B e 15 (FIG14, FIG14B, FIG15) e Tabela 5 (TABLE05).*

> Nota de leitura: a Tabela 5 (TABLE05) usa **bytes entregues** por execução (coluna "Bytes entregues/run"); a Tabela 6 (TABLE06) usa **bytes enviados** por execução. São grandezas diferentes: com 0% de perda, as médias diferem em cerca de 0,09% (C1), diferença pequena entre as duas grandezas (não é inconsistência nos dados); a causa dessa pequena diferença não foi investigada e não afeta nenhuma conclusão.

**Validação da comunicação (fatos, não conclusões de tráfego).** Com 0% de perda, não houve descartes. Com 20% e 50%, a
taxa de descarte observada ficou entre 19,9% e 20,2% (20%) e entre 49,7% e 50,2% (50%) — a taxa
observada não precisa igualar a nominal em amostras finitas. Com 100% de perda, 1.872.000 mensagens foram enviadas, 1.872.000 descartadas e
**0 entregues** (0 bytes entregues). Nenhuma mensagem ficou obsoleta (atraso 0).

**Resultado de tráfego.** A degradação **não foi monotônica**. Em relação a 0% de perda (pareado por seed):

| Controlador | Mudança | Vazão | Conclusão (ofer.) | Espera | Fila média |
|---|---|---|---|---|---|
| C1 | 0% → 20% | +8,6% IC95% [+7,5%; +9,7%] | +9,6% IC95% [+8,5%; +10,8%] | −3,3% IC95% [−5,4%; −1,3%] | +2,7% IC95% [+0,4%; +4,9%] |
| C1 | 0% → 50% | +10,3% IC95% [+9,3%; +11,4%] | +11,6% IC95% [+10,5%; +12,7%] | −1,4% IC95% [−3,4%; +0,7%] | +6,7% IC95% [+4,9%; +8,3%] |
| C1 | 0% → 100% | +6,1% IC95% [+4,2%; +8,2%] | +6,9% IC95% [+4,6%; +9,3%] | +17,9% IC95% [+14,4%; +21,9%] | +22,4% IC95% [+19,7%; +25,5%] |
| C2 | 0% → 20% | +15,9% IC95% [+14,9%; +16,7%] | +17,6% IC95% [+16,8%; +18,3%] | −13,9% IC95% [−15,0%; −12,7%] | −2,3% IC95% [−3,8%; −0,8%] |
| C2 | 0% → 50% | +19,5% IC95% [+18,5%; +20,4%] | +21,9% IC95% [+21,1%; +22,8%] | −14,3% IC95% [−15,8%; −12,9%] | +0,3% IC95% [−1,3%; +1,8%] |
| C2 | 0% → 100% | +15,6% IC95% [+14,7%; +16,7%] | +17,6% IC95% [+16,3%; +18,9%] | +1,5% IC95% [−0,9%; +3,9%] | +14,7% IC95% [+12,7%; +16,9%] |

- **C1.** Com 20% e 50% de perda, a vazão **aumentou** (+8,6% e +10,3%) e a conclusão também; o atraso de partida e os veículos nunca
  inseridos diminuíram, enquanto a fila média e as paradas pioraram levemente (+2,7% e +6,7% na fila média).
- **C2.** Com 20% e 50% de perda, a vazão aumentou (+15,9% e +19,5%), assim como a conclusão, e a espera diminuiu (−13,9% e −14,3%), em 10/10 seeds. O ponto
  de menor vazão do C2 foi com comunicação completa (0%).
- **100% de perda.** As métricas de tráfego do C1 e do C2 foram **idênticas** às do B2 da mesma seed em 380/380 comparações
  (execução × métrica de tráfego). Os controladores cooperativos permaneceram operacionais sem mensagens entregues (**fallback operacional**):
  a simulação concluiu, as métricas foram finalizadas e o controlador continuou decidindo; **isso não constitui verificação formal de segurança** (Seção 3.5).

Em relação ao B2 de referência, o C1 e o C2 com 20% e 50% de perda ficaram próximos ou melhores em vazão e conclusão e melhores em atraso e fila
(por exemplo, C1 com 20%: vazão +2,4%, espera −18,0%); com 0%, o C1 teve vazão −5,7% e espera
−15,2% (o mesmo trade-off do S2 do experimento principal), e o C2 teve vazão −13,5%.

| Controlador | Perda | Vazão | Concl. (ofer.) | Espera (s) | Fila média | Msgs entregues/run | Bytes entregues/run |
|---|---|---|---|---|---|---|---|
| B2 (referência) | — | 973,0 | 0,765 | 166,0 | 46,1 | — | — |
| C1 | 0% | 917,4 ± 17,1 | 0,716 ± 0,015 | 140,8 ± 4,3 | 37,7 ± 1,0 | 93.600 | 30,2 MB |
| C1 | 20% | 996,1 ± 6,3 | 0,785 ± 0,006 | 136,1 ± 3,5 | 38,7 ± 1,1 | 74.856 | 24,3 MB |
| C1 | 50% | 1012,2 ± 10,5 | 0,799 ± 0,008 | 138,8 ± 4,1 | 40,2 ± 1,1 | 46.806 | 15,2 MB |
| C1 | 100% | 973,0 ± 23,2 | 0,765 ± 0,020 | 166,0 ± 7,1 | 46,1 ± 1,5 | 0 | 0,0 MB |
| C2 | 0% | 841,4 ± 11,8 | 0,651 ± 0,009 | 163,6 ± 3,1 | 40,2 ± 0,6 | 93.600 | 70,3 MB |
| C2 | 20% | 974,9 ± 7,4 | 0,765 ± 0,008 | 140,9 ± 4,3 | 39,3 ± 1,1 | 74.856 | 56,3 MB |
| C2 | 50% | 1005,6 ± 7,7 | 0,794 ± 0,005 | 140,2 ± 4,0 | 40,3 ± 1,1 | 46.806 | 35,3 MB |
| C2 | 100% | 973,0 ± 23,2 | 0,765 ± 0,020 | 166,0 ± 7,1 | 46,1 ± 1,5 | 0 | 0,0 MB |

**Interpretação (limitada ao que os dados mostram).** Não foi possível identificar um limiar monotônico de tolerância à perda de pacotes:
apenas quatro níveis foram avaliados e o efeito não é monotônico. O mecanismo que explica o desempenho maior com perda moderada
**não foi investigado** neste trabalho (Seção 7).

## 6.9 Custo de comunicação: C1 × C2

*Figuras 16 e 17 (FIG16, FIG17) e Tabela 6 (TABLE06).*

> Nota de leitura: a Tabela 6 (TABLE06) usa **bytes enviados** por execução; a Tabela 5 (TABLE05) usa **bytes entregues**. Por isso, o valor do C1 com 0% de perda é 30,3 MB aqui (enviados) e 30,2 MB na Tabela 5 (entregues); não há alteração de dados.

C1 e C2 enviam aproximadamente o mesmo número de mensagens por execução (93.600 e 93.600), mas a mensagem expandida é maior:

| Controlador | Mensagens enviadas/run | Bytes enviados/run | Bytes por mensagem |
|---|---|---|---|
| C1 | 93.600 | 30,3 MB | 323 |
| C2 | 93.600 | 70,3 MB | 751 |

O C2 envia cerca de 2,32 vezes os bytes do C1 (faixa 2,27–2,36× entre cenários e níveis de perda). Em desempenho, o C2 não superou o C1 em
geral (Seção 6.6). Não se afirma que o C2 seja superior pelo fato de enviar mais informação. A conclusão é cautelosa: nas condições simuladas,
**o maior custo de comunicação do C2 não produziu benefício geral de tráfego** (o benefício observado em S4 limita-se a atraso e fila, com custo no atraso de partida).

## 6.10 Piloto V2 (N = 5) × Final (N = 10): comparação metodológica

*Figuras 18 e 18B (FIG18, FIG18B).* **Esta seção não combina amostras:** as cinco seeds do Pilot V2 são as cinco primeiras do final. Reexecutar essas cinco
seeds reproduziu exatamente as diferenças do piloto (57/57 comparações), de modo que o que o N = 10 acrescenta são as cinco seeds adicionais.

| Cenário | Métrica | Piloto (N=5): Δ relativo C1 vs B2 | Final (N=10): Δ relativo C1 vs B2 | Direção persistiu | Largura IC final/piloto |
|---|---|---|---|---|---|
| S1 | vazão (veículos concluídos) | −0,2% | −0,3% | sim | 0,86 |
| S1 | tempo de espera médio (s) | +44,7% | +35,0% | sim | 0,94 |
| S1 | fila média da rede (veículos) | +44,1% | +34,2% | sim | 1,01 |
| S2 | vazão (veículos concluídos) | −6,1% | −5,7% | sim | 0,65 |
| S2 | tempo de espera médio (s) | −12,7% | −15,2% | sim | 1,02 |
| S2 | fila média da rede (veículos) | −16,3% | −18,3% | sim | 1,11 |
| S3 | vazão (veículos concluídos) | −1,6% | −1,7% | sim | 0,64 |
| S3 | tempo de espera médio (s) | +24,7% | +21,4% | sim | 0,67 |
| S3 | fila média da rede (veículos) | +21,9% | +18,5% | sim | 0,68 |
| S4 | vazão (veículos concluídos) | +12,0% | +8,8% | sim | 0,53 |
| S4 | tempo de espera médio (s) | −20,4% | −19,5% | sim | 1,01 |
| S4 | fila média da rede (veículos) | −17,7% | −17,3% | sim | 0,60 |

A direção da diferença C1 − B2 persistiu em 50/51 comparações com efeito não nulo no piloto, e nenhuma conclusão central foi revertida; 2 vereditos
de IC mudaram (S1 vazão (veículos concluídos); S2 atraso de partida médio (s)). No S4, o efeito do C1 sobre a vazão foi estimado em +12,0% no piloto e +8,8% no final, e a largura do IC95%
da vazão estreitou em S2 (razão final/piloto 0,65), S3 (0,64) e S4 (0,53). Retrospectivamente, N = 10 aumentou a precisão e reduziu o risco de
superestimar o efeito (S4), sem inverter conclusões; isto é uma avaliação metodológica, **não uma nova regra de parada**.
