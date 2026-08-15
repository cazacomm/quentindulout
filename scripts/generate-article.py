#!/usr/bin/env python3
"""
generate-article.py — génération et publication automatique d'un article de blog.

Principe : le gabarit HTML n'est jamais dupliqué dans ce script. Il est relu à
chaque exécution depuis un article existant du site (`template_article` dans
blog-config.json), puis ses zones variables sont remplacées. Toute évolution du
design du blog est donc reprise automatiquement par les articles suivants.

Enchaînement :
  1. lecture de blog-config.json
  2. extraction des sujets de BLOG_WORKFLOW.md (section « Douze sujets »)
  3. scan de /blog/*/index.html pour lister ce qui est déjà publié
  4. choix du premier sujet non traité, dans l'ordre de la liste
  5. appel OpenAI (JSON strict) puis contrôles éditoriaux
  6. écriture de /blog/<slug>/index.html + mise à jour de
     /blog/index.html, sitemap.xml, rss.xml et llms.txt

Codes de sortie : 0 succès · 1 erreur · 78 aucun nouveau sujet à traiter.

Options :
  --dry-run   n'écrit aucun fichier, affiche ce qui serait produit
  --mock      n'appelle pas l'API, utilise une charge utile de test
              (permet de valider toute la chaîne hors ligne)
  --topic N   force le numéro de sujet à traiter
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "blog-config.json"
WORKFLOW_PATH = ROOT / "BLOG_WORKFLOW.md"
BLOG_DIR = ROOT / "blog"
BLOG_INDEX = BLOG_DIR / "index.html"
SITEMAP = ROOT / "sitemap.xml"
RSS = ROOT / "rss.xml"
LLMS = ROOT / "llms.txt"

EXIT_OK, EXIT_ERROR, EXIT_NO_TOPIC = 0, 1, 78

MONTHS_FR = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]
DAYS_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MONTHS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def log(msg: str) -> None:
    print(f"[blog-auto] {msg}", flush=True)


def fail(msg: str) -> None:
    print(f"[blog-auto] ERREUR — {msg}", file=sys.stderr, flush=True)
    sys.exit(EXIT_ERROR)


# --------------------------------------------------------------------------
# Configuration et sujets
# --------------------------------------------------------------------------

@dataclass
class Topic:
    number: int
    title: str
    angle: str
    slug: str


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        fail(f"blog-config.json introuvable ({CONFIG_PATH})")
    try:
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"blog-config.json illisible : {exc}")
    for key in ("site_name", "site_url", "author", "template_article"):
        if not cfg.get(key):
            fail(f"clé « {key} » manquante dans blog-config.json")
    cfg["site_url"] = cfg["site_url"].rstrip("/")
    return cfg


def parse_topics() -> list[Topic]:
    """Extrait les sujets de la section « Douze sujets » de BLOG_WORKFLOW.md."""
    if not WORKFLOW_PATH.exists():
        fail(f"BLOG_WORKFLOW.md introuvable ({WORKFLOW_PATH})")
    md = WORKFLOW_PATH.read_text(encoding="utf-8")

    # On borne la recherche à la section des sujets : les autres listes
    # numérotées du document (règles éditoriales) ne doivent pas être captées.
    start = re.search(r"^##\s*\d+\.\s*Douze sujets.*$", md, re.M)
    if not start:
        fail("section « Douze sujets » absente de BLOG_WORKFLOW.md")
    rest = md[start.end():]
    end = re.search(r"^##\s", rest, re.M)
    section = rest[: end.start()] if end else rest

    pattern = re.compile(
        r"^(\d+)\.\s+\*\*(.+?)\*\*\s*\n(.*?)Slug\s*:\s*`([^`]+)`",
        re.S | re.M,
    )
    topics = [
        Topic(
            number=int(m.group(1)),
            title=m.group(2).strip(),
            angle=" ".join(m.group(3).split()),
            slug=m.group(4).strip(),
        )
        for m in pattern.finditer(section)
    ]
    if not topics:
        fail("aucun sujet exploitable dans BLOG_WORKFLOW.md")
    log(f"{len(topics)} sujets lus dans BLOG_WORKFLOW.md")
    return topics


def scan_published(site_slug: str) -> tuple[set[str], set[int]]:
    """Renvoie (slugs publiés, numéros de sujets déjà traités)."""
    slugs: set[str] = set()
    numbers: set[int] = set()
    marker = re.compile(rf"<!--\s*{re.escape(site_slug)}-topic:\s*(\d+)\s*-->")
    for page in sorted(BLOG_DIR.glob("*/index.html")):
        slugs.add(page.parent.name)
        hit = marker.search(page.read_text(encoding="utf-8"))
        if hit:
            numbers.add(int(hit.group(1)))
    log(f"{len(slugs)} article(s) déjà publié(s) : {', '.join(sorted(slugs)) or '—'}")
    if numbers:
        log(f"sujets déjà traités (marqueur) : {sorted(numbers)}")
    return slugs, numbers


def pick_topic(topics: list[Topic], slugs: set[str], numbers: set[int],
               forced: int | None) -> Topic | None:
    if forced is not None:
        for topic in topics:
            if topic.number == forced:
                return topic
        fail(f"sujet n°{forced} absent de la liste")
    for topic in topics:
        if topic.number in numbers or topic.slug in slugs:
            continue
        return topic
    return None


# --------------------------------------------------------------------------
# Génération du contenu
# --------------------------------------------------------------------------

def build_prompt(cfg: dict, topic: Topic) -> tuple[str, str]:
    geo = ", ".join(cfg.get("geo_keywords", []))
    words = cfg.get("target_word_count", 1300)
    n_faq = cfg.get("faq_questions_count", 5)

    system = (
        f"Tu es {cfg['author']}, {cfg.get('author_role', 'professionnel')} basé à "
        f"{cfg['location']}. Tu rédiges en français les articles du blog de "
        f"{cfg['site_name']}. Secteur : {cfg['sector']}. "
        f"Ton : {cfg.get('tone', 'expert-conseil, factuel')}. "
        "Tu écris à la première personne du singulier quand tu parles de ton "
        "accompagnement, et tu t'adresses au lecteur en « vous »."
    )

    user = f"""Rédige un article de blog complet sur ce sujet.

