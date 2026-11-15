"""Roteiros dos Reels da Factor Ofertas.

Transforma um trabalho da fila (ofertas ou um conteúdo do feed) em cenas com falas curtas.
Cada fala vira uma legenda e um trecho de voz; o tempo de cada fala vem da própria voz gerada.
Tudo é determinístico: o mesmo Reels gera sempre o mesmo roteiro (a variação vem do id).
"""
from __future__ import annotations

import re
import unicodedata

UNITS = ["zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez",
         "onze", "doze", "treze", "catorze", "quinze", "dezesseis", "dezessete", "dezoito", "dezenove"]
TENS = ["", "", "vinte", "trinta", "quarenta", "cinquenta", "sessenta", "setenta", "oitenta", "noventa"]
HUNDREDS = ["", "cento", "duzentos", "trezentos", "quatrocentos", "quinhentos", "seiscentos",
            "setecentos", "oitocentos", "novecentos"]


def _under_1000(n: int) -> str:
    if n == 0:
        return ""
    if n == 100:
        return "cem"
    parts = []
    h, rest = divmod(n, 100)
    if h:
        parts.append(HUNDREDS[h])
    if rest:
        if rest < 20:
            parts.append(UNITS[rest])
        else:
            t, u = divmod(rest, 10)
            parts.append(TENS[t] + (f" e {UNITS[u]}" if u else ""))
    return " e ".join(parts)


def number_words(n: int) -> str:
    """Número inteiro por extenso, em português do Brasil (até 999.999.999)."""
    if n == 0:
        return "zero"
    if n < 0:
        return "menos " + number_words(-n)
    millions, rest = divmod(n, 1_000_000)
    thousands, units = divmod(rest, 1000)
    chunks: list[str] = []
    if millions:
        chunks.append("um milhão" if millions == 1 else f"{_under_1000(millions)} milhões")
    if thousands:
        chunks.append("mil" if thousands == 1 else f"{_under_1000(thousands)} mil")
    if units:
        # regra do "e": mil e duzentos, dois mil e cinquenta, mas mil duzentos e trinta
        if chunks and (units < 100 or units % 100 == 0):
            chunks.append("e " + _under_1000(units))
        else:
            chunks.append(_under_1000(units))
    return " ".join(chunks)


def money_words(value: float) -> str:
    """7799.90 -> 'sete mil setecentos e noventa e nove reais e noventa centavos'."""
    cents_total = int(round(float(value) * 100))
    reais, cents = divmod(cents_total, 100)
    out = []
    if reais:
        w = "um real" if reais == 1 else f"{number_words(reais)} reais"
        if reais % 1_000_000 == 0:
            w = w.replace(" reais", " de reais")
        out.append(w)
    if cents:
        out.append("um centavo" if cents == 1 else f"{number_words(cents)} centavos")
    return " e ".join(out) if out else "zero reais"


def money_text(value: float) -> str:
    """7799.9 -> 'R$ 7.799,90' (como aparece na tela)."""
    s = f"{float(value):,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def pct_off(price: float | None, original: float | None) -> int:
    if not price or not original or original <= price:
        return 0
    return int(round((1 - float(price) / float(original)) * 100))


SPEC = re.compile(r"\d")
STOP = {"com", "para", "de", "da", "do", "das", "dos", "e", "em", "kit", "c/", "-", "|", "+", "p/"}


def short_name(title: str, max_words: int = 4, max_chars: int = 30) -> str:
    """Nome curto para a tela e para a fala. Corta no primeiro código técnico (1000w, 48v, Gt16...)."""
    words = [w for w in re.split(r"\s+", title.strip()) if w]
    out: list[str] = []
    for w in words:
        # código técnico (letras e números juntos: 1000w, Gt16, 887ml) encerra o nome
        if SPEC.search(w) and not w.isdigit() and out:
            break
        if w.isdigit() and len(out) >= 2:
            break
        if len(" ".join(out + [w])) > max_chars and out:
            break
        out.append(w)
        if len(out) >= max_words:
            break
    while len(out) > 1 and (out[-1].lower() in STOP or out[-1].isdigit()):
        out.pop()
    return " ".join(out) or title[:max_chars]


