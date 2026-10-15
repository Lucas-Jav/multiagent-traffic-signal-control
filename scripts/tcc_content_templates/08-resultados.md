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

{{T_desc(S1)}}

**S2 — pico direcional**

{{T_desc(S2)}}

**S3 — mudança de demanda**

{{T_desc(S3)}}

**S4 — saturação localizada**

{{T_desc(S4)}}

A classificação das comparações congeladas, por cenário (regra da Seção 3.11), é:

{{T_class()}}

## 6.2 S1 — balanceado

*Figuras 3 e 4 (FIG03, FIG04).*

**Adaptação (B0 → B2).** O B2 teve desempenho melhor que o tempo fixo calibrado: espera {{rel(S1,B0,B2,'mean_waiting_time')}}
{{relci(S1,B0,B2,'mean_waiting_time')}}, perda de tempo {{rel(S1,B0,B2,'mean_time_loss')}} e fila média {{rel(S1,B0,B2,'mean_network_queue_vehicles')}}, com vazão praticamente igual
({{rel(S1,B0,B2,'throughput')}}). B0 → B1 não mostrou diferença clara no conjunto das métricas-chave (B1 teve menos paradas).

**Cooperação (B2 → C1).** O C1 teve desempenho **pior** que o B2: espera {{rel(S1,B2,C1,'mean_waiting_time')}} {{relci(S1,B2,C1,'mean_waiting_time')}},
fila média {{rel(S1,B2,C1,'mean_network_queue_vehicles')}} {{relci(S1,B2,C1,'mean_network_queue_vehicles')}}, perda de tempo {{rel(S1,B2,C1,'mean_time_loss')}} e conclusão {{pp(S1,B2,C1)}}, com
{{nfav(S1,B2,C1,'mean_waiting_time')}} seeds favoráveis ao C1 nas métricas de atraso. Em S1, o B2 foi o controlador de melhor
desempenho nas métricas de atraso e fila, e a cooperação não trouxe ganho.

{{T_pair(S1,B2,C1)}}

## 6.3 S2 — pico direcional (trade-off)

*Figuras 4 e 6 (FIG04, FIG06).*

**Cooperação (B2 → C1): compromisso entre métricas.** O C1 reduziu a espera ({{rel(S2,B2,C1,'mean_waiting_time')}} {{relci(S2,B2,C1,'mean_waiting_time')}}),
a perda de tempo ({{rel(S2,B2,C1,'mean_time_loss')}}), a fila média ({{rel(S2,B2,C1,'mean_network_queue_vehicles')}} {{relci(S2,B2,C1,'mean_network_queue_vehicles')}}) e a fila máxima
({{rel(S2,B2,C1,'max_network_queue_vehicles')}}) em {{nfav(S2,B2,C1,'mean_waiting_time')}} seeds, mas reduziu a vazão ({{rel(S2,B2,C1,'throughput')}} {{relci(S2,B2,C1,'throughput')}}), a razão de
partida ({{pp(S2,B2,C1,'departure_ratio')}}) e a conclusão ({{pp(S2,B2,C1)}}), e deixou
{{dabs(S2,B2,C1,'never_inserted_vehicle_count').replace('+','')}} veículos a mais nunca inseridos por execução (média B2 {{mu(S2,B2,'never_inserted_vehicle_count')}}; C1 {{mu(S2,C1,'never_inserted_vehicle_count')}}).
**O menor tempo de viagem e de espera do C1 é condicional a menos viagens concluídas** (a fila de entrada
cresce) e, portanto, não pode ser interpretado como melhora isolada. Não se aponta um controlador vencedor.

**Adaptação (B0 → B2, B0 → B1).** O tempo fixo calibrado teve desempenho substancialmente melhor que o B2 e o B1
neste regime: o B2 reduziu a vazão ({{rel(S2,B0,B2,'throughput')}}) e a conclusão ({{pp(S2,B0,B2)}}) e aumentou a espera
({{rel(S2,B0,B2,'mean_waiting_time')}}) e a fila média ({{rel(S2,B0,B2,'mean_network_queue_vehicles')}}); o B0 não deixou veículos nunca inseridos (média {{mu(S2,B0,'never_inserted_vehicle_count')}}),
enquanto o B2 deixou {{mu(S2,B2,'never_inserted_vehicle_count')}}. O B1 teve espera {{rel(S2,B0,B1,'mean_waiting_time')}} e fila {{rel(S2,B0,B1,'mean_network_queue_vehicles')}} em relação ao B0, sem diferença clara de vazão.

