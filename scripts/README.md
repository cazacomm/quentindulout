# Automatisation du blog — Quentin Dulout Courtage

Un article de blog est généré et publié automatiquement **chaque lundi à 9h00 UTC**
par le workflow [`.github/workflows/blog-auto.yml`](../.github/workflows/blog-auto.yml).

## 1. Mettre la clé API en place (à faire une seule fois)

1. Créer une clé sur <https://platform.openai.com/api-keys>.
2. Dans le dépôt GitHub : **Settings → Secrets and variables → Actions → New repository secret**.
3. Nom : `OPENAI_API_KEY` — Valeur : la clé (`sk-…`).

En ligne de commande :

```bash
gh secret set OPENAI_API_KEY -R cazacomm/quentindulout
```

Sans ce secret, le workflow échoue proprement (code 1) sans rien committer.

## 2. Lancer manuellement

**Depuis GitHub** : onglet *Actions* → *Blog auto — Quentin Dulout Courtage* → *Run workflow*.
La case **dry_run** génère l'article et affiche le résultat dans les logs **sans rien écrire ni pousser**.

**En local** :

```bash
pip install openai
export OPENAI_API_KEY="sk-..."

python3 scripts/generate-article.py --dry-run   # simulation, aucun fichier touché
python3 scripts/generate-article.py             # génère et écrit (à committer soi-même)
python3 scripts/generate-article.py --mock      # teste la tuyauterie sans appeler l'API
```

`--mock` ne produit **aucun contenu éditorial réel** : il recopie un texte de remplissage
pour vérifier que le choix du sujet, la validation, l'assemblage HTML et les mises à jour
de fichiers fonctionnent.

## 3. Codes de sortie

| Code | Signification | Effet sur le workflow |
|---|---|---|
| `0` | Article généré et validé | commit + push |
| `78` | Aucun sujet restant dans `BLOG_WORKFLOW.md` | arrêt propre, pas de commit |
| `1` | Erreur (API, validation, fichier manquant) | échec visible, **aucun fichier écrit** |

## 4. Ce que fait le script

1. Lit `blog-config.json`. Tout ce qui est propre au site y vit — rien de
   spécifique n'est codé en dur dans le script, ce qui permet de le réutiliser
   tel quel sur un autre site en ne changeant que ce fichier. **18 clés sont
   obligatoires** et contrôlées au démarrage (`REQUIRED_KEYS`) : il vaut mieux
   échouer tout de suite avec un message clair que publier un JSON-LD portant le
   logo ou la raison sociale d'un autre site.

   | Clé | Rôle |
   |---|---|
   | `site_name` | Nom affiché et suffixe du `<title>` |
   | `site_url` | Origine, sans barre finale |
   | `sector` | Activité, injectée dans le prompt |
   | `location` | Zone principale ; la ville en est déduite pour le JSON-LD |
   | `geo_keywords` | Mots-clés géo du prompt ; les 6 premiers vont dans `keywords` |
   | `tone` | Ton de rédaction |
   | `author` | Auteur affiché et JSON-LD |
   | `target_word_count` | Cible éditoriale de référence |
   | `faq_questions_count` | Nombre exact de questions de FAQ (validé) |
   | `language` | Langue de rédaction |
   | `model` | Modèle OpenAI (`gpt-4o`) |
   | `temperature` | Température d'échantillonnage |
   | `topic_marker_prefix` | Préfixe du marqueur d'idempotence (`qdc-topic`) |
   | `og_image` | Visuel Open Graph / Twitter, chemin local |
   | `logo_path` | Logo du site, chemin local |
   | `default_article_section` | Catégorie éditoriale (`articleSection`, catégorie RSS) |
   | `reference_article_slug` | Article servant de gabarit HTML |
   | `facts` | **Seuls faits chiffrés, adresses et coordonnées** que le modèle a le droit d'employer |

   S'y ajoutent des clés propres à ce site, avec repli automatique si elles
   manquent : `author_role`, `author_job_title`, `author_url`, `publisher_id`,
   `blog_id`, `internal_link_targets`, `post_tag`, `publish_hour_local`,
   `publish_tz_offset`.

