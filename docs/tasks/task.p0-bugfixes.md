# task.p0-bugfixes — Radioactive Round 1

**Data**: 2026-09-15 · **Branch**: master · **Escopo**: bugs P0 identificados na avaliação

## Contexto
Sistema em produção desde 14/09 (cron 9h BRT, no_agent). Avaliação crítica encontrou 3 bugs + 1 risco operacional. Aprovação: Gold ("Faz um radioactive pra fix dos bugs").

## Tasks

- [ ] **B1 — dedupe antes do fetch**: check "já coletado hoje" está DEPOIS da coleta (fetch jogado fora em re-run). Mover para antes de collect_*, logo após o gate DORMANT.
- [ ] **B2 — GH sem datas**: watch de hotel define checkin/checkout mas a URL do Google Hotels não leva datas → métrica mede semana genérica. Investigar params `checkin`/`checkout` no endpoint /travel/search (evidência ao vivo antes de wire); fallback: protobuff ts= (padrão conhecido).
- [ ] **B3 — parser EUR/USD pt-BR**: "€ 1.234,56" parsearia €1.23. Heurística pt-BR: vírgula com 2 dígitos = decimal; vírgula com 3 dígitos = milhar (leak en-US); ambos presentes = último é decimal.
- [ ] **B4 — morte silenciosa**: DOM mudou → FAIL para sempre sem ninguém saber. (a) contador de fails consecutivos; (b) alerta-formatted de HEALTH WARNING no cron mode após 3 fails seguidos; (c) modo `--health` p/ heartbeat semanal (cron novo, Mondays).

## Limpeza P1 incluída (trivial, mesma passada)
- [ ] `main._payload` → dict local retornado
- [ ] `~/.hermes/scripts/travel-tracker.sh` vira wrapper fino (exec no tick canônico do repo)

## Verificação
- unittest do parser (strings reais capturadas: BRL `\xa0`, EUR inteiro, EUR pt-BR decimal, en-US leak)
- `probe.py --once` verde com 4 watches (2 dormant esperados)
- tick silencioso (dedupe) + heartbeat entrega
- diff review (thermo) zero 🔴/🟠
