# Modelo de Tráfego

Este documento define o modelo físico de tráfego usado por `scenarios/grid_3x3`
antes de adicionar novos controladores científicos.

## Escopo

O cenário 3x3 contém nove interseções controladas, expostas aos controladores
como `A1` até `A9`. A rede SUMO mantém seus IDs de junção gerados
(`A0`, `B1`, `C2`, etc.); `scenarios/grid_3x3/metadata.json` mapeia os IDs de
interseção dos controladores para os IDs de semáforo (traffic-light) do SUMO.

A estilização visual de veículos, cores, legibilidade das vias e configurações de depuração da GUI é
mantida nos arquivos de rotas/visualização e na configuração da simulação. Ela não faz parte da
política de controle.

## Movimentos

Cada interseção modela movimentos por direção de aproximação e direção de saída:

- `north_to_south`
- `north_to_east`
- `north_to_west`
- `south_to_north`
- `south_to_east`
- `south_to_west`
- `east_to_west`
- `east_to_north`
- `east_to_south`
- `west_to_east`
- `west_to_north`
- `west_to_south`

Retornos em U (U-turns) são excluídos. Na topologia 3x3 atual, todas as nove interseções possuem
os doze movimentos sem retorno em U listados acima.

O código representa esses movimentos como valores `MovementId` usando:

```text
<intersection_id>:<from_direction>_to_<to_direction>
```

Exemplo:

```text
A5:north_to_south
A5:west_to_north
```

O modelo de movimentos é construído a partir de:

- lanes de entrada ordenadas em `scenario.yaml`: north, east, south, west;
- lanes de saída ordenadas em `scenario.yaml`: north, east, south, west;
- elementos `<connection>` do SUMO e seu `linkIndex`;
- informações de conflito `<request>` das junções do SUMO.

## Conflitos

Os conflitos são representados explicitamente por interseção como uma matriz de
conflitos entre movimentos. A matriz é derivada dos dados de request das junções do SUMO e anexada ao
`IntersectionTrafficModel`.

Um par de movimentos é considerado conflitante quando o SUMO marca os link indexes
correspondentes como foes ou conflitos de resposta. Movimentos da mesma lane de
entrada são tratados como compatíveis no nível do controle semafórico, pois apenas um fluxo de
veículos pode escoar dessa lane por vez.

Os controladores não devem codificar regras de conflito com instruções `if` locais. Eles usam
intents de controlador, e a segurança de fase valida os movimentos contra a matriz.

## Plano de Fases

O cenário usa `--tls.layout incoming` do SUMO. Cada fase verde atualmente abre
uma aproximação de entrada e todos os movimentos válidos sem retorno em U dessa aproximação:

```text
PHASE_NORTH_APPROACH: GGGrrrrrrrrr
PHASE_EAST_APPROACH:  rrrGGGrrrrrr
PHASE_SOUTH_APPROACH: rrrrrrGGGrrr
PHASE_WEST_APPROACH:  rrrrrrrrrGGG
```

Isso é conservador, mas válido. O modelo não exige apenas uma aproximação por
fase para sempre. Planos de fase futuros podem compartilhar movimentos compatíveis de várias
aproximações se a matriz explícita de conflitos permitir.

Cada fase verde possui uma lista de movimentos derivada. Uma fase é segura somente quando nenhum par
de movimentos listados entra em conflito.

## Amarelo e Vermelho Total (All-Red)

Toda transição entre fases verdes deve seguir:

```text
green -> yellow -> all-red clearance -> next green
```

Temporização atual de desenvolvimento:

- `min_green_seconds`: `10.0`
- `yellow_seconds`: `3.0`
- `all_red_seconds`: `2.0`
- `max_green_seconds`: `60.0`

Os controladores não podem pular as fases de amarelo ou vermelho total (all-red). Eles só podem retornar intents
como `KEEP_PHASE`, `REQUEST_NEXT_PHASE` ou um alvo de fase permitido. O
`PhaseSafetyManager` converte esses intents em índices de fase SUMO legais.

## Linha de Retenção e Liberação (Clearance)

As arestas de entrada têm `stopOffset` do SUMO para veículos de passeio, atualmente `7.0m`.
Isso desloca a posição visual de parada para montante, de modo que os veículos em fila não pareçam
parados sobre a linha do semáforo.

Veículos que já entraram legalmente em uma junção podem terminar a travessia. O requisito de segurança
é não fazer teleport nem reposicionar veículos. O requisito é:

- não admitir novos veículos após o fechamento do seu movimento;
- manter a liberação de amarelo e vermelho total (all-red) antes que um verde conflitante abra;
- manter verificações de liberação de lanes internas para controladores adaptativos.

Se um veículo aparecer dentro da junção, inspecione:

- se ele entrou durante seu intervalo legal de verde/amarelo;
- o formato da lane de entrada e o stop offset;
- a ocupação das lanes internas;
- a temporização de amarelo e vermelho total (all-red);
- se a próxima fase abriu enquanto uma lane interna ainda estava bloqueada.

## Rotas de Conversão

A configuração de rotas contém demanda de movimentos em frente (straight), conversão à esquerda (left) e conversão à direita (right).
As razões de conversão são configuradas no YAML do cenário e conduzem a geração de rotas
(`src/traffic_agents/simulation/route_walk.py`): em cada junção semaforizada o veículo escolhe
straight/left/right com essas probabilidades, usando apenas movimentos legais da rede:

```yaml
turning_ratios:
  straight: 0.70
  left: 0.15
  right: 0.15
```

Esses são os valores aprovados do protocolo V1. A geração de rotas permanece determinística por seed; as
contagens e proporções de movimentos realizadas são reportadas nos metadados das rotas.

## Fase Segura

Uma fase segura é uma fase verde que:

- lista os movimentos que ela permite;
- não contém nenhum par de movimentos conflitantes;
- é alcançável pela sequência configurada de amarelo e vermelho total (all-red) do SUMO;
- respeita as restrições de verde mínimo e máximo;
- nunca exige que um controlador emita uma string bruta de estado de sinal.
