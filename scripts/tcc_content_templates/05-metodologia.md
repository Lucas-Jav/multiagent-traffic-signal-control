# Metodologia — texto final proposto

> Descreve o experimento **final congelado**. Identidade científica: fonte
> `{{'176178e36eeafb329a5a1350161be61cf97902b0'}}`, árvore científica `b713917890e2dc65b7c25dfca80c627a7607146539bd2dadf5613f70451cdeff`,
> manifesto de congelamento `de4af93262e4ab6734ed72a35a5d0d9aeeb0507c6db32c29fc7adc47978164ec`.
> Figuras e tabelas indicadas: ver `13-figure-table-placement.md`.

## 3.1 Ambiente de simulação

O experimento foi executado no simulador de tráfego microscópico SUMO 1.27.1, controlado por
Python 3.12 por meio da interface TraCI (TraCI e sumolib 1.27.1). Todas as execuções finais foram
realizadas em modo *headless* (sem interface gráfica), de forma sequencial, com passo de simulação
de 1,0 s. Cada execução tem 300 s de aquecimento (*warm-up*) e 3600 s de janela de medição
(total de 3900 s); as métricas são calculadas somente na janela de medição.

## 3.2 Rede viária

A rede é uma grade urbana sintética 3×3 com nove interseções semaforizadas. Nos textos e figuras
as interseções são denominadas **A1 a A9** (da esquerda para a direita e de cima para baixo; A5 é a
interseção central); os identificadores internos do SUMO (`A0`…`C2`) servem apenas como
identificadores de implementação (por exemplo, A5 corresponde a `B1` no SUMO). Cada aproximação
tem uma faixa; as arestas internas medem 235,6 m e as de borda 92,8 m; a rede tem 12 entradas e 12
saídas de borda. A rede é idêntica para todos os controladores, cenários e seeds (hash de rede único).

**Figura 1 (FIG01)** apresenta a visão geral do experimento (rede, controladores, cenários, seeds e
S5); **Tabela 2 (TABLE02)** resume os cenários.

## 3.3 Cenários de demanda

Todos os cenários compartilham a rede, o aquecimento, a janela de medição e as razões de
conversão por interseção (70% em frente, 15% à esquerda, 15% à direita). Os veículos são
gerados por um percurso determinístico com seed e usam apenas movimentos legais da rede. A demanda
de cada cenário foi calibrada, antes da campanha, com critérios independentes dos controladores
(execuções apenas do baseline de referência, seeds de calibração 101, 1009 e 2029, disjuntas das seeds
finais).

- **S1 — balanceado (`S1_BALANCED`).** As 12 entradas de borda injetam a mesma taxa (150 veículos/h
  cada). Regime estável de referência.
- **S2 — pico direcional (`S2_DIRECTIONAL_PEAK`).** Forte viés oeste→leste: as três entradas
  oeste (320 veículos/h cada) respondem por cerca de 80% da demanda oferecida.
- **S3 — mudança de demanda (`S3_DEMAND_SHIFT`).** Primeira metade idêntica ao S1; em t = 2100 s
  (50% da janela de medição) um choque abrupto de demanda é adicionado nas três entradas oeste,
  roteado pela interseção central A5.
- **S4 — saturação localizada (`S4_LOCAL_SATURATION`).** Demanda de fundo leve mais um fluxo
  roteado por A5 que excede a capacidade nominal das aproximações dessa interseção (carga esperada de
  cerca de 740 veículos/h por aproximação de A5), de modo que o congestionamento se concentra em
  A5 e pode se propagar às vizinhas. Cerca de {{pct_not_completing(S4)}} das viagens oferecidas não concluem em S4
  (conforme o controlador), isto é, a saturação é severa.
- **S5 — experimento de degradação da comunicação.** **Não é um quinto perfil de demanda
  independente.** O S5 usa a demanda do S2 e varia apenas a perda de mensagens entre agentes
  (0%, 20%, 50% e 100%), com atraso de comunicação fixo em zero.

## 3.4 Controladores

