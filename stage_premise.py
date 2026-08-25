#!/usr/bin/env python3
"""Etape 0 : discussion interactive pour definir la premisse du roman
(concept, ton, genre, conflit central) — le point de depart avant le
pipeline de worldbuilding complet."""
import config
import workflow

SYSTEM_PROMPT = """Tu es un co-auteur expert en litterature fantasy qui aide l'utilisateur a definir \
la premisse de son roman : univers, ton, conflit central, enjeux, inspirations. Pose des questions \
pertinentes une a la fois, propose des pistes concretes, utilise l'outil web_search si tu as besoin \
de t'inspirer de mythologies, folklores ou references historiques reelles. Reste concis dans tes \
reponses intermediaires.

Quand l'utilisateur tape /valider, redige un document de premisse final, structure en francais avec \
ces sections : Titre provisoire, Pitch (3-4 phrases), Ton et registre, Univers (un paragraphe), \
Conflit central, Themes."""


def run_premise_chat():
    workflow.run_interactive_stage(
        system_prompt=SYSTEM_PROMPT,
        doc_path=config.BIBLE_DIR / "premise.md",
        intro_message=(
            "Discussion pour definir la premisse du roman.\n"
            "Tape /valider quand tu es pret a figer la premisse, /quitter pour sortir sans sauvegarder.\n"
        ),
    )
