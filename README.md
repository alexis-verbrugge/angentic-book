# novel_writer — Workflow agentique d'ecriture de roman fantasy

Agent (Anthropic Claude) qui t'accompagne pour construire un univers fantasy
complet puis ecrire un roman a plusieurs personnages (plusieurs POV en
alternance), etape par etape, avec validation humaine a chaque etape cle et
une bible d'univers tenue a jour automatiquement.

## Installation

```bash
cd scripts/novel_writer
pip install -r requirements.txt
cp .env.example .env   # puis renseigner ANTHROPIC_API_KEY
```

## Deja du contenu existant ? Importe-le d'abord

Si tu as deja ecrit des elements de worldbuilding, des fiches personnages, une
liste d'evenements prevus, ou meme des chapitres entiers avant de decouvrir cet
outil, tu n'as pas besoin de tout retaper : importe-les pour poser les bases,
PUIS continue avec le pipeline normal (l'agent completera/affinera ce qui
manque plutot que de repartir de zero).

```bash
# Notes en vrac (worldbuilding, personnages, evenements prevus...) -> bible d'univers
python main.py import-notes --file mes_notes_worldbuilding.txt
python main.py import-notes --file fiches_personnages.txt

# Chapitres deja rediges -> chapters/ + bible synchronisee a partir du texte
python main.py import-chapter --file brouillon_chap1.md --number 1 --pov "Nom du personnage"
python main.py import-chapter --file brouillon_chap2.md --number 2 --pov "Nom du personnage"
```

- `import-notes` n'invente rien : il extrait uniquement ce qui est present dans
  tes notes et l'enregistre dans la bonne categorie de la bible (personnages,
  lieux, factions, ...). Les evenements qui ne se sont **pas encore** produits
  dans l'histoire sont marques `statut: a_venir` dans `timeline.md` pour rester
  distincts de l'Histoire deja etablie.
- `import-chapter` copie ton texte dans `chapters/chapitre_XXX.md`, cree une
  entree minimale dans le plan si elle n'existe pas encore, puis synchronise
  la bible a partir de ce texte (memes mecanismes que `sync`).
- Le fichier source original n'est jamais modifie ni supprime.
- Une fois importe, lance `python main.py status` pour verifier ce qui a ete
  detecte, puis complete manuellement (ou via `world`/`outline`) ce qui manque.

## Workflow complet (ordre recommande)

```bash
# 0. Si tu as deja de la matiere : importe-la d'abord (voir section ci-dessus)

# 1. Discussion interactive pour definir/affiner la premisse (genre, ton, conflit central)
python main.py premise

# 2. Pipeline de worldbuilding complet (voir section dediee ci-dessous) — a faire une fois,
#    dans cet ordre, meme si tu as deja importe des elements (l'agent les reprend et comble les trous)
python main.py world --list
python main.py world --stage cosmology
python main.py world --stage magic
python main.py world --stage geography
python main.py world --stage history
python main.py world --stage peoples
python main.py world --stage religions
python main.py world --stage politics
python main.py world --stage landmarks
python main.py world --stage synthesis

# 3. Generation du plan (chapitre par chapitre, POV inclus), avec validation/feedback
python main.py outline --chapters 12

# 4. Pour CHAQUE chapitre restant a ecrire (boucle a repeter) :
python main.py chapter --number 1 --words 1800     # redaction
python main.py critique --number 1                  # critique severe et constructive
# -> si besoin, relance `chapter --number 1` en integrant le feedback de la critique

# 5. Verification de coherence globale (a lancer periodiquement, pas apres CHAQUE chapitre
#    — voir section economie de tokens ci-dessous)
python main.py check

# A tout moment : etat d'avancement (plan, bible, repartition par POV)
python main.py status
```

Chaque etape (premise, worldbuilding, outline, chapter) laisse l'auteur
garder la main : rien n'est sauvegarde tant qu'il n'a pas valide (ou tape
`/valider` pour les etapes en dialogue). L'ordre 0→5 n'est pas rigide : tu
peux revenir sur une etape de worldbuilding en cours de redaction (les fiches
verrouillees resteront intactes), mais fais premise et worldbuilding AVANT
outline, et outline AVANT chapter, pour que chaque etape s'appuie sur un
contexte deja stable.

## Pipeline de worldbuilding : les etapes d'un pro

`python main.py world --stage <cle>` lance une discussion interactive avec
l'agent pour cette etape (il pose des questions, propose des pistes, utilise
`web_search` pour s'inspirer de mythologies/folklore reels, et enregistre les
entites au fur et a mesure). Tape `/valider` pour figer le document de
synthese de l'etape, `/quitter` pour sortir sans rien sauvegarder.

L'ordre suit une logique "top-down" volontaire (du plus fondamental au plus
concret), utilisee par la plupart des worldbuilders professionnels pour
eviter les incoherences : chaque etape s'appuie sur celles deja etablies.

