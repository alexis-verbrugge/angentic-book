#!/usr/bin/env python3
"""Etape : generation du plan du roman (chapitre par chapitre, multi-POV),
avec validation humaine et feedback avant sauvegarde definitive."""
import config
import md_bible
import outline_store
import workflow

SAVE_OUTLINE_TOOL = {
    "name": "save_outline",
    "description": "Sauvegarde le plan complet du roman, chapitre par chapitre.",
    "input_schema": {
        "type": "object",
        "properties": {
            "chapters": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "number": {"type": "integer"},
                        "title": {"type": "string"},
                        "pov": {"type": "string"},
                        "objectif": {"type": "string"},
                        "synopsis": {"type": "string"},
                    },
                    "required": ["number", "title", "synopsis"],
                },
            }
        },
        "required": ["chapters"],
    },
}

SYSTEM_PROMPT = """Tu es un co-auteur expert en structure narrative fantasy (structure en trois actes, \
voyage du heros) pour un roman a PLUSIEURS PERSONNAGES POV (points de vue alternes, comme dans un roman \
choral). A partir de la premisse et de la bible d'univers (worldbuilding) deja etablies, propose un \
decoupage chapitre par chapitre coherent, avec une progression dramatique claire (mise en place, montee \
des enjeux, climax, resolution) pour chaque fil POV. Assure une rotation equilibree entre les \
personnages POV (evite qu'un personnage disparaisse trop longtemps), et prevois des points de \
convergence ou les fils se croisent. Utilise l'outil web_search si tu as besoin d'inspiration \
(structures narratives, mythologies, folklore). Pour chaque personnage/lieu/faction principal introduit \
dans le plan, appelle record_bible_entry (pour un personnage POV recurrent, precise son role et son \
arc dans le champ 'arc_narratif'). Termine en appelant save_outline UNE SEULE FOIS avec la liste \
complete et finale des chapitres, en indiquant le POV de chacun."""


def generate_outline(num_chapters=12):
    premise_path = config.BIBLE_DIR / "premise.md"
    if not premise_path.exists():
        print("✗ Aucune premisse trouvee. Lance d'abord `python main.py premise`.")
        return None
    premise_text = premise_path.read_text(encoding="utf-8")

    saved = {}

    def handle_save_outline(args):
        saved["chapters"] = args["chapters"]
        return f"Plan sauvegarde avec {len(args['chapters'])} chapitres."

    tools = [workflow.RECORD_BIBLE_TOOL, SAVE_OUTLINE_TOOL]
    if config.ENABLE_WEB_SEARCH:
        tools.insert(0, workflow.WEB_SEARCH_TOOL)

    def generate(feedback):
        saved.clear()
        content_text = (
            f"Premisse du roman :\n{premise_text}\n\n"
            f"{md_bible.summarize_names()}\n\n"
            f"Propose un plan en environ {num_chapters} chapitres pour ce roman fantasy multi-personnages, "
            "en alternant les points de vue de maniere equilibree."
        )
        if feedback:
            content_text += f"\n\nFeedback de l'auteur a integrer par rapport a la version precedente : {feedback}"

        workflow.run_tool_loop(
            system_prompt=SYSTEM_PROMPT,
            content=[{"type": "text", "text": content_text}],
            tools=tools,
            tool_handlers={
                "record_bible_entry": workflow.make_bible_handler(chapter_ref="plan", source_label="plan"),
                "save_outline": handle_save_outline,
            },
        )
        return saved.get("chapters")

    def describe(chapters):
        if not chapters:
            print("✗ L'agent n'a pas produit de plan exploitable.")
            return
        print("\n=== Plan propose ===")
        for ch in sorted(chapters, key=lambda c: c["number"]):
            print(f"Chapitre {ch['number']} — {ch['title']} (POV: {ch.get('pov', '?')})")
            synopsis = ch.get("synopsis", "")
            print(f"  {synopsis[:200]}{'...' if len(synopsis) > 200 else ''}")

    result = workflow.validate_with_feedback(generate, describe)
    if result:
        outline_store.save_outline(result)
        print(f"✓ Plan sauvegarde dans {outline_store.OUTLINE_PATH}")
    return result