TITRE DE TRAVAIL : {topic.title}
ANGLE ATTENDU : {topic.angle}

RÈGLES ÉDITORIALES ABSOLUES — toute infraction rend l'article inutilisable :
- Aucun chiffre inventé : pas de tarif, pas de taux, pas de pourcentage, pas de
  montant, pas de plafond de garantie, pas de statistique, pas de prix en euros.
- Aucune référence réglementaire précise : pas de numéro d'article de loi, pas de
  date de texte, pas de nom de loi cité de mémoire. On décrit un principe général.
- Aucun nom de client, aucun cas réel identifiable, aucun témoignage.
- Aucune comparaison nominative entre assureurs ou compagnies.
- Aucune promesse de résultat, aucune date de fondation, aucun chiffre d'affaires.
- On renvoie toujours vers un échange personnalisé plutôt que vers une certitude.

ANCRAGE LOCAL OBLIGATOIRE : la ville principale ({cfg['location']}) doit apparaître
dans le titre, dans le chapô et dans au moins deux sections. Utilise naturellement
des lieux de la zone quand c'est pertinent : {geo}. Ne leur invente aucune
caractéristique chiffrée.

STRUCTURE DEMANDÉE :
- {words} mots environ pour le corps (hors FAQ), avec une tolérance de 15 %.
- 4 à 6 sections <h2>, chacune pouvant contenir des <h3>.
- Au moins une liste <ul> avec des <li> dont l'idée-clé est en <strong>.
- Exactement un encadré conseil, au format :
  <div class="callout"><p><strong>Le réflexe utile :</strong> ...</p></div>
- {n_faq} questions de FAQ, formulées comme une vraie recherche tapée dans Google,
  avec des réponses de 3 à 5 phrases, autonomes et directement utiles.

FORMAT DE SORTIE : un objet JSON strict, sans texte autour, avec ces clés :
{{
  "title": "titre final de l'article, 60 à 95 caractères, ville incluse",
  "meta_description": "150 caractères MAXIMUM, une promesse concrète, ville incluse",
  "excerpt": "2 phrases de résumé pour la carte de la page blog (280 caractères max)",
  "tag": "catégorie en 1 à 2 mots (ex : Habitation, Auto, Prévoyance, Épargne, Pro)",
  "reading_minutes": 7,
  "body_html": "le corps de l'article en HTML : uniquement des balises <p>, <h2>, <h3>, <ul>, <li>, <strong>, <em> et le <div class=\\"callout\\">. Pas de <h1>, pas de <section>, pas d'attribut style, pas de lien externe.",
  "faq": [{{"question": "...", "answer": "..."}}]
}}

