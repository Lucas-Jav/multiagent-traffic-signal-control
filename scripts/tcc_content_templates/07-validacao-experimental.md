# Validação experimental — texto final proposto

> Reúne a validação de software, a identidade e a reprodutibilidade científicas, a validade das
> execuções finais e as verificações de consistência da análise. Os números de testes são os do
> **estado atual do repositório**, validados em {{TESTS.get('executed_on','n/d')}}.

## 5.1 Validação de software

No estado final do repositório, a suíte automatizada contém {{tests('pytest_total')}} testes
(739 que não exigem o simulador e 5 que executam o SUMO) e **{{tests('pytest_passed')}} passaram**
(tempo total de {{tests('pytest_seconds')}} s). A verificação estática de tipos (`mypy`, modo estrito)
resulta em *{{tests('mypy')}}*; a verificação de estilo e correção (`ruff check`) e de formatação
(`ruff format --check`) passa para o código-fonte, a análise e os testes (*{{tests('ruff_check_scientific')}}*;
*{{tests('ruff_format_scientific')}}*). O pipeline de integração contínua do projeto executa ruff, mypy, a
parte dos testes que não exige o SUMO, auditoria de dependências e a construção da imagem de contêiner.
Os testes cobrem, entre outros, os controladores, o gerenciador de segurança de fase, o barramento de
mensagens (atraso, perda, atualidade, ordenação e semente), a geração de rotas, as métricas canônicas,
o pareamento entre controladores, o congelamento científico e o isolamento do pacote de replay.

> Observação de transparência: os *scripts* auxiliares de análise e de visualização criados **após** o
> congelamento (geração de figuras, vídeos e relatórios) ficam fora da árvore científica e ainda não
> foram submetidos ao formatador/lint do projeto; eles não alteram resultados.

## 5.2 Identidade científica e congelamento

A campanha final foi executada a partir de uma especificação científica **congelada**. As identidades
autoritativas são:

| Item | Valor |
|---|---|
| Commit da fonte científica | `176178e36eeafb329a5a1350161be61cf97902b0` |
| Árvore científica (SHA-256, 183 arquivos) | `b713917890e2dc65b7c25dfca80c627a7607146539bd2dadf5613f70451cdeff` |
| Manifesto de congelamento (SHA-256) | `de4af93262e4ab6734ed72a35a5d0d9aeeb0507c6db32c29fc7adc47978164ec` |
| Ambiente | Python 3.12.14; SUMO, TraCI e sumolib 1.27.1; `uv.lock` fixado (SHA-256 `46f15418…ee02c`) |

Elementos do congelamento:

- **Identidade de código e árvore científica.** A árvore científica (código científico, configurações
  finais, plano do B0, rede, cenários e rotas, geradores e dependências travadas) tem um *fingerprint*
  único. O commit posterior de registro do congelamento contém apenas ferramentas de hash, testes e
  evidência, e a verificação exige que a árvore científica seja idêntica à do commit científico.
- **Hashes canônicos portáteis.** Arquivos de texto são verificados por um hash canônico independente de
  fim de linha (`CANONICAL_TEXT_LF_V1`: decodificação UTF-8, remoção de BOM e normalização de CRLF/CR para LF),
  de modo que um *checkout* com LF ou CRLF verifica o mesmo conteúdo científico; o hash bruto é mantido
  como evidência forense. Os metadados de rotas usam um hash semântico que exclui apenas o campo de data
  de geração.
- **Congelamento de experimento portátil.** Cada experimento (principal e S5) tem um congelamento de
  esquema 3, com arquivos identificados por **caminho relativo à raiz do repositório** (POSIX), sem
  caminhos absolutos, de modo que a mesma verificação vale após mover ou clonar o repositório.
- **Verificação de rotas independente de fim de linha.** A validação dos artefatos de rota e rede
  aceita o hash canônico e rejeita conteúdo alterado ou hash desconhecido.
- **Plano estatístico e matriz de execuções congelados**, incluindo seeds, níveis de perda, aquecimento,
  janela de medição, instante do choque, definições de métricas, rota de referência e sementes do
  bootstrap.

Após a campanha, a verificação do congelamento continuou passando e a árvore científica permaneceu
idêntica; nenhum arquivo-fonte ou de configuração rastreado mudou durante a execução. O pacote de
*replay* (vídeos) é isolado da execução científica e **não** faz parte da árvore científica; nenhum
módulo científico o importa (verificado por teste).

