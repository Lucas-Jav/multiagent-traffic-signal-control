# Outline final do TCC — conteúdo acadêmico preparado (Prompt 65)

**Título de trabalho:** CONTROLE DISTRIBUÍDO E COOPERATIVO DE SEMÁFOROS URBANOS

> Conteúdo preparado **somente** a partir da metodologia congelada, da análise final N = 10, das figuras/tabelas oficiais e
> do histórico experimental documentado no repositório. Nada foi simulado, nenhum resultado foi alterado e **nenhuma referência
> bibliográfica foi inventada** (marcadores **[CITAÇÃO NECESSÁRIA]**). O manuscrito submetido **não foi sobrescrito**.

Identidade científica: fonte `176178e36eeafb329a5a1350161be61cf97902b0`; árvore `b713917890e2dc65b7c25dfca80c627a7607146539bd2dadf5613f70451cdeff`;
manifesto `de4af93262e4ab6734ed72a35a5d0d9aeeb0507c6db32c29fc7adc47978164ec`. Evidência final: FINAL_MAIN 200/200 + FINAL_S5 90/90 = 290/290; 10 seeds.

## Estrutura do TCC e arquivos

| Seção | Conteúdo | Arquivo desta pasta | Nesta pasta |
|---|---|---|---|
| Resumo | Resumo (PT) | `01-resumo.md` | texto completo |
| Abstract | Resumo (EN), adaptação fiel | `02-abstract.md` | texto completo |
| 1 Introdução | Contexto, pergunta, objetivos, escopo, contribuições | `03-introducao-ajustes.md` | ajustes/texto proposto |
| 2 Fundamentação | Estrutura e ajustes (sem referências inventadas) | `04-fundamentacao-ajustes.md` | ajustes e marcadores de citação |
| 3 Metodologia | Ambiente, rede, cenários, controladores (B0 calibrado), segurança, comunicação, delineamento, métricas, políticas S3/S4, rota, estatística | `05-metodologia.md` | texto completo |
| 4 Desenvolvimento | Arquitetura do sistema e evolução metodológica | `06-desenvolvimento.md` | texto completo |
| 5 Validação experimental | Testes, congelamento, reprodutibilidade, validade das execuções | `07-validacao-experimental.md` | texto completo |
| 6 Resultados | S1–S4, síntese, rota de referência, S5, custo de comunicação, Piloto × Final | `08-resultados.md` | texto completo + tabelas geradas |
| 7 Discussão | Expectativa × observação, perguntas, resultados inesperados | `09-discussao.md` | texto completo |
| 8 Limitações | Limitações | `10-limitacoes.md` | texto completo |
| 9 Trabalhos futuros | Extensões | `11-trabalhos-futuros.md` | texto completo |
| 10 Conclusão | Resposta direta à pergunta de pesquisa | `12-conclusao.md` | texto completo |
| Apêndices de apoio | Colocação de figuras/tabelas; checklist do orientador; rastreabilidade das afirmações | `13-…`, `14-…`, `15-claims-traceability.md` | gerados |

## Estado do manuscrito existente

**Nenhum arquivo de manuscrito (DOCX, LaTeX, Markdown de TCC ou BibTeX) foi encontrado no repositório**; o texto do TCC vive fora dele
(como a própria nota `docs/methodology/tcc-scope-alignment.md` já registra). Portanto não é possível apontar linhas do manuscrito.
Use a lista abaixo para revisá-lo.

**Pode permanecer (se já estiver coerente com o congelamento):** descrição da rede 3×3, do SUMO/TraCI, da arquitetura geral do sistema, dos conceitos de segurança de fase e dos controladores B1/B2/C1/C2.

**Exige revisão substancial:**

1. **Resumo, introdução, resultados, discussão e conclusão** — substituir pelas versões desta pasta (resultado final N = 10, conclusão "dependente do cenário").
2. **Qualquer resultado baseado no Pilot V2 (N = 5)** apresentado como final (por exemplo, o efeito do C1 sobre a vazão em S4 estimado em +12,0% no piloto, apresentado como resultado final; o valor final é +8,8%). O piloto só pode aparecer como evidência metodológica/histórica.
3. **Referências ao B0 antigo (ciclo de 98 s) como baseline final.** O baseline final é `B0_FIXED_CALIBRATED` (ciclo de 84 s, método `EMPIRICAL_FIXED_TIME`, **não Webster**).
4. **Vocabulário obsoleto/não sustentado:** "preditivo", "predição", "inteligência artificial", "aprendizado de máquina/por reforço" aplicados ao sistema implementado; "demanda projetada" (usar "demanda de entrada estimada a partir do estado atual"); "S5 não executado" ou "S5 com atraso {0,1,3,5} × perda {0; 5; 10; 25%}" (S5 final: perda 0/20/50/100%, atraso 0, tráfego S2, 10 seeds); "5 seeds" como configuração final; "N = 15" (piloto + final).
5. **Afirmações não sustentadas:** superioridade geral da cooperação; "o C1 reduz de forma geral tempo de viagem, paradas e filas"; limiar de tolerância à perda de pacotes; segurança de sinais comprovada formalmente.
6. **Nomes de interseção** fora de A1–A9 (IDs SUMO só na primeira menção).

**Documentos do repositório que estão desatualizados em relação à campanha final** (não foram alterados aqui; úteis para evitar copiar texto obsoleto):
`docs/methodology/tcc-scope-alignment.md` (resultados descritos como "apenas Pilot V2" e "S5 não foi executado"), `docs/experiments.md`
("S5 ainda não foi executado"; 5 seeds, 45 execuções), `docs/methodology/campaign-matrix.md` (pré-congelamento), `docs/testes-validacao-experimental.md`
(seção "Status atual": contagem de testes de 353 e decisão de seeds "pendente"), `docs/advisor-feedback-checklist.md` (itens 7 e 8 anteriores à campanha) e `docs/v1-readiness-report.md` (histórico).

## Marcadores [CITAÇÃO NECESSÁRIA]

Há **15 lacunas de citação** que exigem bibliografia (marcador **[CITAÇÃO NECESSÁRIA]** no corpo do texto; distribuídas por: `03-introducao-ajustes`: 3, `04-fundamentacao-ajustes`: 10, `11-trabalhos-futuros`: 2). Cada uma corresponde a uma afirmação teórica ou de contexto que depende de fonte do(a)
autor(a) ou do orientador. No total há 18 ocorrências textuais do marcador nestes arquivos (`03-introducao-ajustes`: 4, `04-fundamentacao-ajustes`: 11, `11-trabalhos-futuros`: 3), incluindo 3 em notas de cabeçalho/instrução (linhas iniciadas por `>`) que não são lacunas de citação. Nenhum DOI, autor, ano ou artigo foi inventado.

## Convenções de leitura dos números

- Δ = tratamento − baseline, pareado por cenário + seed (N = 10); diferença relativa = diferença média / média do baseline; IC95% por bootstrap percentil pareado (10 000 reamostragens, semente congelada).
- Vazão e conclusão: valores maiores são favoráveis; espera, perda de tempo, fila, atraso de partida: valores menores são favoráveis; um lado só é "favorecido" quando o IC95% exclui zero.
- Métricas de tempo são condicionais a viagens concluídas; ler com conclusão, partida, não inseridos e inacabados.
- Todos os valores numéricos desta pasta são gerados programaticamente a partir de `artifacts/final-analysis/`; ver `15-claims-traceability.md`.
