#!/bin/bash
# Travel tracker - tick diario. stdout vazio = silencio (nao entrega nada).
# So imprime quando ha ALERTA (preco < baseline*0.85).
export BU_CDP_URL="http://127.0.0.1:9333"
python3 "$HOME/.hermes/travel-tracker/probe.py" 2>>"$HOME/.hermes/travel-tracker/probe.err.log"
