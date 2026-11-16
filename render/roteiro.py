"""Roteiro em cenas para o motor de animação (Remotion).

Três origens:
  - "conteudo": roteiro escrito pelo agente de conteúdo (gancho, número, lista, mito x verdade, passos,
    comparação, pergunta, destaque) e aprovado pelo PTK no painel;
  - "alerta" e "lista": ofertas (montadas aqui, a partir dos dados do produto);
  - "dica": um conteúdo do feed já aprovado, virado em vídeo.
Todo Reels termina com a cena "Curte e segue". Cada fala vira legenda e trecho de voz.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import script as S
import tts

HANDLE = "@factorofertas"
PRON = json.loads((Path(__file__).resolve().parent.parent / "voz" / "pronuncia.json").read_text(encoding="utf-8"))
_PRON_RE = [(re.compile(rf"(?<![\wÀ-ú]){re.escape(k)}(?![\wÀ-ú])", re.I), v) for k, v in sorted(PRON["palavras"].items(), key=lambda kv: -len(kv[0]))]

CONTENT_TYPES = {"gancho", "numero", "lista", "mito_verdade", "passos", "comparacao", "pergunta", "destaque", "historia", "chat", "tela"}
ELENCO = {"ana", "bia", "carla", "duda", "lu", "mari"}  # mesmas chaves de remotion/src/story.tsx
EMOCOES = {"neutra", "feliz", "animada", "desconfiada", "pensativa", "brava", "furiosa", "chocada", "assustada", "triste", "cansada", "apaixonada", "aliviada"}
LUGARES = {"casa", "loja", "rua"}


def respell(t: str) -> str:
    """Palavras estrangeiras escritas como se pronunciam. Só para a voz Kokoro: o Chatterbox já pronuncia
    "Black Friday" e "air fryer" certo com a grafia original (o teste com o Whisper mostrou isso)."""
    for rx, v in _PRON_RE:
        t = rx.sub(v, t)
    return t


def falar(text: str) -> str:
    """Texto que a voz lê: números e preços por extenso, sem símbolos."""
    return S.speakable(text)


def L(text: str, say: str | None = None) -> dict:
    text = re.sub(r"\s+", " ", text).strip()
    return {"text": text, "say": falar(say if say is not None else text)}


def cta(seed: int, oferta: int | None = None, ofertas: list[int] | None = None, salvar: bool = False) -> dict:
    first = ["Curte esse vídeo", "Deixa o seu like"] if (oferta or ofertas) else ["Curte esse vídeo", "Se te ajudou, curte", "Deixa o seu like"]
    lines = [L(S.pick(first, seed)),
             L(S.pick(["e segue a Factor Ofertas", "e segue a Factor Ofertas pra não perder", "e segue a Factor Ofertas, todo dia tem achado"], seed // 3))]
    if oferta:
        lines.append(L(f"O link tá na bio: oferta {oferta}."))
    elif ofertas:
        lines.append(L("Todos os links estão na bio."))
    elif salvar:
        lines.append(L("E salva pra ver depois!"))
    return {"type": "cta", "handle": HANDLE, "oferta": oferta, "ofertas": ofertas, "salvar": salvar, "lines": lines}


def build(job: dict) -> dict:
    seed = int(job["id"])
    kind = job["kind"]
    if kind == "conteudo":
        return _conteudo(job, seed)
    if kind == "alerta":
        return _alerta(job, seed)
    if kind == "lista":
        return _lista(job, seed)
    if kind == "dica":
        return _dica(job, seed)
    raise ValueError(f"tipo de Reels desconhecido: {kind}")


# ---------- conteúdo (roteiro do agente) ----------

def _txt(v, n: int) -> str:
    s = re.sub(r"\s+", " ", str(v or "")).strip()
    if len(s) > n:  # texto de tela longo demais: corta na última palavra inteira (a fala continua completa)
        s = s[: n + 1].rsplit(" ", 1)[0].rstrip(",;:")
    return s


def _conteudo(job: dict, seed: int) -> dict:
    r = job["roteiro"]
    if isinstance(r, str):
        r = json.loads(r)
    scenes = []
    # quem é a protagonista: fala com a voz do vídeo; a outra personagem fala com a outra voz
    elenco = [str(x).lower() for x in (r.get("elenco") or []) if str(x).lower() in ELENCO]
    for c in r.get("cenas", []):
        for p in c.get("personagens") or []:
            if str(p).lower() in ELENCO and str(p).lower() not in elenco:
                elenco.append(str(p).lower())
    principal = elenco[0] if elenco else None
    for c in r.get("cenas", []):
        t = c.get("tipo")
        if t == "cta":
            continue
        if t not in CONTENT_TYPES:
            raise ValueError(f"cena desconhecida: {t}")
        raw = [x for x in (c.get("fala") or []) if (x.get("texto") if isinstance(x, dict) else str(x)).strip()]
        if not raw:
            raise ValueError(f"cena {t} sem fala")
        lines, falas = [], []
        for x in raw:
            if isinstance(x, dict):
                quem = str(x.get("quem") or "").lower() or None
                if quem and quem not in ELENCO:
                    raise ValueError(f"personagem desconhecida: {quem}")
                ln = L(x["texto"])
                if quem and quem != principal:
                    ln["voz"] = "outra"
                lines.append(ln)
                f = {"quem": quem}
                if x.get("emocao") in EMOCOES:
                    f["emocao"] = x["emocao"]
                if x.get("reacao") in EMOCOES:
                    f["reacao"] = x["reacao"]
                falas.append(f)
            else:
                lines.append(L(x))
                falas.append({})
        sc: dict = {"type": t, "lines": lines}
        if t == "gancho":
            sc.update(kicker=_txt(c.get("kicker"), 24) or None, titulo=_txt(c["titulo"], 80), destaque=_txt(c.get("destaque"), 30) or None)
        elif t == "numero":
            sc.update(numero=_txt(c["numero"], 9), rotulo=_txt(c["rotulo"], 70), kicker=_txt(c.get("kicker"), 24) or None)
        elif t == "lista":
            sc.update(titulo=_txt(c["titulo"], 60), itens=[_txt(x, 40) for x in c["itens"][:4]], kicker=_txt(c.get("kicker"), 24) or None)
        elif t == "mito_verdade":
            sc.update(mito=_txt(c["mito"], 70), verdade=_txt(c["verdade"], 80))
        elif t == "passos":
            sc.update(titulo=_txt(c["titulo"], 50), passos=[_txt(x, 44) for x in c["passos"][:4]])
        elif t == "comparacao":
            def side(d):
                return {"titulo": _txt(d["titulo"], 16), "itens": [_txt(x, 26) for x in d["itens"][:3]]}
            sc.update(titulo=_txt(c.get("titulo"), 50) or None, esquerda=side(c["esquerda"]), direita=side(c["direita"]))
        elif t == "pergunta":
            sc.update(pergunta=_txt(c["pergunta"], 80), opcoes=[_txt(x, 26) for x in c["opcoes"][:3]])
        elif t == "destaque":
            sc.update(antes=_txt(c.get("antes"), 50) or None, destaque=_txt(c["destaque"], 30), depois=_txt(c.get("depois"), 50) or None, kicker=_txt(c.get("kicker"), 24) or None)
        elif t in ("historia", "chat"):
            pers = [str(p).lower() for p in (c.get("personagens") or [])][:2]
            if not pers or any(p not in ELENCO for p in pers):
                raise ValueError(f"cena {t}: personagens devem ser do elenco {sorted(ELENCO)}")
            # a protagonista fica sempre à esquerda (ou é "eu" na conversa)
            if principal in pers:
                pers.remove(principal); pers.insert(0, principal)
            sc.update(personagens=pers, falas=falas)
            if t == "historia":
                if c.get("lugar") in LUGARES:
                    sc["lugar"] = c["lugar"]
                ini = {k.lower(): v for k, v in (c.get("inicio") or {}).items() if v in EMOCOES}
                if ini:
                    sc["inicio"] = ini
                nomes = {k.lower(): _txt(v, 14) for k, v in (c.get("nomes") or r.get("nomes") or {}).items()}
                if nomes:
                    sc["nomes"] = nomes
            elif c.get("contato"):
                sc["contato"] = _txt(c["contato"], 18)
        elif t == "tela":
            itens = []
            for it in (c.get("itens") or [])[:4]:
                itens.append({"rotulo": _txt(it["rotulo"], 22), "valor": _txt(it["valor"], 14), **({"riscado": True} if it.get("riscado") else {}), **({"alerta": True} if it.get("alerta") else {})})
            if not itens:
                raise ValueError("cena tela sem itens")
            sc.update(titulo=_txt(c.get("titulo") or "Carrinho", 24), itens=itens, total=_txt(c.get("total"), 14) or None, carimbo=_txt(c.get("carimbo"), 16) or None)
        scenes.append(sc)
    if not scenes or scenes[0]["type"] != "gancho":
        raise ValueError("o roteiro precisa começar com um gancho")
    scenes.append(cta(seed, salvar=True))
    tags = S._hashtags(r.get("hashtags"), "#achadinhos #reels")
    cap = (r.get("legenda") or r.get("titulo") or "").strip()
    if "#" not in cap:
        cap += "\n\n" + tags
    return {"kind": "conteudo", "scenes": scenes, "caption": cap, "hashtags": tags, "title": r.get("titulo") or scenes[0]["titulo"], "mood": r.get("clima") or "animada"}


# ---------- ofertas ----------

def _alerta(job: dict, seed: int) -> dict:
    o = job["offers"][0]
    name = S.short_name(o["title"])
    price = float(o["price"])
    orig = float(o["original"]) if o.get("original") else None
    off = S.pct_off(price, orig)
    badges = S.badges_of(o)
    hook = S.pick(["Alerta de preço!", "Para tudo!", "Caiu o preço!"], seed) if off >= 5 else S.pick(["Achadinho do dia!", "Olha esse achado!"], seed)
    scenes = [{"type": "produto", "kicker": "Alerta de preço" if off >= 5 else "Achadinho do dia", "nome": name, "imagem": o["image"], "desconto": off or None,
               "lines": [L(hook), L(f"{name} com {off}% de desconto." if off >= 5 else f"{name}.")]},
              {"type": "preco", "nome": name, "imagem": o["image"], "de": S.money_text(orig) if off >= 5 else None, "por": S.money_text(price), "desconto": off or None,
               "lines": [L(f"Saiu de {S.money_text(orig)}"), L(f"por {S.money_text(price)}.")] if off >= 5 else [L(f"Tá saindo por {S.money_text(price)}.")]}]
    if badges:
        spoken = [b[1] for b in badges[:3]]
        say = "Tem " + (", ".join(spoken[:-1]) + " e " + spoken[-1] if len(spoken) > 1 else spoken[0]) + "."
        scenes.append({"type": "prova", "imagem": o["image"], "selos": [b[0] for b in badges[:3]], "lines": [L(", ".join(b[0] for b in badges[:3]) + ".", say)]})
    scenes.append(cta(seed, oferta=o["id"]))
    badge_txt = " · ".join(b[0] for b in badges[:4])
    cap = [f"🚨 {o['title']}", "", f"De {S.money_text(orig)} por {S.money_text(price)} (-{off}%)" if off >= 5 else f"Por {S.money_text(price)}"]
    if badge_txt:
        cap.append(f"✔ {badge_txt}")
    cap += ["", f"🔗 Link na bio → oferta #{o['id']}", "Curte e segue a @factorofertas: achado novo todo dia.", "Preço e estoque podem mudar a qualquer momento."]
    tags = S._hashtags(o.get("hashtags"), "#achadinhos #ofertas #reels")
    return {"kind": "alerta", "scenes": scenes, "caption": "\n".join(cap) + "\n\n" + tags, "hashtags": tags, "title": f"Alerta: {name}", "mood": "urgente"}


def _lista(job: dict, seed: int) -> dict:
    offers = job["offers"]
    n = len(offers)
    niches = {o.get("niche_label") for o in offers if o.get("niche_label")}
    niche = next(iter(niches)) if len(niches) == 1 else None
    top = max(float(o["price"]) for o in offers)
    limit = next((v for v in (50, 100, 150, 200, 300, 500) if top <= v), None)
    title = f"{n} achados de {niche.lower()}" if niche and niche.lower() not in ("achadinho", "em alta") else f"{n} achadinhos do dia"
    sub = f"até {S.money_text(limit).replace(',00', '')}" if limit else "com desconto"
    scenes = [{"type": "produtos", "kicker": "Lista do dia", "titulo": title.capitalize(), "sub": sub, "imagens": [o["image"] for o in offers[:3]],
               "lines": [L(f"{title.capitalize()} {sub}"), L(S.pick(["que valem a pena.", "pra você não perder.", "que eu separei hoje."], seed))]}]
    ordinals = ["Primeiro", "Segundo", "Terceiro", "Quarto", "Quinto"]
    for i, o in enumerate(offers):
        name = S.short_name(o["title"])
        off = S.pct_off(float(o["price"]), float(o["original"]) if o.get("original") else None)
        scenes.append({"type": "item", "indice": i + 1, "total": n, "nome": name, "imagem": o["image"], "por": S.money_text(float(o["price"])), "desconto": off or None,
                       "lines": [L(f"{ordinals[i]}: {name}."), L(f"Por {S.money_text(float(o['price']))}" + (f", {off}% mais barato." if off >= 10 else "."))]})
    scenes.append(cta(seed, ofertas=[o["id"] for o in offers]))
    cap = [f"🛒 {title.capitalize()} {sub}", ""] + [f"{i + 1}. {S.short_name(o['title'], 6, 48)} · {S.money_text(float(o['price']))} → oferta #{o['id']}" for i, o in enumerate(offers)]
    cap += ["", "🔗 Todos os links na bio, pelo número da oferta.", "Curte e segue a @factorofertas: achado novo todo dia.", "Preço e estoque podem mudar a qualquer momento."]
    tags = S._hashtags(offers[0].get("hashtags"), "#achadinhos #ofertas #reels")
    return {"kind": "lista", "scenes": scenes, "caption": "\n".join(cap) + "\n\n" + tags, "hashtags": tags, "title": title.capitalize(), "mood": "animada"}


def _dica(job: dict, seed: int) -> dict:
    c = job["content"]
    slides = (c.get("slides") or [])[:4]
    if not slides:
        raise ValueError("conteúdo sem slides")
    first = slides[0]
    head = first.get("headline") or c["title"]
    scenes = [{"type": "gancho", "kicker": (first.get("kicker") or "Dica")[:24], "titulo": head[:80], "destaque": None, "lines": [L(x) for x in S._sentences(head)]}]
    for s in (slides[1:] or [first]):
        items = [x for x in S._bullets(s.get("body") or "") if len(x) <= 40][:3]
        if len(items) < 2:
            sent = re.split(r"(?<=[.!?])\s+", (s.get("body") or "").strip())[0]
            items = [sent] if sent and len(sent) <= 40 else []
        if not items:
            sent = re.split(r"(?<=[.!?])\s+", (s.get("body") or "").strip())[0]
            scenes.append({"type": "destaque", "kicker": (s.get("kicker") or "")[:24] or None, "antes": None, "destaque": (s.get("headline") or "")[:30], "depois": None,
                           "lines": [L(x) for x in S._sentences(s.get("headline") or "") + S._sentences(sent)[:2]]})
            continue
        scenes.append({"type": "lista", "kicker": (s.get("kicker") or "")[:24] or None, "titulo": (s.get("headline") or "")[:60], "itens": items,
                       "lines": [L(x) for x in S._sentences(s.get("headline") or "")[:1] + items]})
    scenes.append(cta(seed, salvar=True))
    cap = (c.get("caption") or c["title"]).strip()
    tags = S._hashtags(c.get("hashtags"), "#dicas #achadinhos #reels")
    if "#" not in cap:
        cap += "\n\n" + tags
    return {"kind": "dica", "scenes": scenes, "caption": cap, "hashtags": tags, "title": c["title"], "mood": "animada"}


# ---------- legenda em páginas ----------

def caption_pages(timeline: dict, max_chars: int = 20, max_words: int = 4) -> list[dict]:
    """Uma linha por vez. "R$" fica colado no valor; nenhuma página termina com uma palavra sozinha."""
    pages = []
    for sc in timeline["scenes"]:
        for ln in sc["lines"]:
            toks = tts.caption_tokens(ln["text"])
            if not toks:
                continue
            if ln.get("words") and len(ln["words"]) == len(toks):
                # tempo real de cada palavra, ouvido pelo Whisper
                words = [dict(w) for w in ln["words"]]
            else:
                weights = [len(re.sub(r"[^\wÀ-ú%$]", "", t)) + 2 for t in toks]
                total, acc, words = sum(weights), 0, []
                for t, wgt in zip(toks, weights):
                    s = ln["start"] + acc / total * (ln["end"] - ln["start"])
                    acc += wgt
                    words.append({"text": t, "start": round(s, 3), "end": round(ln["start"] + acc / total * (ln["end"] - ln["start"]), 3)})
            # páginas equilibradas: divide a fala em n partes parecidas (nada de palavra sozinha no fim)
            full = len(" ".join(w["text"] for w in words))
            n = max(1, -(-full // max_chars), -(-len(words) // max_words))
            target = full / n
            groups, cur = [], []
            for w in words:
                cur_len = len(" ".join(x["text"] for x in cur))
                if cur and len(groups) < n - 1 and cur_len + 1 + len(w["text"]) / 2 > target:
                    groups.append(cur)
                    cur = []
                cur.append(w)
            if cur:
                groups.append(cur)
            for gi, g in enumerate(groups):
                # a página aparece um instante antes da primeira palavra (o olho chega antes do ouvido)
                start = max(ln["start"], g[0]["start"] - 0.08) if gi == 0 else g[0]["start"] - 0.04
                end = groups[gi + 1][0]["start"] - 0.04 if gi < len(groups) - 1 else ln["end"] + 0.12
                pages.append({"start": round(start, 3), "end": round(end, 3), "words": g})
    return pages


def props(plan: dict, timeline: dict, audio_rel: str) -> dict:
    scenes = []
    for sc, tl in zip(plan["scenes"], timeline["scenes"]):
        d = {k: v for k, v in sc.items() if k != "lines"}
        d.update(start=tl["start"], end=tl["end"], lines=[{k: x[k] for k in ("text", "start", "end", "voz", "words") if k in x} for x in tl["lines"]])
        scenes.append(d)
    return {"scenes": scenes, "pages": caption_pages(timeline), "audio": audio_rel, "duration": timeline["duration"], "handle": HANDLE,
            "cover": round(min(1.6, timeline["duration"] / 3), 2)}
