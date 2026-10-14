# Glossário de Interseções

Dois níveis de nomes coexistem no projeto. Este documento é a fonte única do mapeamento.

- **IDs lógicos do TCC: `A1`-`A9`.** Usados no texto acadêmico, nas figuras e nas configs dos
  cenários (`via_intersection_id: A5`, agentes dos controladores).
- **IDs internos do SUMO: `A0`..`C2`.** Letra = coluna (A = oeste, B = centro, C = leste), número =
  linha (0 = sul, 1 = centro, 2 = norte). Aparecem em `network.net.xml`, nos nomes de arestas
  (`A1B1`, `left1A1`) e em artefatos de telemetria.

O mapeamento é gerado por `scripts/generate_grid.py` (`build_traffic_light_metadata`: ordena as
junções semafóricas por `-y` e depois `x`, isto é, de cima para baixo e da esquerda para a direita) e
gravado em `scenarios/grid_3x3/metadata.json` (`traffic_light_ids`).

## Mapeamento completo

| ID lógico (TCC) | ID SUMO | Posição na grade | Offset do B0 (s) |
|---|---|---|---|
| `A1` | `A2` | noroeste (canto) | 0 |
| `A2` | `B2` | norte (borda) | 10 |
| `A3` | `C2` | nordeste (canto) | 20 |
| `A4` | `A1` | oeste (borda) | 30 |
| `A5` | `B1` | **centro** | 40 |
| `A6` | `C1` | leste (borda) | 50 |
| `A7` | `A0` | sudoeste (canto) | 60 |
| `A8` | `B0` | sul (borda) | 70 |
| `A9` | `C0` | sudeste (canto) | 80 |

Disposição espacial:

```text
 A1(A2)  A2(B2)  A3(C2)      norte
 A4(A1)  A5(B1)  A6(C1)      centro     lógico(SUMO)
 A7(A0)  A8(B0)  A9(C0)      sul
 oeste   centro  leste
```

**`A5` lógico = `B1` no SUMO**: a interseção central, usada no S3 (choque roteado por A5), no S4
(saturação localizada em A5) e na rota de referência (`reference-route.md`).

Os offsets do B0 são o `offset` do `tlLogic` de cada interseção (`traffic_light_offsets_seconds`
em `metadata.json`).

## Arestas de borda (entradas e saídas)

As arestas externas usam o ID SUMO da interseção a que se ligam:

| Sentido | Entradas (para a rede) | Saídas (da rede) |
|---|---|---|
| Oeste | `left0A0`, `left1A1`, `left2A2` | `A0left0`, `A1left1`, `A2left2` |
| Leste | `right0C0`, `right1C1`, `right2C2` | `C0right0`, `C1right1`, `C2right2` |
| Norte | `top0A2`, `top1B2`, `top2C2` | `A2top0`, `B2top1`, `C2top2` |
| Sul | `bottom0A0`, `bottom1B0`, `bottom2C0` | `A0bottom0`, `B0bottom1`, `C0bottom2` |

Arestas internas: `<origem><destino>` em IDs SUMO (por exemplo `A1B1` liga `A1` a `B1`, isto é,
lógico `A4` a `A5`).

## Regras de uso

1. O **texto do TCC usa `A1`-`A9`**. IDs SUMO não devem substituir os nomes lógicos na prosa.
2. Ao citar um artefato, aresta ou arquivo de telemetria que usa IDs SUMO, escreva o ID lógico e o
   ID SUMO na primeira menção, por exemplo "A5 (`B1` no SUMO)".
3. Nomes de interseção genéricos como `J1`-`J9` aparecem apenas em fixtures de teste e não são nomes
   do experimento.
4. Em tabelas e figuras, rotule os eixos com IDs lógicos; registre este mapeamento na legenda ou em
   nota de rodapé.