ACRONYMS = {"CPF": "cê pê efe", "TV": "tê vê", "USB": "u ésse bê", "LED": "léd", "SSD": "ésse ésse dê",
            "RGB": "érre gê bê", "4K": "quatro k", "HD": "agá dê", "Full": "Ful", "Wi-Fi": "uai fai", "WiFi": "uai fai"}


def speakable(text: str) -> str:
    """Limpa o texto para a voz: tira emoji, troca R$, %, siglas e números por palavras."""
    t = unicodedata.normalize("NFC", text)
    t = re.sub(r"[\U0001F000-\U0001FAFF☀-➿️→✔]", "", t)
    t = re.sub(r"R\$\s?(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)",
               lambda m: money_words(float(m.group(1).replace(".", "").replace(",", "."))), t)
    t = re.sub(r"(\d+)\s?%", lambda m: f"{number_words(int(m.group(1)))} por cento", t)
    for k, v in ACRONYMS.items():
        t = re.sub(rf"(?<![\w-]){re.escape(k)}(?![\w-])", v, t)
    t = re.sub(r"(\d+),(\d+)", lambda m: f"{number_words(int(m.group(1)))} vírgula {number_words(int(m.group(2)))}", t)
    t = re.sub(r"\d+", lambda m: number_words(int(m.group(0))) if len(m.group(0)) <= 9 else m.group(0), t)
    t = re.sub(r"[()\[\]\"“”]", "", t)
    t = t.replace("&", " e ").replace("/", " ").replace("+", " mais ").replace("#", " ")
    return re.sub(r"\s+", " ", t).strip()


def pick(options: list[str], seed: int) -> str:
    return options[seed % len(options)]


def badges_of(o: dict) -> list[tuple[str, str]]:
    """Selos de confiança: (texto na tela, texto falado)."""
    out = []
    if o.get("free_shipping"):
        out.append(("Frete grátis", "frete grátis"))
    if o.get("full"):
        out.append(("Entrega Full", "entrega Full, que chega rapidinho"))
    if o.get("official"):
        out.append(("Loja oficial", "venda pela loja oficial"))
    elif o.get("medal") in ("platinum", "gold"):
        out.append(("MercadoLíder", "vendedor MercadoLíder"))
    if o.get("rating"):
        r = float(o["rating"])
        out.append((f"Nota {r:.1f}".replace(".", ","), f"nota {r:.1f} de cinco".replace(".", ",")))
    if o.get("sold") and int(o["sold"]) >= 50:
        out.append((f"+{int(o['sold'])} vendidos", f"mais de {int(o['sold'])} vendidos"))
    return out


def line(text: str, say: str | None = None) -> dict:
    return {"text": text, "say": speakable(say if say is not None else text)}


def _hashtags(base: str | None, extra: str) -> str:
    tags: list[str] = []
    for t in (base or "").split() + extra.split():
        t = t.strip()
        if t.startswith("#") and len(t) > 1 and t.lower() not in [x.lower() for x in tags]:
            tags.append(t)
    return " ".join(tags[:6])


def build(job: dict) -> dict:
    kind = job["kind"]
    seed = int(job["id"])
    if kind == "alerta":
        return _alerta(job, seed)
    if kind == "lista":
        return _lista(job, seed)
    if kind == "dica":
        return _dica(job, seed)
    raise ValueError(f"tipo de Reels desconhecido: {kind}")


