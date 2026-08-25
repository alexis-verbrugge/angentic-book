#!/usr/bin/env python3
"""Etape : critique litteraire severe et constructive d'un chapitre redige,
sur tous les axes qui comptent pour qu'il soit pret a etre edite/publie.

Contrairement a stage_consistency.py (qui verifie la coherence FACTUELLE
entre chapitres et bible), cette etape juge la QUALITE litteraire du texte :
rythme, voix, dialogues, style, impact emotionnel, etc. Elle ne modifie
jamais la bible ni le chapitre : elle produit un rapport de critique."""
from datetime import datetime

import config
import md_bible
import outline_store
import workflow

CRITERIA = [
    "ouverture_et_accroche",
    "rythme_et_tension",
    "voix_narrative_pov",
    "dialogues",
    "descriptions_show_dont_tell",
    "style_et_prose",
    "coherence_personnages_univers",
    "enjeux_et_impact_emotionnel",
    "cloture_et_transition",
]

CRITERIA_LABELS = {
    "ouverture_et_accroche": "Ouverture & accroche",
    "rythme_et_tension": "Rythme & tension narrative",
    "voix_narrative_pov": "Voix narrative / fidelite au POV",
    "dialogues": "Dialogues (naturel, sous-texte, distinction des voix)",
    "descriptions_show_dont_tell": "Descriptions (show, don't tell / equilibre)",
    "style_et_prose": "Style & prose (repetitions, cliches, rythme de phrase)",
    "coherence_personnages_univers": "Coherence avec personnages & univers",
    "enjeux_et_impact_emotionnel": "Enjeux & impact emotionnel",
    "cloture_et_transition": "Cloture du chapitre & transition",
}

SEVERITY_ORDER = {"redhibitoire": 0, "majeure": 1, "moderee": 2, "mineure": 3}

SCORE_ASPECT_TOOL = {
    "name": "score_aspect",
    "description": "Note un aspect precis du chapitre de 1 (tres faible) a 10 (excellent, publiable en l'etat).",
    "input_schema": {
        "type": "object",
        "properties": {
            "aspect": {"type": "string", "enum": CRITERIA},
            "score": {"type": "integer", "minimum": 1, "maximum": 10},
            "justification": {
                "type": "string",
                "description": "Justification concise et factuelle de la note, appuyee sur le texte.",
            },
        },
        "required": ["aspect", "score", "justification"],
    },
}

FLAG_CRITIQUE_TOOL = {
    "name": "flag_critique",
    "description": (
        "Signale un probleme litteraire precis dans le chapitre, avec citation exacte du "
        "texte concerne et une suggestion concrete et actionnable pour le corriger."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "aspect": {"type": "string", "enum": CRITERIA},
            "severity": {
                "type": "string",
                "enum": ["mineure", "moderee", "majeure", "redhibitoire"],
                "description": (
                    "redhibitoire = casse l'immersion ou rend le chapitre non publiable en l'etat ; "
                    "majeure = affaiblit nettement le chapitre ; moderee = a corriger ; "
                    "mineure = detail de finition."
                ),
            },
            "citation": {
                "type": "string",
                "description": "Extrait exact (courte citation) du chapitre concerne par la critique.",
            },
            "probleme": {"type": "string", "description": "Ce qui ne fonctionne pas, et pourquoi."},
            "suggestion": {
                "type": "string",
                "description": "Suggestion concrete et actionnable pour ameliorer ce passage precis.",
            },
        },
        "required": ["aspect", "severity", "citation", "probleme", "suggestion"],
    },
}

SYSTEM_PROMPT = f"""Tu es un editeur litteraire senior specialise en fantasy, reconnu pour son exigence \
implacable ET pour l'utilite de ses retours : les auteurs qui travaillent avec toi progressent vite parce \
que chaque critique est precise, argumentee et actionnable. Ton objectif n'est jamais de decourager mais \
de faire en sorte que ce chapitre devienne publiable.

Tu juges le chapitre fourni sur exactement ces {len(CRITERIA)} axes (aucun de plus, aucun de moins) :
{chr(10).join(f"- {c} : {CRITERIA_LABELS[c]}" for c in CRITERIA)}

Regles strictes :
1. Sois severe : ne mets jamais une note superieure a 7/10 par complaisance. Un 9-10 doit etre reserve a \
un travail qui rivaliserait avec un roman publie par un grand editeur. Un texte "correct mais generique" \
merite un 5-6, pas plus.
2. Sois toujours constructif : CHAQUE probleme signale (flag_critique) doit citer exactement le passage \
concerne (citation) et proposer une suggestion concrete et applicable, jamais une remarque vague du type \
"a ameliorer".
3. Ne complimente jamais sans preciser aussi au moins un axe d'amelioration : meme un excellent chapitre \
a des marges de progression, trouve-les.
4. Appelle score_aspect UNE FOIS pour CHACUN des {len(CRITERIA)} axes ci-dessus (couverture complete \
obligatoire), et flag_critique pour chaque probleme concret identifie (autant de fois que necessaire, \
severite variable).
5. Verifie la coherence du personnage POV et de l'univers avec la fiche de personnage et le resume de \
la bible fournis (axe coherence_personnages_univers) : rupture de voix narrative, contradiction avec des \
traits etablis, incoherence avec le synopsis prevu.
6. Tu peux utiliser web_search si tu as besoin de verifier un principe d'ecriture ou une reference \
(structure en trois actes, techniques de dialogue, etc.) pour etayer une critique, mais reste focalise \
sur CE texte.

Une fois tous les scores et critiques enregistres, termine par une synthese textuelle structuree \
(sans outil) contenant, dans cet ordre :
- Un **verdict** en une phrase : pret a editer / a retravailler / a reecrire en profondeur.
- Les **3 a 5 priorites absolues** a corriger avant tout, classees par impact.
- Un paragraphe court sur ce qui fonctionne deja et doit etre preserve.
Sois direct, sans flatterie inutile, mais jamais meprisant : le but est de faire progresser l'oeuvre."""


