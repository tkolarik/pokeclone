import json
import os

import pygame

from src.core import config
from src.core.monster_schema import (
    derive_move_pool_from_learnset,
    normalize_monster,
    normalize_monsters,
)
from src.editor.constrained_fields import (
    load_move_options,
    load_type_options,
    normalize_learnset_entries,
    normalize_multi_selection,
    normalize_single_selection,
)
from src.editor.editor_ui import Button

LIST_PANEL_WIDTH = 320
PADDING = 20
ITEM_HEIGHT = 32
STATUS_DURATION_MS = 2500


def load_monsters():
    monsters_file = os.path.join(config.DATA_DIR, "monsters.json")
    try:
        with open(monsters_file, "r") as f:
            monsters = json.load(f)
        normalized_monsters, warnings = normalize_monsters(monsters, strict_conflicts=False)
        for warning in warnings:
            print(f"Monster schema warning: {warning}")
        return normalized_monsters
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        print(f"Error loading monsters: {exc}")
        return []


def save_monsters(monsters):
    monsters_file = os.path.join(config.DATA_DIR, "monsters.json")
    normalized_monsters, warnings = normalize_monsters(monsters, strict_conflicts=False)
    for warning in warnings:
        print(f"Monster schema warning: {warning}")
    with open(monsters_file, "w") as f:
        json.dump(normalized_monsters, f, indent=4)
    print(f"Saved {len(normalized_monsters)} monsters to {monsters_file}")


def load_move_names():
    return load_move_options(config.DATA_DIR)


def load_type_names():
    return load_type_options(config.DATA_DIR)


def ensure_monster_structure(monster):
    normalized_monster, warnings = normalize_monster(monster, strict_conflicts=False)
    for warning in warnings:
        print(f"Monster schema warning: {warning}")
    monster.clear()
    monster.update(normalized_monster)


def clamp_scroll(selected_index, scroll_offset, visible_count, total_count):
    if selected_index < scroll_offset:
        scroll_offset = selected_index
    elif selected_index >= scroll_offset + visible_count:
        scroll_offset = selected_index - visible_count + 1
    max_scroll = max(0, total_count - visible_count)
    scroll_offset = max(0, min(scroll_offset, max_scroll))
    return scroll_offset


def draw_wrapped_text(surface, text, rect, font, color):
    words = text.split()
    lines = []
    line = ""
    for word in words:
        test_line = f"{line} {word}".strip()
        if font.size(test_line)[0] <= rect.width:
            line = test_line
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)

    y = rect.top
    for line in lines:
        if y + font.get_height() > rect.bottom:
            break
        surf = font.render(line, True, color)
        surface.blit(surf, (rect.left, y))
        y += font.get_height() + 2


