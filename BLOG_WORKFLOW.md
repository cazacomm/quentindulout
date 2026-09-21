# Workflow blog — Quentin Dulout Courtage

Procédure de publication d'un nouvel article sur `quentinduloutcourtage.fr`.
Site statique, hébergé sur GitHub Pages, branche `main`. Aucun CMS, aucun build :
ce qui est commité sur `main` est en ligne quelques minutes plus tard.

---

## 1. Structure des fichiers

```
/blog/index.html                  → liste des articles
/blog/<slug>/index.html           → un article = un dossier + un index.html
/assets/blog.css                  → styles du blog (copie du CSS du site)
/assets/blog.js                   → menu mobile, animations, sélecteur particulier/pro
/sitemap.xml                      → à mettre à jour à chaque article
/rss.xml                          → à mettre à jour à chaque article
/llms.txt                         → à mettre à jour à chaque article
/robots.txt                       → ne bouge pas
```

**Convention de slug** : minuscules, tirets, sans accent, mot-clé principal + ville.
Exemple : `assurance-habitation-tarbes-locataire-proprietaire-pno`.
Un slug ne se modifie jamais après publication (cela casserait les liens et l'indexation).

---

## 2. Publier un article — la checklist

Le plus simple est de **dupliquer le dossier du dernier article** et de tout remplacer.

### a. Créer la page

- [ ] `cp -r blog/<dernier-article> blog/<nouveau-slug>`
- [ ] `<title>` : 60 caractères max, mot-clé en tête, marque à la fin.
- [ ] `<meta name="description">` : **moins de 155 caractères**, une promesse concrète.
- [ ] `<link rel="canonical">` : URL absolue du nouvel article, avec le `/` final.
- [ ] Open Graph : `og:title`, `og:description`, `og:url`, `og:image`, `article:published_time`.
- [ ] Twitter Card : `twitter:title`, `twitter:description`, `twitter:image`.
- [ ] Fil d'Ariane visible (`.crumbs`) mis à jour.
- [ ] `<h1>` unique, identique ou très proche du titre de l'article.

### b. Écrire

- [ ] **1200 à 1500 mots** hors FAQ.
- [ ] Un `<h2>` par grande idée, des `<h3>` pour les sous-cas. Jamais de `<h2>` décoratif.
- [ ] **Ancrage local obligatoire** : Tarbes nommée dans le titre, le chapô et au moins
      deux sections. Communes et départements limitrophes cités quand c'est pertinent
      (Lourdes, Bagnères-de-Bigorre, Aureilhan, Séméac, Ibos, Pau, Auch, Foix…).
- [ ] Un encadré `.callout` avec un conseil actionnable.
- [ ] Un CTA de fin (`.postCta`) vers `/#projet`.
- [ ] Le disclaimer de fin d'article (« repères généraux, pas un conseil personnalisé »).
- [ ] **FAQ de 5 questions** en `<h3>`, réponses de 3 à 5 phrases, formulées comme
      une vraie question tapée dans un moteur.

### c. Balisage structuré (JSON-LD)

Trois blocs sur chaque article, à valider sur <https://validator.schema.org/> :

- [ ] `Article` — `headline`, `datePublished`, `dateModified`, `author` (Quentin Dulout),
      `publisher` pointant vers `{"@id": "https://quentinduloutcourtage.fr/#business"}`.
- [ ] `BreadcrumbList` — Accueil › Blog › Article.
- [ ] `FAQPage` — le texte des réponses doit être **strictement identique** à celui
      visible dans la page. Toute divergence est une violation des règles Google.

Ne jamais ajouter de `Review`, `AggregateRating` ni `Offer` : ces balises engagent
juridiquement et exigent des données vérifiables.

### d. Répercuter partout

- [ ] `/blog/index.html` : ajouter une `.postCard` **en haut** de la grille.
- [ ] `/blog/index.html` : ajouter l'article au tableau `blogPost` du JSON-LD.
- [ ] `/sitemap.xml` : nouvelle `<url>` + mettre à jour les `<lastmod>` de `/` et `/blog/`.
- [ ] `/rss.xml` : nouvel `<item>` en tête + `<lastBuildDate>`.
- [ ] `/llms.txt` : ligne dans la section « Articles du blog ».

### e. Vérifier avant de commiter

```bash
# Validité des flux
python3 -c "import xml.dom.minidom as m; m.parse('sitemap.xml'); m.parse('rss.xml'); print('OK')"

# Validité de tous les blocs JSON-LD d'un fichier
python3 -c "
import re,json,sys
s=open(sys.argv[1],encoding='utf-8').read()
[json.loads(b) for b in re.findall(r'<script type=\"application/ld\+json\">(.*?)</script>',s,re.S)]
print('JSON-LD OK')" blog/<nouveau-slug>/index.html

# Aperçu local
python3 -m http.server 8000   # puis http://localhost:8000/blog/
```

- [ ] Relecture sur mobile (menu burger, titres qui ne débordent pas).
- [ ] Bascule **particulier / professionnel** testée : le thème sombre doit rester lisible.
- [ ] Tous les liens internes commencent par `/` (chemins absolus).

### f. Mettre en ligne

```bash
git add blog/<nouveau-slug> blog/index.html sitemap.xml rss.xml llms.txt
git commit -m "feat(blog): <titre de l'article>"
git push origin main
```

Puis, sous 24 h : soumettre l'URL dans **Google Search Console → Inspection d'URL →
Demander l'indexation**.

---

## 3. Règles de contenu — non négociables

1. **Aucun chiffre inventé.** Pas de tarif, pas de taux, pas de plafond de garantie,
   pas de pourcentage, pas de statistique locale. Si un chiffre est indispensable,
   il vient d'une source publique citée, ou il ne figure pas dans l'article.
2. **Aucune référence réglementaire approximative.** Pas de numéro d'article de loi,
   pas de date de texte citée de mémoire. On décrit le principe, pas la référence.
3. **Aucun nom de client**, aucun cas réel identifiable, même anonymisé partiellement.
4. **Aucun avis, note ou témoignage** créé pour les besoins de l'article.
5. **Aucune comparaison nominative d'assureurs** (« X est moins cher que Y »).
6. Toujours renvoyer vers un échange personnalisé plutôt que promettre un résultat.

---

## 4. Cadence conseillée

Un article toutes les deux à trois semaines vaut mieux que quatre d'un coup puis six
mois de silence. Alterner les cibles : un article particulier, un article
professionnel, un article épargne. Retravailler un ancien article (mise à jour du
`dateModified` et du contenu) a autant de valeur SEO qu'en publier un nouveau.

---

## 5. Sujets prêts à traiter

Chaque sujet est déjà cadré pour respecter les règles ci-dessus.

### Particuliers

1. **Assurance auto à Tarbes : tiers, tiers étendu ou tous risques, comment trancher ?**
   Critères d'arbitrage selon l'âge du véhicule et l'usage. Le cas des trajets
   domicile-travail vers Pau ou Toulouse. Slug : `assurance-auto-tarbes-tiers-ou-tous-risques`.

2. **Changer d'assurance de prêt immobilier quand on achète dans les Hautes-Pyrénées.**
   Principe de la délégation d'assurance, équivalence des garanties, calendrier des
   démarches. Slug : `changer-assurance-pret-immobilier-hautes-pyrenees`.

3. **Complémentaire santé à Tarbes : lire un tableau de garanties sans se noyer.**
   Décoder les pourcentages de la base de remboursement, l'optique, le dentaire,
   les dépassements d'honoraires. Slug : `comprendre-tableau-garanties-mutuelle-sante-tarbes`.

4. **Mutuelle santé pour les seniors dans les Hautes-Pyrénées : ce qui change après la retraite.**
   Fin du contrat collectif d'entreprise, postes de dépenses qui évoluent, questions
   à poser. Slug : `mutuelle-sante-senior-retraite-hautes-pyrenees`.

5. **Assurance deux-roues et scooter à Tarbes : les points que l'on oublie.**
   Équipements du pilote, stationnement, usage saisonnier, vol.
   Slug : `assurance-deux-roues-scooter-tarbes`.

6. **Prévoyance : que se passe-t-il pour vos revenus en cas d'arrêt de travail ?**
   Articulation régime obligatoire / contrat de prévoyance, notions de franchise et de
   maintien de salaire. Slug : `prevoyance-arret-de-travail-comment-ca-marche`.

### Professionnels

7. **RC Pro dans les Hautes-Pyrénées : qui en a vraiment besoin ?**
   Professions réglementées, prestataires de services, artisans, ce que couvre
   réellement la garantie. Slug : `rc-pro-hautes-pyrenees-qui-est-concerne`.

8. **Garantie décennale pour les artisans du bâtiment à Tarbes : les erreurs qui coûtent cher.**
   Activités déclarées, sous-traitance, reprise d'un chantier commencé.
   Slug : `garantie-decennale-artisan-batiment-tarbes`.

9. **Multirisque professionnelle : assurer un local commercial à Tarbes.**
   Contenu, marchandises, bris de matériel, perte d'exploitation, vitrines.
   Slug : `multirisque-professionnelle-local-commercial-tarbes`.

10. **Travailleur indépendant dans le 65 : santé, prévoyance et retraite, par où commencer ?**
    Ordre de priorité des protections pour un TNS qui démarre.
    Slug : `travailleur-independant-65-sante-prevoyance-retraite`.

### Épargne

11. **Assurance vie ou PER : comment choisir quand on prépare sa retraite ?**
    Logique de chaque enveloppe, disponibilité de l'épargne, horizon de placement.
    Sans aucun chiffre ni promesse de rendement.
    Slug : `assurance-vie-ou-per-comment-choisir`.

12. **Placer la trésorerie de sa société : le contrat de capitalisation personne morale.**
    À qui s'adresse l'outil, différences avec l'assurance vie, points de vigilance.
    Slug : `placer-tresorerie-societe-contrat-capitalisation`.

13. **Assurance habitation à Lourdes : comment protéger votre maison contre les intempéries ?**
    Découvrez les options d'assurance habitation qui protègent efficacement votre
    maison à Lourdes contre les intempéries.
    Slug : `assurance-habitation-lourdes-intemperies`.

14. **Pourquoi souscrire une assurance santé pour les auto-entrepreneurs à Pau ?**
    Examinez les avantages d'une assurance santé pour les auto-entrepreneurs évoluant
    à Pau et ses environs.
    Slug : `assurance-sante-auto-entrepreneur-pau`.

15. **Assurance auto : les spécificités à connaître dans les Hautes-Pyrénées.**
    Explorez les particularités de l'assurance auto adaptées aux routes et conditions
    des Hautes-Pyrénées.
    Slug : `assurance-auto-specificites-hautes-pyrenees`.

16. **Protection juridique : pourquoi est-ce crucial pour votre entreprise à Tarbes ?**
    Découvrez l'importance d'une protection juridique pour sécuriser votre entreprise
    située à Tarbes.
    Slug : `protection-juridique-entreprise-tarbes`.

17. **Assurance emprunteur à Bagnères-de-Bigorre : comment éviter les pièges ?**
    Identifiez les erreurs courantes à éviter lors de la souscription d'une assurance
    emprunteur à Bagnères-de-Bigorre.
    Slug : `assurance-emprunteur-eviter-pieges-bagneres-bigorre`.

18. **Assurer son camping-car pour explorer les Pyrénées : conseils pratiques.**
    Apprenez comment bien assurer votre camping-car pour explorer les routes des
    Pyrénées en toute sérénité.
    Slug : `assurer-camping-car-explorer-pyrenees`.

19. **Mutuelle santé à Vic-en-Bigorre : choisir les meilleures garanties pour votre famille.**
    Guide pour sélectionner une mutuelle santé optimale pour vous et votre famille à
    Vic-en-Bigorre.
    Slug : `mutuelle-sante-garanties-famille-vic-bigorre`.

20. **Assurance décennale : est-elle obligatoire pour les entreprises du bâtiment à Argelès-Gazost ?**
    Explorez l'obligation de souscrire une assurance décennale pour les entreprises du
    bâtiment dans la région d'Argelès-Gazost.
    Slug : `assurance-decennale-obligatoire-argeles-gazost`.

21. **Choisir une assurance vie à Ibos : quels sont les critères essentiels ?**
    Découvrez comment sélectionner une assurance vie en tenant compte des critères
    essentiels à Ibos.
    Slug : `choisir-assurance-vie-ibos`.

22. **Assurance prévoyance : comment protéger vos revenus à Séméac ?**
    Apprenez à sécuriser vos revenus grâce à une assurance prévoyance adaptée à
    Séméac.
    Slug : `assurance-prevoyance-proteger-revenus-semeac`.

23. **Assurance auto à Lannemezan : comment réduire votre prime annuelle ?**
    Découvrez des astuces pour diminuer le coût de votre assurance auto à Lannemezan.
    Slug : `assurance-auto-reduire-prime-lannemezan`.

24. **Assurance multirisque professionnelle : l'essentiel pour les commerces à Aureilhan.**
    Explorez les éléments clés d'une assurance multirisque pour les commerces situés à
    Aureilhan.
    Slug : `assurance-multirisque-commerce-aureilhan`.

25. **Assurance santé dans le Gers : quelles options pour les familles nombreuses ?**
    Examinez les meilleures options d'assurance santé pour les familles nombreuses
    dans le Gers.
    Slug : `assurance-sante-familles-nombreuses-gers`.

26. **Assurance responsabilité civile professionnelle : les indispensables pour les consultants à Toulouse.**
    Découvrez les aspects essentiels de l'assurance RC Pro pour les consultants
    opérant à Toulouse.
    Slug : `assurance-rc-pro-consultants-toulouse`.

27. **Préserver votre patrimoine avec une assurance habitation adaptée à Foix.**
    Apprenez comment une assurance habitation peut protéger efficacement votre
    patrimoine à Foix.
    Slug : `assurance-habitation-proteger-patrimoine-foix`.

28. **Assurance santé et prévoyance : les clés pour bien choisir à Auch.**
    Explorez les critères pour choisir votre assurance santé et prévoyance à Auch.
    Slug : `assurance-sante-prevoyance-choisir-auch`.

29. **Assurer sa voiture de collection dans les Pyrénées-Atlantiques : ce qu'il faut savoir.**
    Découvrez les particularités de l'assurance pour véhicules de collection dans les
    Pyrénées-Atlantiques.
    Slug : `assurance-voiture-collection-pyrenees-atlantiques`.

30. **Assurance emprunteur pour les jeunes actifs à Bordères-sur-l'Échez.**
    Guide sur l'assurance emprunteur adaptée aux besoins des jeunes actifs à Bordères-
    sur-l'Échez.
    Slug : `assurance-emprunteur-jeunes-actifs-borderes-echez`.

31. **Assurance santé : comment bien choisir son contrat dans la Haute-Garonne ?**
    Découvrez les critères pour sélectionner un contrat d'assurance santé optimal en
    Haute-Garonne.
    Slug : `choisir-assurance-sante-haute-garonne`.

32. **Assurance auto pour les conducteurs seniors à Tarbes : quels avantages ?**
    Examinez les avantages spécifiques des assurances auto pour les conducteurs
    seniors à Tarbes.
    Slug : `assurance-auto-seniors-avantages-tarbes`.

33. **L'assurance pour les vélos de route à Pau : est-ce vraiment utile ?**
    Analysez l'importance d'une assurance pour protéger votre vélo de route à Pau.
    Slug : `assurance-velo-route-utile-pau`.

34. **Assurance habitation en Ariège : comment sécuriser votre résidence secondaire ?**
    Découvrez les options d'assurance habitation pour protéger votre résidence
    secondaire en Ariège.
    Slug : `assurance-habitation-residence-secondaire-ariege`.

35. **Assurance santé pour les étudiants à Tarbes : quelles sont les meilleures options ?**
    Explorez les solutions d'assurance santé adaptées aux étudiants basés à Tarbes.
    Slug : `assurance-sante-etudiants-options-tarbes`.

36. **Assurance vie : comment optimiser votre épargne dans les Hautes-Pyrénées ?**
    Découvrez les stratégies pour maximiser les rendements de votre assurance vie dans
    les Hautes-Pyrénées.
    Slug : `optimiser-epargne-assurance-vie-hautes-pyrenees`.

37. **Assurance auto à Lourdes : comment choisir entre neuf et occasion ?**
    Guide pour déterminer le type d'assurance auto qui convient aux véhicules neufs ou
    d'occasion à Lourdes.
    Slug : `assurance-auto-neuf-occasion-lourdes`.

38. **Pourquoi souscrire une assurance pour votre bateau à moteur dans le Gers ?**
    Découvrez les raisons de souscrire une assurance pour votre bateau à moteur
    naviguant dans le Gers.
    Slug : `assurance-bateau-moteur-gers`.

39. **Assurance santé pour les familles à Bagnères-de-Bigorre : comment faire le bon choix ?**
    Guide pour choisir une assurance santé adaptée aux besoins des familles à
    Bagnères-de-Bigorre.
    Slug : `assurance-sante-familles-choix-bagneres-bigorre`.

40. **Assurance retraite complémentaire : est-ce utile dans les Pyrénées-Atlantiques ?**
    Examinez l'utilité d'une assurance retraite complémentaire pour les habitants des
    Pyrénées-Atlantiques.
    Slug : `assurance-retraite-complementaire-pyrenees-atlantiques`.

41. **Assurance habitation à Tarbes : comment protéger vos biens contre le vol ?**
    Découvrez les options d'assurance habitation pour protéger vos biens contre le vol
    à Tarbes.
    Slug : `assurance-habitation-vol-tarbes`.

42. **Assurance auto à Vic-en-Bigorre : comment choisir une franchise adaptée ?**
    Apprenez à sélectionner une franchise d'assurance auto qui correspond à vos
    besoins à Vic-en-Bigorre.
    Slug : `assurance-auto-franchise-vic-bigorre`.

43. **Assurance multirisque : pourquoi est-ce indispensable pour un commerce à Pau ?**
    Explorez les raisons pour lesquelles une assurance multirisque est cruciale pour
    un commerce à Pau.
    Slug : `assurance-multirisque-commerce-indispensable-pau`.

44. **Assurance santé pour expatriés : les options à considérer en Haute-Garonne.**
    Examinez les solutions d'assurance santé disponibles pour les expatriés résidant
    en Haute-Garonne.
    Slug : `assurance-sante-expatries-haute-garonne`.

45. **Comment choisir une assurance scolaire pour vos enfants à Argelès-Gazost ?**
    Découvrez les critères pour sélectionner une assurance scolaire adaptée à vos
    enfants à Argelès-Gazost.
    Slug : `choisir-assurance-scolaire-argeles-gazost`.

46. **Assurance prévoyance individuelle à Bagnères-de-Bigorre : comment bien se couvrir ?**
    Apprenez comment une assurance prévoyance individuelle peut vous offrir une
    couverture optimale à Bagnères-de-Bigorre.
    Slug : `assurance-prevoyance-individuelle-couvrir-bagneres-bigorre`.

47. **Assurance auto pour les jeunes conducteurs à Foix : comment réduire les coûts ?**
    Découvrez des astuces pour diminuer le coût de l'assurance auto pour les jeunes
    conducteurs à Foix.
    Slug : `assurance-auto-jeunes-conducteurs-reduire-couts-foix`.

48. **Assurance habitation : quelle couverture pour un appartement en Ariège ?**
    Explorez les options de couverture d'assurance habitation pour les appartements
    situés en Ariège.
    Slug : `assurance-habitation-couverture-appartement-ariege`.

49. **Assurance santé à Lannemezan : comment bien comprendre votre contrat ?**
    Guide pour déchiffrer les termes de votre contrat d'assurance santé à Lannemezan.
    Slug : `assurance-sante-comprendre-contrat-lannemezan`.

50. **Assurance multirisque professionnelle : protéger votre atelier à Ibos.**
    Découvrez comment une assurance multirisque professionnelle peut protéger
    efficacement votre atelier à Ibos.
    Slug : `assurance-multirisque-atelier-ibos`.

51. **Assurance vie à Lourdes : comment s'adapter aux besoins de votre famille ?**
    Découvrez les critères pour adapter votre assurance vie aux besoins spécifiques de
    votre famille à Lourdes. Cet article vous guidera dans le choix des options de
    couverture les plus pertinentes.
    Slug : `assurance-vie-adapter-famille-lourdes`.

52. **Assurance emprunteur en Haute-Garonne : quelles garanties privilégier ?**
    Explorez les garanties essentielles à privilégier pour votre assurance emprunteur
    en Haute-Garonne. Cet article vous aidera à faire des choix éclairés pour
    sécuriser votre projet immobilier.
    Slug : `assurance-emprunteur-garanties-haute-garonne`.

---

## 6. Points restés ouverts

- **Fiche Google Business** : l'URL n'est pas connue. Deux emplacements l'attendent —
  le lien « Google Maps » de la section Avis dans `index.html` (marqué `TODO`) et le
  champ `sameAs` du JSON-LD `InsuranceAgency`. À compléter dès réception.
- **Réseaux sociaux** : aucun compte fourni, `sameAs` volontairement absent.
- **Consentement cookies** : la balise Google Ads est active sans bandeau de
  consentement. Sujet de conformité signalé, hors périmètre du blog.