Os cinco controladores finais são identificados explicitamente por `B0_FIXED_CALIBRATED`,
`B1_LOCAL_ADAPTIVE`, `B2_LOCAL_PRESSURE`, `C1_COOPERATIVE_COMPACT` e `C2_COOPERATIVE_EXPANDED`
(rótulos acadêmicos: tempo fixo calibrado, adaptativo local, pressão local, cooperativo compacto e
cooperativo expandido). Todos são **reativos**; nenhum prevê demanda nem aprende. **Tabela 1
(TABLE01)** resume os controladores.

### 3.4.1 B0 — tempo fixo calibrado

O baseline de tempo fixo do Pilot V2 era um plano estático de 98 s, herdado dos valores padrão do
gerador de rede, sem calibração por demanda; esse plano é o baseline **histórico** e não é usado
como baseline final. Como um baseline de tempo fixo artificialmente fraco poderia inflar os ganhos
aparentes dos controladores adaptativos e cooperativos, o baseline final foi recalibrado.

O método é **`EMPIRICAL_FIXED_TIME`**: uma busca em grade **predeclarada** sobre ciclo
(68, 84, 100, 116 e 132 s), divisão de verde (igual ou proporcional à demanda) e defasagem
(zero, em escada ou alternada), totalizando 30 candidatos, avaliados apenas por execuções do próprio B0.
**Não se trata do método de Webster**, que exige fluxos de saturação e razões de fluxo crítico não
modelados formalmente aqui e foi concebido para um único regime; como um único plano comum
precisa servir a quatro regimes distintos, usá-lo seria atribuir ao modelo uma base teórica que ele
não sustenta. O critério de seleção (função objetivo normalizada pelo plano histórico e guardas contra
backlog e piora de fila ou perda de tempo) foi congelado antes de simular qualquer candidato. A
calibração usou as seeds 101, 1009 e 2029 e a validação usou as seeds 3011, 4021 e 5003; **nenhum
resultado de B1, B2, C1 ou C2 foi lido ou usado** para escolher o plano.

O plano selecionado é `fx_c84_demand_proportional_alternate`: ciclo de 84 s; amarelo de 3 s;
all-red total de 2 s; divisão de verde `DEMAND_PROPORTIONAL` (verdes entre 14 e 20 s, proporcionais à
demanda média dos quatro cenários, com mínimo de 10 s e máximo de 60 s); defasagem `ALTERNATE`
(0 s e 42 s em padrão de xadrez). Um único plano comum foi calibrado para S1–S4; não há plano por
cenário (calibrar separadamente "para vencer" cada cenário seria otimizar contra o teste). O plano
foi validado em seeds intocadas. A calibração mostrou que o plano é muito mais forte que o histórico
em S1–S3 e ligeiramente pior em S4 (custo do plano comum), e isso **não foi ajustado retroativamente**.
O B0 instala o plano uma única vez e não responde ao tráfego.

### 3.4.2 B1 e B2 — adaptação local

**B1 (adaptativo local).** Heurística de pressão de fila: compara a pressão da fase verde corrente
com a das fases concorrentes após o verde mínimo, usando apenas observações locais.

**B2 (pressão local).** Calcula, para cada movimento, uma pressão local
`1,0 × fila_a_montante − 10,0 × min(ocupação_a_jusante / 1,0; 1)` (taxa de chegada com peso zero),
soma-a por fase e comanda a fase de maior pontuação permitida; mantém a fase quando nenhuma
alternativa melhora a pontuação. Usa apenas observações locais; não há comunicação.

### 3.4.3 C1 e C2 — cooperação

**C1 (cooperativo compacto).** Mesma família de pressão local do B2, acrescida de uma mensagem
**compacta** recebida das interseções adjacentes. O ajuste cooperativo soma, às fases locais
compatíveis, a estimativa de demanda de entrada enviada pelo vizinho (soma das filas de saída
resumidas mais a taxa de chegada medida), ponderada por pesos de conversão e por um peso de
pressão dirigida, e subtrai o congestionamento a jusante. Sem mensagens válidas, a pontuação
coincide com a do B2.

