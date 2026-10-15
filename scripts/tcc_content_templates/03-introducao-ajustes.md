# Introdução — texto de ajuste

> Texto proposto para substituir/ajustar a Introdução do manuscrito. Onde uma afirmação teórica
> exige fonte e o repositório não fornece referência, aparece **[CITAÇÃO NECESSÁRIA]**: nenhuma
> referência foi inventada. Os resultados finais não são antecipados em detalhe aqui; a
> Introdução apenas enuncia a pergunta, o desenho e a natureza da conclusão.

## 1.1 Contexto e problema

O controle semafórico é um dos principais instrumentos de gestão da circulação em redes urbanas.
Em planos de tempo fixo, ciclo, divisão de verde e defasagens são definidos previamente e
permanecem os mesmos durante o período a que se aplicam [CITAÇÃO NECESSÁRIA]. Controladores
adaptativos ajustam a temporização a partir de medições do tráfego, e abordagens cooperativas
permitem que interseções vizinhas compartilhem informação para coordenar suas decisões
[CITAÇÃO NECESSÁRIA]. Não há, entretanto, uma resposta geral sobre em que condições a adaptação
local e a cooperação entre interseções trazem ganho em relação a um plano fixo bem calibrado:
o benefício pode depender do regime de demanda, do critério de desempenho e do custo de
comunicação envolvido [CITAÇÃO NECESSÁRIA].

Este trabalho trata desse problema em um ambiente de simulação controlado: uma rede sintética 3×3
no simulador SUMO, na qual cada interseção semaforizada é controlada por um agente que decide a
partir do estado corrente observado e, quando cooperativo, de mensagens recebidas das interseções
adjacentes.

## 1.2 Pergunta de pesquisa

> Em uma rede urbana simulada, a troca local de informações entre controladores semafóricos
> descentralizados melhora o desempenho da rede em comparação com um controlador adaptativo local
> sem cooperação e com controle de tempo fixo, sob diferentes condições de demanda?

A resposta não foi definida previamente. Ela é tratada como pergunta de pesquisa, e não como
hipótese confirmada: todas as conclusões decorrem da campanha experimental final congelada e da
análise estatística pareada. Ao final do trabalho, a resposta é **dependente do cenário**
(Seção 10, Conclusão).

## 1.3 Objetivo geral e objetivos específicos

**Objetivo geral.** Avaliar, por simulação, o efeito da cooperação local entre controladores
semafóricos descentralizados sobre o desempenho de uma rede urbana, em comparação com controle
adaptativo local sem cooperação e com controle de tempo fixo calibrado, sob diferentes condições
de demanda.

**Objetivos específicos.**

1. Implementar um sistema reativo, distribuído e descentralizado de controle semafórico, com um agente por interseção e
   restrições de segurança de fase comuns a todos os controladores adaptativos.
2. Definir uma linha de base de tempo fixo calibrada de forma explícita e independente dos controladores comparados.
3. Comparar cinco estratégias (B0, B1, B2, C1, C2) em quatro cenários de demanda (balanceado, pico direcional,
   mudança de demanda e saturação localizada), com delineamento pareado por seed.
4. Avaliar o efeito da degradação da comunicação (perda de 0, 20, 50 e 100%) sobre os controladores cooperativos.
5. Comparar tempos de viagem em uma rota de referência oeste–leste, separando o efeito da adaptação e o da cooperação.
6. Analisar o custo de comunicação das duas variantes cooperativas.

## 1.4 Escopo e delimitação

O sistema implementado é **reativo**: cada decisão usa o estado observado no passo corrente (filas,
ocupação das faixas de saída, taxa de chegada medida e mensagens de vizinhos recebidas dentro de
uma janela de atualidade). Não há previsão de demanda, aprendizado de máquina, aprendizado por
reforço nem predição por rede neural. Os nomes históricos `arrival_trend`, `projected_incoming_weight`
e "demanda projetada" presentes no código referem-se a uma **estimativa do estado corrente**, e
não a uma previsão temporal. Técnicas preditivas e de aprendizado são tratadas apenas como
trabalho futuro (Seção 9).

Os resultados referem-se a uma rede sintética 3×3 em simulação, a quatro padrões de demanda e à
parametrização congelada dos controladores; não há validação em campo.

## 1.5 Contribuições

- Um desenho experimental congelado e reprodutível (identidade de código, árvore científica e
  entradas verificáveis por hash) para comparar tempo fixo, adaptação local e cooperação.
- Uma linha de base de tempo fixo calibrada de forma explícita e independente, que evita inflar
  artificialmente os ganhos dos controladores adaptativos.
- Evidência, com 10 seeds pareadas e intervalos de confiança por bootstrap, de que o efeito da
  cooperação depende do regime de demanda, incluindo resultados que **não** favorecem a cooperação.
- Uma análise de rota de referência e de degradação de comunicação com resultados e limitações
  reportados de forma transparente (inclusive o comportamento não monotônico observado).

## 1.6 Organização do texto

A Seção 2 (Fundamentação) apresenta os conceitos necessários; a Seção 3 (Metodologia) descreve a
rede, os cenários, os controladores, as métricas e a estatística; a Seção 4 (Desenvolvimento)
descreve o sistema e a evolução metodológica; a Seção 5 (Validação experimental) trata de
validação de software e de reprodutibilidade; a Seção 6 (Resultados) apresenta os resultados
finais; a Seção 7 (Discussão) os interpreta; as Seções 8 a 10 tratam de limitações, trabalhos
futuros e conclusão.

## Pontos do texto atual a revisar nesta seção

- Remover qualquer formulação "preditivo", "inteligente", "aprendizado" aplicada ao sistema implementado.
- Substituir qualquer afirmação de superioridade geral da cooperação por "o efeito dependeu do cenário".
- Apresentar a pergunta como pergunta de pesquisa, não como hipótese confirmada.