Le champ body_html commence directement par le chapô en <p> (2 paragraphes), sans
titre de niveau 1 et sans reprendre le titre de l'article."""
    return system, user


MOCK_PAYLOAD = {
    "title": "Assurance auto à Tarbes : tiers, tiers étendu ou tous risques ?",
    "meta_description": "Tiers, tiers étendu ou tous risques à Tarbes : les critères pour choisir sans payer une garantie qui ne vous servira jamais.",
    "excerpt": "Trois formules, trois logiques. Comment arbitrer selon l'âge de votre véhicule, vos trajets et votre capacité à encaisser un sinistre, à Tarbes et dans les Hautes-Pyrénées.",
    "tag": "Auto",
    "reading_minutes": 7,
    "body_html": (
        "<p>Chapô de test hors ligne pour valider la chaîne de publication à Tarbes.</p>"
        "<p>Second paragraphe du chapô, sans appel au modèle.</p>"
        "<h2>Une première section</h2><p>Texte de démonstration.</p>"
        "<ul><li><strong>Un point clé.</strong> Son explication.</li></ul>"
        "<div class=\"callout\"><p><strong>Le réflexe utile :</strong> relire ses conditions particulières.</p></div>"
        "<h2>Une seconde section</h2><h3>Un sous-cas</h3><p>Texte de démonstration.</p>"
    ),
    "faq": [
        {"question": f"Question de test n°{i} ?", "answer": "Réponse de test hors ligne, sans appel au modèle."}
        for i in range(1, 6)
    ],
}


