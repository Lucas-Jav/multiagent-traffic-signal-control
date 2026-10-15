# Resumo

> Versão final proposta do resumo (português). Todos os valores numéricos vêm da análise final
> validada (N = 10 seeds); ver `15-claims-traceability.md`.

**CONTROLE DISTRIBUÍDO E COOPERATIVO DE SEMÁFOROS URBANOS**

## Texto do resumo

O controle de semáforos em redes urbanas condiciona o tempo de viagem, as filas e a capacidade de
escoamento do tráfego, e a escolha entre planos fixos, adaptação local e cooperação entre
interseções permanece uma questão em aberto. Este trabalho investiga se a troca local de
informações entre controladores semafóricos descentralizados melhora o desempenho da rede em
comparação com um controlador adaptativo local sem cooperação e com o controle de tempo fixo,
sob diferentes condições de demanda. Para isso, implementou-se um sistema reativo, distribuído e
descentralizado, com um agente por interseção, avaliado no simulador SUMO 1.27.1 (interface
TraCI, Python 3.12) em uma rede sintética 3×3 com nove interseções. Foram comparadas cinco
estratégias: tempo fixo calibrado (B0), adaptativo local (B1), pressão local (B2), cooperativo
compacto (C1) e cooperativo expandido (C2). A campanha final, congelada antes da execução,
utilizou 200 execuções no experimento principal (quatro cenários de demanda: balanceado,
pico direcional, mudança de demanda e saturação localizada) e 90 execuções em um experimento
de degradação da comunicação (perda de 0, 20, 50 e 100% sobre a demanda do pico direcional),
com 10 seeds por condição, totalizando 290 execuções. A análise baseou-se em
comparações pareadas por seed e em intervalos de confiança de 95% por bootstrap pareado, e
incluiu uma rota de referência oeste–leste. Os resultados indicam que o efeito da cooperação
dependeu do cenário. Em relação ao controlador de pressão local, o cooperativo compacto teve
desempenho inferior nos cenários balanceado e de mudança de demanda, apresentou um
compromisso (trade-off) no pico direcional (espera −15,2% e fila média
−18,3%, porém vazão −5,7%) e foi vantajoso sob saturação localizada (vazão
+8,8%, espera −19,5%, fila média −17,3%). O tempo fixo calibrado superou o
controlador de pressão local nos cenários de pico direcional, mudança de demanda e saturação
localizada. A comunicação expandida enviou cerca de 2,3 vezes mais bytes que a compacta
sem benefício geral de tráfego, e a degradação da comunicação não foi monotônica. Não foi
observada evidência de superioridade geral da cooperação: o maior benefício apareceu sob
saturação localizada, enquanto em outros regimes o controle adaptativo local ou o tempo fixo
calibrado foram mais competitivos. As conclusões valem para a rede sintética, a simulação e a
parametrização congelada utilizadas.

**Palavras-chave:** controle semafórico; controle distribuído; cooperação entre agentes; simulação de tráfego; SUMO; redes urbanas.

## Notas de redação

- O resumo não descreve o sistema como preditivo nem como baseado em aprendizado de máquina.
- "Superior" e "vantajoso" só aparecem qualificados por cenário e métrica.
- Se o limite de palavras da instituição for menor, remover primeiro os valores numéricos
  entre parênteses (mantidos na seção Resultados).
