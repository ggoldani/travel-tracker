#!/usr/bin/env python3
"""Travel tracker - coleta diaria de precos (Google Flights + Google Hotels).

Uso: probe.py          -> tick: coleta, append no history, imprime so se deal
     probe.py --once   -> foreground pra testes (imprime sempre)
"""
import json
import os
import re
import subprocess
import sys
import datetime
import statistics
import urllib.parse

BASE = os.path.expanduser("~/.hermes/travel-tracker")
CLI = os.path.expanduser("~/.hermes/hermes-agent/venv/bin/browser-use")
CDP_URL = "http://127.0.0.1:9333"
HIST = os.path.join(BASE, "history")
os.makedirs(HIST, exist_ok=True)


def ensure_chrome():
    """Garante o Chrome headless dedicado (port 9333) no ar."""
    import urllib.request
    import time as _t
    try:
        urllib.request.urlopen(CDP_URL + "/json/version", timeout=3)
        return
    except Exception:
        pass
    subprocess.Popen(
        ["/usr/bin/chromium", "--headless=new", "--disable-gpu",
         "--remote-debugging-port=9333",
         "--user-data-dir=" + os.path.join(BASE, "chrome-profile"),
         "--no-first-run", "--no-default-browser-check"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(20):
        _t.sleep(1)
        try:
            urllib.request.urlopen(CDP_URL + "/json/version", timeout=3)
            return
        except Exception:
            continue
    raise RuntimeError("chrome dedicado nao subiu na port 9333")

JUNK = {100, 150, 200, 250, 300, 400, 500, 750, 1000, 1500, 2000, 2500, 3000,
        4000, 5000, 6000, 8000, 10000, 15000, 20000}


def now_br():
    return datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M")


def run_browser(script, timeout=220):
    p = subprocess.run([CLI], input=script, capture_output=True, text=True,
                       timeout=timeout,
                       env=dict(os.environ, BU_CDP_URL=CDP_URL))
    d = {}
    for line in (p.stdout or "").splitlines():
        m = re.match(r"^(PRICES|PRICES_GH)\s*=\s*(.+)$", line.strip())
        if m:
            d[m.group(1)] = m.group(2)
    return d


def parse_brl(strings):
    vals = []
    for s in strings:
        c = s.replace("\\xa0", " ").replace("\xa0", " ")
        m = re.search(r"R\$\s*([\d.]+)(?:,(\d{2}))?", c)
        if not m:
            continue
        v = float(m.group(1).replace(".", ""))
        if m.group(2):
            v += int(m.group(2)) / 100.0
        if v > 50 and int(v) not in JUNK:
            vals.append(v)
    if vals:
        med = statistics.median(vals)
        vals = [v for v in vals if v > 0.35 * med]  # lixo de UI tipo R$545
    return vals


def parse_multi(strings):
    """Captura R$/US$/EUR e devolve valores brutos + moedas vistas."""
    out = []
    for s in strings:
        c = s.replace("\\xa0", " ").replace("\xa0", " ")
        m = re.search(r"(R\$|US\$|\u20ac)\s*([\d.,]+)", c)
        if not m:
            continue
        cur = {"R$": "BRL", "US$": "USD", "\u20ac": "EUR"}[m.group(1)]
        num = m.group(2)
        if cur in ("USD", "EUR"):
            v = float(num.replace(",", ""))
        else:
            parts = num.split(",")
            if len(parts) == 2 and len(parts[1]) == 2:
                v = float(num.replace(".", "").replace(",", "."))
            else:
                v = float(num.replace(".", ""))
        if v > 20:
            out.append((cur, v))
    if out:
        med = statistics.median([v for _, v in out])
        out = [(c, v) for c, v in out if v > 0.35 * med]
    return out


_FX_CACHE = None


def fx_to_brl(vals):
    """[(moeda, valor)] -> valor minimo convertido pra BRL."""
    global _FX_CACHE
    import urllib.request
    today = datetime.date.today().isoformat()
    if all(cur == "BRL" for cur, _ in vals):
        return min(v for _, v in vals)
    if _FX_CACHE is None:
        path = os.path.join(BASE, "fx.json")
        if os.path.exists(path):
            with open(path) as f:
                _FX_CACHE = json.load(f)
    if not _FX_CACHE or _FX_CACHE.get("date") != today:
        rates = {}
        # primario: open.er-api.com (free, sem key); fallback: awesomeapi
        try:
            with urllib.request.urlopen("https://open.er-api.com/v6/latest/USD",
                                        timeout=10) as r:
                d = json.loads(r.read().decode())
            rates["USDBRL"] = float(d["rates"]["BRL"])
            try:
                with urllib.request.urlopen(
                        "https://open.er-api.com/v6/latest/EUR",
                        timeout=10) as r:
                    rates["EURBRL"] = float(
                        json.loads(r.read().decode())["rates"]["BRL"])
            except Exception:
                rates["EURBRL"] = rates["USDBRL"] * 1.08
        except Exception:
            for pair in ("USD-BRL", "EUR-BRL"):
                try:
                    with urllib.request.urlopen(
                            "https://economia.awesomeapi.com.br/last/" + pair,
                            timeout=10) as r:
                        d = json.loads(r.read().decode())
                    rates[pair.replace("-", "")] = float(d[pair.replace("-", "")]["bid"])
                except Exception:
                    pass
        if rates:
            _FX_CACHE = {"date": today, "rates": rates, "stale": False}
            with open(os.path.join(BASE, "fx.json"), "w") as f:
                json.dump(_FX_CACHE, f)
    if not _FX_CACHE:
        _FX_CACHE = {"date": today, "rates": {"USDBRL": 5.4, "EURBRL": 6.3},
                     "stale": True}
    rates = _FX_CACHE["rates"]
    best = None
    for cur, v in vals:
        if cur == "BRL":
            b = v
        elif cur == "USD":
            b = v * rates.get("USDBRL", 5.4)
        else:
            b = v * rates.get("EURBRL", 6.3)
        if best is None or b < best:
            best = b
    return best


def collect_gf(w):
    q = "Flights from %s to %s on %s through %s" % (
        w["origem"], w["destino"], w["data_ida"], w["data_volta"])
    url = ("https://www.google.com/travel/flights?q="
           + urllib.parse.quote(q) + "&hl=pt-BR&gl=BR&curr=BRL")
    script = (
        "import time\n"
        "new_tab(%r)\n" % url
        + "wait_for_load()\n"
        + "time.sleep(16)\n"
        + "t = js(\"document.title\")\n"
        + "if 'Before' in t or 'Antes' in t:\n"
        + "    js(\"(() => { const c = Array.from(document.querySelectorAll('button, a[href], div[role=button]')); const b = c.find(x => /^(Accept all|Aceitar tudo|Aceitar todos)$/i.test((x.innerText||'').trim())); if (b) b.click(); })()\")\n"
        + "    time.sleep(16)\n"
        + "prices = js(\"(() => (document.body.innerText.match(/R\\\\$\\\\s?[\\\\d.,]+/g) || []).slice(0, 12))()\")\n"
        + "print('PRICES =', prices)\n"
    )
    return run_browser(script)


def collect_gh(w):
    q = w["destino"] + " hoteis"
    url = ("https://www.google.com/travel/search?q="
           + urllib.parse.quote(q) + "&hl=pt-BR&gl=BR&curr=BRL")
    script = (
        "import time\n"
        "new_tab(%r)\n" % url
        + "wait_for_load()\n"
        + "time.sleep(16)\n"
        + "t = js(\"document.title\")\n"
        + "if 'Before' in t or 'Antes' in t:\n"
        + "    js(\"(() => { const c = Array.from(document.querySelectorAll('button, a[href], div[role=button]')); const b = c.find(x => /^(Accept all|Aceitar tudo|Aceitar todos)$/i.test((x.innerText||'').trim())); if (b) b.click(); })()\")\n"
        + "    time.sleep(16)\n"
        + "prices = js(\"(() => (document.body.innerText.match(/(?:R\\$|US\\$|€)\\s?[\\d.,]+/g) || []).slice(0, 12))()\")\n"
        + "print('PRICES =', prices)\n"
    )
    return run_browser(script)


def load_obs(slug):
    path = os.path.join(HIST, slug + ".jsonl")
    out = []
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
    return out


def format_alert(w, val, base, metric):
    """Mensagem humana pro Telegram."""
    if w["tipo"] == "voo":
        rota = "%s->%s (%s a %s)" % (w["origem"], w["destino"],
                                     w["data_ida"][8:10] + "/" + w["data_ida"][5:7],
                                     w["data_volta"][8:10] + "/" + w["data_volta"][5:7])
        q = "Flights from %s to %s on %s through %s" % (
            w["origem"], w["destino"], w["data_ida"], w["data_volta"])
        link = ("https://www.google.com/travel/flights?q="
                + urllib.parse.quote(q) + "&hl=pt-BR&gl=BR&curr=BRL")
        head = "✈️ *PASSAGEM EM PROMO* %s" % rota
        body = "%s por pessoa (ida+volta, economy)" % _brl(val)
    else:
        rota = "%s (%s a %s)" % (w["destino"],
                                 w["data_checkin"][8:10] + "/" + w["data_checkin"][5:7],
                                 w["data_checkout"][8:10] + "/" + w["data_checkout"][5:7])
        link = ("https://www.google.com/travel/search?q="
                + urllib.parse.quote(w["destino"] + " hoteis")
                + "&hl=pt-BR&gl=BR&curr=BRL")
        head = "🏨 *HOSPEDAGEM EM PROMO* %s" % rota
        body = "%s/noite (mediana dos listings)" % _brl(val)
    delta = (1 - val / base) * 100
    lines = [head, body, "📉 *%.0f%% abaixo* da mediana de 30 dias (%s)" % (
        delta, _brl(base)), link,
        "_Comprar c/ cripto: Travala.com, Sleap.io (hotel) | Aerodex/AlternativeAirlines (voo)_"]
    return "\n".join(lines)


def _brl(v):
    return "R$ " + format(round(v), ",.0f").replace(",", ".")


def main():
    once = ("--once" in sys.argv) or ("--flush" in sys.argv)
    ensure_chrome()
    with open(os.path.join(BASE, "watches.json")) as f:
        cfg = json.load(f)
    msgs = []
    today = datetime.date.today()
    for w in cfg["watches"]:
        slug = w["slug"]
        # gate GF: google recusou data a 324 dias na pratica; gate = 315
        if w["tipo"] == "voo":
            di = datetime.date.fromisoformat(w["data_ida"])
            dias = (di - today).days
            if dias > 315:
                wake = di - datetime.timedelta(days=315)
                msgs.append("DORMANT: %s ida em %d dias; acorda %s"
                            % (slug, dias, wake.isoformat()))
                continue
        if w["tipo"] == "voo":
            res = collect_gf(w)
        else:
            res = collect_gh(w)
        raw = res.get("PRICES", "[]")
        try:
            import ast
            strings = ast.literal_eval(raw)
        except Exception:
            strings = []
        pairs = parse_multi(strings)
        # cleanup: fechar todas as tabs pra nao acumular memoria
        run_browser("for t in list_tabs():\n    try:\n        close_tab(t)\n    except Exception:\n        pass\nprint('CLEAN = ok')\n", timeout=60)
        hist = load_obs(slug)
        good = [h for h in hist if h.get("ok")]
        prev = good[-1] if good else None
        # dedupe: 1 observacao por dia (tick idempotente)
        if any(h.get("date") == today.isoformat() for h in hist):
            msgs.append("SKIP: %s ja coletado hoje" % slug)
            continue
        if w["tipo"] == "hotel":
            # hotel: mediana dos listings = preco tipico do destino
            brls = sorted(fx_to_brl([p]) for p in pairs)
            val = brls[len(brls) // 2] if brls else None
            metric = "mediana-listings"
        else:
            val = fx_to_brl(pairs) if pairs else None
            metric = "min-tarifa"
        obs = {
            "ts": now_br(),
            "date": today.isoformat(),
            "ok": val is not None,
            "n": len(pairs),
            "moedas": sorted({c for c, _ in pairs}),
            "min_brl": round(val, 2) if val else None,
            "min_raw": min(pairs, key=lambda p: p[1]) if pairs else None,
        }
        # baseline: mediana de ate 30 obs proprias; enquanto <14, ultimo min
        if len(good) >= 14:
            base = statistics.median([h["min_brl"] for h in good[-30:]])
            base_note = "mediana30"
        elif prev:
            base = prev["min_brl"]
            base_note = "ultimo-min (seeding)"
        else:
            base = None
            base_note = "primeira-obs"
        obs["baseline"] = round(base, 2) if base else None
        with open(os.path.join(HIST, slug + ".jsonl"), "a") as f:
            f.write(json.dumps(obs) + "\n")
        if val is None:
            msgs.append("FAIL: %s sem precos (mantido estado anterior)" % slug)
            continue
        alert = bool(base and base_note == "mediana30" and val < base * 0.85)
        # cooldown: max 1 alerta por watch a cada 3 dias
        cpath = os.path.join(BASE, "alerts.json")
        cooldown = {}
        if os.path.exists(cpath):
            with open(cpath) as f:
                cooldown = json.load(f)
        last = cooldown.get(slug)
        if last and (today - datetime.date.fromisoformat(last)).days < 3:
            alert = False
        tag = "ALERTA" if alert else "ok"
        if alert:
            cooldown[slug] = today.isoformat()
            with open(cpath, "w") as f:
                json.dump(cooldown, f)
        alert_payload = getattr(main, "_payload", {})
        if alert:
            alert_payload[slug] = format_alert(w, val, base, metric)
            main._payload = alert_payload
        msgs.append("%s: %s %s R$ %.0f (%s; baseline %s = %.0f, n=%d, %s)" % (
            tag, slug, metric, val, "BRL-conv", base_note,
            base if base else 0, len(pairs), ",".join(obs["moedas"])))
    if once:
        print("\n".join(msgs) if msgs else "(nada)")
    else:
        # modo cron: imprime somente alertas formatados (vazio = silencio)
        payload = getattr(main, "_payload", {})
        print(("\n\n" + "―" * 20 + "\n\n").join(payload.values()) if payload else "")


if __name__ == "__main__":
    main()
