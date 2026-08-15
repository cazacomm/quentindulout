# Automatisation du blog

Un article est généré et publié **chaque lundi à 9h UTC** par le workflow
`.github/workflows/blog-auto.yml`, qui exécute `scripts/generate-article.py`.

Le script prend le premier sujet non traité de la section « Douze sujets » de
[`BLOG_WORKFLOW.md`](../BLOG_WORKFLOW.md), le fait rédiger par l'API OpenAI, puis
écrit `blog/<slug>/index.html` et met à jour `blog/index.html`, `sitemap.xml`,
`rss.xml` et `llms.txt`.

Le gabarit HTML n'est pas recopié dans le script : il est **relu à chaque
exécution** depuis l'article désigné par `template_article` dans
`blog-config.json`. Si le design du blog évolue, les articles suivants suivent.

---

## 1. Installer la clé API

1. Créer une clé sur <https://platform.openai.com/api-keys>.
2. Sur GitHub : **Settings → Secrets and variables → Actions → New repository secret**
3. Nom exact : `OPENAI_API_KEY` — valeur : la clé (`sk-…`).

Sans ce secret, le job échoue proprement avec le message
`variable d'environnement OPENAI_API_KEY absente`.

---

## 2. Lancer manuellement

**Depuis GitHub** : onglet **Actions → Blog auto → Run workflow**. Deux options
facultatives : `topic` (forcer un numéro de sujet) et `dry_run` (simuler sans
publier).

**En local** :

```bash
pip install openai
export OPENAI_API_KEY="sk-..."

python3 scripts/generate-article.py --dry-run      # simulation, aucun fichier écrit
python3 scripts/generate-article.py --dry-run --mock  # simulation sans appel API
python3 scripts/generate-article.py --topic 4      # force le sujet n°4
python3 scripts/generate-article.py                # génère et écrit les fichiers
```

En local, le script **n'effectue jamais de commit** : il écrit les fichiers, à
vous de relire puis de commiter. C'est le workflow GitHub qui commite et pousse.

| Option | Effet |
|---|---|
| `--dry-run` | Appelle l'API, n'écrit rien, affiche titre, métadonnées et extrait |
| `--mock` | N'appelle pas l'API, charge utile de test — sert à valider la chaîne hors ligne |
| `--topic N` | Force le sujet n°N au lieu du prochain non traité |

---

## 3. Codes de sortie

| Code | Signification | Comportement du workflow |
|---|---|---|
| `0` | Article généré | Commit + push |
| `78` | Aucun sujet non traité, ou fichier déjà existant | Job vert, aucun commit |
| `1` | Erreur (API, clé absente, gabarit cassé, contenu refusé) | Job rouge, aucun commit |

---

## 4. Garde-fous

- **Idempotence** : chaque article porte un marqueur `<!-- qdc-topic: N -->`.
  Le script scanne `blog/*/index.html` au démarrage ; un sujet déjà marqué, ou un
  dossier de slug déjà présent, est ignoré. Rejouer le workflow ne réécrit jamais
  un article existant.
- **Contrôles éditoriaux** avant écriture, conformes aux règles de
  `BLOG_WORKFLOW.md` : longueur du corps, nombre de `<h2>`, meta description sous
  155 caractères, FAQ complète, et **rejet automatique** de tout montant en euros,
  pourcentage, numéro de loi, article de code ou décret cité. En cas d'échec, une
  seconde tentative est lancée avec les consignes correctives ; si elle échoue
  aussi, le script sort en code 1 **sans rien écrire**.
- **Aucune modification des articles existants** : le script est en écriture
  seule sur le nouveau dossier, et en insertion sur les index et les flux.

---

## 5. Coût estimé

Modèle `gpt-4o-mini`, un appel par article (deux si le premier jet est refusé).
Ordre de grandeur : environ 1 500 tokens en entrée et 3 000 en sortie par article,
soit **moins d'un centime d'euro par exécution**, et de l'ordre de quelques
centimes par an à raison d'un article par semaine. Les tarifs officiels font foi :
<https://openai.com/api/pricing/>. Les minutes GitHub Actions sont gratuites sur
un dépôt public.

---

## 6. Alimenter la liste des sujets

Quand les 12 sujets sont épuisés, le workflow sort en code 78 chaque semaine sans
rien publier. Pour relancer la machine, ajoutez des entrées à la section
« Douze sujets » de `BLOG_WORKFLOW.md`, au même format :

```markdown
13. **Titre de l'article, avec la ville dedans.**
    Angle attendu, en une ou deux phrases.
    Slug : `slug-de-l-article`.
```

La numérotation doit rester unique : c'est elle qui sert de marqueur d'idempotence.