{{T_pair(S2,B2,C1)}}

## 6.4 S3 — mudança de demanda

*Figuras 4, 7 e 8 (FIG04, FIG07, FIG08); Figura 13 (FIG13) para a comparação com a rota.*

**Cooperação (B2 → C1).** O B2 teve desempenho melhor que o C1 nas métricas-chave: com o C1, espera
{{rel(S3,B2,C1,'mean_waiting_time')}} {{relci(S3,B2,C1,'mean_waiting_time')}}, fila média {{rel(S3,B2,C1,'mean_network_queue_vehicles')}}, vazão {{rel(S3,B2,C1,'throughput')}}, conclusão {{pp(S3,B2,C1)}}; a área da
fila pós-choque aumentou {{rel(S3,B2,C1,'post_shock_queue_auc_vehicle_seconds')}} {{relci(S3,B2,C1,'post_shock_queue_auc_vehicle_seconds')}} com o C1
({{nfav(S3,B2,C1,'post_shock_queue_auc_vehicle_seconds')}} seeds favoráveis). A **Figura 7** mostra que as filas dos três controladores crescem após o choque
em t = 2100 s; a fila média pós-choque foi de {{mu(S3,B0,'post_shock_mean_network_queue_vehicles')}} veículos no B0, {{mu(S3,B2,'post_shock_mean_network_queue_vehicles')}} no B2 e {{mu(S3,C1,'post_shock_mean_network_queue_vehicles')}} no C1, e as curvas se aproximam ao final da janela.

**Adaptação (B0 → B2).** O B0 teve desempenho melhor que o B2 em conclusão ({{pp(S3,B0,B2)}}), razão de partida
({{pp(S3,B0,B2,'departure_ratio')}}), espera ({{rel(S3,B0,B2,'mean_waiting_time')}}) e fila média ({{rel(S3,B0,B2,'mean_network_queue_vehicles')}}); a vazão total não diferiu claramente
({{rel(S3,B0,B2,'throughput')}} {{relci(S3,B0,B2,'throughput')}}). A área da fila pós-choque com o B2 foi {{rel(S3,B0,B2,'post_shock_queue_auc_vehicle_seconds')}} {{relci(S3,B0,B2,'post_shock_queue_auc_vehicle_seconds')}} em relação ao B0
(B0: {{mu(S3,B0,'post_shock_queue_auc_vehicle_seconds',0)}}; B2: {{mu(S3,B2,'post_shock_queue_auc_vehicle_seconds',0)}}; C1: {{mu(S3,C1,'post_shock_queue_auc_vehicle_seconds',0)}} veículo·s). O caso de mudança de demanda
**não sustentou superioridade geral da cooperação**.

> **Divulgação metodológica (S3).** O critério composto de validade do S3 foi formalizado após a inspeção
> diagnóstica do Pilot V2 e é um refinamento metodológico *post-hoc*; nenhuma métrica de recuperação nova
> foi criada após ver os resultados finais (a área da fila pós-choque é a métrica congelada da metodologia do S3).

{{T_pair(S3,B2,C1,['throughput','completion_ratio_offered','departure_ratio','mean_waiting_time','mean_time_loss','mean_network_queue_vehicles','max_network_queue_vehicles','mean_depart_delay_seconds','never_inserted_vehicle_count','post_shock_queue_auc_vehicle_seconds'])}}

## 6.5 S4 — saturação localizada

*Figuras 4, 9 e 10 (FIG04, FIG09, FIG10).*

