# Site web — Fédération des Chasseurs de la Vendée

Site statique [Astro](https://astro.build/) administrable dans [Pages CMS](https://pagescms.org/). Il fonctionne sans serveur, base de données, suivi d’audience, cookie publicitaire ni ressource externe nécessaire à l’exécution.

## Développement et validation

Prérequis : Node.js 22 et npm.

```bash
npm ci
npm run dev
```

Le build de production exécute le contrôle TypeScript, génère le site puis vérifie les routes, les liens internes, les médias et plusieurs repères d’accessibilité :

```bash
npm run build
npm run preview
```

L’URL de production est `https://federationchassevendee.github.io/site-web/`. Astro génère donc tous les liens et médias sous le préfixe `/site-web/`.

## Les 7 templates

L’architecture reste volontairement limitée. Il n’y a pas de constructeur de page universel.

| Template | Collection | Usage |
| --- | --- | --- |
| Accueil | `src/content/home.json` | Démarches prioritaires, informations importantes, présentation et contact |
| Page carrefour | `src/content/crossroads/` | Entrée de rubrique avec cartes ordonnées ou contenus enfants générés |
| Page standard | `src/content/standard-pages/` | Contenu courant, contact et pages légales, avec documents, liens et appel à l’action facultatifs |
| Article | `src/content/articles/` | Actualité datée, catégorisée et éventuellement archivée |
| Fiche espèce | `src/content/species/` | Identification, habitat, alimentation, reproduction, répartition, statut et galerie |
| Formation | `src/content/trainings/` | Objectifs, public, prérequis, programme, informations pratiques, dates et inscription |
| Index générique | `src/content/indexes/` | Liste ou cartes provenant d’une collection choisie explicitement |

L’Index générique affiche les actualités, espèces, formations, documents, questions fréquentes, termes du glossaire ou entrées d’annuaire. Ces quatre dernières sources sont de simples collections de données dans `src/content/documents/`, `faqs/`, `glossary/` et `directories/` : elles ne créent pas de nouveaux templates.

Les schémas typés et leurs valeurs par défaut sont définis dans `src/content.config.ts`. La route statique `src/pages/[...slug].astro` associe chaque collection à son template. Deux contenus ne peuvent pas produire la même URL.

## Modifier le site avec Pages CMS

1. Ouvrir [Pages CMS](https://app.pagescms.org/) et choisir le dépôt `FederationChasseVendee/site-web`.
2. Choisir la branche de travail appropriée.
3. Ouvrir la collection correspondant au besoin : **Pages standard**, **Pages carrefour**, **Actualités**, **Fiches espèces**, **Formations**, **Index et listes**, ou une collection de ressources.
4. Modifier les champs en français, enregistrer puis publier. Aucun Git ni HTML n’est demandé.

Les collections autorisent explicitement création, renommage et suppression. **Accueil** et **Paramètres du site** sont protégés contre ces trois opérations. Les images et documents chargés dans la médiathèque sont enregistrés dans `public/assets/`.

Pour une image informative, renseigner une description utile. Pour une image purement décorative, activer **Image uniquement décorative** et laisser sa description vide. Le build refuse une image qui n’est ni décrite ni déclarée décorative.

### Créer une page

Le nom de fichier devient l’URL. Par exemple :

- `src/content/standard-pages/contact.md` → `/contact/` ;
- `src/content/articles/actualites/mon-article.md` → `/actualites/mon-article/`.

Les sous-dossiers servent à créer le fil d’Ariane. La page parente doit exister avant d’exposer un lien vers une page profonde.

Pour une page carrefour, saisir des cartes dans l’ordre souhaité. Lorsque la rubrique doit simplement reprendre tous les articles, espèces, formations ou index enfants, choisir **Ajouter automatiquement les contenus** plutôt que dupliquer les liens.

Pour un index, choisir clairement sa **Collection à afficher**, sa présentation en liste ou en cartes et, si nécessaire, une catégorie. FAQ, glossaire et annuaire sont toujours affichés directement : aucun accordéon ou contenu indispensable masqué.

## Navigation et accessibilité

Le menu principal est limité aux six rubriques conservées dans `src/content/site.json`. Le logo fournit le retour à l’accueil. **Valider mon permis** et **Contact** restent séparés comme actions prioritaires.

Le socle vise WCAG 2.2 AA : landmarks, titre unique, lien d’évitement, fils d’Ariane, focus visible, navigation clavier, cibles d’au moins 44 px, menu mobile à état explicite, alternatives d’images, annonce des nouveaux onglets, mise en page responsive et respect de `prefers-reduced-motion`. Les tests statiques ne remplacent pas un audit manuel avec clavier, lecteur d’écran et zoom à 200 %.

## Publication

`.github/workflows/deploy-pages.yml` installe les dépendances avec `npm ci`, lance `npm run build`, puis publie `dist/` sur GitHub Pages après fusion dans `main`.
