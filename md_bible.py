#!/usr/bin/env python3
"""Bible d'univers en Markdown : personnages, lieux, factions, systeme de
magie, objets. Chaque fichier contient une section '## Nom' par entite, avec
des champs '- **cle**: valeur' et un historique horodate des mises a jour.
"""
import re

from config import BIBLE_DIR

CATEGORIES = ["characters", "locations", "factions", "magic_system", "items", "timeline"]

FILE_TITLES = {
    "characters": "Personnages",
    "locations": "Lieux",
    "factions": "Factions",
    "magic_system": "Systeme de magie",
    "items": "Objets",
    "timeline": "Chronologie (evenements cles, tous fils POV confondus)",
}

LOCK_FIELD = "verrouille"
LOCK_VALUES = {"oui", "yes", "true"}


def _file(category):
    return BIBLE_DIR / f"{category}.md"


def ensure_bible_files():
    BIBLE_DIR.mkdir(parents=True, exist_ok=True)
    for category in CATEGORIES:
        f = _file(category)
        if not f.exists():
            f.write_text(f"# {FILE_TITLES[category]}\n\n", encoding="utf-8")


def parse_sections(text):
    """Retourne une liste de tuples (nom_entite, bloc_markdown_complet)."""
    if not text or "## " not in text:
        return []
    lines = text.splitlines()
    sections = []
    header = None
    buf = []
    for line in lines:
        if line.startswith("## "):
            if header is not None:
                sections.append((header, "\n".join(buf).rstrip() + "\n"))
            header = line[3:].strip()
            buf = [line]
        elif header is not None:
            buf.append(line)
    if header is not None:
        sections.append((header, "\n".join(buf).rstrip() + "\n"))
    return sections


def list_names(category):
    f = _file(category)
    if not f.exists():
        return []
    return [name for name, _ in parse_sections(f.read_text(encoding="utf-8"))]


def get_entity_text(category, name):
    """Retourne le bloc markdown complet d'une entite (fiche complete), ou None."""
    f = _file(category)
    if not f.exists():
        return None
    for header, block in parse_sections(f.read_text(encoding="utf-8")):
        if header.strip().lower() == name.strip().lower():
            return block
    return None


def summarize_names():
    lines = ["Bible d'univers existante (noms deja connus, a reutiliser si l'entite existe deja) :"]
    for category in CATEGORIES:
        names = list_names(category)
        shown = ", ".join(names[:50]) if names else "(vide)"
        lines.append(f"- {category}: {shown}")
    return "\n".join(lines)


def _split_list(raw):
    return [v.strip() for v in raw.split(",") if v.strip()] if raw else []


def _parse_entity_fields(block_text):
    lines = block_text.splitlines()[1:]  # ignore la ligne "## Nom"
    fields = {}
    history = []
    in_history = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("### Historique"):
            in_history = True
            continue
        if in_history:
            if stripped.startswith("- "):
                history.append(stripped[2:])
            continue
        m = re.match(r"-\s+\*\*(.+?)\*\*:\s*(.*)", stripped)
        if m:
            fields[m.group(1)] = m.group(2)
    return fields, history


def _render_entity(name, fields, history):
    lines = [f"## {name}", ""]
    for key, value in fields.items():
        lines.append(f"- **{key}**: {value}")
    lines.append("")
    lines.append("### Historique")
    for entry in history:
        lines.append(f"- {entry}")
    lines.append("")
    return "\n".join(lines) + "\n"


def record_entity(category, name, data, confidence="likely", source="chapitre", chapter_ref=None):
    """Cree ou met a jour une entite. Les champs texte sont ecrases, les listes
    sont fusionnees sans doublon, et une ligne d'historique est ajoutee a chaque
    appel pour tracer la provenance de l'information."""
    if category not in CATEGORIES:
        raise ValueError(f"Categorie inconnue: {category}")

    ensure_bible_files()
    path = _file(category)
    text = path.read_text(encoding="utf-8")
    sections = parse_sections(text)

    match_index = None
    display_name = name
    for i, (header, _) in enumerate(sections):
        if header.strip().lower() == name.strip().lower():
            match_index = i
            display_name = header
            break

    is_new = match_index is None
    if is_new:
        fields, history = {}, []
    else:
        _, block = sections[match_index]
        fields, history = _parse_entity_fields(block)

    if not is_new and fields.get(LOCK_FIELD, "").strip().lower() in LOCK_VALUES:
        # L'auteur a verrouille cette entite : on trace la tentative sans rien modifier.
        history.append(
            f"[{chapter_ref or '?'}] Mise a jour ignoree (entite verrouillee par l'auteur) — source: {source}"
        )
        new_block = _render_entity(display_name, fields, history)
        sections[match_index] = (display_name, new_block)
        header_line = f"# {FILE_TITLES[category]}\n\n"
        new_text = header_line + "\n".join(block for _, block in sections)
        path.write_text(new_text.rstrip() + "\n", encoding="utf-8")
        return {"is_new": False, "name": display_name, "category": category, "locked": True}

    data = dict(data)
    history_note = data.pop("history_note", "")

    for key, value in data.items():
        if isinstance(value, list):
            existing = _split_list(fields.get(key, ""))
            merged = existing + [str(v) for v in value if str(v) not in existing]
            fields[key] = ", ".join(merged)
        else:
            fields[key] = str(value)

    history.append(
        f"[{chapter_ref or '?'}] ({confidence}, source: {source}) — {history_note or fields.get('description', '')}"
    )

    new_block = _render_entity(display_name, fields, history)

    if is_new:
        sections.append((display_name, new_block))
    else:
        sections[match_index] = (display_name, new_block)

    header_line = f"# {FILE_TITLES[category]}\n\n"
    new_text = header_line + "\n".join(block for _, block in sections)
    path.write_text(new_text.rstrip() + "\n", encoding="utf-8")
    return {"is_new": is_new, "name": display_name, "category": category, "locked": False}