def _alerta(job: dict, seed: int) -> dict:
    o = job["offers"][0]
    name = short_name(o["title"])
    price = float(o["price"])
    orig = float(o["original"]) if o.get("original") else None
    off = pct_off(price, orig)
    badges = badges_of(o)
    scenes = []
    if off >= 5:
        hook = pick(["Alerta de preço!", "Para tudo!", "Caiu o preço!"], seed)
        scenes.append({"type": "hook", "kicker": "ALERTA DE PREÇO", "name": name, "off": off, "image": o["image"],
                       "lines": [line(hook), line(f"{name} com {off}% de desconto.")]})
        scenes.append({"type": "price", "name": name, "old": money_text(orig), "new": money_text(price), "off": off, "image": o["image"],
                       "lines": [line(f"Saiu de {money_text(orig)}"), line(f"por {money_text(price)}.")]})
    else:
        hook = pick(["Achadinho do dia!", "Olha esse achado!"], seed)
        scenes.append({"type": "hook", "kicker": "ACHADINHO DO DIA", "name": name, "off": 0, "image": o["image"],
                       "lines": [line(hook), line(f"{name}.")]})
        scenes.append({"type": "price", "name": name, "old": None, "new": money_text(price), "off": 0, "image": o["image"],
                       "lines": [line(f"Tá saindo por {money_text(price)}.")]})
    if badges:
        spoken = [b[1] for b in badges[:3]]
        say = "Tem " + (", ".join(spoken[:-1]) + " e " + spoken[-1] if len(spoken) > 1 else spoken[0]) + "."
        scenes.append({"type": "proof", "badges": [b[0] for b in badges[:4]], "image": o["image"],
                       "lines": [{"text": " · ".join(b[0] for b in badges[:3]), "say": speakable(say)}]})
    scenes.append({"type": "cta", "offer": o["id"],
                   "lines": [line("O link tá na bio."),
                             line(f"Procura a oferta {o['id']}."),
                             line(pick(["Corre, que preço assim acaba rápido!", "Salva esse vídeo pra não perder!"], seed))]})
    badge_txt = " · ".join(b[0] for b in badges[:4])
    cap = [f"🚨 {o['title']}", ""]
    cap.append(f"De {money_text(orig)} por {money_text(price)} (-{off}%)" if off >= 5 else f"Por {money_text(price)}")
    if badge_txt:
        cap.append(f"✔ {badge_txt}")
    cap += ["", f"🔗 Link na bio → oferta #{o['id']}", "Preço e estoque podem mudar a qualquer momento."]
    tags = _hashtags(o.get("hashtags"), "#achadinhos #ofertas #reels")
    return {"kind": "alerta", "scenes": scenes, "caption": "\n".join(cap) + "\n\n" + tags, "hashtags": tags,
            "title": f"Alerta: {name}", "mood": "urgente"}


def _lista(job: dict, seed: int) -> dict:
    offers = job["offers"]
    n = len(offers)
    niches = {o.get("niche_label") for o in offers if o.get("niche_label")}
    niche = next(iter(niches)) if len(niches) == 1 else None
    top = max(float(o["price"]) for o in offers)
    limit = next((v for v in (50, 100, 150, 200, 300, 500) if top <= v), None)
    if niche and niche.lower() not in ("achadinho", "em alta"):
        title = f"{n} achados de {niche.lower()}"
    else:
        title = f"{n} achadinhos do dia"
    sub = f"até {money_text(limit).replace(',00', '')}" if limit else "com desconto"
    scenes = [{"type": "listhook", "kicker": "LISTA DO DIA", "title": title.capitalize(), "sub": sub,
               "images": [o["image"] for o in offers[:3]],
               "lines": [line(f"{title.capitalize()} {sub}"),
                         line(pick(["que valem a pena.", "pra você não perder.", "que eu separei hoje."], seed))]}]
    ordinals = ["Primeiro", "Segundo", "Terceiro", "Quarto", "Quinto"]
    for i, o in enumerate(offers):
        name = short_name(o["title"])
        off = pct_off(float(o["price"]), float(o["original"]) if o.get("original") else None)
        say_price = f"Por {money_text(float(o['price']))}" + (f", {off}% mais barato." if off >= 10 else ".")
        scenes.append({"type": "item", "index": i + 1, "total": n, "name": name, "new": money_text(float(o["price"])),
                       "old": money_text(float(o["original"])) if off >= 5 else None, "off": off, "image": o["image"], "offer": o["id"],
                       "lines": [line(f"{ordinals[i]}: {name}."), line(say_price)]})
    scenes.append({"type": "cta", "offer": None, "offers": [o["id"] for o in offers],
                   "lines": [line("Todos os links estão na bio."), line("Salva esse vídeo e manda pra quem precisa!")]})
    cap = [f"🛒 {title.capitalize()} {sub}", ""]
    for i, o in enumerate(offers):
        cap.append(f"{i + 1}. {short_name(o['title'], 6, 48)} · {money_text(float(o['price']))} → oferta #{o['id']}")
    cap += ["", "🔗 Todos os links na bio, pelo número da oferta.", "Preço e estoque podem mudar a qualquer momento."]
    tags = _hashtags(offers[0].get("hashtags"), "#achadinhos #ofertas #reels")
    return {"kind": "lista", "scenes": scenes, "caption": "\n".join(cap) + "\n\n" + tags, "hashtags": tags,
            "title": title.capitalize(), "mood": "animada"}


