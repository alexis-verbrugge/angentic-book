#!/usr/bin/env python3
"""Moteur agentique partage : boucle d'appel a Claude avec outils (tool use),
outil de recherche web natif, et boucle de validation humaine avec feedback."""
from anthropic import Anthropic

import config
import md_bible

WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 6,
}

RECORD_BIBLE_TOOL = {
    "name": "record_bible_entry",
    "description": (
        "Cree ou met a jour une entite de la bible d'univers (personnage, lieu, "
        "faction, systeme de magie, objet, ou evenement de la chronologie 'timeline' "
        "partagee entre tous les fils POV). A appeler pour tout element notable "
        "nouveau ou modifie. Si l'entite est marquee verrouillee par l'auteur, la "
        "mise a jour sera ignoree automatiquement."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "category": {"type": "string", "enum": md_bible.CATEGORIES},
            "name": {
                "type": "string",
                "description": "Nom canonique de l'entite (reutiliser le nom existant si connu).",
            },
            "data": {
                "type": "object",
                "description": (
                    "Champs a fusionner (ex: description, alias, statut, affiliations, "
                    "pouvoirs, apparence, history_note, ...)."
                ),
            },
            "confidence": {"type": "string", "enum": ["confirmed", "likely", "uncertain"]},
            "source": {"type": "string"},
        },
        "required": ["category", "name", "data"],
    },
}


def get_client():
    return Anthropic(api_key=config.ANTHROPIC_API_KEY)


def make_bible_handler(chapter_ref, source_label):
    def handler(args):
        result = md_bible.record_entity(
            category=args["category"],
            name=args["name"],
            data=args.get("data", {}),
            confidence=args.get("confidence", "likely"),
            source=args.get("source", source_label),
            chapter_ref=chapter_ref,
        )
        if result.get("locked"):
            return (
                f"{result['category']}/{result['name']} est verrouille par l'auteur : "
                "mise a jour ignoree."
            )
        return (
            f"Enregistre : {result['category']}/{result['name']} "
            f"({'nouveau' if result['is_new'] else 'mis a jour'})"
        )

    return handler


def run_tool_loop(system_prompt, content, tools, tool_handlers, max_tokens=None):
    """Boucle generique d'appel a Claude avec tool use. `tool_handlers` est un
    dict {nom_outil: fonction(input_dict) -> texte_resultat}. Les outils
    serveur (ex: web_search) sont geres automatiquement par l'API et n'ont pas
    besoin de handler."""
    client = get_client()
    messages = [{"role": "user", "content": content}]

    while True:
        response = client.messages.create(
            model=config.MODEL,
            max_tokens=max_tokens or config.MAX_TOKENS,
            system=system_prompt,
            tools=tools,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in response.content:
            if block.type == "tool_use" and block.name in tool_handlers:
                result_text = tool_handlers[block.name](block.input)
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": result_text}
                )

        if tool_results:
            messages.append({"role": "user", "content": tool_results})
            continue

        return "".join(block.text for block in response.content if block.type == "text")


def validate_with_feedback(generate_fn, describe_fn):
    """Boucle de validation humaine : genere, affiche, et redemande avec
    feedback tant que l'auteur ne valide pas (ou n'annule pas)."""
    feedback = None
    while True:
        result = generate_fn(feedback)
        describe_fn(result)
        answer = input("\nValider ? (o = oui / n = regenerer avec feedback / q = annuler) : ").strip().lower()
        if answer == "o":
            return result
        if answer == "q":
            return None
        feedback = input("Feedback pour la regeneration : ").strip()
