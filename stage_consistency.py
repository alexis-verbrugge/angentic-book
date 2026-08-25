#!/usr/bin/env python3
"""Etape 4 : verification de coherence entre tous les chapitres rediges et la
bible d'univers (statuts, chronologie, regles de magie, descriptions...)."""
from datetime import datetime

import config
import md_bible
import workflow

FLAG_ISSUE_TOOL = {
    "name": "flag_issue",
    "description": "Signale une incoherence detectee entre les chapitres et/ou la bible d'univers.",
    "input_schema": {
        "type": "object",
        "properties": {
            "severity": {"type": "string", "enum": ["mineure", "moderee", "majeure"]},
            "description": {"type": "string"},
            "location": {
                "type": "string",
                "description": "Ou se trouve l'incoherence, ex: 'Chapitre 3 vs bible personnages'.",
            },
        },
        "required": ["severity", "description", "location"],
    },
}

SYSTEM_PROMPT = """Tu es un correcteur de coherence narrative pour un roman a plusieurs personnages POV. \
Compare l'ensemble des chapitres rediges entre eux et avec la bible d'univers fournie. Detecte les \
contradictions : statut d'un personnage (vivant/mort), chronologie des evenements (utilise la categorie \
'timeline' de la bible pour verifier que les evenements concordent entre les differents fils POV, y \
compris quand deux personnages sont censes se croiser ou vivre des evenements simultanes), description \
physique, regles du systeme de magie, noms de lieux/personnages incoherents. Pour chaque probleme \
trouve, appelle l'outil flag_issue. Termine par un court resume global de l'etat de coherence du roman \
(en francais), y compris un avis sur l'equilibre entre les differents fils POV."""


def run_check():
    chapter_paths = sorted(config.CHAPTERS_DIR.glob("chapitre_*.md")) if config.CHAPTERS_DIR.exists() else []
    if not chapter_paths:
        print("✗ Aucun chapitre redige a verifier.")
        return

    chapters_texts = [p.read_text(encoding="utf-8") for p in chapter_paths]

    bible_texts = []
    for category in md_bible.CATEGORIES:
        f = md_bible._file(category)
        if f.exists():
            bible_texts.append(f.read_text(encoding="utf-8"))

    issues = []

    def handle_flag(args):
        issues.append(args)
        return "Incoherence enregistree."

    content_text = (
        "Bible d'univers :\n"
        + "\n\n".join(bible_texts)
        + "\n\nChapitres rediges :\n"
        + "\n\n---\n\n".join(chapters_texts)
    )

    summary = workflow.run_tool_loop(
        system_prompt=SYSTEM_PROMPT,
        content=[{"type": "text", "text": content_text}],
        tools=[FLAG_ISSUE_TOOL],
        tool_handlers={"flag_issue": handle_flag},
        max_tokens=4000,
    )

    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = config.REPORTS_DIR / f"consistency_{timestamp}.md"

    lines = [f"# Rapport de coherence — {timestamp}", "", summary, "", "## Incoherences detectees", ""]
    if issues:
        for i, issue in enumerate(issues, 1):
            lines.append(f"{i}. **[{issue['severity']}]** {issue['location']} — {issue['description']}")
    else:
        lines.append("Aucune incoherence detectee.")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"✓ Rapport sauvegarde dans {report_path}")
    print(f"\n{len(issues)} incoherence(s) detectee(s).")
