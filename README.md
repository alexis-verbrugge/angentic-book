# novel_writer — Workflow agentique d'ecriture de roman fantasy

Agent (Anthropic Claude) qui t'accompagne pour ecrire un roman fantasy en
francais, a plusieurs personnages (plusieurs POV en alternance), etape par
etape, avec validation humaine a chaque etape cle et une bible d'univers
tenue a jour automatiquement (personnages, lieux, factions, systeme de
magie, objets, chronologie).

## Installation

```bash
cd scripts/novel_writer
pip install -r requirements.txt
cp .env.example .env   # puis renseigner ANTHROPIC_API_KEY
```

## Workflow

```bash
# 1. Discussion interactive pour definir la premisse du roman
python main.py premise

# 2. Generation du plan (chapitre par chapitre, POV inclus), avec validation/feedback
python main.py outline --chapters 12

# 3. Redaction d'un chapitre (repeter pour chaque chapitre), avec validation/feedback
python main.py chapter --number 1 --words 1800

# 4. Verification de coherence sur l'ensemble des chapitres rediges
python main.py check

# Etat d'avancement (plan, bible, repartition par POV)
python main.py status
```

A chaque etape cle (plan, chapitre), l'agent propose un resultat que tu peux
valider (`o`), rejeter avec un feedback texte pour regeneration (`n`), ou
annuler (`q`). Rien n'est sauvegarde tant que tu n'as pas valide.

## Ce que fait l'agent a chaque etape

- **Premise** : brainstorm interactif (univers, ton, conflit central),
  utilise `web_search` pour s'inspirer de mythologies/folklore/references
  reelles si besoin. Sauvegarde dans `story_bible/premise.md`.
- **Outline** : propose un decoupage chapitre par chapitre (structure en
  trois actes) en alternant les POV de maniere equilibree, enregistre les
  personnages/lieux/factions principaux dans la bible, sauvegarde
  `story_bible/outline.md`.
- **Chapter** : redige la prose du chapitre dans la voix du personnage POV,
  en tenant compte de la bible, du plan, de la continuite narrative
  immediate (chapitre precedent) ET de la continuite du fil de ce
  personnage (son dernier chapitre, meme si d'autres POV se sont intercales
  entre-temps). Enregistre tout nouvel element notable ainsi que les
  evenements marquants (categorie `timeline`). Sauvegarde
  `chapters/chapitre_XXX.md`.
- **Sync** : re-analyse le texte ACTUEL d'un chapitre (utile si tu l'as
  modifie a la main) et met a jour la bible en consequence, sans regenerer
  le texte.
- **Check** : relit tous les chapitres rediges + la bible (dont la
  chronologie), signale les incoherences (statut d'un personnage,
  chronologie inter-POV, regles de magie...) dans un rapport
  `reports/consistency_<date>.md`.

## Liberte de l'auteur : comment ameliorer/corriger le roman toi-meme

Tout est stocke en Markdown, donc directement editable dans l'editeur.
Plusieurs mecanismes te laissent la main :