2. Extrait de `BLOG_WORKFLOW.md` les 12 sujets de la section
   « Douze sujets prêts à traiter » **et** les règles de contenu, qui sont
   injectées telles quelles dans le prompt. Sur ce site un sujet tient sur
   plusieurs lignes (titre en gras, puis l'angle et le slug retenu), donc la
   section est découpée en blocs séparés par une ligne vide.
3. Scanne `/blog/*/index.html` : un article généré porte un marqueur
   `<!-- qdc-topic: N -->` juste après `<body>`. Un sujet marqué n'est jamais repris.
4. Choisit le premier sujet non traité, dans l'ordre de la liste. **Le slug
   annoncé dans `BLOG_WORKFLOW.md` fait foi** quand il existe ; sinon il est
   déduit du titre.
5. **Relit l'article de référence** (`blog/assurance-habitation-tarbes-locataire-proprietaire-pno/index.html`)
   et s'en sert de gabarit. Aucun template HTML n'est dupliqué dans le script :
   `<head>`, favicons, feuille de style, header, footer, bloc CTA et mentions de
   bas d'article en sont extraits à chaque exécution, donc si le gabarit évolue
   les articles suivants suivent.
6. Appelle OpenAI (`gpt-4o`, `temperature` 0.7, `max_tokens` 9000, réponse forcée
   en `json_object`) et lui demande **uniquement le contenu éditorial** :

   ```json
   {"title": …, "h1": …, "breadcrumb": …, "meta_description": …, "lede": …,
    "sections": [{"h2": …, "content": [{"type": "p|h3|ul|ol|strong", "text": …}]}],
    "faq": [{"question": …, "answer": …}]}
   ```

   Le modèle **n'écrit plus une ligne de HTML**. Auparavant il régénérait la page
   entière : les deux tiers de ses tokens de sortie partaient en balisage
   (`<head>`, JSON-LD, header, footer), ce qui plafonnait le corps rédigé autour
   de 850 mots quelle que soit la consigne.

   Seul balisage autorisé dans les textes : `**gras**` et `[libellé](/chemin)`.
   Les liens sont restreints aux chemins internes, un lien externe est donc
   structurellement impossible. Tout le reste est échappé — le modèle ne peut pas
   injecter de HTML.
7. **Valide le contenu** avant toute écriture : champs présents, longueur du
   `title` (40–70) et de la `meta_description` (< 155), types de blocs connus,
   exactement 5 questions de FAQ, maillage interne (≥ 2 liens vers les cibles de
   `internal_link_targets` et ≥ 1 vers `/blog/`), volume entre 900 et 1900 mots.
   Le moindre échec ⇒ code 1, **rien n'est écrit**.

   Les contrôles sur le canonical, l'Open Graph, la Twitter Card, le marqueur,
   le `<h1>` unique et la validité des JSON-LD **ne portent plus sur le modèle** :
   ces éléments sont désormais fabriqués par le script (`json.dumps` pour les
   JSON-LD) et ne peuvent plus être faux. Ils restent vérifiés une fois la page
   assemblée, par `validate_assembled()`, qui contrôle notre propre code.

   Le volume se compte sur le **contenu** (`content_word_count()`), pas sur du
   HTML : `lede` + sections, FAQ exclue.

   *Rattrapage :* le script relance un appel avec un prompt correctif dès que le
   corps passe **sous la cible de 1200 mots** — même si la validation passerait —
   **ou** qu'une erreur de validation que le modèle peut corriger subsiste
   (maillage interne absent, nombre de questions, longueur du `title`). Le message
   de reprise est construit à partir des erreurs réellement relevées
   (`build_correction()`). Il garde ensuite **la meilleure des copies** : celle qui
   a le moins d'erreurs, puis la plus proche de la cible de volume, et chaque
   reprise repart de la meilleure copie obtenue. Plafond strict : **3 appels**
   (`MAX_CALLS`).

   Le maillage interne est le point sur lequel le modèle achoppe le plus : la
   consigne liste les chemins un par un et montre la forme attendue, et
   `internal_link_targets` est tenu court (trois cibles) — six ancres noyées dans
   une phrase donnaient un article au bon volume mais sans un seul lien.
8. **Assemble la page** : `<head>` repris du gabarit avec seulement les champs
   propres à l'article remplacés (title, description, canonical, OG, Twitter,
   date de publication), les trois blocs JSON-LD sérialisés depuis le contenu, le
   marqueur d'idempotence inséré après `<body>`, le `<main>` construit de toutes
   pièces, header et footer repris tels quels.
9. Écrit `blog/<slug>/index.html`, puis met à jour `blog/index.html` (carte + JSON-LD),
   `sitemap.xml`, `rss.xml` et `llms.txt`.

## 4 bis. Conventions HTML attendues dans le gabarit

`split_template()` est calé sur le balisage **de ce site**, qui diffère de celui
d'autres sites propulsés par le même script. Si le gabarit change, ce sont ces
repères qu'il faut préserver :

