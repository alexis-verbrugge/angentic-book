#!/usr/bin/env python3
"""Pipeline de worldbuilding complet pour un univers fantasy, dans l'ordre
"top-down" recommande par les worldbuilders pro (cosmologie -> magie ->
geographie -> histoire -> peuples -> religions -> politique -> lieux notables
-> synthese) : chaque etape s'appuie sur celles deja etablies, evite les
incoherences, et nourrit directement la bible d'univers.

Chaque etape est une discussion interactive (comme la premisse) : l'auteur
et l'agent construisent l'etape ensemble, l'agent enregistre les entites au
fur et a mesure (record_bible_entry), et /valider produit un document de
synthese sauvegarde dans story_bible/<doc>.
"""
import config
import md_bible
import workflow

BASE_PROMPT = """Tu es un worldbuilder professionnel specialise en fantasy (a la maniere de Brandon \
Sanderson, N.K. Jemisin, ou des concepteurs de settings de jeux de role). Tu accompagnes l'auteur \
etape par etape pour construire un univers riche et coherent, en t'appuyant sur ce qui a deja ete \
etabli (fourni ci-dessous en contexte). Pose des questions precises, une ou deux a la fois, propose \
des choix concrets (evite les generalites vagues et les cliches plats), et utilise l'outil web_search \
si tu as besoin de t'inspirer de mythologies, folklores ou references historiques reelles. Enregistre \
au fur et a mesure les entites importantes via record_bible_entry, dans la ou les categorie(s) \
indiquee(s) pour cette etape, en reutilisant les noms deja connus quand ils correspondent. Quand \
l'auteur tape /valider, redige un document de synthese clair et structure (titres, listes) de tout ce \
qui a ete decide pour cette etape."""

WORLD_STAGES = [
    {
        "key": "cosmology",
        "label": "Cosmologie & metaphysique",
        "doc": "cosmology.md",
        "categories": "cosmology",
        "focus": (
            "ETAPE 1 — Cosmologie & metaphysique. Explore avec l'auteur : comment le monde a-t-il ete "
            "cree (mythe(s) de creation) ? Quelle est la nature de la realite (plans d'existence, "
            "forces cosmiques, cycles, magie primordiale) ? Y a-t-il des dieux/entites superieures : "
            "quel est leur role, leur caractere, leur rapport au monde mortel ? Que devient-on apres la "
            "mort ? Enregistre chaque entite cosmologique importante (dieu, plan d'existence, force "
            "fondamentale) via record_bible_entry (categorie 'cosmology')."
        ),
    },
    {
        "key": "magic",
        "label": "Systeme de magie",
        "doc": "magic_system_overview.md",
        "categories": "magic_system",
        "focus": (
            "ETAPE 2 — Systeme de magie. Definis un systeme coherent selon les principes eprouves du "
            "genre (cf. lois de Sanderson) : quelle est la SOURCE du pouvoir (lien avec la cosmologie "
            "deja etablie) ? Qui peut y acceder et pourquoi (inne, appris, pacte, rituel) ? Quelles "
            "sont les LIMITES et les COUTS concrets (plus ils sont clairs, moins la magie devient un "
            "deus ex machina) ? Comment la societe percoit-elle la magie (peur, veneration, "
            "reglementation, interdits) ? Quels usages quotidiens/militaires en decoulent ? Enregistre "
            "chaque regle, ecole ou tradition magique via record_bible_entry (categorie 'magic_system')."
        ),
    },
    {
        "key": "geography",
        "label": "Geographie & climat",
        "doc": "geography.md",
        "categories": "locations",
        "focus": (
            "ETAPE 3 — Geographie & climat. Construis la geographie physique du monde : "
            "continents/regions majeures, climats et biomes, ressources naturelles marquantes, "
            "barrieres naturelles (montagnes, mers, deserts) et comment elles ont faconne les "
            "frontieres, les routes commerciales et les rivalites. Reflechis a comment cette geographie "
            "va justifier les cultures et conflits definis dans les etapes suivantes. Enregistre chaque "
            "region/continent majeur via record_bible_entry (categorie 'locations')."
        ),
    },
    {
        "key": "history",
        "label": "Histoire & chronologie",
        "doc": "history.md",
        "categories": "timeline",
        "focus": (
            "ETAPE 4 — Histoire & chronologie. Construis la grande Histoire de cet univers : eres "
            "majeures, evenements fondateurs, cataclysmes, essor et chute de civilisations, menant "
            "jusqu'a la situation actuelle (celle ou commencera le roman). Chaque evenement marquant "
            "doit expliquer une consequence encore visible aujourd'hui (une ruine, une rancune, une "
            "loi, une peur collective). Enregistre chaque evenement cle via record_bible_entry "
            "(categorie 'timeline'), avec un champ 'epoque' pour l'ordonner."
        ),
    },
    {
        "key": "peoples",
        "label": "Peuples, especes & cultures",
        "doc": "peoples_and_cultures.md",
        "categories": "races, cultures",
        "focus": (
            "ETAPE 5 — Peuples, especes & cultures. Definis d'abord les peuples/especes intelligents "
            "de cet univers (biologie, duree de vie, capacites particulieres, relations inter-especes) "
            "via record_bible_entry (categorie 'races'). PUIS, pour chaque grande culture/societe qui "
            "en decoule : valeurs, tabous, structure familiale/sociale, art, coutumes marquantes, "
            "rapport a la magie et aux autres peuples, via record_bible_entry (categorie 'cultures'). "
            "Assume des tensions internes plutot qu'un peuple = un seul trait plat."
        ),
    },
    {
        "key": "religions",
        "label": "Religions & croyances",
        "doc": "religions.md",
        "categories": "religions",
        "focus": (
            "ETAPE 6 — Religions & croyances. Distingue la pratique religieuse concrete de la "
            "cosmologie deja definie : cultes, clerge et hierarchie religieuse, rituels marquants, "
            "lieux sacres, sectes ou heresies, tensions entre foi et pouvoir politique/magique. "
            "Enregistre chaque culte/religion via record_bible_entry (categorie 'religions')."
        ),
    },
    {
        "key": "politics",
        "label": "Politique & factions",
        "doc": "politics_and_factions.md",
        "categories": "factions",
        "focus": (
            "ETAPE 7 — Politique & factions. Definis les structures de pouvoir actuelles : "
            "gouvernements, guildes, ordres, factions rebelles, avec leurs objectifs, moyens, "
            "rivalites et alliances. Identifie au moins un conflit ou une tension majeure en cours qui "
            "pourra nourrir l'intrigue du roman. Enregistre chaque faction via record_bible_entry "
            "(categorie 'factions')."
        ),
    },
    {
        "key": "landmarks",
        "label": "Lieux notables & objets marquants",
        "doc": "landmarks_and_items.md",
        "categories": "locations, items",
        "focus": (
            "ETAPE 8 — Lieux notables & objets marquants. Identifie les lieux notables (villes cles, "
            "sites sacres, ruines, forteresses) issus de la geographie/histoire/politique deja "
            "etablies, et les objets/artefacts culturellement ou historiquement importants. Enregistre "
            "les lieux via record_bible_entry (categorie 'locations') et les objets (categorie "
            "'items')."
        ),
    },
    {
        "key": "synthesis",
        "label": "Synthese : etat du monde au debut de l'histoire",
        "doc": "world_state.md",
        "categories": "(aucune — document de synthese uniquement)",
        "focus": (
            "ETAPE 9 — Synthese finale. A partir de TOUT ce qui a ete etabli (cosmologie, magie, "
            "geographie, histoire, peuples, religions, politique, lieux), redige une synthese de "
            "l'etat du monde au moment ou commence le roman : quelles tensions sont sur le point "
            "d'exploser ? Quel equilibre est fragile ? Quels secrets ne sont pas encore reveles au "
            "grand jour ? Cette synthese servira de pont direct vers le plan du roman (`python main.py "
            "outline`)."
        ),
    },
]