- **Edition manuelle libre** : modifie `chapters/chapitre_XXX.md` ou les
  fichiers `story_bible/*.md` directement, puis lance
  `python main.py sync --number N` pour que la bible reflete tes
  changements (elle n'ecrase jamais ton texte, elle ne fait que se mettre a
  jour a partir de ce qu'elle lit).
- **Verrouillage d'une entite** : ajoute le champ `- **verrouille**: oui`
  dans une fiche (personnage, lieu...) pour empecher l'agent de la modifier
  automatiquement lors des prochaines etapes ; tu restes le seul a pouvoir
  la changer.
- **Notes de direction** : cree `story_bible/notes.md` (directives globales,
  ex: "plus de tension dans les dialogues", "eviter les cliches de prophetie")
  et/ou `chapters/chapitre_XXX.notes.md` (notes specifiques a un chapitre) ;
  elles sont automatiquement injectees dans le prompt de redaction.
- **Feedback iteratif** : a la validation d'un plan ou d'un chapitre, tape
  `n` puis donne un feedback texte libre ("rends ce chapitre plus sombre",
  "Elandriel doit hesiter davantage") pour faire regenerer sans perdre la
  main.
- **Versionner avec git** (recommande) : initialise un depot git dans ce
  dossier et commite apres chaque chapitre valide. Tu obtiens un historique
  complet, la possibilite de revenir en arriere, et un diff clair de tes
  propres corrections manuelles par rapport a la version generee.

## Structure de la bible d'univers (`story_bible/*.md`)

- `characters.md`, `locations.md`, `factions.md`, `magic_system.md`,
  `items.md`, `timeline.md` — un fichier par categorie, une section
  `## Nom` par entite, avec des champs `- **cle**: valeur` et un historique
  horodate (`### Historique`) qui trace la provenance de chaque information
  (chapitre, confiance, source). `timeline.md` recense les evenements cles
  tous fils POV confondus, pour verifier la coherence chronologique globale.
- `premise.md`, `outline.md` — documents editables a la main si besoin (les
  regenerations via l'agent ecrasent tout le fichier concerne).
- `notes.md` (optionnel) — directives globales de l'auteur.

Champs recommandes pour un personnage POV : `voix_narrative` (registre/ton
propre au personnage), `derniere_position`, `etat_actuel`, `arc_narratif`.

## Recherche web

Utilise l'outil de recherche web natif d'Anthropic (`web_search_20250305`),
sans dependance a une API tierce. Desactivable via `ENABLE_WEB_SEARCH=false`
dans `.env` si tu preferes un univers 100% invente sans reference externe.

## Pistes pour rendre le workflow encore plus puissant

Idees non implementees, par ordre de valeur/effort estime :

1. **Regeneration au niveau scene** (pas juste chapitre entier) : decouper
   les chapitres en blocs `## Scene N` et permettre de ne regenerer qu'une
   scene precise avec une instruction ciblee ("rends ce dialogue plus
   tendu"). Gain de precision important pour l'edition fine.
2. **Passe d'auto-critique avant validation** : un agent "critique
   litteraire" qui relit chaque brouillon (rythme, dialogues, show-dont-tell,
   cliches) et liste des suggestions AVANT de te le presenter, sans les
   appliquer automatiquement — tu gardes la main mais avec un premier filtre
   qualite.
3. **Recherche semantique (RAG) dans la bible** au lieu du dump complet en
   contexte : necessaire quand le roman grossit (au-dela d'une vingtaine de
   chapitres, le contexte plein devient couteux/limite). Embeddings sur les
   fiches de la bible + chapitres, recuperation des passages pertinents pour
   chaque nouvelle generation.
4. **Verification de coherence par lots** (par arc narratif ou par fil POV)
   plutot qu'en un seul appel, pour scaler au-dela des limites de contexte.
5. **Export manuscrit** : commande qui compile tous les chapitres valides
   en un seul document (Markdown concatene, ou .docx/.epub) pour relecture
   confortable ou partage.
6. **Tableau de bord de pacing** : visualiser la longueur des chapitres,
   l'equilibre entre POV, et la position de chaque chapitre dans la courbe
   dramatique (acte 1/2/3).
7. **Branches alternatives** : pouvoir explorer 2 versions d'un meme
   chapitre (ex: 2 fins possibles) sans écraser l'autre, via des branches
   git ou des copies nommees, puis choisir/fusionner.
8. **Glossaire linguistique / prononciation** : fichier dedie aux noms
   inventes (etymologie, prononciation) pour garantir une orthographe stable
   sur des centaines de pages.
9. **Alertes de rythme POV automatiques** : detection automatique (dans
   `status` ou `check`) si un personnage POV n'est pas apparu depuis trop
   longtemps, ou si un fil est deseiquilibre en volume.

## Limites connues

- La verification de coherence (`check`) envoie l'integralite des chapitres
  et de la bible dans le contexte : au-dela d'une vingtaine de chapitres,
  cela peut depasser la fenetre de contexte du modele (cf. piste 3 et 4
  ci-dessus).
- La fusion de champs liste dans la bible se base sur un decoupage par
  virgule : evite les virgules a l'interieur d'une valeur individuelle
  (ex: prefere "Ordre des Veilleurs" a "Ordre, des Veilleurs").

