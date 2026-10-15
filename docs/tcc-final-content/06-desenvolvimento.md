# Desenvolvimento — texto final proposto

> Descreve o sistema implementado e a **evolução metodológica** do experimento (não é um diário de
> desenvolvimento de software). Nomes de pacotes e módulos refletem o repositório
> (`src/traffic_agents/`).

## 4.1 Arquitetura do sistema

O sistema é um pacote Python (`traffic_agents`) organizado em camadas com responsabilidades
separadas:

- **Simulação (`simulation/`).** Executa o SUMO via TraCI, passo a passo (1 s), aplica os comandos dos
  controladores e coleta observações. É o único componente que interage com o simulador.
- **Agentes (`agents/`).** Um agente por interseção semaforizada (A1–A9). Cada agente observa o estado
  local (filas, ocupação, taxa de chegada medida), decide uma intenção (manter a fase ou solicitar a
  próxima fase verde) e, quando cooperativo, publica e recebe mensagens.
- **Controladores (`controllers/`).** Implementam B0 (plano de tempo fixo instalado uma vez), B1
  (adaptativo local), B2 (pressão local), C1 e C2 (cooperativos). Os adaptativos e cooperativos
  compartilham o mesmo núcleo de segurança de fase.
- **Segurança de fase (`controllers/phase_safety.py` e `traffic_light_actuator.py`).** Valida a intenção
  contra verde mínimo/máximo, amarelo e all-red e só então aplica o comando via TraCI; o controlador
  nunca comanda estados brutos de sinal.
- **Comunicação (`communication/`).** Barramento determinístico de mensagens por passo, com mensagens
  compactas e expandidas, atraso, perda aleatória reprodutível, controle de atualidade e contabilização
  (enviadas, entregues, descartadas, obsoletas, bytes).
- **Métricas (`metrics/`).** Telemetria de faixas e interseções por passo, métricas canônicas e
  métricas do SUMO por viagem (`tripinfo`); o pipeline é único e congelado.
- **Experimentos (`experiments/`).** Execução de campanhas a partir de configurações versionadas,
  status por execução, agregação, congelamento científico (hashes canônicos) e verificações de
  invariantes entre controladores.
- **Replay (`replay/`).** Ferramenta de apresentação (vídeos sincronizados) **isolada da execução
  científica**: não é importada por nenhum módulo científico e não faz parte da árvore científica
  congelada; serve apenas à ilustração.

A mesma implementação científica executa todos os controladores; diferenças entre controladores
ficam restritas ao módulo de decisão (e à comunicação, quando aplicável).

## 4.2 Decisões de projeto relevantes para a validade científica

1. **Equidade por construção.** A mesma rede, rotas e demanda (por seed) são usadas por todos os
   controladores; o hash do cenário neutro ao controlador é verificado antes de cada análise pareada.
2. **Reatividade explícita.** Todos os controladores decidem com o estado corrente; nomes históricos
   ("projetada") referem-se a estimativas do estado atual.
3. **Segurança comum.** Os mesmos limites de verde, amarelo e all-red valem para todos os adaptativos.
4. **Baseline de tempo fixo independente.** O B0 final é calibrado com execuções apenas do próprio B0.
5. **Cenários calibrados sem controladores.** Os níveis de demanda foram escolhidos com critérios
   independentes dos controladores comparados.
6. **Congelamento antes da campanha.** Código, entradas, matriz de execuções e plano estatístico foram
   congelados antes de qualquer execução final (Seção 5).

## 4.3 Evolução metodológica

A tabela resume os marcos que levaram ao desenho final. O foco é a maturação do método; detalhes de
engenharia constam do repositório.

| Etapa | O que foi feito | Por que importa para o resultado |
|---|---|---|
| Protótipo e verificação de ponta a ponta (`mvp1`, mini-piloto) | Pipeline completo em poucas execuções, com invariantes idênticas entre B0/B1/B2/C1/C2 | Verificou infraestrutura e pareamento; **não** é evidência científica |
| **Pilot V1** (100 execuções) | Primeira campanha completa de verificação | Válido apenas para infraestrutura: expôs S1–S3 superssaturados (backlog de inserção), fila duplicada na telemetria, `KEEP_PHASE` sem efeito, conversões que não moldavam as rotas, choque do S3 não medido e métricas canônicas ausentes |
| Correções metodológicas e calibração de cenários | Telemetria unificada, filas por faixa única, retenção de verde efetiva, conversões operacionais, choque real no S3, hotspot em A5 no S4, contabilidade oferecidos/partidos/concluídos, calibração de demanda com critérios independentes de controlador | Regime de cada cenário passou a ser o pretendido; os resultados do V1 foram declarados superados (erratum) |
| **Pilot V2** (N = 5; 100 execuções) | Campanha completa com a metodologia corrigida; 100/100 concluídas, 0 falhas | Cenários válidos; resultado **misto** (benefício da cooperação restrito ao S4); serviu para estimar a necessidade de seeds |
| Refinamento do gate do S3 e política do S4 | Gate composto de validade (post-hoc, divulgado) e política `ALLOW_AND_MEASURE` para teleports | Evita reprovar tráfego estável por flutuação; teleports medidos e não excluídos |
| **Calibração do B0** | Busca em grade predeclarada (30 candidatos), seeds exclusivas de calibração e validação, sem usar resultados de outros controladores | Baseline de tempo fixo defensável (plano `fx_c84_demand_proportional_alternate`) |
| Experimento da rota de referência (pré-final, N = 5) | Comparação B0 calibrado × B2 × C1 na rota exata solicitada pelo orientador | Metodologia validada; a evidência final é refeita com N = 10 |
| **Decisão do número de seeds** | Fixou-se N = 10, usando apenas seeds já reservadas antes do piloto | O piloto (N = 5) terminou com resultado misto e IC largos; N = 10 dobra os pares por cenário sem inflar o custo (290 execuções) |
| Congelamento definitivo | Hashes canônicos de código/entradas, árvore científica, caminhos relativos portáteis, plano estatístico e matriz de execuções | Reprodutibilidade e identidade científica verificáveis |
| **Campanha final** (FINAL_MAIN, 200 execuções) e **S5** (FINAL_S5, 90 execuções) | Execução sequencial *headless*; todas as 290 execuções válidas | Evidência final |
| Análise final | Comparações pareadas, IC por bootstrap, rota de referência, S5, custo de comunicação, comparação Piloto × Final | Resposta à pergunta de pesquisa |

O Pilot V2 foi usado para validar os cenários e estimar a necessidade de seeds; **seus resultados
não entram na campanha final e não são combinados com ela** (as cinco seeds do piloto são as cinco
primeiras do final, portanto as amostras não são independentes).

## 4.4 Ajustes ao texto existente

- Se o manuscrito descreve etapas de desenvolvimento em ordem cronológica de *commits*, condensar na
  tabela acima.
- Referências ao "B0 de 98 s" como baseline devem ser rotuladas como histórico (Pilot V2).
- Números do Pilot V2 só podem aparecer como evidência metodológica/histórica (Seção 6.9).