**Cooperação (B2 → C1): benefício sob saturação localizada.** O C1 teve desempenho melhor que o B2 nas
principais métricas de congestionamento: vazão {{rel(S4,B2,C1,'throughput')}} {{relci(S4,B2,C1,'throughput')}}, espera {{rel(S4,B2,C1,'mean_waiting_time')}} {{relci(S4,B2,C1,'mean_waiting_time')}},
perda de tempo {{rel(S4,B2,C1,'mean_time_loss')}}, fila média {{rel(S4,B2,C1,'mean_network_queue_vehicles')}} {{relci(S4,B2,C1,'mean_network_queue_vehicles')}}, fila máxima {{rel(S4,B2,C1,'max_network_queue_vehicles')}} e conclusão
{{pp(S4,B2,C1)}}, em {{nfav(S4,B2,C1,'throughput')}} seeds. **Por outro lado,** o atraso de partida **piorou** com o C1
({{rel(S4,B2,C1,'mean_depart_delay_seconds')}} {{relci(S4,B2,C1,'mean_depart_delay_seconds')}}), a razão de partida não diferiu claramente ({{pp(S4,B2,C1,'departure_ratio')}}) e o número de veículos
nunca inseridos não diferiu claramente ({{dabs(S4,B2,C1,'never_inserted_vehicle_count')}} veículos por execução). O benefício é, portanto, específico das métricas
de congestionamento e de vazão, e não universal em todas as dimensões.

**Saturação severa e cautela com métricas condicionais.** Em S4, cerca de {{pct_not_completing(S4)}} das viagens oferecidas
não concluem (conforme o controlador). As métricas de tempo valem para uma minoria de viagens e devem ser lidas
com a razão de conclusão ({{span(S4,'completion_ratio_offered')}}, entre controladores) e os veículos nunca inseridos
({{span(S4,'never_inserted_vehicle_count',d=0)}} por execução).

**Adaptação.** Em S4, o B0 teve desempenho melhor que o B2 e que o B1 em vazão, conclusão e atraso
(B2 vs B0: vazão {{rel(S4,B0,B2,'throughput')}}, espera {{rel(S4,B0,B2,'mean_waiting_time')}}). **Teleports do SUMO** (política `ALLOW_AND_MEASURE`;
medidos e mantidos): {{tele(None,'runs')}} das 50 execuções do S4 tiveram teleports, num total de {{tele(None,'total')}}: B0 {{tele(B0,'total')}} (em {{tele(B0,'runs')}}/10 execuções),
B2 {{tele(B2,'total')}} (em {{tele(B2,'runs')}}/10) e B1, C1 e C2 zero; não houve teleports em S1–S3. Nenhuma execução foi excluída
por teleports. Os teleports concentram-se no B0, o controlador de maior vazão em S4, e devem ser lidos junto da severidade da
congestão, e não como falha do experimento.

{{T_pair(S4,B2,C1)}}

## 6.6 Síntese das comparações do experimento principal

**Comparação primária B2 → C1.** S1: B2 favorecido; S2: trade-off; S3: B2 favorecido; S4: C1 favorecido sob saturação
localizada. A contribuição da cooperação é, portanto, **dependente do cenário** (Figuras 4, 5 e 19).

**B0 → B2 (efeito da adaptação por pressão local).** O B2 teve melhor desempenho que o B0 apenas em S1; o B0 foi mais forte em S2,
S3 e S4 (Figura 3). **B0 → B1.** Sem diferença clara em S1; B0 mais forte em S2, S3 e S4.
**C1 → C2.** O C1 foi mais forte em S1–S3 (por exemplo, a espera do C2 em relação ao C1 foi {{rel(S1,C1,C2,'mean_waiting_time')}} em S1 e {{rel(S3,C1,C2,'mean_waiting_time')}} em S3);
em S4 houve trade-off (C2: espera {{rel(S4,C1,C2,'mean_waiting_time')}}, fila média {{rel(S4,C1,C2,'mean_network_queue_vehicles')}}, vazão {{rel(S4,C1,C2,'throughput')}}; porém atraso de partida {{rel(S4,C1,C2,'mean_depart_delay_seconds')}}).

*Comparação complementar exploratória (fora da lista congelada).* B0 × C1 foi calculada com o mesmo estimador e
marcada como exploratória no arquivo suplementar da análise: o tempo fixo calibrado teve menor espera e fila em S1, S2 e S3 e, em S2–S4, maior vazão
e conclusão; em S4 teve também menor espera, mas o C1 teve fila média menor. Essa comparação não foi usada para a classificação principal.

## 6.7 Rota de referência (N = 10)

*Figuras 11, 12 e 13 (FIG11, FIG12, FIG13) e Tabela 4 (TABLE04).*

A coorte da rota `left1A1 → A1B1 → B1C1 → C1right1` tem, por execução, em média {{rrcoh(S1,B0)}} (S1), {{rrcoh(S2,B0)}} (S2),
{{rrcoh(S3,B0)}} (S3) e {{rrcoh(S4,B0)}} (S4) veículos oferecidos. As diferenças pareadas e a conclusão são:

