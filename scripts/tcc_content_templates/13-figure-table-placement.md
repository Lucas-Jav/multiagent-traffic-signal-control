# Figuras e tabelas — colocação recomendada no manuscrito

> Fonte: pacote oficial `artifacts/tcc-visuals/final/` (22 figuras e 6 tabelas; todas as figuras de resultado usam N = 10 seeds;
> somente FIG18 e FIG18B mostram o Pilot V2, rotuladas). Nenhum dado plotado foi alterado. Para o texto, preferir os
> arquivos vetoriais (PDF/SVG) em `document/`; para slides, `presentation/` (16:9). Rastreabilidade de cada item:
> `figure-manifest.json`.

## Mapa de colocação

{{T_placement()}}

## Ordem mínima exigida

| Figura | Local no manuscrito |
|---|---|
| FIG01 | Metodologia — visão geral |
| FIG03 | Resultados — adaptação |
| FIG04 | Resultados — comparação primária da cooperação |
| FIG06 | Resultados — S2 (trade-off) |
| FIG07 e FIG08 | Resultados — S3 |
| FIG09 e FIG10 | Resultados — S4 |
| FIG11, FIG12 e FIG13 | Resultados — rota de referência |
| FIG14 e FIG15 | Resultados — S5 |
| FIG16 e FIG17 | Resultados/Discussão — custo de comunicação |
| FIG18 | Resultados — comparação metodológica Piloto × Final |
| FIG19 e FIG20 | Discussão e conclusão |

| Tabela | Local |
|---|---|
| TABLE01_CONTROLLERS | Metodologia |
| TABLE02_SCENARIOS | Desenho experimental |
| TABLE03_PRIMARY_B2_VS_C1 (= "resultados primários finais") | Resultados |
| TABLE04_REFERENCE_ROUTE | Subseção da rota de referência |
| TABLE05_S5 | Subseção S5 |
| TABLE06_COMMUNICATION_COST | Discussão |

## Legendas sugeridas (editar conforme a norma da instituição)

{{T_captions()}}

## Recomendações de uso

1. Mantenha o aviso de que a seed 42 dos vídeos é apenas ilustrativa; as figuras de resultado usam as 10 seeds.
2. Em todas as figuras de tempo de espera, perda de tempo e tempo de viagem, mantenha a nota de que são **condicionais a viagens concluídas**.
3. Não recolora as figuras com "verde = bom / vermelho = ruim"; os rótulos de controladores e marcadores são os mesmos em todo o pacote.
4. Não some Piloto + Final em uma mesma figura de resultado (as cinco primeiras seeds coincidem).
5. Se o editor de texto exigir PNG, use `document/*_A4w_300dpi.png`.
