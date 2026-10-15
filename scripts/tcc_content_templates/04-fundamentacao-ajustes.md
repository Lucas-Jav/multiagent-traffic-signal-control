# Fundamentação teórica — texto de ajuste

> Este arquivo propõe a estrutura e os ajustes da fundamentação. O repositório **não contém um
> corpus bibliográfico**; portanto, nenhuma referência foi inserida. Cada afirmação teórica marcada
> com **[CITAÇÃO NECESSÁRIA]** deve receber fonte do orientador/autor. Não inventar autor, ano, DOI
> ou artigo.

## 2.1 Controle semafórico em redes urbanas

Conceitos a apresentar (cada um com fonte): fase, ciclo, divisão de verde, defasagem (offset),
tempo perdido, intervalos de amarelo e vermelho total (all-red) [CITAÇÃO NECESSÁRIA]. Neste
trabalho, os valores de segurança usados por todos os controladores adaptativos são: verde mínimo
de 10 s, verde máximo de 60 s, amarelo de 3 s e all-red de 2 s.

## 2.2 Controle de tempo fixo e calibração

- Planos de tempo fixo: definição, vantagens (simplicidade, previsibilidade) e limitações
  (insensibilidade a variações de demanda) [CITAÇÃO NECESSÁRIA].
- Métodos clássicos de dimensionamento de ciclo (por exemplo, o método de Webster) [CITAÇÃO NECESSÁRIA].
  **Importante:** o baseline deste trabalho (B0) **não** usa Webster; foi calibrado por busca em grade
  predeclarada (`EMPIRICAL_FIXED_TIME`). A Seção 3 justifica essa escolha. Evitar escrever "B0 de Webster".

## 2.3 Controle adaptativo local e pressão

- Controle adaptativo por medições locais [CITAÇÃO NECESSÁRIA].
- Conceito de pressão (diferença entre carga a montante e a jusante) como base de política de
  controle descentralizada [CITAÇÃO NECESSÁRIA]. O controlador B2 usa uma pressão de movimento local
  (fila a montante menos ocupação a jusante ponderada); não afirmar equivalência com nenhuma
  política da literatura sem verificar a definição na fonte.

## 2.4 Sistemas multiagente, cooperação e comunicação

- Agentes descentralizados com informação local, e cooperação por troca de mensagens entre vizinhos
  [CITAÇÃO NECESSÁRIA].
- Modelo de comunicação deste trabalho: mensagens entre interseções adjacentes, entregues no mesmo
  passo (atraso 0), com perda aleatória configurável e janela de atualidade de 1 passo.
  É um **modelo simplificado** (sem latência de rede real, largura de banda ou falha de nó).

## 2.5 Simulação de tráfego

- Simulação microscópica de tráfego e o simulador SUMO, e a interface TraCI [CITAÇÃO NECESSÁRIA].
- Limitações do SUMO relevantes aqui: comportamento de seguimento de veículos e *teleports*
  (remoção/reinserção de veículos bloqueados), medidos mas não excluídos neste trabalho (Seção 3.9).

## 2.6 Avaliação experimental

- Delineamento pareado e replicação por seed em simulação estocástica [CITAÇÃO NECESSÁRIA].
- Intervalos de confiança por bootstrap percentil [CITAÇÃO NECESSÁRIA]; o trabalho usa 10 000
  reamostragens das diferenças pareadas por seed.
- Viés de sobrevivência em métricas condicionais a viagens concluídas (Seção 3.8).

## 2.7 Métodos preditivos e de aprendizado (contexto e trabalho futuro)

Aprendizado de máquina, previsão de demanda e aprendizado por reforço multiagente podem ser citados
como **contexto** da área e como **trabalho futuro**, sem sugerir que sejam parte do sistema
implementado [CITAÇÃO NECESSÁRIA].

## 2.8 Revisão do texto existente

- Verificar se alguma subseção apresenta ML/RL/previsão como método implementado: reescrever como contexto.
- Verificar se "Webster" aparece associado ao B0: remover (o B0 final é `EMPIRICAL_FIXED_TIME`).
- Verificar menções ao "B0 de 98 s" como baseline final: esse é o baseline **histórico** do Pilot V2.