| # | Cle | Etape | Pourquoi cet ordre |
|---|-----|-------|---------------------|
| 1 | `cosmology` | Cosmologie & metaphysique | Definit les regles ultimes (dieux, creation, apres-vie) qui contraignent tout le reste, y compris la magie. |
| 2 | `magic` | Systeme de magie | Doit decouler de la cosmologie ; ses regles/couts/limites influencent directement la geographie (qui vit ou), l'histoire (guerres magiques) et la politique (qui controle la magie). |
| 3 | `geography` | Geographie & climat | Les continents/climats/ressources faconnent les futures cultures, routes commerciales et conflits — a definir avant l'histoire et les peuples. |
| 4 | `history` | Histoire & chronologie | Les grandes eres et cataclysmes expliquent l'etat actuel du monde ; s'appuie sur la geographie et la magie deja etablies. |
| 5 | `peoples` | Peuples, especes & cultures | Qui vit dans ce monde, avec quelles cultures — consequence directe de la geographie et de l'histoire. |
| 6 | `religions` | Religions & croyances | Pratique concrete de la foi (distincte de la cosmologie abstraite), enracinee dans les cultures deja definies. |
| 7 | `politics` | Politique & factions | Qui detient le pouvoir aujourd'hui, et pourquoi — synthese des peuples, religions et Histoire. |
| 8 | `landmarks` | Lieux notables & objets marquants | Concretise geographie/histoire/politique en lieux et objets precis, utilisables dans l'intrigue. |
| 9 | `synthesis` | Etat du monde au debut de l'histoire | Pont direct vers le plan du roman : quelles tensions sont sur le point d'exploser ? |

`python main.py world --list` affiche l'avancement (✓ = etape deja figee).

## Critique litteraire severe et constructive (`python main.py critique --number N`)

Distincte de `check` (qui verifie la coherence FACTUELLE entre chapitres et bible), cette etape juge la \
QUALITE litteraire d'un chapitre deja redige, comme le ferait un editeur senior exigeant. Elle note et \
commente systematiquement 9 axes :