_STAGES_BY_KEY = {s["key"]: s for s in WORLD_STAGES}


def list_stages():
    print("=== Pipeline de worldbuilding (ordre recommande) ===\n")
    for i, stage in enumerate(WORLD_STAGES, 1):
        doc_path = config.BIBLE_DIR / stage["doc"]
        done = "✓" if doc_path.exists() else " "
        print(f"{i}. [{done}] {stage['key']:<10} — {stage['label']} (categories: {stage['categories']})")
    print("\nLance une etape avec : python main.py world --stage <cle>")
    print("Exemple : python main.py world --stage cosmology")


def _previous_context(stage_key):
    parts = []
    premise_path = config.BIBLE_DIR / "premise.md"
    if premise_path.exists():
        parts.append("Premisse du roman (deja etablie) :\n" + premise_path.read_text(encoding="utf-8"))

    for prev in WORLD_STAGES:
        if prev["key"] == stage_key:
            break
        prev_doc = config.BIBLE_DIR / prev["doc"]
        if prev_doc.exists():
            parts.append(f"{prev['label']} (deja etabli) :\n" + prev_doc.read_text(encoding="utf-8"))

    parts.append(md_bible.summarize_names())
    return "\n\n---\n\n".join(parts)


def run_stage(key):
    stage = _STAGES_BY_KEY.get(key)
    if not stage:
        valid = ", ".join(_STAGES_BY_KEY.keys())
        print(f"✗ Etape inconnue '{key}'. Etapes valides : {valid}")
        return

    system_prompt = f"{BASE_PROMPT}\n\n{stage['focus']}\n\n--- Contexte deja etabli ---\n{_previous_context(key)}"
    intro = (
        f"=== Worldbuilding — {stage['label']} ===\n"
        "Discute avec l'agent pour construire cette etape. Tape /valider pour figer le document de "
        "synthese, /quitter pour sortir sans sauvegarder.\n"
    )
    doc_path = config.BIBLE_DIR / stage["doc"]

    workflow.run_interactive_stage(system_prompt=system_prompt, doc_path=doc_path, intro_message=intro)