def call_openai(cfg: dict, topic: Topic, attempt_note: str = "") -> dict:
    try:
        from openai import OpenAI
    except ImportError:
        fail("paquet « openai » absent — pip install openai")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        fail("variable d'environnement OPENAI_API_KEY absente")

    system, user = build_prompt(cfg, topic)
    if attempt_note:
        user += f"\n\nCORRECTION DEMANDÉE : {attempt_note}"

    client = OpenAI(api_key=api_key)
    log(f"appel OpenAI ({cfg.get('model', 'gpt-4o-mini')}, temperature "
        f"{cfg.get('temperature', 0.7)})…")
    try:
        resp = client.chat.completions.create(
            model=cfg.get("model", "gpt-4o-mini"),
            temperature=cfg.get("temperature", 0.7),
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
    except Exception as exc:  # réseau, quota, auth, filtrage…
        fail(f"appel OpenAI échoué : {type(exc).__name__} — {exc}")

    raw = resp.choices[0].message.content or ""
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        fail(f"réponse OpenAI non parsable en JSON : {exc}")


def text_of(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def word_count(html: str) -> int:
    return len([w for w in text_of(html).split() if any(c.isalnum() for c in w)])


def validate(payload: dict, cfg: dict) -> list[str]:
    """Contrôles éditoriaux. Renvoie la liste des problèmes bloquants."""
    problems: list[str] = []
    required = ("title", "meta_description", "excerpt", "tag", "body_html", "faq")
    for key in required:
        if not payload.get(key):
            problems.append(f"clé « {key} » manquante ou vide")
    if problems:
        return problems

    n_faq = cfg.get("faq_questions_count", 5)
    faq = payload["faq"]
    if not isinstance(faq, list) or len(faq) != n_faq:
        problems.append(f"la FAQ doit contenir exactement {n_faq} questions "
                        f"(reçu : {len(faq) if isinstance(faq, list) else 'format invalide'})")
    else:
        for i, item in enumerate(faq, 1):
            if not isinstance(item, dict) or not item.get("question") or not item.get("answer"):
                problems.append(f"question de FAQ n°{i} incomplète")

    if len(payload["meta_description"]) > 155:
        problems.append(f"meta description trop longue "
                        f"({len(payload['meta_description'])} caractères, 155 maximum)")

    body = payload["body_html"]
    words = word_count(body)
    target = cfg.get("target_word_count", 1300)
    if not (target * 0.7 <= words <= target * 1.35):
        problems.append(f"corps hors cible : {words} mots (visé : {target})")

    if "<h1" in body.lower():
        problems.append("le corps contient un <h1>, réservé au titre de la page")
    if len(re.findall(r"<h2", body, re.I)) < 3:
        problems.append("moins de 3 sections <h2>")

    # Règle 5 de BLOG_WORKFLOW.md : ni chiffre inventé, ni référence réglementaire.
    haystack = " ".join([text_of(body), payload["title"], payload["meta_description"]]
                        + [f"{q.get('question','')} {q.get('answer','')}"
                           for q in faq if isinstance(q, dict)])
    forbidden = [
        (r"\d[\d\s.,]*\s*(?:€|euros?)", "montant en euros"),
        (r"\d[\d.,]*\s*%", "pourcentage"),
        (r"\bloi\s+n[°o]", "référence de loi numérotée"),
        (r"\barticle\s+[LRD]\.?\s*\d", "article de code cité"),
        (r"\bloi\s+(?:du|de)\s+\d", "loi datée"),
        (r"\bdécret\s+n?[°o]?\s*\d", "décret cité"),
    ]
    for pattern, label in forbidden:
        hit = re.search(pattern, haystack, re.I)
        if hit:
            problems.append(f"contenu interdit ({label}) : « {hit.group(0).strip()} »")
    return problems


def generate(cfg: dict, topic: Topic, mock: bool) -> dict:
    if mock:
        log("mode --mock : aucune requête OpenAI, charge utile de test")
        payload = json.loads(json.dumps(MOCK_PAYLOAD))
        payload["title"] = topic.title
        return payload

    payload = call_openai(cfg, topic)
    problems = validate(payload, cfg)
    if problems:
        log("contrôles échoués au 1er essai : " + " | ".join(problems))
        log("nouvelle tentative avec consignes correctives…")
        payload = call_openai(cfg, topic, attempt_note=" ; ".join(problems))
        problems = validate(payload, cfg)
        if problems:
            fail("contenu refusé après 2 tentatives : " + " | ".join(problems))
    log(f"contenu validé — {word_count(payload['body_html'])} mots, "
        f"{len(payload['faq'])} questions de FAQ")
    return payload


# --------------------------------------------------------------------------
# Assemblage HTML à partir du gabarit existant
# --------------------------------------------------------------------------

def esc(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))


def slugify(text: str) -> str:
    norm = unicodedata.normalize("NFKD", text)
    norm = "".join(c for c in norm if not unicodedata.combining(c))
    norm = re.sub(r"[^a-zA-Z0-9]+", "-", norm).strip("-").lower()
    return re.sub(r"-{2,}", "-", norm)


def date_fr(day: dt.date) -> str:
    return f"{day.day} {MONTHS_FR[day.month - 1]} {day.year}"


def date_rfc822(day: dt.date, cfg: dict) -> str:
    hour = cfg.get("publish_hour_local", "09:00:00")
    offset = cfg.get("publish_tz_offset", "+02:00").replace(":", "")
    return (f"{DAYS_EN[day.weekday()]}, {day.day:02d} {MONTHS_EN[day.month - 1]} "
            f"{day.year} {hour} {offset}")


def replace_attr(html: str, pattern: str, value: str) -> str:
    """Remplace la valeur capturée par le groupe 1 du motif."""
    def sub(match: re.Match) -> str:
        return match.group(0).replace(match.group(1), value, 1)
    new_html, count = re.subn(pattern, sub, html, count=1)
    if count == 0:
        fail(f"motif introuvable dans le gabarit : {pattern}")
    return new_html


def build_article_html(template: str, payload: dict, topic: Topic,
                       cfg: dict, slug: str, day: dt.date) -> str:
    base = cfg["site_url"]
    url = f"{base}/blog/{slug}/"
    iso = day.isoformat()
    title = payload["title"]
    desc = payload["meta_description"]
    html = template

    # --- <head> : titre, métadonnées, canonical, Open Graph, Twitter ---
    html = replace_attr(html, r"<title>(.*?)</title>", esc(title))
    html = replace_attr(html, r'<meta name="description" content="(.*?)"', esc(desc))
    html = replace_attr(html, r'<link rel="canonical" href="(.*?)"', url)
    html = replace_attr(html, r'<meta property="og:title" content="(.*?)"', esc(title))
    html = replace_attr(html, r'<meta property="og:description" content="(.*?)"', esc(desc))
    html = replace_attr(html, r'<meta property="og:url" content="(.*?)"', url)
    html = replace_attr(html, r'<meta property="article:published_time" content="(.*?)"', iso)
    html = replace_attr(html, r'<meta name="twitter:title" content="(.*?)"', esc(title))
    html = replace_attr(html, r'<meta name="twitter:description" content="(.*?)"', esc(desc))

    # --- Blocs JSON-LD : on repart des blocs du gabarit et on mute les champs ---
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
    if len(blocks) < 3:
        fail("le gabarit ne contient pas les 3 blocs JSON-LD attendus")

    rebuilt: list[str] = []
    for block in blocks:
        try:
            data = json.loads(block)
        except json.JSONDecodeError as exc:
            fail(f"JSON-LD du gabarit illisible : {exc}")
        kind = data.get("@type")
        if kind == "Article":
            data["@id"] = f"{url}#article"
            data["headline"] = title
            data["description"] = desc
            data["datePublished"] = iso
            data["dateModified"] = iso
            data["articleSection"] = payload["tag"]
            data["mainEntityOfPage"] = {"@type": "WebPage", "@id": url}
            data["keywords"] = ", ".join(
                [topic.slug.replace("-", " ")] + cfg.get("geo_keywords", [])[:4]
            )
            data["about"] = [
                {"@type": "Thing", "name": payload["tag"]},
                {"@type": "Place", "name": cfg["location"].split(",")[0].strip()},
            ]
        elif kind == "BreadcrumbList":
            for item in data.get("itemListElement", []):
                if item.get("position") == 3:
                    item["name"] = title
                    item["item"] = url
        elif kind == "FAQPage":
            data["mainEntity"] = [
                {
                    "@type": "Question",
                    "name": q["question"],
                    "acceptedAnswer": {"@type": "Answer", "text": q["answer"]},
                }
                for q in payload["faq"]
            ]
        rebuilt.append(json.dumps(data, ensure_ascii=False, indent=2))

    counter = {"i": 0}

    def swap_jsonld(match: re.Match) -> str:
        body = rebuilt[counter["i"]]
        counter["i"] += 1
        indented = "\n".join("  " + line for line in body.splitlines())
        return f'<script type="application/ld+json">\n{indented}\n  </script>'

    html = re.sub(r'<script type="application/ld\+json">.*?</script>',
                  swap_jsonld, html, count=len(rebuilt), flags=re.S)

    # --- Fil d'Ariane visible : version courte du titre, comme sur le gabarit ---
    crumb = title.split(" : ")[0].split(" ? ")[0].strip()
    if len(crumb) > 60:
        crumb = crumb[:57].rsplit(" ", 1)[0] + "…"
    html = replace_attr(html, r'<li><span aria-current="page">(.*?)</span></li>',
                        esc(crumb))

    # --- Corps de l'article ---
    article = re.search(r'(<article class="article">)(.*?)(</article>)', html, re.S)
    if not article:
        fail("bloc <article class=\"article\"> introuvable dans le gabarit")
    inner = article.group(2)

    # Le pied de l'article (CTA, avertissement, retour au blog) est repris tel
    # quel depuis le gabarit : il est générique et ne dépend pas du sujet.
    tail_start = inner.find('<div class="postCta">')
    if tail_start == -1:
        fail("bloc <div class=\"postCta\"> introuvable dans le gabarit")
    tail = inner[tail_start:].rstrip()

    faq_items = "\n\n".join(
        "          <div class=\"faqItem\">\n"
        f"            <h3>{esc(q['question'])}</h3>\n"
        f"            <p>{esc(q['answer'])}</p>\n"
        "          </div>"
        for q in payload["faq"]
    )

    body = "\n".join("        " + line.strip()
                     for line in re.sub(r">\s*<", ">\n<", payload["body_html"]).splitlines()
                     if line.strip())

    marker = f'<!-- {cfg.get("site_slug", "site")}-topic: {topic.number} -->'
    new_inner = f"""
        {marker}
        <h1>{esc(title)}</h1>

        <div class="articleMeta">
          <span>Par <strong>{esc(cfg['author'])}</strong>, {esc(cfg.get('author_role', ''))}</span>
          <span class="sep" aria-hidden="true">·</span>
          <time datetime="{iso}">{date_fr(day)}</time>
          <span class="sep" aria-hidden="true">·</span>
          <span>Lecture {int(payload.get('reading_minutes') or 7)} min</span>
        </div>

{body}

        <hr>

        <h2>Questions fréquentes</h2>

        <section class="faq" aria-label="Questions fréquentes">
{faq_items}
        </section>

        {tail}
      """
    html = html[: article.start(2)] + new_inner + html[article.end(2):]
    return html


# --------------------------------------------------------------------------
# Mises à jour des pages d'index
# --------------------------------------------------------------------------

def update_blog_index(payload: dict, cfg: dict, slug: str, day: dt.date) -> str:
    html = BLOG_INDEX.read_text(encoding="utf-8")
    url_path = f"/blog/{slug}/"
    if url_path in html:
        log("carte déjà présente dans /blog/index.html — pas de doublon inséré")
        return html

    card = f"""
        <a class="postCard reveal" href="{url_path}">
          <div class="postMeta">
            <span class="postTag">{esc(payload['tag'])}</span>
            <time datetime="{day.isoformat()}">{date_fr(day)}</time>
            <span aria-hidden="true">·</span>
            <span>Lecture {int(payload.get('reading_minutes') or 7)} min</span>
          </div>
          <h2>{esc(payload['title'])}</h2>
          <p>{esc(payload['excerpt'])}</p>
          <span class="postMore">Lire l'article →</span>
        </a>
"""
    anchor = '<div class="postGrid">'
    if anchor not in html:
        fail("conteneur .postGrid introuvable dans /blog/index.html")
    html = html.replace(anchor, anchor + card, 1)

    # JSON-LD Blog : nouvel article en tête de blogPost.
    def add_post(match: re.Match) -> str:
        data = json.loads(match.group(1))
        if data.get("@type") != "Blog":
            return match.group(0)
        entry = {
            "@type": "BlogPosting",
            "headline": payload["title"],
            "url": f"{cfg['site_url']}{url_path}",
            "datePublished": day.isoformat(),
            "author": {"@type": "Person", "name": cfg["author"]},
        }
        data.setdefault("blogPost", []).insert(0, entry)
        body = json.dumps(data, ensure_ascii=False, indent=2)
        indented = "\n".join("  " + line for line in body.splitlines())
        return f'<script type="application/ld+json">\n{indented}\n  </script>'

    html = re.sub(r'<script type="application/ld\+json">(.*?)</script>',
                  add_post, html, flags=re.S)
    return html


def update_sitemap(cfg: dict, slug: str, day: dt.date) -> str:
    xml = SITEMAP.read_text(encoding="utf-8")
    loc = f"{cfg['site_url']}/blog/{slug}/"
    iso = day.isoformat()
    if loc in xml:
        log("URL déjà présente dans sitemap.xml")
    else:
        entry = (f"  <url>\n    <loc>{loc}</loc>\n    <lastmod>{iso}</lastmod>\n"
                 f"    <changefreq>monthly</changefreq>\n    <priority>0.7</priority>\n  </url>\n")
        xml = xml.replace("</urlset>", entry + "</urlset>", 1)

    # lastmod rafraîchi pour l'accueil et la page blog.
    for path in ("/", "/blog/"):
        target = f"{cfg['site_url']}{path}"
        xml = re.sub(
            rf"(<loc>{re.escape(target)}</loc>\s*<lastmod>)[^<]*(</lastmod>)",
            rf"\g<1>{iso}\g<2>", xml, count=1)
    return xml


def update_rss(payload: dict, cfg: dict, slug: str, day: dt.date) -> str:
    xml = RSS.read_text(encoding="utf-8")
    link = f"{cfg['site_url']}/blog/{slug}/"
    if link in xml:
        log("article déjà présent dans rss.xml")
        return xml
    stamp = date_rfc822(day, cfg)
    item = f"""    <item>
      <title>{esc(payload['title'])}</title>
      <link>{link}</link>
      <guid isPermaLink="true">{link}</guid>
      <description>{esc(payload['excerpt'])}</description>
      <category>{esc(payload['tag'])}</category>
      <pubDate>{stamp}</pubDate>
    </item>

"""
    xml = re.sub(r"(<lastBuildDate>)[^<]*(</lastBuildDate>)",
                 rf"\g<1>{stamp}\g<2>", xml, count=1)
    if "<item>" in xml:
        xml = xml.replace("    <item>", item + "    <item>", 1)
    else:
        xml = xml.replace("  </channel>", item + "  </channel>", 1)
    return xml


def update_llms(payload: dict, cfg: dict, slug: str, day: dt.date) -> str | None:
    if not LLMS.exists():
        return None
    text = LLMS.read_text(encoding="utf-8")
    url = f"{cfg['site_url']}/blog/{slug}/"
    if url in text:
        log("article déjà présent dans llms.txt")
        return text
    heading = "## Articles du blog"
    if heading not in text:
        log("section « Articles du blog » absente de llms.txt — ignoré")
        return text
    line = (f"\n- [{payload['title']}]({url}) — {date_fr(day)}. "
            f"{text_of(payload['excerpt'])}")
    head, _, rest = text.partition(heading)
    return f"{head}{heading}{line}{rest}"


# --------------------------------------------------------------------------
# Entrée
# --------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Génère et publie un article de blog.")
    parser.add_argument("--dry-run", action="store_true",
                        help="n'écrit aucun fichier, affiche le résultat")
    parser.add_argument("--mock", action="store_true",
                        help="n'appelle pas OpenAI (charge utile de test)")
    parser.add_argument("--topic", type=int, default=None,
                        help="force le numéro de sujet à traiter")
    args = parser.parse_args()

    cfg = load_config()
    log(f"site : {cfg['site_name']} — {cfg['site_url']}")

    topics = parse_topics()
    slugs, numbers = scan_published(cfg.get("site_slug", "site"))
    topic = pick_topic(topics, slugs, numbers, args.topic)
    if topic is None:
        log("aucun sujet non traité dans BLOG_WORKFLOW.md — rien à publier.")
        log("Ajoutez de nouveaux sujets à la section « Douze sujets » pour relancer.")
        return EXIT_NO_TOPIC

    slug = topic.slug or slugify(topic.title)
    target_dir = BLOG_DIR / slug
    target_file = target_dir / "index.html"
    log(f"sujet retenu : n°{topic.number} — {topic.title}")
    log(f"slug : {slug}")

    if target_file.exists():
        log(f"{target_file.relative_to(ROOT)} existe déjà — publication annulée "
            f"(idempotence). Ajoutez le marqueur de sujet ou changez de slug.")
        return EXIT_NO_TOPIC

    template_path = BLOG_DIR / cfg["template_article"] / "index.html"
    if not template_path.exists():
        fail(f"gabarit introuvable : {template_path.relative_to(ROOT)}")
    template = template_path.read_text(encoding="utf-8")
    log(f"gabarit relu depuis {template_path.relative_to(ROOT)} "
        f"({len(template)} caractères)")

    payload = generate(cfg, topic, args.mock)
    day = dt.date.today()
    html = build_article_html(template, payload, topic, cfg, slug, day)

    index_html = update_blog_index(payload, cfg, slug, day)
    sitemap_xml = update_sitemap(cfg, slug, day)
    rss_xml = update_rss(payload, cfg, slug, day)
    llms_txt = update_llms(payload, cfg, slug, day)

    if args.dry_run:
        log("--dry-run : aucun fichier écrit.")
        print("\n" + "=" * 72)
        print(f"TITRE            : {payload['title']}")
        print(f"META DESCRIPTION : {payload['meta_description']} "
              f"({len(payload['meta_description'])} car.)")
        print(f"TAG              : {payload['tag']}")
        print(f"MOTS (corps)     : {word_count(payload['body_html'])}")
        print(f"FAQ              : {len(payload['faq'])} questions")
        print(f"FICHIER PRÉVU    : blog/{slug}/index.html ({len(html)} caractères)")
        print("=" * 72)
        print("\n--- 200 PREMIERS MOTS DU CORPS ---\n")
        print(" ".join(text_of(payload["body_html"]).split()[:200]))
        print("\n--- QUESTIONS DE FAQ ---")
        for q in payload["faq"]:
            print(f"  • {q['question']}")
        print()
        return EXIT_OK

    target_dir.mkdir(parents=True, exist_ok=True)
    target_file.write_text(html, encoding="utf-8")
    BLOG_INDEX.write_text(index_html, encoding="utf-8")
    SITEMAP.write_text(sitemap_xml, encoding="utf-8")
    RSS.write_text(rss_xml, encoding="utf-8")
    if llms_txt is not None:
        LLMS.write_text(llms_txt, encoding="utf-8")

    log(f"écrit : blog/{slug}/index.html")
    log("mis à jour : blog/index.html, sitemap.xml, rss.xml, llms.txt")
    log(f"publication prête — sujet n°{topic.number}")
    return EXIT_OK


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as exc:  # filet de sécurité : jamais de trace brute en CI
        print(f"[blog-auto] ERREUR inattendue — {type(exc).__name__} : {exc}",
              file=sys.stderr)
        sys.exit(EXIT_ERROR)
