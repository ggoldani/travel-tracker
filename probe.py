#!/usr/bin/env python3
"""Travel tracker - coleta diaria de precos (Google Flights + Google Hotels).

Uso: probe.py            -> tick: coleta, append no history, imprime so se deal
     probe.py --once     -> foreground pra testes (imprime sempre)
     probe.py --health   -> relatorio de saude (pra heartbeat semanal)
     TT_FORCE=1          -> ignora dedupe diario (ops/testes)
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

PT_WEEKDAYS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
               "sexta-feira", "sábado", "domingo"]
PT_MONTHS = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
             "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]


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


def now_br():
    return datetime.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M")


def run_browser(script, timeout=220):
    p = subprocess.run([CLI], input=script, capture_output=True, text=True,
                       timeout=timeout,
                       env=dict(os.environ, BU_CDP_URL=CDP_URL))
    d = {}
    for line in (p.stdout or "").splitlines():
        m = re.match(r"^(PRICES|PRICES_GH|STEPS|PICKER)\s*=\s*(.+)$", line.strip())
        if m:
            d[m.group(1)] = m.group(2)
    return d


def parse_multi(strings):
    """Captura R$/US$/EUR e devolve [(moeda, valor)].

    Heuristica de separador (paginas pt-BR com leak en-US):
    - dot presente -> dot = milhar, resto decimal se tiver virgula de 2 digitos
    - virgula com exatamente 2 digitos no fim -> decimal
    - virgula com 3 digitos e sem dot -> leak en-US = milhar
    """
    out = []
    for s in strings:
        c = s.replace("\\xa0", " ").replace("\xa0", " ")
        m = re.search(r"(R\$|US\$|\u20ac)\s*([\d.,]+)", c)
        if not m:
            continue
        cur = {"R$": "BRL", "US$": "USD", "\u20ac": "EUR"}[m.group(1)]
        num = m.group(2)
        if "." in num and "," in num:
            v = float(num.replace(".", "").replace(",", "."))
        elif "," in num:
            parts = num.split(",")
            if len(parts) == 2 and len(parts[1]) == 2:
                v = float(num.replace(",", "."))
            else:
                v = float(num.replace(",", ""))
        else:
            # dot-only: pagina forçada pt-BR -> dot = milhar ("8.561" = 8561);
            # decimal em pt-BR usa virgula, entao dot solto nunca e decimal
            v = float(num.replace(".", ""))
        if v > 20:
            out.append((cur, v))
    return out


def filter_junk(pairs, ratio=0.20):
    """Mata lixo de UI so pra metrica min (voo). Hotel usa mediana = robusta,
    nao filtra (spread legitimo de listings chega a 10x)."""
    if not pairs:
        return pairs
    med = statistics.median([v for _, v in pairs])
    return [(c, v) for c, v in pairs if v > ratio * med]


def _gh_date_label(d):
    return "%s, %d de %s de %d" % (
        PT_WEEKDAYS[d.weekday()], d.day, PT_MONTHS[d.month - 1], d.year)


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
                    rates[pair.replace("-", "")] = float(
                        d[pair.replace("-", "")]["bid"])
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


CONSENT_JS = ("(() => { const c = Array.from(document.querySelectorAll("
              "'button, a[href], div[role=button]')); const b = c.find("
              "x => /^(Accept all|Aceitar tudo|Aceitar todos)$/i.test("
              "(x.innerText||'').trim())); if (b) b.click(); })()")


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
        + "    js(%r)\n" % CONSENT_JS
        + "    time.sleep(16)\n"
        + "prices = js(\"(() => (document.body.innerText.match(/(?:R\\\\$|US\\\\$|\u20ac)\\\\s?[\\\\d.,]+/g) || []).slice(0, 12))()\")\n"
        + "print('PRICES =', prices)\n"
    )
    return run_browser(script)


def collect_gh(w):
    """GH com datas reais: abre, clica Alterar datas, marca checkin/checkout
    por aria-label pt-BR, aplica (Concluido) e extrai precos da semana."""
    url = ("https://www.google.com/travel/search?q="
           + urllib.parse.quote(w["destino"] + " hoteis")
           + "&hl=pt-BR&gl=BR&curr=BRL")
    ci = _gh_date_label(datetime.date.fromisoformat(w["data_checkin"]))
    co = _gh_date_label(datetime.date.fromisoformat(w["data_checkout"]))
    script = (
        "import time\n"
        "new_tab(%r)\n" % url
        + "wait_for_load()\n"
        + "time.sleep(16)\n"
        + "t = js(\"document.title\")\n"
        + "if 'Before' in t or 'Antes' in t:\n"
        + "    js(%r)\n" % CONSENT_JS
        + "    time.sleep(16)\n"
        # abrir picker
        + "p = js(%r)\n" % (
            "(() => { const b = Array.from(document.querySelectorAll("
            "'[aria-label]')).find(e => /^Alterar datas/i.test("
            "e.getAttribute('aria-label'))); if (!b) return 'NO-BTN'; "
            "b.click(); return 'OK'; })()")
        + "print('PICKER =', p)\n"
        + "time.sleep(3)\n"
        # marcar checkin e checkout
        + "d1 = js(%r)\n" % (
            "((lbl) => { const c = Array.from(document.querySelectorAll("
            "'[aria-label]')).find(e => e.getAttribute('aria-label') === lbl);"
            " if (!c) return 'NO-CELL'; (c.closest('button')||c).click(); "
            "return 'OK'; })(%r)" % ci)
        + "time.sleep(2)\n"
        + "d2 = js(%r)\n" % (
            "((lbl) => { const c = Array.from(document.querySelectorAll("
            "'[aria-label]')).find(e => e.getAttribute('aria-label') === lbl);"
            " if (!c) return 'NO-CELL'; (c.closest('button')||c).click(); "
            "return 'OK'; })(%r)" % co)
        + "time.sleep(2)\n"
        # aplicar
        + "dn = js(%r)\n" % (
            "(() => { const b = Array.from(document.querySelectorAll("
            "'button')).find(x => /Conclu[ií]do|^Done$|Aplicar/i.test("
            "(x.innerText||'').trim())); if (b) { b.click(); return 'OK'; } "
            "return 'NO-BTN'; })()")
        + "time.sleep(14)\n"
        + "prices = js(\"(() => (document.body.innerText.match(/(?:R\\\\$|US\\\\$|\u20ac)\\\\s?[\\\\d.,]+/g) || []).slice(0, 12))()\")\n"
        + "print('STEPS =', p, d1, d2, dn)\n"
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


def _brl(v):
    return "R$ " + format(round(v), ",.0f").replace(",", ".")


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


def format_health(cfg, health):
    lines = ["🩺 *TRAVEL TRACKER — saúde semanal*"]
    for w in cfg["watches"]:
        slug = w["slug"]
        h = health.get(slug, {})
        last_ok = h.get("last_ok") or "nunca"
        fails = h.get("consecutive_fails", 0)
        n = len(load_obs(slug))
        estado = "dormant" if h.get("dormant") else ("FAIL x%d" % fails if fails else "ok")
        lines.append("• `%s`: %s, último ok %s, %d obs" % (slug, estado, last_ok, n))
    return "\n".join(lines)


def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)


def health_path():
    return os.path.join(BASE, "health.json")


def health_tick(slug, ok, dormant=False):
    hp = health_path()
    health = load_json(hp, {})
    h = health.setdefault(slug, {})
    if dormant:
        h["dormant"] = True
    elif ok:
        h["dormant"] = False
        h["consecutive_fails"] = 0
        h["last_ok"] = datetime.date.today().isoformat()
    else:
        h["dormant"] = False
        h["consecutive_fails"] = h.get("consecutive_fails", 0) + 1
    save_json(hp, health)
    return h


def main():
    once = "--once" in sys.argv
    force = os.environ.get("TT_FORCE") == "1"
    if "--health" in sys.argv:
        with open(os.path.join(BASE, "watches.json")) as f:
            cfg = json.load(f)
        print(format_health(cfg, load_json(health_path(), {})))
        return
    ensure_chrome()
    with open(os.path.join(BASE, "watches.json")) as f:
        cfg = json.load(f)
    msgs = []
    payload = {}
    today = datetime.date.today()
    for w in cfg["watches"]:
        slug = w["slug"]
        hist = load_obs(slug)
        good = [h for h in hist if h.get("ok")]
        # B1: dedupe ANTES de qualquer fetch
        if not force and any(h.get("date") == today.isoformat() for h in hist):
            msgs.append("SKIP: %s ja coletado hoje" % slug)
            continue
        # gate GF: google recusou data a 324 dias na pratica; gate = 315
        if w["tipo"] == "voo":
            di = datetime.date.fromisoformat(w["data_ida"])
            dias = (di - today).days
            if dias > 315:
                wake = di - datetime.timedelta(days=315)
                msgs.append("DORMANT: %s ida em %d dias; acorda %s"
                            % (slug, dias, wake.isoformat()))
                health_tick(slug, False, dormant=True)
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
        # cleanup: fechar tabs
        run_browser("for t in list_tabs():\n    try:\n        close_tab(t)\n    except Exception:\n        pass\nprint('CLEAN = ok')\n", timeout=60)
        if w["tipo"] == "hotel":
            brls = sorted(fx_to_brl([p]) for p in pairs)
            val = brls[len(brls) // 2] if brls else None
            metric = "mediana-listings"
        else:
            val = fx_to_brl(filter_junk(pairs)) if pairs else None
            metric = "min-tarifa"
        # baseline: mediana de ate 30 obs proprias; enquanto <14, ultimo min
        prev = good[-1] if good else None
        if len(good) >= 14:
            base = statistics.median([h["min_brl"] for h in good[-30:]])
            base_note = "mediana30"
        elif prev:
            base = prev["min_brl"]
            base_note = "ultimo-min (seeding)"
        else:
            base = None
            base_note = "primeira-obs"
        obs = {
            "ts": now_br(),
            "date": today.isoformat(),
            "ok": val is not None,
            "n": len(pairs),
            "moedas": sorted({c for c, _ in pairs}),
            "min_brl": round(val, 2) if val else None,
            "min_raw": min(pairs, key=lambda p: p[1]) if pairs else None,
            "baseline": round(base, 2) if base else None,
        }
        if w["tipo"] == "hotel":
            # rastro do fluxo de datas: se picker/celulas/aplicar falharam, o
            # preco veio da pagina generica e NAO e comparavel com a serie
            steps = res.get("STEPS", "").split()
            obs["dates_flow_ok"] = (res.get("PICKER", "") == "OK"
                                    and steps == ["OK", "OK", "OK", "OK"])
        with open(os.path.join(HIST, slug + ".jsonl"), "a") as f:
            f.write(json.dumps(obs) + "\n")
        h = health_tick(slug, val is not None)
        if val is None:
            msgs.append("FAIL: %s sem precos (mantido estado anterior)" % slug)
            # B4: morte silenciosa -> avisa no canal a partir de 3 fails seguidos
            if h.get("consecutive_fails", 0) == 3:
                payload[slug] = ("⚠️ *TRAVEL TRACKER quebrado p/ %s*\n"
                                 "3 coletas seguidas falharam (DOM da fonte "
                                 "mudou?). Último preço bom: %s" % (
                                     slug, _brl(base) if base else "n/a"))
            continue
        # preco-alvo absoluto (opcional no watch)
        target = w.get("target")
        alert = bool(base and base_note == "mediana30" and val < base * 0.85)
        if target and val <= target:
            alert = True
        # cooldown: max 1 alerta por watch a cada 3 dias
        cpath = os.path.join(BASE, "alerts.json")
        cooldown = load_json(cpath, {})
        last = cooldown.get(slug)
        if last and (today - datetime.date.fromisoformat(last)).days < 3:
            alert = False
        if alert:
            cooldown[slug] = today.isoformat()
            save_json(cpath, cooldown)
            payload[slug] = format_alert(w, val, base, metric)
        tag = "ALERTA" if alert else "ok"
        msgs.append("%s: %s %s R$ %.0f (baseline %s = %.0f, n=%d, %s)" % (
            tag, slug, metric, val, base_note, base if base else 0,
            len(pairs), ",".join(obs["moedas"])))
    if once:
        print("\n".join(msgs) if msgs else "(nada)")
    else:
        print(("\n\n" + "―" * 20 + "\n\n").join(payload.values()) if payload else "")


if __name__ == "__main__":
    main()
