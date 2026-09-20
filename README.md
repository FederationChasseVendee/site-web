# Site web — Fédération des Chasseurs de la Vendée

Site statique réalisé avec [Astro](https://astro.build/) et administrable avec [Pages CMS](https://pagescms.org/), sans serveur, base de données, analytics ni cookies.

## Développement local

Prérequis : Node.js 22 et npm.

```bash
npm install
npm run dev
```

Le serveur local indique l’URL à ouvrir. Pour vérifier la version de production :

```bash
npm run build
npm run preview
```

Le site est configuré pour l’URL `https://federationchassevendee.github.io/site-web/` et le sous-chemin `/site-web/`.

## Contenu et médias

- `src/content/site.json` : identité, pied de page et réseaux sociaux.
- `src/content/home.json` : tous les textes, cartes, liens, image et SEO de l’accueil.
- `src/content/pages/*.md` : pages secondaires créées dans Pages CMS, avec métadonnées YAML et contenu Markdown.
- `src/content.config.ts` : schéma de validation Astro des pages secondaires.
- `public/assets/` : logo et images chargés dans Pages CMS.
- `.pages.yml` : formulaires d’édition proposés par Pages CMS.

La page d’accueil est spéciale et protégée contre la suppression et le renommage. Toutes les autres pages utilisent une collection : Astro crée une route statique pour chaque fichier Markdown lors du déploiement.

## Modifier avec Pages CMS

1. Aller sur [Pages CMS](https://app.pagescms.org/) et se connecter avec le compte GitHub autorisé à modifier ce dépôt.
2. Choisir `FederationChasseVendee/site-web`, puis la branche `main`.
3. Ouvrir **Page d’accueil**, **Pages secondaires** ou **Paramètres du site**.
4. Modifier les champs, enregistrer puis publier. Pages CMS crée directement un commit GitHub : aucune commande Git n’est nécessaire.

Les images ajoutées dans la médiathèque sont stockées dans `public/assets/`. Renseigner un texte alternatif utile pour chaque image informative.

### Créer une page

1. Dans **Pages secondaires**, cliquer sur **Nouvelle entrée**.
2. Saisir le titre : Pages CMS propose automatiquement un nom de fichier propre, par exemple `la-federation.md`, qui devient l’URL `/la-federation/`.
3. Compléter la description SEO, l’introduction et le contenu principal.
4. Activer **Afficher dans le menu**, choisir son libellé et son ordre si la page doit être visible dans la navigation.
5. Les cartes, horaires et appel à l’action sont facultatifs.
6. Enregistrer puis publier.

### Renommer, masquer ou supprimer une page

- **Renommer et changer l’URL** : ouvrir la page, modifier son nom de fichier dans Pages CMS, puis publier. Le menu adopte automatiquement la nouvelle URL.
- **Masquer du menu** : désactiver **Afficher dans le menu**. La page reste accessible par son URL.
- **Supprimer** : utiliser l’action de suppression de Pages CMS. La route et son entrée de menu disparaissent au déploiement suivant.

Les noms `index` et `404` sont réservés. Deux fichiers ne doivent pas produire le même nom d’URL. Le build refuse ces cas explicitement pour éviter d’écraser l’accueil ou la page d’erreur. Après publication, GitHub Actions reconstruit le site ; la mise en ligne prend généralement une à deux minutes. Les liens ajoutés manuellement dans le contenu ne sont pas réécrits lors d’un renommage : ils doivent être mis à jour par l’éditrice.

## Publication

Chaque push sur `main` déclenche `.github/workflows/deploy-pages.yml` : installation, validation du contenu et des routes, build Astro, dépôt de l’artifact puis déploiement par `actions/deploy-pages`.

Une seule activation peut être nécessaire dans GitHub : **Settings → Pages → Build and deployment → Source → GitHub Actions**. L’URL publiée est ensuite :

<https://federationchassevendee.github.io/site-web/>

Les liens vers les démarches du site actuel s’ouvrent dans un nouvel onglet tant que ces services n’ont pas été migrés.
