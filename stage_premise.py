#!/usr/bin/env python3
"""Etape 1 : discussion interactive pour definir la premisse du roman."""
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
    client = workflow.get_client()
    messages = []
    print(
        "Discussion pour definir la premisse du roman.\n"
        "Tape /valider quand tu es pret a figer la premisse, /quitter pour sortir sans sauvegarder.\n"
    )
    while True:
        user_input = input("Toi > ").strip()
        if user_input == "/quitter":
            print("Session annulee, rien n'a ete sauvegarde.")
            return

        user_message = user_input
        if user_input == "/valider":
            user_message = "Redige maintenant le document de premisse final, structure comme demande."

        messages.append({"role": "user", "content": user_message})
        response = client.messages.create(
            model=config.MODEL,
            max_tokens=config.MAX_TOKENS,
            system=SYSTEM_PROMPT,
            tools=[workflow.WEB_SEARCH_TOOL] if config.ENABLE_WEB_SEARCH else [],
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})
        text = "".join(block.text for block in response.content if block.type == "text")
        print(f"\nAgent > {text}\n")

        if user_input == "/valider":
            config.BIBLE_DIR.mkdir(parents=True, exist_ok=True)
            path = config.BIBLE_DIR / "premise.md"
            path.write_text(text, encoding="utf-8")
            print(f"✓ Premisse sauvegardee dans {path}")
            return
