# task.p0-bugfixes — Radioactive Round 1

**Data**: 2026-09-15 · **Branch**: master · **Escopo**: bugs P0 identificados na avaliação

## Contexto
Sistema em produção desde 14/09 (cron 9h BRT, no_agent). Avaliação crítica encontrou 3 bugs + 1 risco operacional. Aprovação: Gold ("Faz um radioactive pra fix dos bugs").

## Tasks

- [x] **B1 — dedupe antes do fetch**: check "já coletado hoje" está DEPOIS da coleta (fetch jogado fora em re-run). Mover para antes de collect_*, logo após o gate DORMANT.
- [x] **B2 — GH sem datas**: watch de hotel define checkin/checkout mas a URL do Google Hotels não leva datas → métrica mede semana genérica. Investigar params `checkin`/`checkout` no endpoint /travel/search (evidência ao vivo antes de wire); fallback: protobuff ts= (padrão conhecido). **RESOLVIDO**: URL plana e ts= protobuf ignorados/token de sessão; fluxo de UI (Alterar datas → aria-label pt-BR → Concluído) funciona; obs registra `dates_flow_ok` (4 STEPS==OK).
- [x] **B3 — parser EUR/USD pt-BR**: "€ 1.234,56" parsearia €1.23. Heurística pt-BR: vírgula com 2 dígitos = decimal; vírgula com 3 dígitos = milhar (leak en-US); ambos presentes = último é decimal. **Bônus**: dot-only ("8.561") = milhar sempre em página forçada pt-BR.
- [x] **B4 — morte silenciosa**: DOM mudou → FAIL para sempre sem ninguém saber. (a) contador de fails consecutivos; (b) alerta-formatted de HEALTH WARNING no cron mode após 3 fails seguidos; (c) modo `--health` p/ heartbeat semanal (cron novo, Mondays).

## Limpeza P1 incluída (trivial, mesma passada)
- [x] `main._payload` → dict local `payload` retornado
- [x] `~/.hermes/scripts/travel-tracker.sh` vira wrapper fino (exec no tick canônico do repo)

## Round 2 — features (task.features)

- [x] **F2 — preco-alvo absoluto**: campo `target` opcional por watch, dispara alerta mesmo em seeding.
- [x] **F3 — watch GRU→TYO**: semeado, R$ 7.124 vs GIG R$ 8.561 (-16,8% na 1ª leitura). Flag `--only` pra coleta pontual sem duplicar obs.
- [x] **F4 — sparkline**: PNG matplotlib por watch ativo no heartbeat semanal (heartbeat virou agent-job pra poder anexar MEDIA:).
- [x] **F1 — melhor dia da janela**: SPIKE NEGATIVO. GF não expõe preços por dia de forma extraível: SVG do gráfico só tem eixos (hover via CDP não produz tooltip com dados), strip de datas imune a click sintético e CDP Input, grade mensal "in July 2027" fora da janela de 315d e sem preços renderizados nem na aba Calendário. **Deferido** — reavaliar com browser stealth ou fonte alternativa (Kiwi tequila API se reabrir).
- [ ] **F5 — cross-check cripto no alerta**: deferido por design (exige 2+ semanas de estabilidade do tick antes de adicionar flakiness).

## Verificação
- unittest do parser (strings reais capturadas: BRL `\xa0`, EUR inteiro, EUR pt-BR decimal, en-US leak)
- `probe.py --once` verde com 4 watches (2 dormant esperados)
- tick silencioso (dedupe) + heartbeat entrega
- diff review (thermo) zero 🔴/🟠
