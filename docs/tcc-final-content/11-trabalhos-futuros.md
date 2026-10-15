# Trabalhos futuros — texto final proposto

> Itens preditivos e de aprendizado são **trabalho futuro**, não contribuições do sistema atual
> (que é reativo). Onde a literatura é necessária, usar **[CITAÇÃO NECESSÁRIA]**.

## Extensões de rede e de demanda

1. **Rede viária real**, por exemplo construída a partir de dados do OpenStreetMap, com geometria, número de faixas e demandas reais.
2. **Redes maiores** que 3×3, para avaliar escalabilidade da cooperação e do custo de comunicação.
3. **Mais regimes de tráfego**, incluindo outros padrões direcionais, picos sucessivos e incidentes.
4. **Mais rotas e corredores de referência**, além do eixo oeste→leste, para generalizar a análise de tempo de viagem.

## Comunicação

5. **Atraso de comunicação combinado com perda**, e **níveis de perda mais granulares** (incluindo valores entre 0% e 20% e entre 50% e 100%), para investigar se o padrão não monotônico se repete e onde ocorre.
6. **Políticas de comunicação adaptativas**, que decidam quando e o que comunicar, de modo a reduzir o custo em bytes sem perder o benefício observado sob saturação localizada.
7. **Investigação dos mecanismos** do comportamento não monotônico e da diferença C1 × C2 por meio de experimentos de ablação do conteúdo e dos pesos das mensagens.

## Controle

8. **Estimativa/previsão de demanda de curto prazo** para alimentar o ajuste cooperativo [CITAÇÃO NECESSÁRIA].
9. **Aprendizado de máquina e aprendizado por reforço multiagente** como alternativa ao ajuste manual dos controladores [CITAÇÃO NECESSÁRIA]. Essas abordagens **não** fazem parte do sistema implementado.
10. **Otimização/ajuste dos parâmetros** dos controladores adaptativos e cooperativos com protocolo semelhante ao usado para o baseline de tempo fixo, e baselines de tempo fixo por cenário ou por horário.

## Validação

11. **Validação com dados reais e em campo**, e *hardware-in-the-loop*, antes de qualquer conclusão sobre aplicação prática.
12. **Verificação formal de propriedades de segurança** do gerenciador de fases sob falhas de comunicação.
13. **Análise de sensibilidade** às seeds de demanda e à parametrização do simulador (por exemplo, modelo de seguimento de veículos e política de teleports).