{{T_ref()}}

**Adaptação (B0 → B2), na rota.** Em S1 o B2 reduziu o tempo de viagem da rota ({{rrd(S1,B0,B2)}} s {{rrci(S1,B0,B2)}}), com conclusão praticamente
igual ({{rrpp(S1,B0,B2)}}). Em S2, S3 e S4 o tempo de viagem condicional **aumentou** ({{rrd(S2,B0,B2)}} s, {{rrd(S3,B0,B2)}} s e {{rrd(S4,B0,B2)}} s) e a conclusão
caiu ({{rrpp(S2,B0,B2)}}, {{rrpp(S3,B0,B2)}} e {{rrpp(S4,B0,B2)}}): em S4, a conclusão da rota cai aproximadamente {{rrpp(S4,B0,B2)}} (B0: {{rrm(S4,B0,'cmp')}}; B2: {{rrm(S4,B2,'cmp')}}), o que mostra
que o tempo de viagem do B2 é medido sobre uma fração muito menor da coorte.

**Cooperação (B2 → C1), na rota.** Em S1 o C1 piorou o tempo de viagem da rota ({{rrd(S1,B2,C1)}} s {{rrci(S1,B2,C1)}}). Em S2, S3 e S4 o C1 **reduziu** o tempo de viagem
({{rrd(S2,B2,C1)}} s, {{rrd(S3,B2,C1)}} s e {{rrd(S4,B2,C1)}} s), com conclusão sem diferença clara em S2 e S3 e maior em S4 ({{rrpp(S4,B2,C1)}}; B2: {{rrm(S4,B2,'cmp')}}; C1: {{rrm(S4,C1,'cmp')}}).
O efeito da adaptação e o da cooperação são interpretados **separadamente**; as conclusões de rota condicionais a
coortes parciais (S2 e S4) devem ser lidas com a conclusão.

**Rede × rota em S3.** Na rede inteira, o B2 teve desempenho melhor que o C1: a diferença no tempo de viagem médio da rede (C1 − B2) foi
{{net_vs_route('network_mean_travel_time_diff')}} s (conclusão da rede {{pp(S3,B2,C1)}}). Na rota de referência, o C1 **reduziu** o tempo de viagem
em {{rrd(S3,B2,C1)}} s {{rrci(S3,B2,C1)}} em relação ao B2, com conclusão sem diferença clara ({{rrpp(S3,B2,C1)}}). Isso **não é contraditório**: a rede inteira
(cerca de {{mu(S3,B2,'offered_vehicle_count',0)}} veículos oferecidos por execução) e a coorte da rota (cerca de {{rrcoh(S3,B2)}} veículos) representam populações e escalas diferentes, e os
resultados são reportados em conjunto (Figura 13).

## 6.8 S5 — degradação da comunicação (tráfego S2)

*Figuras 14, 14B e 15 (FIG14, FIG14B, FIG15) e Tabela 5 (TABLE05).*

**Validação da comunicação (fatos, não conclusões de tráfego).** Com 0% de perda, não houve descartes. Com 20% e 50%, a
taxa de descarte observada ficou entre {{drop_ratio(0.2,'min')}} e {{drop_ratio(0.2,'max')}} (20%) e entre {{drop_ratio(0.5,'min')}} e {{drop_ratio(0.5,'max')}} (50%) — a taxa
observada não precisa igualar a nominal em amostras finitas. Com 100% de perda, {{total100('sent')}} mensagens foram enviadas, {{total100('dropped')}} descartadas e
**0 entregues** ({{bytes100()}} bytes entregues). Nenhuma mensagem ficou obsoleta (atraso 0).

**Resultado de tráfego.** A degradação **não foi monotônica**. Em relação a 0% de perda (pareado por seed):

{{T_s5deg()}}

- **C1.** Com 20% e 50% de perda, a vazão **aumentou** ({{s5rel(C1,0.2,'throughput')}} e {{s5rel(C1,0.5,'throughput')}}) e a conclusão também; o atraso de partida e os veículos nunca
  inseridos diminuíram, enquanto a fila média e as paradas pioraram levemente ({{s5rel(C1,0.2,'mean_network_queue_vehicles')}} e {{s5rel(C1,0.5,'mean_network_queue_vehicles')}} na fila média).
