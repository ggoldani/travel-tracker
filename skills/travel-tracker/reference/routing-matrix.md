# Routing matrix — travel-tracker

| Intenção do usuário | Cmd | Workflow | Evidência de fechamento |
|---|---|---|---|
| "monitora X", "adiciona destino" | `/travel-tracker add-watch` | workflows/add-watch | obs nova em history/ no próximo tick; entrada em watches.json |
| "roda agora", "coleta hoje" | `/travel-tracker tick` | workflows/tick | stdout do probe (ok/ALERTA/DORMANT/SKIP) |
| "tá quebrado?", "heartbeat", "não chegou alerta" | `/travel-tracker health` | workflows/health | relatório --health + health.json |
| "quanto tá?", "preço atual", "histórico" | `/travel-tracker status` | workflows/status | último obs por watch + spark.png |

## Regras de roteamento

- Task de **código/mudança de comportamento** em probe.py → ciclos radioactive (skill global), não é cmd aqui
- Task que menciona "cron", "entrega", "silêncio" → `health`
- Dúvida entre `status` e `health`: status = preços; health = operação
