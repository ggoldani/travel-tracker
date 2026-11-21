#!/bin/bash
# Travel tracker - tick diario. stdout vazio = silencio (nao entrega nada).
# So imprime quando ha ALERTA ou health warning.
export BU_CDP_URL="http://127.0.0.1:9333"
LOG="$HOME/.hermes/travel-tracker/probe.err.log"
LOCK="$HOME/.hermes/travel-tracker/.tick.lock"

# anti-concorrencia: cron + rodada manual nunca se cruzam
exec 9>"$LOCK"
flock -n 9 || { echo "tick anterior ainda em execucao"; exit 0; }

# rotacao simples de err.log (1 MB)
[ -f "$LOG" ] && [ "$(stat -c%s "$LOG" 2>/dev/null || echo 0)" -gt 1048576 ] && : > "$LOG"

exec python3 "$HOME/.hermes/travel-tracker/probe.py" 2>>"$LOG"
