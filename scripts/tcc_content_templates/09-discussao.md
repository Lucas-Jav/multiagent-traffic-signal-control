# Discussão — texto final proposto

> A discussão interpreta resultados **observados**. Explicações causais que o experimento não testou
> são apresentadas somente como **hipóteses explicitamente rotuladas** ("possível explicação, não
> testada"). Linguagem: "os resultados indicam", "nas condições simuladas", "o efeito dependeu do cenário".

## 7.1 Expectativa inicial × observação final

**Expectativa inicial.** A hipótese de trabalho implícita no tema (controle distribuído e cooperativo) era que a troca local
de informação poderia melhorar a coordenação sob congestionamento e sob mudança de demanda, e que a
adaptação local poderia superar um plano fixo. O protocolo, entretanto, **não definiu previamente a
resposta esperada**: a pergunta foi mantida como pergunta de pesquisa, e o Pilot V2 já havia sugerido um
resultado misto, com benefício aparente da cooperação restrito ao regime saturado. A formulação original não é reescrita à luz dos resultados.

**Observação final.** Os benefícios da cooperação foram **condicionais ao regime**: o mais claro apareceu sob saturação
localizada (S4), com custo no atraso de partida; em S1 e S3 o controlador adaptativo local sem cooperação (B2) teve melhor
desempenho; em S2 houve um trade-off. Não houve melhoria universal em S1, S2 ou S3. Quanto à adaptação, o B2 superou o tempo fixo calibrado
apenas em S1; em S2–S4 o tempo fixo calibrado foi mais forte. A expectativa de que a cooperação ajuda sob congestionamento foi,
portanto, **apoiada apenas em S4** (e apenas em parte das dimensões), e a expectativa de que a adaptação local supera o tempo fixo em todos os cenários **não** foi observada.

## 7.2 Respostas às perguntas de discussão

**Quando o tempo fixo calibrado permaneceu competitivo?** Em S2, S3 e S4 o B0 teve desempenho melhor que o B2 (e, em S2–S4, que o B1)
nas métricas de serviço e de atraso/fila (Figura 3; classificações: S2 — {{cls(S2,B0,B2)}}; S3 — {{cls(S3,B0,B2)}}; S4 — {{cls(S4,B0,B2)}}), e a comparação exploratória B0 × C1 apontou o mesmo padrão geral
(exceto pela fila média em S4). Isso é coerente com a calibração explícita do B0: um plano de tempo fixo bem calibrado pode ser
uma referência muito exigente, e os ganhos aparentes de controladores adaptativos sobre o B0 histórico de 98 s **não** se estendem ao B0 final.
Esse resultado não é um fracasso do trabalho; ele indica que a adaptação não supera automaticamente um plano fixo bem calibrado em todos os regimes.

**Quando a adaptação local ajudou?** Em S1 (tráfego balanceado): o B2 reduziu espera ({{rel(S1,B0,B2,'mean_waiting_time')}}) e fila ({{rel(S1,B0,B2,'mean_network_queue_vehicles')}}) em relação ao B0. Na rota de referência, o
B0 → B2 melhorou o tempo de viagem apenas em S1.

**Quando a cooperação ajudou?** Sob saturação localizada (S4): vazão {{rel(S4,B2,C1,'throughput')}}, espera {{rel(S4,B2,C1,'mean_waiting_time')}} e fila média {{rel(S4,B2,C1,'mean_network_queue_vehicles')}}
em relação ao B2, e maior conclusão da rota de referência ({{rrpp(S4,B2,C1)}}). Em S2 e S3, a rota de referência também mostrou redução do tempo de viagem condicional com o C1.

**Quando a cooperação prejudicou?** Em S1 (espera {{rel(S1,B2,C1,'mean_waiting_time')}}, fila {{rel(S1,B2,C1,'mean_network_queue_vehicles')}}) e em S3 na rede inteira (espera {{rel(S3,B2,C1,'mean_waiting_time')}}, fila {{rel(S3,B2,C1,'mean_network_queue_vehicles')}}, área da fila pós-choque
{{rel(S3,B2,C1,'post_shock_queue_auc_vehicle_seconds')}}).

**Quando houve trade-off?** Em S2 (menos espera e fila, menor vazão e conclusão), e em S4 na comparação C1 × C2 (C2: menos espera e fila, maior atraso de partida e menor razão de partida).
A leitura do S2 exige cautela: tempos menores condicionais a menos viagens concluídas não são, isoladamente, uma melhora.

**A comunicação mais rica justificou o custo?** Nas condições simuladas, não de forma geral. O C2 enviou cerca de {{ratio_bytes(d=1)}}× os bytes do C1 e teve desempenho
inferior em S1–S3 (trade-off em S4); com perda de 20–50% as variantes se aproximam, mas o C2 não passa a ser claramente melhor que o C1 em todas as métricas.

**O que se conclui sobre a perda de comunicação?** O efeito não foi monotônico: com 20% e 50% de perda, C1 e C2 tiveram vazão e conclusão maiores que com 0%; com 100%, as métricas
de tráfego de C1 e C2 coincidiram com as do B2 (fallback operacional). Não é possível declarar um limiar de tolerância (quatro níveis, efeito não monotônico),
nem concluir sobre atraso de comunicação (fixo em zero) ou sobre segurança formal.

**Como as conclusões de rota e de rede diferiram?** Em S3, o B2 foi favorecido na rede inteira, enquanto o C1 reduziu o tempo de viagem da rota de referência.
Rede e coorte da rota representam populações e escalas diferentes; ambas as leituras são reportadas, sem tratá-las como contradição automática. Em S2 e S4, os tempos de viagem
da rota devem ser lidos com a conclusão (coortes parciais para o B2 e o C1).

## 7.3 Resultados inesperados ou contraintuitivos

Os itens abaixo são **observações**; as explicações oferecidas são **hipóteses não testadas** e não constituem resultados.

1. **O B0 superou B1 e B2 em S2, S3 e S4.** Observação: Seção 6.3–6.5. *Possível explicação (não testada):* a calibração do B0 repartiu o verde proporcionalmente à demanda e usou
   defasagens alternadas (na calibração, esses foram os dois fatores de maior influência sobre o objetivo), o que pode favorecer o escoamento em regimes com padrão de demanda estável; a parametrização dos controladores adaptativos foi congelada
   e não foi otimizada nesta campanha.
2. **O C2 foi muito pior que o C1 em S1 e S3** (por exemplo, a espera em S1 foi {{rel(S1,C1,C2,'mean_waiting_time')}} e em S3 {{rel(S3,C1,C2,'mean_waiting_time')}} em relação ao C1). *Possível explicação (não testada):* a
   mensagem expandida pode introduzir sinais adicionais que o ajuste cooperativo pondera de forma inadequada nesses regimes.
3. **A degradação da comunicação foi não monotônica** (perdas de 20% e 50% melhoraram vazão e conclusão em relação a 0%). *Possível explicação (não testada):* a informação plena dos vizinhos
   pode causar acoplamento excessivo entre agentes no S2, e a perda parcial reduzir esse acoplamento. Não houve experimento para testar essa hipótese.
4. **Com 100% de perda, C1 e C2 reproduziram exatamente o B2.** Isso é consistente com o recuo local do controlador cooperativo quando nenhuma mensagem é válida (documentado: sem mensagens
   válidas, a pontuação coincide com a do B2); foi observado empiricamente em todas as execuções, e não é uma prova formal.
5. **Direções opostas entre rede e rota em S3** (B2 favorecido na rede; C1 reduz o tempo da rota). Explicação estrutural: populações diferentes (Seção 6.7). Que o choque entre pela borda oeste e passe por A5 pode tornar a coorte mais sensível é
   uma **hipótese não testada**.
6. **Teleports do S4 concentrados no B0** ({{tele(B0,'total')}} de {{tele(None,'total')}}), o controlador de maior vazão em S4. *Possível explicação (não testada):* maior número de veículos movidos para a região saturada. Os teleports foram medidos e mantidos (política `ALLOW_AND_MEASURE`).

## 7.4 Implicações e cuidados de interpretação

- O valor da cooperação local depende do regime de tráfego e do critério de desempenho; recomendações gerais de adoção não são sustentadas por estes resultados.
- Comparações com o tempo fixo exigem um baseline calibrado de forma explícita; usar um plano fraco poderia produzir conclusões opostas em S1–S3.
- Métricas condicionais exigem leitura conjunta com conclusão e partida; em S2 e S4 isso muda a interpretação.
- N = 10 mostrou-se útil em precisão e para evitar superestimar o efeito no S4; direções e vereditos centrais do piloto persistiram.
- Os resultados valem para a rede sintética 3×3, a simulação SUMO e a parametrização congelada (Seção 8).
