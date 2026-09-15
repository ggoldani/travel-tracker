# Role contracts — travel-tracker

## Gold (owner)
- Define destinos, datas, thresholds (`target`) e prioridades.
- Único que envia coisa a terceiros; repo público é dele (ggoldani).

## Hermes (agente executor)
- Executa workflows via router; mantém probe.py/watches.json como fonte canônica.
- Deve carregar o contrato do cmd antes de agir; fechar com evidência (stdout, obs, relatório).
- Mudança de comportamento ⇒ ciclo radioactive + testes + commit em nome de Gold.

## Cron (travel-tracker-japan, 9h BRT)
- no_agent; executa scripts/travel-tracker.sh; stdout vazio = silêncio.
- Nunca recebe prompt; nada de LLM no caminho quente.

## Cron (travel-tracker-heartbeat, Mondays 10h BRT)
- Agent-job: reenvia relatório de saúde verbatim; se `[[spark]]`, anexa spark.png via MEDIA:.

## Fronteiras
- Agente NÃO cria watch sem slug único e datas ISO.
- Agente NÃO marca `dates_flow_ok=true` sem os 4 STEPS == OK.
- Falha de coleta nunca sobrescreve último preço bom.