**C2 (cooperativo expandido).** Mesma arquitetura, núcleo local e caminho de segurança, com uma
mensagem **expandida** (filas por movimento de saída, taxa de chegada estimada por movimento relevante,
ocupação por conexão a jusante). O C2 difere do C1 no conteúdo da mensagem.

**Comparação científica primária: B2 vs C1**, porque ambos pertencem à mesma família de pressão
local e o C1 apenas acrescenta a informação compacta dos vizinhos; a diferença pareada isola o efeito
incremental da cooperação. As demais comparações são secundárias: B0 vs B2 (efeito da adaptação por
pressão local sobre o tempo fixo calibrado), B0 vs B1 (adaptação local simples) e C1 vs C2 (efeito
e custo de uma comunicação mais rica).

## 3.5 Segurança de fase

Todas as decisões dos controladores adaptativos (B1, B2, C1 e C2) passam por um `PhaseSafetyManager`
comum, que impõe verde mínimo de 10 s, verde máximo de 60 s, amarelo de 3 s e all-red de 2 s, e a
sequência de transições permitidas; estados brutos de sinal nunca são comandados. A degradação da
comunicação não contorna essas restrições. Essa verificação é uma propriedade do software de simulação
(sustentada por testes automatizados); **não constitui certificação formal de segurança de sinais
em uso real**.

## 3.6 Comunicação entre agentes

Cada agente cooperativo publica, a cada passo, uma mensagem para as interseções adjacentes (topologia
de vizinhança da grade 3×3), o que equivale a {{comm(C1,0.0,'mean_messages_sent')}} mensagens enviadas por execução (24 por
passo). As mensagens do C1 têm, em média, cerca de {{bytes_msg(C1)}} bytes e as do C2 cerca de {{bytes_msg(C2)}} bytes. Com atraso zero, a
mensagem é entregue no mesmo passo; uma mensagem só é usada se tiver no máximo 1 passo de
idade (`max_message_age_steps = 1`). A perda é aplicada por mensagem com probabilidade configurada e
gerador pseudoaleatório derivado deterministicamente da seed da simulação, do atraso e da
probabilidade de perda, de modo que as execuções são reprodutíveis.

## 3.7 Delineamento experimental

**Seeds.** Dez seeds finais: 42, 2027, 3253, 4517, 5791, 6841, 8089, 10007, 12011 e 16001, definidas
antes do piloto e não escolhidas com base em desempenho. As cinco primeiras são as do Pilot V2; as
cinco seguintes são o restante do pool predeclarado.

**Matriz principal (FINAL_MAIN).** 4 cenários × 5 controladores × 10 seeds = **200 execuções**.
**Experimento S5 (FINAL_S5).** Tráfego-base S2; C1 e C2 com 4 níveis de perda × 10 seeds (40 execuções
cada) e **uma** referência B2 por seed (10 execuções, pois o B2 não usa comunicação): **90 execuções**.
**Total: 290 execuções finais.**

**Pareamento.** Cada comparação é pareada por **cenário e seed**: para uma mesma seed, todos os
controladores compartilham rede, população de veículos, rotas, razões de conversão, aquecimento,
janela de medição e definição de cenário; apenas o comportamento do controlador (e, no S5, a
perda de comunicação) difere. Foram auditados {{val('FINAL_MAIN_RUNS_ANALYZED').split('/')[0]}} + {{val('FINAL_S5_RUNS_ANALYZED').split('/')[0]}} execuções
sem divergências de rede, rotas, população, conversões ou medição entre as execuções comparadas.

## 3.8 Métricas

O conjunto de métricas é único e canônico (definições, fórmulas e denominadores congelados).
Reportam-se: vazão (veículos concluídos), razão de partida (partidos/oferecidos), razão de conclusão
(concluídos/oferecidos e concluídos/partidos), atraso de partida médio, tempo de espera médio, perda de
tempo média, tempo de viagem médio, paradas médias, fila média e máxima da rede (soma das filas das faixas
de entrada, por passo), veículos nunca inseridos, veículos inacabados na rede e teleports do SUMO; no S3,
métricas pré e pós-choque (incluindo a área da fila pós-choque); no S5, métricas de comunicação
(mensagens enviadas, entregues, descartadas e obsoletas; bytes enviados e entregues; idade das mensagens).