def _bullets(body: str) -> list[str]:
    return [re.sub(r"^[-•*]\s*", "", x).strip() for x in body.split("\n") if x.strip()]


def _sentences(text: str, max_chars: int = 64) -> list[str]:
    """Quebra um texto em falas curtas (até ~64 caracteres), sem cortar palavra."""
    out: list[str] = []
    for sent in re.split(r"(?<=[.!?:])\s+", text.strip()):
        cur = ""
        for w in sent.split():
            if len(cur) + len(w) + 1 > max_chars and cur:
                out.append(cur)
                cur = w
            else:
                cur = f"{cur} {w}".strip()
        if cur:
            out.append(cur)
    return out


def _dica(job: dict, seed: int) -> dict:
    c = job["content"]
    slides = (c.get("slides") or [])[:5]
    if not slides:
        raise ValueError("conteúdo sem slides")
    first = slides[0]
    head = first.get("headline") or c["title"]
    scenes = [{"type": "tiphook", "kicker": (first.get("kicker") or "DICA").upper(), "title": head,
               "lines": [line(x) for x in _sentences(head)]}]
    first_items = _bullets(first.get("body") or "")
    if len(slides) == 1 and len(first_items) > 1:
        for i, b in enumerate(first_items[:5]):
            scenes.append({"type": "tip", "index": i + 1, "kicker": "", "title": b, "body": "", "lines": [line(b)]})
    for i, s in enumerate(slides[1:4]):
        body = s.get("body") or ""
        items = [x for x in _bullets(body) if not re.search(r"[.!?]$", x) or len(x) <= 40]
        spoken = _sentences(s.get("headline") or "")
        if len(items) > 1:
            spoken += items[:3]
            shown = "\n".join(items[:3])
        else:
            first_sentence = re.split(r"(?<=[.!?])\s+", body.strip())[0] if body.strip() else ""
            spoken += _sentences(first_sentence)
            shown = first_sentence
        scenes.append({"type": "tip", "index": i + 1, "kicker": (s.get("kicker") or "").upper(), "title": s.get("headline") or "",
                       "body": shown, "lines": [line(x) for x in spoken if x]})
    scenes.append({"type": "cta", "offer": None, "follow": True,
                   "lines": [line("Salva esse vídeo pra consultar depois."), line("E segue a Factor Ofertas pra mais dicas!")]})
    cap = (c.get("caption") or c["title"]).strip()
    tags = _hashtags(c.get("hashtags"), "#dicas #achadinhos #reels")
    if "#" not in cap:
        cap = cap + "\n\n" + tags
    return {"kind": "dica", "scenes": scenes, "caption": cap, "hashtags": tags, "title": c["title"], "mood": "animada"}
