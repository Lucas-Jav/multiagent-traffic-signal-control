> **Proveniencia (copia versionada).**
> Fonte: `artifacts/experiments/pilot_v2/final-audit.md` (git-ignorado) | Experimento: `pilot_v2` |
> Git SHA do codigo que gerou as runs: `7fffb4efff9ad98498c81cc0d829911ad44baa46` | Git SHA no empacotamento: `0215e852603cb56a2c1ebd2ddd615b94c50b95ad` |
> Data de empacotamento: 2026-10-13 | Tipo: **derived** | Conteudo copiado sem alteracao abaixo.

# Auditoria final de consistência do Pilot V2 (Prompt 52)

Escopo: 15 arquivos de `artifacts/experiments/pilot_v2/` (8 documentos de decisão/resultado, 4 tabelas de suporte, `pilot-assessment.md` e as duas auditorias 46.9), verificados por leitura e busca textual e conferência dos números contra `b2-vs-c1-final-comparison-table.csv` e `b2-vs-c1-seed-sensitivity.csv`. Nenhuma simulação executada.

## 1. Sequência e datas dos arquivos (ordem de criação)

`pilot-assessment.md` (46.8) → tabelas e auditorias S3/S4 (46.9) → `pilot-v2-methodological-decision.md` (47) → `s3-composite-gate-*` (48) → `pilot-v2-release-decision.md` (49) → `b2-vs-c1-*` (50) → `final-scientific-conclusion.md`, `tcc-ready-summary.md`, `presentation-talking-points.md` (51). A comparação B2 vs C1 só existe depois da decisão de liberação formal: nenhum uso antecipado.

## 2. Verificações

| Item procurado | Resultado |
| --- | --- |
| Algum arquivo dizendo que S3 ainda bloqueia | **Encontrado e corrigido**: `pilot-assessment.md` (S3 NO, `SCIENTIFIC_PILOT_VALID = NO`, comparação WITHHELD), `s3-stability-adjudication.md` ("S3 stays NO" com a regra congelada) e `pilot-v2-methodological-decision.md` ("ainda não foi reavaliado"/"pendente") descreviam estados históricos. Todos continuam com o texto original, mas receberam uma nota de status no topo ou no fim apontando o gate composto e a aprovação 5/5. |
| S4 tratado como bloqueante | Não encontrado. Todos os documentos dizem `ALLOW_AND_MEASURE` e "não bloqueia". |
| Afirmação de superioridade geral do C1 | Não encontrada. Toda ocorrência é negação ("não fornece evidência", "não dá para dizer", `C1_GENERAL_SUPERIORITY_CLAIMED = NO`). |
| Texto escondendo o MIXED | Não encontrado. O termo aparece na abertura dos três textos finais e na comparação. |
| Texto ignorando S1 e S3 piores | Não encontrado. As três peças finais e a comparação os citam com números. |
| Texto ignorando o trade-off do S2 | Não encontrado. |
| Omissão de que o ganho agregado vem do S4 | Não encontrada (conclusão final seção 2 e 3, resumo TCC, pontos de apresentação). |
| Omissão da sensibilidade de throughput à seed 5791 | Não encontrada (conclusão final, resumo TCC e pontos de apresentação, comparação seção 6). |
| B2 vs C1 antes da liberação formal | Não. O `pilot-assessment.md` reteve a comparação; a comparação foi feita após a liberação (49). |
| Conclusão mais forte do que os dados | Não. A confiança é MEDIUM (nunca HIGH), os IC são chamados de descritivos e o S4 é dito dependente do regime. |
| Menção a simulações novas que não ocorreram | Não. As 20 simulações B0 da 46.9 (`CALIBRATION_DIAGNOSTIC`) estão declaradas no `s3-stability-adjudication.md` e no `s4-teleport-audit.md`; os Prompts 47 a 51 dizem que não executaram simulações. |
| Números consistentes entre documentos | Conferidos contra os CSV: S4 (espera −20,4%, time loss −23,3%, fila −17,7%, tempo de viagem −22,1%, throughput +12,0%, conclusão 0,265 → 0,306); S1 (espera +44,7%, fila +44,1%); S3 (espera +24,7%, fila +21,9%, time loss pós-choque +11,5%); S2 (espera −12,7%, fila −16,3%, throughput −6,1%, conclusão −0,052); placar 10/13/1; sensibilidade (throughput do S4 +142,6 → +85,5; agregado +11,7 → −7,2); teleports (B2 3, C1 0). Sem divergência. |
| IC dos rótulos FAV/UNFAV | Nas 63 linhas de resumo com rótulo, o IC bootstrap exclui zero em todas (inclui as 23 células classificadas como favoráveis/desfavoráveis das métricas principais). |
| Arquivos do repositório alterados | Nenhum. Ver seção 3. |

## 3. Estado do repositório

- `git status --short`: **vazio**.
- `git diff --stat HEAD`: vazio.
- Últimos commits: `7fffb4e experiment: add pilot v2 campaign config` (config `pilot_v2.yaml`, necessária para rodar o piloto e criada antes da execução), `ffa1307 experiment: calibrate Pilot V2 traffic scenarios`, `238a33c`, `08fb597`. Nenhum commit nem alteração depois da execução do Pilot V2.
- Todas as mudanças feitas desde a execução estão em `artifacts/` (git-ignorado): análise, relatórios e as notas de status desta auditoria.

## 4. Inconsistências encontradas

1. Três documentos históricos (`pilot-assessment.md`, `s3-stability-adjudication.md`, `pilot-v2-methodological-decision.md`) mostravam estado do S3 ou da comparação que foi superado; o `pilot-v2-release-decision.md` indicava como próximo passo algo que já foi executado. **Corrigido** com notas de status (texto original e números preservados, nada reescrito).
2. Nenhuma outra inconsistência: nenhum texto final contradiz o resultado MIXED.

## 5. Observações (não são inconsistências)

- O `analysis/pilot_v2_analysis.py` ainda aplica o critério antigo de 360 s no S3. É o script do Prompt 46.8 e está descrito como tal; a comparação final usou `analysis/b2_vs_c1.py`. Não usar o primeiro para reavaliar o S3.
- As notas de status acima são a única edição feita em documentos existentes. Cada uma nomeia o prompt que superou o estado anterior.
- Os resultados do Pilot V2 são de piloto (5 seeds, IC descritivos); essa limitação está em todos os textos finais.

## 6. Veredito

O pacote final está consistente e pronto para uso no TCC: resultado **MIXED** com confiança **MEDIUM**, benefício específico do C1 no S4, piora em S1 e S3, trade-off no S2, S3 aprovado pelo gate composto (seed 4517 com aviso diagnóstico), S4 como `ALLOW_AND_MEASURE`, sensibilidade de throughput à seed 5791 documentada, nenhuma afirmação de superioridade geral.
