# Conclusão — texto final proposto

## 10.1 Resposta à pergunta de pesquisa

> Em uma rede urbana simulada, a troca local de informações entre controladores semafóricos
> descentralizados melhora o desempenho da rede em comparação com um controlador adaptativo local sem
> cooperação e com controle de tempo fixo, sob diferentes condições de demanda?

Nas condições simuladas, **o efeito da cooperação dependeu do cenário**, e **não foi observada evidência de superioridade
geral** da cooperação. Os resultados não sustentam uma conclusão de que a cooperação entre controladores semafóricos seja
universalmente superior.

**Em relação ao controlador adaptativo local sem cooperação (B2 → C1):**

- no cenário **balanceado (S1)**, o B2 teve melhor desempenho (com o C1: espera {{rel(S1,B2,C1,'mean_waiting_time')}}, fila média {{rel(S1,B2,C1,'mean_network_queue_vehicles')}});
- no **pico direcional (S2)**, observou-se um **trade-off**: menos espera ({{rel(S2,B2,C1,'mean_waiting_time')}}) e fila ({{rel(S2,B2,C1,'mean_network_queue_vehicles')}}), porém menor vazão ({{rel(S2,B2,C1,'throughput')}}) e conclusão ({{pp(S2,B2,C1)}});
- na **mudança de demanda (S3)**, o B2 teve melhor desempenho na rede (com o C1: espera {{rel(S3,B2,C1,'mean_waiting_time')}}, fila média {{rel(S3,B2,C1,'mean_network_queue_vehicles')}});
- sob **saturação localizada (S4)**, o C1 foi vantajoso nas principais métricas de congestionamento (vazão {{rel(S4,B2,C1,'throughput')}}, espera {{rel(S4,B2,C1,'mean_waiting_time')}}, fila média {{rel(S4,B2,C1,'mean_network_queue_vehicles')}}), com piora do atraso de partida ({{rel(S4,B2,C1,'mean_depart_delay_seconds')}}).

**Em relação ao tempo fixo calibrado (B0):** os controladores adaptativos e cooperativos também **não dominaram** o plano fixo em todos os cenários: o B2 teve melhor desempenho que o B0 apenas em
S1, e o B0 foi mais forte em S2, S3 e S4 (e também que o B1 em S2–S4). O resultado deve ser lido como evidência de que a adaptação não supera automaticamente um plano fixo bem calibrado em todos os regimes, e
não como falha do trabalho.

Portanto, o valor da cooperação local depende do **regime de tráfego** e do **critério de desempenho**: o maior benefício apareceu sob saturação localizada, enquanto em outros regimes o controle adaptativo local ou até o
tempo fixo calibrado foram mais competitivos.

## 10.2 Resultados complementares

- **Rota de referência.** O efeito da adaptação (B0 → B2) e o da cooperação (B2 → C1) foram analisados separadamente; os tempos de viagem foram lidos em conjunto com a conclusão. Em S3, a rede e a rota apontaram direções diferentes, o que reflete populações distintas.
- **Comunicação.** O C2 enviou cerca de {{ratio_bytes(d=1)}}× os bytes do C1 sem benefício geral de tráfego. A degradação da comunicação **não foi monotônica**; com 100% de perda, C1 e C2 igualaram o B2 (fallback operacional), e não foi possível identificar um limiar monotônico de tolerância.
- **Metodologia.** N = 10 manteve as direções do piloto ({{direction_persisted()}} comparações) e reduziu o risco de superestimar o efeito no S4 (de {{pvf(S4,'throughput','pilot_rel_diff',pct_=True)}} no piloto para {{pvf(S4,'throughput','final_rel_diff',pct_=True)}} no final).

## 10.3 Contribuições

Um desenho experimental congelado e reprodutível; um baseline de tempo fixo calibrado de forma independente; evidência pareada com 10 seeds de que o efeito da cooperação é dependente do cenário; e uma análise transparente de rota de referência, de degradação de comunicação e de custo, com resultados contrários à superioridade geral reportados sem omissão.

## 10.4 Ressalvas finais

Os resultados valem para a rede sintética 3×3, para a simulação SUMO, para os quatro padrões de demanda estudados e para a parametrização congelada; o S3 usa um critério de validade formalizado *post-hoc*; o S4 é severamente saturado e contém teleports (medidos e mantidos); as métricas de tempo são condicionais à conclusão; e não há validação em campo (Seção 8).
Trabalhos futuros (Seção 9, itens preditivos e de aprendizado inclusos) podem investigar redes reais, mais regimes, atraso e perda combinados e políticas de comunicação adaptativas.
