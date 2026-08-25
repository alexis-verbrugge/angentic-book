#!/usr/bin/env python3
"""Moteur agentique partage :
- boucle d'appel a Claude avec outils (tool use) pour les taches non interactives
  (outline, chapter, consistency check) ;
- boucle interactive (chat) avec tool use, pour les etapes de dialogue avec
  l'auteur (premise, pipeline de worldbuilding) ;
- boucle de validation humaine avec feedback avant sauvegarde definitive.
"""
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
        "Cree ou met a jour une entite de la bible d'univers (cosmologie, systeme de "
        "magie, lieu, evenement de la chronologie 'timeline', peuple/espece, culture, "
        "religion, faction, objet, personnage). A appeler pour tout element notable "
        "nouveau ou modifie. Si l'entite est marquee verrouillee par l'auteur, la mise "
        "a jour sera ignoree automatiquement."
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


def _cached(text):
    """Marque un bloc de texte comme cacheable cote Anthropic (prompt caching).
    Le prefixe (system prompt et/ou gros contexte statique comme la bible ou un
    chapitre) est alors reutilise sans etre repaye a chaque aller-retour d'un
    meme appel multi-tours (tool use) ou d'une session de chat interactive,
    ce qui reduit fortement la consommation de tokens facturee."""
    return {"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}


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


def run_tool_loop(system_prompt, content, tools, tool_handlers, max_tokens=None, model=None):
    """Boucle generique (non interactive) d'appel a Claude avec tool use.
    `tool_handlers` est un dict {nom_outil: fonction(input_dict) -> texte_resultat}.
    Les outils serveur (ex: web_search) sont geres automatiquement par l'API et
    n'ont pas besoin de handler. `model` permet d'utiliser un modele plus
    economique (config.MODEL_LIGHT) pour les taches mecaniques d'extraction.

    Le system prompt et le dernier bloc de `content` sont marques cacheables :
    quand la boucle fait plusieurs allers-retours (plusieurs appels d'outils
    successifs), ce prefixe n'est repaye qu'une fois au lieu d'a chaque tour."""
    client = get_client()
    content = list(content)
    if content and content[-1].get("type") == "text":
        content[-1] = _cached(content[-1]["text"])
    messages = [{"role": "user", "content": content}]

    while True:
        response = client.messages.create(
            model=model or config.MODEL,
            max_tokens=max_tokens or config.MAX_TOKENS,
            system=[_cached(system_prompt)],
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


def run_interactive_stage(system_prompt, doc_path, intro_message=None):
    """Boucle interactive (chat en console) avec l'auteur, avec acces a
    web_search et record_bible_entry pendant la discussion. Quand l'auteur
    tape /valider, demande un document de synthese final et le sauvegarde
    dans `doc_path`. /quitter sort sans rien sauvegarder."""
    client = get_client()
    tools = [RECORD_BIBLE_TOOL]
    if config.ENABLE_WEB_SEARCH:
        tools.insert(0, WEB_SEARCH_TOOL)
    handlers = {
        "record_bible_entry": make_bible_handler(
            chapter_ref=f"worldbuilding:{doc_path.stem}", source_label=doc_path.stem
        )
    }

    messages = []
    print(
        intro_message
        or "Tape /valider pour figer le document final, /quitter pour sortir sans sauvegarder.\n"
    )

    while True:
        user_input = input("Toi > ").strip()
        if user_input == "/quitter":
            print("Session annulee, rien n'a ete sauvegarde.")
            return None

        user_message = user_input
        if user_input == "/valider":
            user_message = (
                "Redige maintenant le document de synthese final de cette etape, structure "
                "clairement (titres, listes), en te basant sur toute la discussion precedente."
            )
        messages.append({"role": "user", "content": user_message})

        while True:
            # Le system prompt (souvent volumineux : contexte des etapes precedentes +
            # bible) est marque cacheable : sur une session de chat avec plusieurs
            # echanges, il n'est repaye en entier qu'une fois.
            response = client.messages.create(
                model=config.MODEL,
                max_tokens=config.MAX_TOKENS,
                system=[_cached(system_prompt)],
                tools=tools,
                messages=messages,
            )
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use" and block.name in handlers:
                    result_text = handlers[block.name](block.input)
                    tool_results.append(
                        {"type": "tool_result", "tool_use_id": block.id, "content": result_text}
                    )

            if tool_results:
                messages.append({"role": "user", "content": tool_results})
                continue
            break

        text = "".join(block.text for block in response.content if block.type == "text")
        print(f"\nAgent > {text}\n")

        if user_input == "/valider":
            doc_path.parent.mkdir(parents=True, exist_ok=True)
            doc_path.write_text(text, encoding="utf-8")
            print(f"✓ Document sauvegarde dans {doc_path}")
            return text


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
