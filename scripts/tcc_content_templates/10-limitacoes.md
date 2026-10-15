# Limitações — texto final proposto

> Limitações do estudo, organizadas por natureza. Todas se aplicam aos resultados finais (N = 10); as ligadas
> ao Pilot V2 estão indicadas.

## 8.1 Limitações do ambiente e da generalização

1. **Rede sintética 3×3.** Nove interseções, uma faixa por aproximação e geometria regular; não representa a diversidade de redes reais.
2. **Simulação em SUMO.** Os resultados dependem do modelo de seguimento de veículos, da inserção e das regras do simulador; não há validação em campo nem *hardware-in-the-loop*.
3. **Distribuições de demanda específicas.** Quatro padrões de demanda calibrados para este trabalho (taxas, conversões 70/15/15, hotspot e choque com parâmetros fixos); outros regimes podem produzir outro resultado.
4. **Resultados válidos para a parametrização congelada.** Os parâmetros dos controladores B1, B2, C1 e C2 foram congelados e não foram otimizados nesta campanha; outro ajuste poderia alterar as conclusões.

## 8.2 Limitações do baseline de tempo fixo

5. **Plano comum único.** Um único plano calibrado para S1–S4 (sem planos por cenário ou por horário); ele foi ligeiramente pior que o plano histórico em S4 na calibração.
6. **Espaço de busca de calibração limitado.** Trinta candidatos (ciclo, divisão e defasagem); não é um ótimo global, e não houve cálculo de Webster, otimização contínua nem coordenação de onda verde.
7. **Seeds de calibração e validação em pequeno número** (3 + 3), com pesos do objetivo definidos por escolha de projeto.

## 8.3 Limitações estatísticas

8. **Dez seeds.** IC95% por bootstrap de 10 diferenças pareadas podem ser anti-conservadores; não há correção para múltiplas métricas e comparações, nem testes de hipótese ou valores-p.
9. **As cinco primeiras seeds coincidem com as do Pilot V2.** Por isso o piloto e o final não são amostras independentes e não foram combinados.

## 8.4 Limitações dos cenários e métricas

10. **S3: refinamento metodológico post-hoc.** O critério composto de validade do S3 foi formalizado após a inspeção do Pilot V2; o gate foi avaliado no baseline de referência, e o regime realizado pelos controladores adaptativos pode diferir. A regra de "4 de 5 seeds" é grosseira para poucas seeds.
11. **S4: saturação severa e teleports.** Cerca de {{pct_not_completing(S4)}} das viagens oferecidas não concluem; teleports do SUMO foram medidos e mantidos ({{tele(None,'total')}}, concentrados no B0), e o efeito deles sobre as métricas não foi isolado.
12. **Métricas de tempo condicionais à conclusão.** Espera, perda de tempo e tempo de viagem cobrem apenas viagens concluídas; em S2, S4 e na rota de referência, as coortes são parciais para alguns controladores.
13. **Uma única rota de referência oficial.** A conclusão de rota refere-se a um corredor (oeste→leste pelo eixo central); outros corredores não foram avaliados.

## 8.5 Limitações da comunicação (S5)

14. **S5 somente sobre o tráfego do S2.** O efeito da degradação em outros regimes não foi avaliado.
15. **Quatro níveis de perda** (0, 20, 50 e 100%) e **atraso de comunicação fixo em zero**; o efeito combinado de atraso e perda não foi estudado, e não é possível declarar limiar de tolerância.
16. **Modelo de comunicação simplificado.** Mensagens entre vizinhos entregues no mesmo passo, perda independente por mensagem, sem largura de banda, latência variável nem falha de nó.
17. **Mecanismos não investigados.** O comportamento não monotônico e a equivalência ao B2 com 100% de perda foram observados, mas suas causas não foram testadas.
18. **Fallback operacional não é certificação de segurança.** A operação sem mensagens entregues foi observada em simulação; a segurança de sinais depende do gerenciador de fases e de testes de software, e não de verificação formal.

## 8.6 Limitações de implementação e de execução

19. **Execução em Windows com limite de caminho.** Doze execuções do S5 exigiram repetição por falha de infraestrutura (comprimento de caminho); os resultados não foram afetados, e cada identidade contribui uma vez.
20. **Escopo do sistema.** Controle reativo; sem previsão de demanda, aprendizado de máquina ou aprendizado por reforço, e sem implantação em hardware ou em via real.
