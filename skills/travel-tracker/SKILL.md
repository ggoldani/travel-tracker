---
name: travel-tracker-project
version: 1.0.0
description: "Use em qualquer tarefa do projeto travel-tracker (repo local)."
---

# travel-tracker — project skill (router)

Projeto: monitor diário de preços de viagem com alerta Telegram só em deal.
Vive em `~/.hermes/travel-tracker/` (repo público: github.com/ggoldani/travel-tracker).

## Orchestrator

1. **Classifique** a tarefa: é sobre adicionar monitor? rodar coleta? diagnosticar? consultar preço?
2. **Roteie** para o workflow correspondente (Command routing abaixo) e carregue SÓ o contrato do cmd.
3. **Feche** com a verificação do Review gate do workflow executado.

## Command routing (router-only)

Invocação: `/travel-tracker <cmd>`

| cmd | workflow | uso |
|---|---|---|
| `add-watch` | [workflows/add-watch/SKILL.md](workflows/add-watch/SKILL.md) | novo destino/datas no monitor |
| `tick` | [workflows/tick/SKILL.md](workflows/tick/SKILL.md) | rodar coleta agora (foreground/forçada) |
| `health` | [workflows/health/SKILL.md](workflows/health/SKILL.md) | diagnóstico, heartbeat, falhas |
| `status` | [workflows/status/SKILL.md](workflows/status/SKILL.md) | preços atuais e histórico |

Se o agente não parseia subcomando, extrair `cmd` da mensagem do usuário e carregar o contrato mapeado.

## Constraints (hard rules)

- Silêncio por padrão no cron: stdout vazio = nada entregue
- Commits: nome de Gold (tech.goldani@gmail.com), sem assinatura de agente
- Nunca filtrar listings de hotel por mediana; filter_junk é só pra min de voo
- Gate GF 315 dias; watches fora da janela ficam DORMANT (não falham)
- `probe.py` é a fonte canônica de comportamento — mudou comportamento, mudou teste

## References

- Governança do projeto: [../../AGENTS.md](../../AGENTS.md) (root doc canônico)
- [routing-matrix](reference/routing-matrix.md) · [Visual](reference/routing-matrix.html)
- [role-contracts](reference/role-contracts.md) · [Visual](reference/role-contracts.html)
- [Interactive HTML View](./README.html)