**Métricas condicionais.** Tempo de espera, perda de tempo, tempo de viagem e paradas são médias
**apenas sobre as viagens que concluem**. Um controlador pode exibir menor tempo médio entre os
concluídos e, ainda assim, concluir menos viagens. Por isso, essas métricas são interpretadas
junto da razão de partida, da razão de conclusão, dos veículos nunca inseridos e dos veículos
inacabados — especialmente em S2, S4 e na rota de referência.

## 3.9 Políticas metodológicas especiais

**Validade do S3 (divulgação obrigatória).** A validade do S3 foi estabelecida por um critério
composto (sem backlog pré-choque, sem veículos nunca inseridos, sem saturação estrutural de faixa e
janela agregada de 1800 s estável, com pelo menos 4 de 5 seeds do piloto válidas). **Esse critério
composto foi formalizado após a inspeção diagnóstica do Pilot V2 e é, portanto, um refinamento
metodológico *post-hoc*.** Nenhum limiar numérico foi alterado; apenas a janela decisiva passou de 360 s
para 1800 s. Não foram criadas métricas de recuperação novas após ver os resultados finais.

**Teleports do SUMO em S4.** A política congelada é `ALLOW_AND_MEASURE`: os teleports são medidos
(`sumo_teleports_total`), reportados em todos os resultados do S4 e **não** invalidam execuções. No S4 final,
{{tele(None,'runs')}} das 50 execuções tiveram teleports, num total de {{tele(None,'total')}} (B0: {{tele(B0,'total')}}; B2: {{tele(B2,'total')}}; B1, C1 e C2: 0);
nenhuma execução foi excluída.

## 3.10 Rota de referência

Por solicitação do orientador, comparou-se o tempo de viagem em uma **rota de referência** oeste→leste
pelo eixo central, com a sequência exata de arestas `left1A1 → A1B1 → B1C1 → C1right1` (entrada oeste,
A4, A5, A6, saída leste). A coorte é formada pelos veículos oferecidos cuja **sequência de arestas
planejada** é exatamente essa e cujo instante de partida programado está na janela de medição; o
identificador de rota do SUMO nunca é usado. Comparam-se B0, B2 e C1, com **interpretação separada**:
**B0 → B2 = efeito da adaptação**; **B2 → C1 = efeito da cooperação**. A razão de conclusão é sempre
apresentada junto do tempo de viagem. A rota foi escolhida por critérios estruturais antes de qualquer
comparação de desempenho (atravessa A5, coincide com o corredor do S2, existe em todos os cenários e
tem amostra suficiente).

## 3.11 Análise estatística

A unidade pareada é cenário + seed (N = 10 pares). Para cada controlador, cenário e métrica
reportam-se N, média, mediana, desvio-padrão, intervalo interquartil, mínimo e máximo. Para cada
comparação reportam-se a diferença média pareada (tratamento − baseline), a diferença mediana
pareada, a diferença relativa (diferença média / média do baseline) e o **intervalo de confiança de
95% por bootstrap percentil pareado**, com 10 000 reamostragens e semente determinística congelada
(20260910; na rota de referência, semente derivada de um rótulo estável). Não foram usados testes de
hipótese nem valores-p, nenhuma seed ou observação atípica foi removida, e nenhum método inferencial
foi acrescentado após a visualização dos resultados.

A leitura por métrica considera uma diferença como favorável a um lado somente se o IC95% exclui zero
nesse sentido. A classificação de cada comparação por cenário usa uma regra fixada antes da análise:
métricas de serviço (vazão, conclusão, razão de partida) × métricas de atraso e fila (espera, perda de
tempo, fila média); "trade-off" quando ambos os grupos têm lados opostos favorecidos; o tempo de viagem
não entra na votação por ser condicional. Não foram feitas correções para múltiplas comparações.

## 3.12 Execução e reprodutibilidade (resumo)

A campanha final foi executada somente após o congelamento da especificação científica; os detalhes
de identidade de código, hashes canônicos e validações estão na Seção 5 (Validação experimental).