| Repère | Rôle |
|---|---|
| `<script type="application/ld+json">` (1er du `<head>`) | marque la coupe du `<head>` — il n'y a pas de commentaire `<!-- Article -->` ici |
| dernier `</script>` avant `</head>` | ce qui suit (la feuille de style) est conservé tel quel |
| `<main class="blogHead" …>` | ouverture du `<main>`, reprise à l'identique |
| `<div class="wrap">` | conteneur de largeur |
| `<ol class="crumbs">` | fil d'Ariane |
| `<article class="article">` | corps de l'article |
| `<div class="articleMeta">` | signature, date, temps de lecture |
| `<section class="faq">` / `<div class="faqItem">` | FAQ (`<h3>` question, `<p>` réponse) |
| `<div class="postCta">` | bloc d'appel à l'action, **repris tel quel** (div imbriqués : l'extraction compte les ouvertures et fermetures) |
| ce qui suit le CTA jusqu'à `</article>` | mentions et lien de retour, repris tels quels |

Le paragraphe de mentions du gabarit nomme le sujet de l'article de référence
(« … des repères généraux **sur l'assurance habitation** »). Repris tel quel sur un
autre sujet il serait faux : le script retire ce complément et garde la phrase
générique.

Côté `blog/index.html`, le point d'insertion est `<div class="postGrid">` et la
carte suit le modèle `<a class="postCard reveal">`. Côté `llms.txt`, la section
visée est `## Articles du blog`.

## 4 ter. Réécrire un article existant

```bash
python scripts/generate-article.py --rewrite <slug>
```

Régénère un article déjà publié et **écrase** son fichier. Le sujet est retrouvé
via le marqueur `<!-- qdc-topic: N -->` présent dans le fichier, donc aucun
risque de se tromper de sujet. Le teaser de `blog/index.html` et l'entrée
`rss.xml` sont resynchronisés (`refresh_entries()`) : les updaters normaux sont
idempotents par URL et laisseraient sinon le texte de l'ancienne version.

Disponible aussi depuis Actions : champ **rewrite** du `workflow_dispatch`.

## 5. Idempotence

- Le slug est **déterministe** : celui annoncé dans `BLOG_WORKFLOW.md`, ou à défaut
  déduit du titre — même titre ⇒ même slug.
- Si `blog/<slug>/index.html` existe déjà, le sujet est considéré comme traité et
  le script passe au suivant : **aucun article existant n'est écrasé** sans `--rewrite`.
- Les mises à jour de `blog/index.html`, `sitemap.xml`, `rss.xml` et `llms.txt` vérifient
  d'abord si l'URL est déjà présente : rejouer le workflow ne crée jamais de doublon.
- Aucun article existant n'est jamais modifié ni supprimé.

## 6. Coût estimé

Tarifs OpenAI `gpt-4o` en vigueur à la mise en place — **à revérifier sur
<https://openai.com/api/pricing/>**, ils changent.

Par exécution : de l'ordre de **5 000 tokens en entrée** et **5 000 à 7 000 en sortie**
par appel, et **jusqu'à 3 appels** si le rattrapage de volume se déclenche (le prompt
de reprise réinjecte la copie précédente, donc l'entrée grossit à chaque tour).

L'ordre de grandeur est de **quelques dizaines de centimes d'euro par article** dans le
pire cas, soit une dizaine d'euros par an pour une publication hebdomadaire. Le poste de
coût réel n'est pas l'API mais la relecture humaine.

Pour vérifier la consommation réelle : les logs du workflow affichent le décompte exact
des tokens de chaque appel (`[blog] Tokens : … entrée + … sortie = …`) et le nombre
d'appels effectués.

## 7. Ajouter des sujets

La réserve de sujets est la section **« Douze sujets prêts à traiter »** de
[`BLOG_WORKFLOW.md`](../BLOG_WORKFLOW.md). Quand elle est épuisée, le workflow sort en
code 78 chaque lundi sans rien casser. Il suffit d'ajouter des blocs numérotés au même
format pour relancer la machine :

```markdown
13. **Titre du sujet** — angle, intention de recherche visée.
    Slug : `slug-retenu-pour-l-article`.
```

## 8. Relecture

La génération est automatique, la responsabilité éditoriale ne l'est pas.
Après chaque publication, vérifier au minimum : aucun tarif, taux, plafond de garantie
ni pourcentage inventé, aucune référence réglementaire chiffrée, aucun assureur nommé
en comparaison, coordonnées exactes, ton conforme. Les règles complètes sont dans
`BLOG_WORKFLOW.md`, section « Règles de contenu — non négociables ».
