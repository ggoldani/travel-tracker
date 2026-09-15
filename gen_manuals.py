#!/usr/bin/env python3
"""Gera os manuais visuais HTML (Tailwind CDN, dark, glassmorphic) a partir
dos .md do projeto. Rerunnable: python3 gen_manuals.py"""
import os
import re
import html as H

ROOT = os.path.dirname(os.path.abspath(__file__))
STYLE = """<script src="https://cdn.tailwindcss.com"></script>
<style>body{background:#09090b}.glass{background:rgba(24,24,27,.65);backdrop-filter:blur(12px);border:1px solid rgba(255,255,255,.06)}code,pre{font-family:ui-monospace,monospace}</style>"""


def md_to_html(md):
    out, i, lines = [], 0, md.splitlines()
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            buf = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(lines[i])
                i += 1
            out.append("<pre class='glass rounded-lg p-4 text-sm text-zinc-300 overflow-x-auto'>%s</pre>"
                       % H.escape("\n".join(buf)))
        elif ln.startswith("|") and i + 1 < len(lines) and set(lines[i + 1].replace("|", "").replace("-", "").strip()) <= {""}:
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip("|").split("|")]
                if not set("".join(cells)) <= set("-: "):
                    rows.append(cells)
                i += 1
            head = "".join("<th class='text-left text-zinc-400 font-medium py-1 pr-4'>%s</th>" % H.escape(c) for c in rows[0])
            body = "".join("<tr>%s</tr>" % "".join(
                "<td class='py-1 pr-4 text-zinc-200'>%s</td>" % inline(c) for c in r)
                for r in rows[1:])
            out.append("<table class='text-sm mb-3'><thead><tr>%s</tr></thead><tbody>%s</tbody></table>" % (head, body))
            continue
        elif re.match(r"^#{1,4} ", ln):
            lvl = len(ln.split(" ")[0])
            txt = inline(ln[lvl + 1:])
            cls = {1: "text-2xl font-bold text-zinc-100 mt-2 mb-4",
                   2: "text-lg font-semibold text-zinc-200 mt-6 mb-2 border-b border-zinc-800 pb-1",
                   3: "text-base font-semibold text-zinc-300 mt-4 mb-1"}.get(lvl, "text-sm font-semibold text-zinc-300 mt-3")
            out.append("<h%d class='%s'>%s</h%d>" % (lvl, cls, txt, lvl))
        elif ln.startswith("- "):
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append("<li class='text-zinc-300 mb-1'>%s</li>" % inline(lines[i][2:]))
                i += 1
            out.append("<ul class='list-disc list-inside mb-3 text-sm'>%s</ul>" % "".join(items))
            continue
        elif ln.strip():
            out.append("<p class='text-sm text-zinc-300 mb-2'>%s</p>" % inline(ln))
        i += 1
    return "\n".join(out)


def inline(s):
    s = H.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong class='text-zinc-100'>\1</strong>", s)
    s = re.sub(r"`(.+?)`", r"<code class='bg-zinc-800/80 text-emerald-300 rounded px-1 py-0.5 text-xs'>\1</code>", s)
    s = re.sub(r"\[(.+?)\]\((.+?)\)", r"<a class='text-sky-400 hover:underline' href='\2'>\1</a>", s)
    return s


def page(title, body_html):
    return ("<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            "<title>%s</title>%s</head>"
            "<body class='min-h-screen text-zinc-100'><main class='max-w-3xl mx-auto px-6 py-10'>"
            "<div class='glass rounded-2xl p-8'>%s</div>"
            "<p class='text-xs text-zinc-500 mt-4'>gerado por gen_manuals.py — não editar à mão</p>"
            "</main></body></html>") % (H.escape(title), STYLE, body_html)


def write(html_path, md_path, title):
    with open(md_path) as f:
        body = md_to_html(f.read())
    with open(html_path, "w") as f:
        f.write(page(title, body))
    print("ok:", os.path.relpath(html_path, ROOT))


JOBS = [
    ("AGENTS.md", "AGENTS.html", "travel-tracker — AGENTS"),
    ("README.md", "README_site.html", "travel-tracker — README"),
    ("skills/travel-tracker/SKILL.md", "skills/travel-tracker/README.html", "travel-tracker — project skill"),
    ("skills/travel-tracker/reference/routing-matrix.md", "skills/travel-tracker/reference/routing-matrix.html", "routing matrix"),
    ("skills/travel-tracker/reference/role-contracts.md", "skills/travel-tracker/reference/role-contracts.html", "role contracts"),
    ("skills/travel-tracker/workflows/add-watch/SKILL.md", "skills/travel-tracker/workflows/add-watch/README.html", "add-watch"),
    ("skills/travel-tracker/workflows/tick/SKILL.md", "skills/travel-tracker/workflows/tick/README.html", "tick"),
    ("skills/travel-tracker/workflows/health/SKILL.md", "skills/travel-tracker/workflows/health/README.html", "health"),
    ("skills/travel-tracker/workflows/status/SKILL.md", "skills/travel-tracker/workflows/status/README.html", "status"),
]

for md, out, title in JOBS:
    src = os.path.join(ROOT, md)
    if os.path.exists(src):
        write(os.path.join(ROOT, out), src, title)
    else:
        print("skip (sem md):", md)
