# travel-tracker

Monitor diário de preços de passagens e hospedagens com alerta no Telegram só quando vale a pena.

Roda num VPS com [Hermes Agent](https://hermes-agent.nousresearch.com): cron diário → coleta via Chrome headless → histórico em JSONL → alerta `< mediana30 −15%` com cooldown.

## Como funciona

```
cron diário (9h BRT, no_agent)
  └─ tick.sh
       └─ probe.py
            ├─ Google Flights  → min-tarifa BRL/pessoa (ida+volta)
            ├─ Google Hotels   → mediana dos listings /noite (convertida p/ BRL)
            ├─ history/<slug>.jsonl  (1 obs/dia)
            └─ stdout vazio = silêncio | deal = alerta Telegram formatado
```

- **Fontes**: Google Flights (voo, typical price nativo) e Google Hotels (hospedagem; agrega Booking/Airbnb/Agoda)
- **Baseline**: mediana das últimas 30 observações próprias; alerta só com ≥14 dias de histórico
- **FX**: EUR/USD → BRL diário via open.er-api.com (fallback awesomeapi), cache em `fx.json`
- **Gate de antecedência**: Google Flights recusa datas > ~315 dias; watch fica `DORMANT` e acorda sozinho na janela

## Estrutura

```
watches.json            # o que monitorar (destino, datas, tipo)
probe.py                # coletor + parser + decisão de alerta
tick.sh                 # entrypoint do cron (stdout vazio = nada entregue)
history/<slug>.jsonl    # séries históricas
alerts.json             # cooldown por watch (3 dias)
```

## Adicionar um destino

```json
{
  "slug": "gig-lis-2026n",
  "tipo": "voo",
  "origem": "GIG",
  "destino": "LIS",
  "data_ida": "2026-11-20",
  "data_volta": "2026-12-10"
}
```

`tipo`: `voo` (pede origem/destino/data_ida/data_volta) ou `hotel` (pede destino/data_checkin/data_checkout).

## Requisitos

- Linux + Chrome/Chromium headless dedicado (`--remote-debugging-port=9333`, o probe sobe sozinho)
- [browser-use CLI](https://github.com/browser-use/browser-use) no PATH apontado em `probe.py`
- Cron que aceite `no_agent` (Hermes) ou qualquer scheduler: `tick.sh` imprime só quando há deal

## Canais de pagamento em cripto

O alerta vem com lembrete dos canais para comparação na hora da compra:
hotéis — Travala, Sleap.io · voos — Aerodex (BR, Foxbit Pay), Alternative Airlines.

## Licença

MIT