## 5.3 Validade das execuções finais

| Verificação | Resultado |
|---|---|
| FINAL_MAIN | 200/200 concluídas, 0 falhas, 0 repetidas; métricas finalizadas em 200/200 |
| FINAL_S5 | 90/90 concluídas, 0 falhas terminais; métricas finalizadas em 90/90 |
| Identidades científicas únicas | 200 (principal) e 90 (S5), sem duplicatas |
| Grupos pareados completos (cenário + seed) | 40 grupos com os 5 controladores |
| Divergências de rede, rotas, população, conversões e medição | 0 em todos os grupos |
| Execução | Sequencial, *headless*, sem GUI e sem alteração de código |

**Repetições de infraestrutura no S5 (transparência).** Doze execuções do S5 (`C2_COOPERATIVE_EXPANDED`,
seeds 10007, 12011 e 16001, nos quatro níveis de perda) falharam na primeira tentativa por uma
limitação de infraestrutura do sistema operacional (comprimento máximo de caminho de 260 caracteres do
Windows ao gravar um arquivo de telemetria). Elas foram refeitas com a mesma configuração e o mesmo
código, por meio da política de retomada (`--resume --retry-failed`), a partir de um diretório de trabalho
de caminho mais curto; as tentativas falhas não geraram resultados e cada identidade científica contribui
**uma única vez** à análise (N permanece 10 por condição). Uma interrupção da sessão de execução durante
essa repetição foi retomada com o mesmo comando. As repetições foram motivadas exclusivamente por falha de
infraestrutura, nunca por desempenho desfavorável.

## 5.4 Verificações de consistência e determinismo

- **Valores recalculados × agregado congelado.** Os valores recalculados na análise final coincidem com
  o agregado canônico produzido pela campanha ({{VALID['combined_metrics_crosscheck']['values_checked']}} valores verificados,
  {{VALID['combined_metrics_crosscheck']['mismatches']}} divergências).
- **Determinismo.** As {{VALID['s5_0pct_vs_main_s2_determinism_check']['compared_runs']}} execuções do S5 sem perda e a referência B2 reproduzem exatamente as execuções
  correspondentes do cenário S2 do experimento principal ({{VALID['s5_0pct_vs_main_s2_determinism_check']['identical_runs']}} idênticas).
- **Reprodução do piloto.** Reexecutar as cinco primeiras seeds no final reproduziu exatamente as diferenças
  pareadas do Pilot V2 ({{first5_identical()}} comparações cenário × métrica idênticas).
- **Telemetria × métricas.** A série temporal da fila usada na figura do S3 foi recomputada a partir da
  telemetria bruta e confere com a métrica congelada de fila média em todas as execuções de S3 (diferença < 10⁻⁶).
- **Legibilidade dos artefatos.** Todas as 290 execuções são legíveis pelo pipeline de análise, incluindo
  as doze com caminhos longos (leitura somente por prefixo de caminho estendido, sem renomear ou mover
  artefatos brutos).

## 5.5 Validade dos cenários e políticas

- **S3.** Todas as 50 execuções de S3 têm choque em 2100 s e horizonte completo. A validade do cenário foi
  estabelecida pelo critério composto (formalizado post-hoc após o Pilot V2; Seção 3.9).
- **S4.** Política `ALLOW_AND_MEASURE`; {{tele(None,'runs')}} de 50 execuções com teleports ({{tele(None,'total')}} no total), todas mantidas.
- **S5.** Validação da comunicação (Seção 6.7): contagens de mensagens consistentes em todas as execuções
  cooperativas (`enviadas = entregues + descartadas`), nenhum descarte com 0% de perda e nenhuma entrega com 100%.

## 5.6 O que a validação não garante

A validação garante que o experimento foi executado como especificado, com identidade verificável e
sem divergências de pareamento. Ela **não** certifica segurança de sinais em uso real, não valida o modelo de
tráfego em campo e não prova a ausência de qualquer erro de software; testes automatizados reduzem, mas não
eliminam, o risco de defeitos. Se um defeito de correção científica fosse descoberto, o procedimento
congelado seria interromper, documentar, corrigir, criar novo congelamento e reexecutar a evidência afetada.