def prompt_text(screen, prompt, default="", numeric=False):
    font = pygame.font.Font(config.DEFAULT_FONT, 24)
    small_font = pygame.font.Font(config.DEFAULT_FONT, 18)
    input_text = ""
    clock = pygame.time.Clock()

    while True:
        screen.fill(config.EDITOR_BG_COLOR)
        prompt_surf = font.render(prompt, True, config.BLACK)
        prompt_rect = prompt_surf.get_rect(center=(config.EDITOR_WIDTH // 2, config.EDITOR_HEIGHT // 2 - 60))
        screen.blit(prompt_surf, prompt_rect)

        display_text = input_text if input_text else str(default)
        value_surf = font.render(display_text, True, config.BLACK)
        value_rect = value_surf.get_rect(center=(config.EDITOR_WIDTH // 2, config.EDITOR_HEIGHT // 2))
        screen.blit(value_surf, value_rect)

        hint_surf = small_font.render("Enter = confirm, Esc = cancel", True, config.GRAY_DARK)
        hint_rect = hint_surf.get_rect(center=(config.EDITOR_WIDTH // 2, config.EDITOR_HEIGHT // 2 + 45))
        screen.blit(hint_surf, hint_rect)

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    return input_text if input_text else str(default)
                if event.key == pygame.K_ESCAPE:
                    return None
                if event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                else:
                    if numeric and not event.unicode.isdigit():
                        continue
                    if event.unicode and len(input_text) < 60:
                        input_text += event.unicode

        clock.tick(config.FPS)


def _filter_options(options, query):
    query = (query or "").strip().lower()
    if not query:
        return list(options)
    return [option for option in options if query in option.lower()]


def prompt_choice(screen, prompt, options, default=None):
    if not options:
        return None

    font = pygame.font.Font(config.DEFAULT_FONT, 24)
    small_font = pygame.font.Font(config.DEFAULT_FONT, 16)
    query = ""
    filtered = list(options)
    selected_index = 0
    if default in filtered:
        selected_index = filtered.index(default)
    clock = pygame.time.Clock()
    visible_rows = 12
    scroll = 0

    while True:
        screen.fill(config.EDITOR_BG_COLOR)
        title_surf = font.render(prompt, True, config.BLACK)
        screen.blit(title_surf, (60, 40))

        query_text = f"Search: {query}" if query else "Search: (type to filter)"
        query_surf = small_font.render(query_text, True, config.GRAY_DARK)
        screen.blit(query_surf, (60, 80))

        filtered = _filter_options(options, query)
        if not filtered:
            empty_surf = small_font.render("No matching options.", True, config.RED)
            screen.blit(empty_surf, (60, 120))
        else:
            selected_index = max(0, min(selected_index, len(filtered) - 1))
            if selected_index < scroll:
                scroll = selected_index
            if selected_index >= scroll + visible_rows:
                scroll = selected_index - visible_rows + 1

            start = scroll
            end = min(len(filtered), scroll + visible_rows)
            for row, idx in enumerate(range(start, end)):
                option = filtered[idx]
                y = 120 + row * 28
                color = config.BLUE if idx == selected_index else config.BLACK
                prefix = "> " if idx == selected_index else "  "
                option_surf = small_font.render(f"{prefix}{option}", True, color)
                screen.blit(option_surf, (60, y))

        hint_surf = small_font.render(
            "Up/Down select, Enter confirm, Esc cancel, Backspace delete search",
            True,
            config.GRAY_DARK,
        )
        screen.blit(hint_surf, (60, config.EDITOR_HEIGHT - 50))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_ESCAPE:
                return None
            if event.key == pygame.K_RETURN:
                if filtered:
                    return filtered[selected_index]
                return None
            if event.key == pygame.K_UP and filtered:
                selected_index = max(0, selected_index - 1)
            elif event.key == pygame.K_DOWN and filtered:
                selected_index = min(len(filtered) - 1, selected_index + 1)
            elif event.key == pygame.K_BACKSPACE:
                query = query[:-1]
            elif event.unicode and event.unicode.isprintable():
                query += event.unicode

        clock.tick(config.FPS)


def prompt_multi_choice(screen, prompt, options, selected_defaults=None):
    if not options:
        return []

    selected = set(selected_defaults or [])
    font = pygame.font.Font(config.DEFAULT_FONT, 24)
    small_font = pygame.font.Font(config.DEFAULT_FONT, 16)
    query = ""
    filtered = list(options)
    selected_index = 0
    clock = pygame.time.Clock()
    visible_rows = 12
    scroll = 0

    while True:
        screen.fill(config.EDITOR_BG_COLOR)
        title_surf = font.render(prompt, True, config.BLACK)
        screen.blit(title_surf, (60, 40))

        query_text = f"Search: {query}" if query else "Search: (type to filter)"
        query_surf = small_font.render(query_text, True, config.GRAY_DARK)
        screen.blit(query_surf, (60, 80))

        filtered = _filter_options(options, query)
        if not filtered:
            empty_surf = small_font.render("No matching options.", True, config.RED)
            screen.blit(empty_surf, (60, 120))
        else:
            selected_index = max(0, min(selected_index, len(filtered) - 1))
            if selected_index < scroll:
                scroll = selected_index
            if selected_index >= scroll + visible_rows:
                scroll = selected_index - visible_rows + 1

            start = scroll
            end = min(len(filtered), scroll + visible_rows)
            for row, idx in enumerate(range(start, end)):
                option = filtered[idx]
                y = 120 + row * 28
                is_selected = option in selected
                marker = "[x]" if is_selected else "[ ]"
                color = config.BLUE if idx == selected_index else config.BLACK
                prefix = "> " if idx == selected_index else "  "
                option_surf = small_font.render(
                    f"{prefix}{marker} {option}",
                    True,
                    color,
                )
                screen.blit(option_surf, (60, y))

        selected_preview = ", ".join(sorted(selected)) if selected else "(none)"
        preview_surf = small_font.render(
            f"Selected: {selected_preview}",
            True,
            config.GRAY_DARK,
        )
        screen.blit(preview_surf, (60, config.EDITOR_HEIGHT - 78))

        hint_surf = small_font.render(
            "Up/Down move, Space toggle, Enter confirm, Esc cancel",
            True,
            config.GRAY_DARK,
        )
        screen.blit(hint_surf, (60, config.EDITOR_HEIGHT - 50))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if event.type != pygame.KEYDOWN:
                continue
            if event.key == pygame.K_ESCAPE:
                return None
            if event.key == pygame.K_RETURN:
                ordered = [option for option in options if option in selected]
                return ordered
            if event.key == pygame.K_UP and filtered:
                selected_index = max(0, selected_index - 1)
            elif event.key == pygame.K_DOWN and filtered:
                selected_index = min(len(filtered) - 1, selected_index + 1)
            elif event.key == pygame.K_SPACE and filtered:
                option = filtered[selected_index]
                if option in selected:
                    selected.remove(option)
                else:
                    selected.add(option)
            elif event.key == pygame.K_BACKSPACE:
                query = query[:-1]
            elif event.unicode and event.unicode.isprintable():
                query += event.unicode

        clock.tick(config.FPS)


def prompt_learnset_entries(screen, move_names, current_entries):
    if not move_names:
        return [], []

    default_count = len(current_entries) if current_entries else len(move_names[:1])
    count_text = prompt_text(
        screen,
        "How many learnset entries?",
        max(1, default_count),
        numeric=True,
    )
    if count_text is None:
        return None, []
    try:
        target_count = max(1, int(count_text))
    except ValueError:
        target_count = max(1, default_count)

    drafted = []
    for idx in range(target_count):
        default_level = 1
        default_move = move_names[0]
        if idx < len(current_entries):
            default_level = current_entries[idx].get("level", 1)
            default_move = current_entries[idx].get("move", move_names[0])

        level_text = prompt_text(
            screen,
            f"Entry {idx + 1}: level",
            default_level,
            numeric=True,
        )
        if level_text is None:
            return None, []
        try:
            level = max(1, int(level_text))
        except ValueError:
            level = max(1, int(default_level))

        move_choice = prompt_choice(
            screen,
            f"Entry {idx + 1}: choose move",
            move_names,
            default=default_move,
        )
        if move_choice is None:
            return None, []
        drafted.append({"level": level, "move": move_choice})

    return normalize_learnset_entries(drafted, move_names)


def derive_move_pool(monster):
    learnset = monster.get("learnset", [])
    return derive_move_pool_from_learnset(learnset)


def summarize_learnset(learnset):
    parts = []
    for entry in learnset:
        level = entry.get("level", 1)
        if "move" in entry:
            parts.append(f"Lv{level} {entry['move']}")
        elif "moves" in entry:
            for move_name in entry.get("moves", []):
                parts.append(f"Lv{level} {move_name}")
    return ", ".join(parts)


def draw_monster_list(screen, monsters, selected_index, scroll_offset, font, small_font):
    list_rects = []
    list_height = config.EDITOR_HEIGHT - PADDING * 2 - 80
    visible_count = max(1, list_height // ITEM_HEIGHT)

    panel_rect = pygame.Rect(PADDING, PADDING, LIST_PANEL_WIDTH, config.EDITOR_HEIGHT - PADDING * 2)
    pygame.draw.rect(screen, config.GRAY_LIGHT, panel_rect)
    pygame.draw.rect(screen, config.GRAY_DARK, panel_rect, 2)

    title = font.render("Monsters", True, config.BLACK)
    screen.blit(title, (panel_rect.x + 10, panel_rect.y + 10))

    start_y = panel_rect.y + 50
    end_index = min(len(monsters), scroll_offset + visible_count)

    for row_index, monster_index in enumerate(range(scroll_offset, end_index)):
        monster = monsters[monster_index]
        item_rect = pygame.Rect(panel_rect.x + 10, start_y + row_index * ITEM_HEIGHT, panel_rect.width - 20, ITEM_HEIGHT)
        is_selected = monster_index == selected_index
        if is_selected:
            pygame.draw.rect(screen, config.SELECTION_HIGHLIGHT_COLOR, item_rect)
        else:
            pygame.draw.rect(screen, config.WHITE, item_rect)
        pygame.draw.rect(screen, config.GRAY_DARK, item_rect, 1)
        name_surf = small_font.render(monster.get("name", "Unknown"), True, config.BLACK)
        screen.blit(name_surf, (item_rect.x + 6, item_rect.y + 6))
        list_rects.append((item_rect, monster_index))

    return list_rects, visible_count


def draw_monster_details(screen, monster, font, small_font, detail_rect):
    if monster is None:
        empty_surf = font.render("No monster selected", True, config.BLACK)
        screen.blit(empty_surf, detail_rect.topleft)
        return

    name = monster.get("name", "Unknown")
    type_ = monster.get("type", "Unknown")
    base_stats = monster.get("base_stats", {})
    move_pool = derive_move_pool(monster)
    learnset = monster.get("learnset", [])

    y = detail_rect.top
    header = font.render(name, True, config.BLACK)
    screen.blit(header, (detail_rect.left, y))
    y += font.get_height() + 8

    type_surf = small_font.render(f"Type: {type_}", True, config.BLACK)
    screen.blit(type_surf, (detail_rect.left, y))
    y += small_font.get_height() + 6

    stats_text = (
        f"Base HP: {base_stats.get('max_hp', 1)}  "
        f"ATK: {base_stats.get('attack', 1)}  "
        f"DEF: {base_stats.get('defense', 1)}"
    )
    stats_surf = small_font.render(stats_text, True, config.BLACK)
    screen.blit(stats_surf, (detail_rect.left, y))
    y += small_font.get_height() + 12

    moves_title = small_font.render("Derived Move Pool:", True, config.BLACK)
    screen.blit(moves_title, (detail_rect.left, y))
    y += small_font.get_height() + 4

    moves_text = ", ".join(move_pool) if move_pool else "(none)"
    moves_rect = pygame.Rect(detail_rect.left, y, detail_rect.width, 80)
    draw_wrapped_text(screen, moves_text, moves_rect, small_font, config.BLACK)
    y = moves_rect.bottom + 8

    learnset_title = small_font.render("Learnset:", True, config.BLACK)
    screen.blit(learnset_title, (detail_rect.left, y))
    y += small_font.get_height() + 4

    learnset_text = summarize_learnset(learnset) if learnset else "(none)"
    learnset_rect = pygame.Rect(detail_rect.left, y, detail_rect.width, 120)
    draw_wrapped_text(screen, learnset_text, learnset_rect, small_font, config.BLACK)


def main():
    pygame.init()
    screen = pygame.display.set_mode((config.EDITOR_WIDTH, config.EDITOR_HEIGHT))
    pygame.display.set_caption("Monster Editor")
    font = pygame.font.Font(config.DEFAULT_FONT, 26)
    small_font = pygame.font.Font(config.DEFAULT_FONT, 18)
    clock = pygame.time.Clock()

    monsters = load_monsters()
    if not monsters:
        pygame.quit()
        return
    for monster in monsters:
        ensure_monster_structure(monster)

    selected_index = 0
    scroll_offset = 0
    status_message = ""
    status_until = 0

    right_panel_x = LIST_PANEL_WIDTH + PADDING * 2
    detail_rect = pygame.Rect(right_panel_x, PADDING + 10, config.EDITOR_WIDTH - right_panel_x - PADDING, 320)

    button_y = detail_rect.bottom + 20
    button_width = 180
    button_height = 36
    button_spacing = 12

    buttons = [
        Button((right_panel_x, button_y, button_width, button_height), "Edit Type", action="edit_type"),
        Button((right_panel_x + button_width + button_spacing, button_y, button_width, button_height), "Edit Base Stats", action="edit_stats"),
        Button((right_panel_x, button_y + button_height + button_spacing, button_width, button_height), "Edit Lv1 Moves", action="edit_moves"),
        Button((right_panel_x + button_width + button_spacing, button_y + button_height + button_spacing, button_width, button_height), "Edit Learnset", action="edit_learnset"),
        Button((right_panel_x, button_y + (button_height + button_spacing) * 2, button_width, button_height), "Save", action="save"),
        Button((right_panel_x + button_width + button_spacing, button_y + (button_height + button_spacing) * 2, button_width, button_height), "Back", action="back"),
    ]

    running = True
    while running:
        screen.fill(config.EDITOR_BG_COLOR)
        list_rects, visible_count = draw_monster_list(
            screen,
            monsters,
            selected_index,
            scroll_offset,
            font,
            small_font,
        )

        selected_monster = monsters[selected_index] if monsters else None
        draw_monster_details(screen, selected_monster, font, small_font, detail_rect)

        for button in buttons:
            button.draw(screen)

        if status_message and pygame.time.get_ticks() < status_until:
            status_surf = small_font.render(status_message, True, config.RED)
            screen.blit(status_surf, (right_panel_x, config.EDITOR_HEIGHT - PADDING - 20))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_monsters(monsters)
                running = False
                break

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    save_monsters(monsters)
                    running = False
                    break
                if event.key == pygame.K_DOWN:
                    selected_index = min(len(monsters) - 1, selected_index + 1)
                elif event.key == pygame.K_UP:
                    selected_index = max(0, selected_index - 1)
                elif event.key == pygame.K_PAGEDOWN:
                    selected_index = min(len(monsters) - 1, selected_index + visible_count)
                elif event.key == pygame.K_PAGEUP:
                    selected_index = max(0, selected_index - visible_count)
                scroll_offset = clamp_scroll(selected_index, scroll_offset, visible_count, len(monsters))

            if event.type == pygame.MOUSEWHEEL:
                if event.y < 0:
                    selected_index = min(len(monsters) - 1, selected_index + 1)
                elif event.y > 0:
                    selected_index = max(0, selected_index - 1)
                scroll_offset = clamp_scroll(selected_index, scroll_offset, visible_count, len(monsters))

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for rect, idx in list_rects:
                    if rect.collidepoint(event.pos):
                        selected_index = idx
                        scroll_offset = clamp_scroll(selected_index, scroll_offset, visible_count, len(monsters))
                        break
                for button in buttons:
                    if button.is_clicked(event):
                        action = button.action
                        if action == "back":
                            save_monsters(monsters)
                            running = False
                            break
                        if action == "save":
                            save_monsters(monsters)
                            status_message = "Saved monster data."
                            status_until = pygame.time.get_ticks() + STATUS_DURATION_MS
                            break
                        if selected_monster is None:
                            status_message = "No monster selected."
                            status_until = pygame.time.get_ticks() + STATUS_DURATION_MS
                            break
                        if action == "edit_type":
                            type_names = load_type_names()
                            if not type_names:
                                status_message = "No type definitions found in type_chart.json."
                                status_until = pygame.time.get_ticks() + STATUS_DURATION_MS
                                continue
                            chosen_type = prompt_choice(
                                screen,
                                "Select monster type",
                                type_names,
                                default=selected_monster.get("type", ""),
                            )
                            if chosen_type is None:
                                continue
                            normalized = normalize_single_selection(chosen_type, type_names)
                            if normalized is None:
                                status_message = "Invalid type selection rejected."
                                status_until = pygame.time.get_ticks() + STATUS_DURATION_MS
                                continue
                            selected_monster["type"] = normalized
                        elif action == "edit_stats":
                            hp_text = prompt_text(screen, "Enter base HP", selected_monster["base_stats"].get("max_hp", 1), numeric=True)
                            if hp_text is None:
                                continue
                            atk_text = prompt_text(screen, "Enter base Attack", selected_monster["base_stats"].get("attack", 1), numeric=True)
                            if atk_text is None:
                                continue
                            def_text = prompt_text(screen, "Enter base Defense", selected_monster["base_stats"].get("defense", 1), numeric=True)
                            if def_text is None:
                                continue
                            selected_monster["base_stats"]["max_hp"] = max(1, int(hp_text))
                            selected_monster["base_stats"]["attack"] = max(1, int(atk_text))
                            selected_monster["base_stats"]["defense"] = max(1, int(def_text))
                        elif action == "edit_moves":
                            move_names = load_move_names()
                            if not move_names:
                                status_message = "No move definitions found in moves.json."
                                status_until = pygame.time.get_ticks() + STATUS_DURATION_MS
                                continue
                            selected_moves = prompt_multi_choice(
                                screen,
                                "Select Lv1 moves",
                                move_names,
                                selected_defaults=derive_move_pool(selected_monster),
                            )
                            if selected_moves is None:
                                continue
                            normalized_moves, rejected = normalize_multi_selection(
                                selected_moves,
                                move_names,
                            )
                            if rejected:
                                status_message = f"Invalid moves rejected: {', '.join(rejected)}"
                                status_until = pygame.time.get_ticks() + STATUS_DURATION_MS
                            selected_monster["learnset"] = [
                                {"level": 1, "move": move_name} for move_name in normalized_moves
                            ]
                            selected_monster.pop("move_pool", None)
                        elif action == "edit_learnset":
                            move_names = load_move_names()
                            if not move_names:
                                status_message = "No move definitions found in moves.json."
                                status_until = pygame.time.get_ticks() + STATUS_DURATION_MS
                                continue
                            entries, rejected_rows = prompt_learnset_entries(
                                screen,
                                move_names,
                                selected_monster.get("learnset", []),
                            )
                            if entries is None:
                                continue
                            selected_monster["learnset"] = entries
                            selected_monster.pop("move_pool", None)
                            if rejected_rows:
                                status_message = f"Rejected {len(rejected_rows)} invalid learnset rows."
                                status_until = pygame.time.get_ticks() + STATUS_DURATION_MS
                        ensure_monster_structure(selected_monster)
                        break

        clock.tick(config.FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
