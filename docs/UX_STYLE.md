# Charte Graphique & Design System - Battle Score

Ce document définit les règles d'interface (UI) et d'expérience utilisateur (UX) du projet Battle Score.

## 1. Identité Visuelle

### Logo & Marque
- **Nom** : Battle Score
- **Acronyme** : BS (utilisé dans les icônes de logo)
- **Style** : Moderne, compétitif, épuré.

## 2. Palette de Couleurs

### Couleurs de Fond (Background)
- **Principal** : `bg-slate-950` (#020617)
- **Surface (Glass)** : `rgba(15, 23, 42, 0.6)` avec `backdrop-filter: blur(12px)`
- **Bordures** : `rgba(255, 255, 255, 0.1)`

### Couleurs de Texte
- **Principal** : `text-slate-200` (#e2e8f0)
- **Secondaire / Muet** : `text-slate-400` (#94a3b8)
- **Accent (Gradient)** : `linear-gradient(to right, #60a5fa, #a855f7)` (Blue to Purple)

### Couleurs Sémantiques
- **Action / Primaire** : Blue (#3b82f6)
- **Succès** : Green (#22c55e)
- **Erreur / Danger** : Red (#ef4444)
- **Sécurité / Attention** : Amber (#f59e0b)
- **Spécial / Tournoi** : Purple (#a855f7)

## 3. Typographie

- **Police principale** : `Outfit`, sans-serif (Google Fonts)
- **Tailles standards** :
  - `H1` : `text-3xl` à `text-4xl`, font-bold
  - `Body` : `text-base`
  - `Small/Support` : `text-sm` ou `text-[10px]` pour les labels

## 4. Principes de Design (Design Tokens)

### Glassmorphism
Le projet utilise intensivement l'effet "Glass" pour les conteneurs :
- Classe CSS : `.glass`
- Propriétés : Fond semi-transparent, flou d'arrière-plan, bordure fine et claire (`border-white/10`).

### Gradients
Utilisés pour les boutons primaires et les titres mis en avant :
- `.text-gradient` : Bleu vers Violet.
- `.btn-primary` : `linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%)`.

## 5. Composants UI

### Boutons
- **Primary** (`.btn-primary`) : Gradient, arrondi (`rounded-xl` ou `rounded-2xl`), ombre portée colorée.
- **Glass** : Bouton discret avec fond `.glass`.

### Formulaires
- **Inputs** (`.form-input`) : Fond sombre (`rgba(30, 41, 59, 0.5)`), bordure fine, focus avec halo bleu.
- **Sélecteurs & Ranges** : Personnalisés avec les couleurs de la marque.

### Cartes (Cards)
- Utilisation systématique de `.glass` et `rounded-3xl` pour les grands blocs de contenu.

### Navigation
- **Desktop Navbar** : Fixée en haut, style glass, devient flottante avec padding sur grand écran.
- **Mobile Navbar** : Fixée en bas de l'écran pour une accessibilité optimale au pouce.

### Notifications & Messages
- **Apparition** : En haut à droite de l'écran (Desktop) ou pleine largeur (Mobile).
- **Animation** : Utiliser `.animate-fade-in` pour l'entrée et `.animate-fade-out` pour la sortie (déplacement vertical de 10px + opacité).
- **Durée de vie** : Les messages doivent disparaître automatiquement après **5 secondes**. Une barre de progression discrète en bas du message indique le temps restant.
- **Style** : Utiliser des bordures gauches colorées pour indiquer le type (Vert = Succès, Rouge = Erreur).

## 6. Bonnes Pratiques UX

- **Feedback Visuel** : Utiliser des transitions douces (`transition-all duration-300`).
- **Accessibilité Mobile** : Les actions principales doivent être accessibles en bas de l'écran.
- **Navigation & Historique** :
    - Les "menus" (overlays, pages de sélection rapides) ne doivent pas polluer l'historique de navigation. Utiliser `location.replace` ou `replaceState` si nécessaire.
    - Après la mise à jour d'un paramètre, ou lors du clic sur le bouton de fermeture (X), rediriger systématiquement vers la page d'origine (en sautant les menus éventuels).
- **Micro-interactions** : Effet de survol (hover) avec légère mise à l'échelle (`scale-105`) ou changement de luminosité.
- **Gestion des États** : Utiliser Alpine.js pour les états locaux (modales, menus, steppers) afin d'assurer une réactivité immédiate sans rechargement.
- **Cohérence** : Toujours utiliser les classes utilitaires Tailwind pré-définies dans `base.html`.
- **Classements & Podiums** :
    - **Or (1er)** : Ambre 500 (`#fbbf24`) avec ombre portée légère.
    - **Argent (2ème)** : Ardoise 400 (`#94a3b8`) / Slate 300.
    - **Bronze (3ème)** : Ambre 700 (`#b45309`) / Marron chaud.
