# Site web — Fédération des Chasseurs de la Vendée

Prototype statique réalisé avec [Astro](https://astro.build/) et administrable avec [Pages CMS](https://pagescms.org/). Il contient les pages Accueil et Contact, sans serveur, base de données, analytics ni cookies.

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

- `src/content/site.json` : identité, navigation, pied de page et réseaux sociaux.
- `src/content/home.json` : tous les textes, cartes, liens, image et SEO de l’accueil.
- `src/content/contact.json` : coordonnées, horaires, explications et SEO du contact.
- `public/assets/` : logo et images chargés dans Pages CMS.
- `.pages.yml` : formulaires d’édition proposés par Pages CMS.

Les pages Astro dans `src/pages/` présentent ces données. Il n’est pas nécessaire de modifier leur HTML pour mettre à jour le contenu courant.

## Modifier avec Pages CMS

1. Aller sur [Pages CMS](https://app.pagescms.org/) et se connecter avec le compte GitHub autorisé à modifier ce dépôt.
2. Choisir `FederationChasseVendee/site-web`, puis la branche `main`.
3. Ouvrir **Page d’accueil**, **Page contact** ou **Paramètres du site**.
4. Modifier les champs, enregistrer puis publier. Pages CMS crée directement un commit GitHub : aucune commande Git n’est nécessaire.

Les images ajoutées dans la médiathèque sont stockées dans `public/assets/`. Renseigner un texte alternatif utile pour chaque image informative.

## Publication

Chaque push sur `main` déclenche `.github/workflows/deploy-pages.yml` : installation, contrôle TypeScript, build Astro, dépôt de l’artifact puis déploiement par `actions/deploy-pages`.

Une seule activation peut être nécessaire dans GitHub : **Settings → Pages → Build and deployment → Source → GitHub Actions**. L’URL publiée est ensuite :

<https://federationchassevendee.github.io/site-web/>

Les liens vers les démarches du site actuel s’ouvrent dans un nouvel onglet tant que ces services n’ont pas été migrés.