- **C2.** Com 20% e 50% de perda, a vazão aumentou ({{s5rel(C2,0.2,'throughput')}} e {{s5rel(C2,0.5,'throughput')}}), assim como a conclusão, e a espera diminuiu ({{s5rel(C2,0.2,'mean_waiting_time')}} e {{s5rel(C2,0.5,'mean_waiting_time')}}), em 10/10 seeds. O ponto
  de menor vazão do C2 foi com comunicação completa (0%).
- **100% de perda.** As métricas de tráfego do C1 e do C2 foram **idênticas** às do B2 da mesma seed em {{eq_b2()}} comparações
  (execução × métrica de tráfego). Os controladores cooperativos permaneceram operacionais sem mensagens entregues (**fallback operacional**):
  a simulação concluiu, as métricas foram finalizadas e o controlador continuou decidindo; **isso não constitui verificação formal de segurança** (Seção 3.5).

Em relação ao B2 de referência, o C1 e o C2 com 20% e 50% de perda ficaram próximos ou melhores em vazão e conclusão e melhores em atraso e fila
(por exemplo, C1 com 20%: vazão {{s5vsb2(C1,0.2,'throughput')}}, espera {{s5vsb2(C1,0.2,'mean_waiting_time')}}); com 0%, o C1 teve vazão {{s5vsb2(C1,0.0,'throughput')}} e espera
{{s5vsb2(C1,0.0,'mean_waiting_time')}} (o mesmo trade-off do S2 do experimento principal), e o C2 teve vazão {{s5vsb2(C2,0.0,'throughput')}}.

{{T_s5()}}

**Interpretação (limitada ao que os dados mostram).** Não foi possível identificar um limiar monotônico de tolerância à perda de pacotes:
apenas quatro níveis foram avaliados e o efeito não é monotônico. O mecanismo que explica o desempenho maior com perda moderada
**não foi investigado** neste trabalho (Seção 7).

## 6.9 Custo de comunicação: C1 × C2

*Figuras 16 e 17 (FIG16, FIG17) e Tabela 6 (TABLE06).*

C1 e C2 enviam aproximadamente o mesmo número de mensagens por execução ({{comm(C1,0.0,'mean_messages_sent')}} e {{comm(C2,0.0,'mean_messages_sent')}}), mas a mensagem expandida é maior:

{{T_cost()}}

O C2 envia cerca de {{ratio_bytes(d=2)}} vezes os bytes do C1 (faixa {{ratio_range()}}× entre cenários e níveis de perda). Em desempenho, o C2 não superou o C1 em
geral (Seção 6.6). Não se afirma que o C2 seja superior pelo fato de enviar mais informação. A conclusão é cautelosa: nas condições simuladas,
**o maior custo de comunicação do C2 não produziu benefício geral de tráfego** (o benefício observado em S4 limita-se a atraso e fila, com custo no atraso de partida).

## 6.10 Piloto V2 (N = 5) × Final (N = 10): comparação metodológica

*Figuras 18 e 18B (FIG18, FIG18B).* **Esta seção não combina amostras:** as cinco seeds do Pilot V2 são as cinco primeiras do final. Reexecutar essas cinco
seeds reproduziu exatamente as diferenças do piloto ({{first5_identical()}} comparações), de modo que o que o N = 10 acrescenta são as cinco seeds adicionais.

{{T_pilot()}}

A direção da diferença C1 − B2 persistiu em {{direction_persisted()}} comparações com efeito não nulo no piloto, e nenhuma conclusão central foi revertida; {{n_verdict_changes()}} vereditos
de IC mudaram ({{verdict_changes()}}). No S4, o efeito do C1 sobre a vazão foi estimado em {{pvf(S4,'throughput','pilot_rel_diff',pct_=True)}} no piloto e {{pvf(S4,'throughput','final_rel_diff',pct_=True)}} no final, e a largura do IC95%
da vazão estreitou em S2 (razão final/piloto {{width_ratio(S2)}}), S3 ({{width_ratio(S3)}}) e S4 ({{width_ratio(S4)}}). Retrospectivamente, N = 10 aumentou a precisão e reduziu o risco de
superestimar o efeito (S4), sem inverter conclusões; isto é uma avaliação metodológica, **não uma nova regra de parada**.