1. Ouverture & accroche
2. Rythme & tension narrative
3. Voix narrative / fidelite au POV
4. Dialogues (naturel, sous-texte, distinction des voix)
5. Descriptions (show, don't tell / equilibre)
6. Style & prose (repetitions, cliches, rythme de phrase)
7. Coherence avec personnages & univers (croise la fiche du personnage POV et la bible)
8. Enjeux & impact emotionnel
9. Cloture du chapitre & transition

Pour chaque probleme identifie, l'agent cite le passage exact concerne et propose une suggestion \
concrete et actionnable — jamais une remarque vague. Les notes sont volontairement severes (un 9-10 \
est reserve a un niveau publiable par un grand editeur), mais toujours accompagnees d'un verdict et de \
3 a 5 priorites d'amelioration classees par impact. Le rapport complet (notes par axe, critiques \
detaillees, synthese) est sauvegarde dans `reports/critique_chapitre_XXX_<timestamp>.md`. Cette etape \
ne modifie ni le chapitre ni la bible : elle sert de base pour une reecriture manuelle ou une nouvelle \
iteration de `chapter --number N` en tenant compte du feedback.

## Liberte de l'auteur : comment ameliorer/corriger le roman toi-meme

Tout est stocke en Markdown, donc directement editable dans l'editeur.

- **Edition manuelle libre** : modifie `chapters/chapitre_XXX.md` ou les
  fichiers `story_bible/*.md` directement, puis lance
  `python main.py sync --number N` pour que la bible reflete tes
  changements (elle ne fait que se mettre a jour a partir de ce qu'elle lit,
  jamais l'inverse).
- **Verrouillage d'une entite** : ajoute le champ `- **verrouille**: oui`
  dans une fiche (personnage, lieu, faction...) pour empecher l'agent de la
  modifier automatiquement.
- **Notes de direction** : `story_bible/notes.md` (directives globales) et/ou
  `chapters/chapitre_XXX.notes.md` (notes par chapitre), injectees
  automatiquement dans le prompt de redaction.
- **Feedback iteratif** : a la validation d'un plan ou d'un chapitre, tape
  `n` puis un feedback texte libre pour faire regenerer sans perdre la main.
- **Versionner avec git** (recommande) : initialise un depot git dans ce
  dossier et commite apres chaque etape validee, pour un historique complet
  et la possibilite de revenir en arriere.

## Structure de la bible d'univers (`story_bible/*.md`)

- `cosmology.md`, `magic_system.md`, `locations.md`, `timeline.md`,
  `races.md`, `cultures.md`, `religions.md`, `factions.md`, `items.md`,
  `characters.md` — un fichier par categorie, une section `## Nom` par
  entite, avec des champs `- **cle**: valeur` et un historique horodate
  (`### Historique`) qui trace la provenance de chaque information (etape,
  chapitre, confiance, source).
- `premise.md` — pitch/ton/conflit central.
- `cosmology.md` ... `world_state.md` — un document de synthese par etape du
  pipeline de worldbuilding (voir tableau ci-dessus), editables a la main.
- `outline.md` — plan chapitre par chapitre.
- `notes.md` (optionnel) — directives globales de l'auteur.

Champs recommandes pour un personnage POV : `voix_narrative` (registre/ton
propre au personnage), `derniere_position`, `etat_actuel`, `arc_narratif`.

## Recherche web

Utilise l'outil de recherche web natif d'Anthropic (`web_search_20250305`),
sans dependance a une API tierce. Desactivable via `ENABLE_WEB_SEARCH=false`
dans `.env` si tu preferes un univers 100% invente sans reference externe
(cela reduit aussi les tokens consommes, voir section suivante).

## Economiser les tokens

Plusieurs mecanismes reduisent la consommation, certains automatiques, d'autres
a activer/adopter selon tes besoins :

**Automatique (deja actif dans le code) :**
- **Cache de prompt Anthropic** (`cache_control: ephemeral`) : le system prompt
  et le gros bloc de contexte statique (bible, chapitre, notes) de chaque appel
  sont marques cacheables. Des qu'une etape fait plusieurs allers-retours
  d'outils (ex: plusieurs `record_bible_entry` pendant la redaction d'un
  chapitre, ou une longue session `world`/`premise`), ce prefixe n'est repaye
  qu'une fois au lieu d'a chaque tour — le gain augmente avec le nombre
  d'echanges dans une meme commande/session.
- **`summarize_names()`** limite deja la liste de noms envoyee a 50 par
  categorie plutot que d'envoyer les fiches completes de toute la bible.

**A configurer :**
- **`ANTHROPIC_MODEL_LIGHT`** dans `.env` : renseigne un modele moins cher/plus
  rapide (ex: un modele Haiku) pour les taches purement mecaniques
  d'extraction (`sync`, `import-notes`), qui n'ont pas besoin de la puissance
  du modele principal. Laisse vide pour ne rien changer.
- **`ENABLE_WEB_SEARCH=false`** si tu n'as pas besoin d'inspiration/verification
  externe pour une session donnee.

**Bonnes pratiques d'usage :**
- Lance `check` periodiquement (tous les 3-5 chapitres) plutot qu'apres
  chaque chapitre : il renvoie l'integralite des chapitres et de la bible a
  chaque appel, c'est l'etape la plus couteuse en tokens du workflow.
- Lors d'un `chapter`/`critique` refuse (`n`), regroupe TOUTES tes remarques
  dans un seul feedback texte plutot que de regenerer plusieurs fois pour des
  corrections isolees : chaque regeneration renvoie tout le contexte depuis
  zero.
- Garde les documents de synthese du worldbuilding (`story_bible/*.md`)
  concis : ce sont eux, pas la transcription complete du chat, qui sont
  reinjectes dans le contexte des etapes suivantes.
- Verrouille (`- **verrouille**: oui`) les fiches definitives : cela n'evite
  pas de les envoyer en contexte, mais evite des allers-retours de correction
  inutiles avec l'agent qui tenterait de les modifier.

## Pistes pour rendre le workflow encore plus puissant

1. **Regeneration au niveau scene** (pas juste chapitre entier) : decouper
   les chapitres en blocs `## Scene N` et permettre de ne regenerer qu'une
   scene precise avec une instruction ciblee.
2. ~~Passe d'auto-critique avant validation~~ — fait : voir `critique`.
3. **Recherche semantique (RAG) dans la bible** au lieu du dump complet en
   contexte : necessaire quand le worldbuilding + le roman grossissent
   au-dela de la fenetre de contexte du modele (voir aussi section "Economiser
   les tokens").
4. **Verification de coherence incrementale** : ne renvoyer en entier que les
   chapitres non encore verifies par un rapport precedent, en s'appuyant sur
   `timeline.md` (deja peuple via `record_bible_entry`) comme memoire
   compressee des chapitres plus anciens.
5. **Export manuscrit** : compilation de tous les chapitres valides en un
   seul document (Markdown concatene, ou .docx/.epub).
6. **Tableau de bord de pacing** : longueur des chapitres, equilibre entre
   POV, position dans la courbe dramatique.
7. **Branches alternatives** : explorer 2 versions d'un meme chapitre ou
   d'une meme etape de worldbuilding via des branches git.
8. **Glossaire linguistique / prononciation** : fichier dedie aux noms
   inventes (etymologie, prononciation) pour garantir une orthographe stable.
9. **Carte generee** : a partir de `geography.md`, generer une carte
   schematique (SVG) des continents/regions decrits.

## Limites connues

- La verification de coherence (`check`) envoie l'integralite des chapitres
  et de la bible dans le contexte : au-dela d'une vingtaine de chapitres,
  cela peut depasser la fenetre de contexte du modele (cf. pistes 3 et 4).
- La fusion de champs liste dans la bible se base sur un decoupage par
  virgule : evite les virgules a l'interieur d'une valeur individuelle
  (ex: prefere "Ordre des Veilleurs" a "Ordre, des Veilleurs").