def run_critique(number):
    path = config.CHAPTERS_DIR / f"chapitre_{number:03d}.md"
    if not path.exists():
        print(f"✗ Chapitre {number} introuvable ({path}). Lance d'abord `python main.py chapter --number {number}`.")
        return

    chapter_text = path.read_text(encoding="utf-8")
    outline = outline_store.get_chapter(number)
    pov = outline.get("pov", "") if outline else ""
    pov_sheet = md_bible.get_entity_text("characters", pov) if pov else None
    bible_summary = md_bible.summarize_names()

    content_text = f"{bible_summary}\n\n"
    if pov_sheet:
        content_text += f"Fiche du personnage POV ({pov}) :\n{pov_sheet}\n\n"
    if outline:
        content_text += (
            f"Ce qui etait prevu au plan pour ce chapitre — Objectif : {outline.get('objectif', '')} ; "
            f"Synopsis : {outline.get('synopsis', '')}\n\n"
        )
    content_text += f"Texte integral du chapitre {number} a critiquer :\n\n{chapter_text}"

    scores = {}
    issues = []

    def handle_score(args):
        scores[args["aspect"]] = {"score": args["score"], "justification": args["justification"]}
        return f"Note enregistree pour {args['aspect']} : {args['score']}/10."

    def handle_flag(args):
        issues.append(args)
        return "Critique enregistree."

    tools = [SCORE_ASPECT_TOOL, FLAG_CRITIQUE_TOOL]
    if config.ENABLE_WEB_SEARCH:
        tools.insert(0, workflow.WEB_SEARCH_TOOL)

    synthesis = workflow.run_tool_loop(
        system_prompt=SYSTEM_PROMPT,
        content=[{"type": "text", "text": content_text}],
        tools=tools,
        tool_handlers={"score_aspect": handle_score, "flag_critique": handle_flag},
        max_tokens=6000,
    )

    _write_report(number, scores, issues, synthesis)


def _write_report(number, scores, issues, synthesis):
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = config.REPORTS_DIR / f"critique_chapitre_{number:03d}_{timestamp}.md"

    lines = [f"# Critique litteraire — Chapitre {number} — {timestamp}", ""]

    if scores:
        average = sum(s["score"] for s in scores.values()) / len(scores)
        lines.append(f"**Note globale : {average:.1f}/10** (moyenne des {len(scores)} axes juges)")
        lines.append("")
        lines.append("## Notes par axe")
        lines.append("")
        for c in CRITERIA:
            if c in scores:
                s = scores[c]
                lines.append(f"- **{CRITERIA_LABELS[c]} : {s['score']}/10** — {s['justification']}")
            else:
                lines.append(f"- **{CRITERIA_LABELS[c]} : non evalue**")
        lines.append("")
    else:
        lines.append("_Aucune note structuree n'a ete produite._")
        lines.append("")

    lines.append("## Critiques detaillees")
    lines.append("")
    if issues:
        ordered = sorted(issues, key=lambda i: SEVERITY_ORDER.get(i.get("severity", "mineure"), 3))
        for i, issue in enumerate(ordered, 1):
            lines.append(
                f"{i}. **[{issue['severity'].upper()}] {CRITERIA_LABELS.get(issue['aspect'], issue['aspect'])}**"
            )
            lines.append(f"   - Citation : \"{issue['citation']}\"")
            lines.append(f"   - Probleme : {issue['probleme']}")
            lines.append(f"   - Suggestion : {issue['suggestion']}")
            lines.append("")
    else:
        lines.append("Aucune critique detaillee n'a ete produite.")
        lines.append("")

    lines.append("## Synthese de l'editeur")
    lines.append("")
    lines.append(synthesis or "_Aucune synthese produite._")

    report_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"\n{synthesis}\n")
    print(f"✓ Rapport de critique sauvegarde dans {report_path}")
    if scores:
        average = sum(s["score"] for s in scores.values()) / len(scores)
        print(f"Note globale : {average:.1f}/10 — {len(issues)} critique(s) detaillee(s).")
