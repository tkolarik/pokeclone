import json
import os

import pygame

from src.core import config
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
        if not isinstance(monsters, list):
            raise ValueError("monsters.json should contain a list of monsters.")
        return monsters
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        print(f"Error loading monsters: {exc}")
        return []


def save_monsters(monsters):
    monsters_file = os.path.join(config.DATA_DIR, "monsters.json")
    with open(monsters_file, "w") as f:
        json.dump(monsters, f, indent=4)
    print(f"Saved {len(monsters)} monsters to {monsters_file}")


def load_move_names():
    moves_file = os.path.join(config.DATA_DIR, "moves.json")
    try:
        with open(moves_file, "r") as f:
            moves = json.load(f)
        return sorted({move.get("name") for move in moves if move.get("name")})
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"Error loading moves: {exc}")
        return []


def ensure_monster_structure(monster):
    base_stats = monster.get("base_stats")
    if not base_stats:
        base_stats = {
            "max_hp": monster.get("max_hp", 1),
            "attack": monster.get("attack", 1),
            "defense": monster.get("defense", 1),
        }
    monster["base_stats"] = {
        "max_hp": int(base_stats.get("max_hp", 1)),
        "attack": int(base_stats.get("attack", 1)),
        "defense": int(base_stats.get("defense", 1)),
    }
    monster["max_hp"] = monster["base_stats"]["max_hp"]
    monster["attack"] = monster["base_stats"]["attack"]
    monster["defense"] = monster["base_stats"]["defense"]

    move_pool = monster.get("move_pool")
    if not move_pool:
        move_pool = monster.get("moves", [])
    monster["move_pool"] = list(move_pool)

    learnset = monster.get("learnset")
    if not learnset:
        learnset = [{"level": 1, "move": move} for move in monster["move_pool"]]
    monster["learnset"] = learnset

    monster["moves"] = list(monster["move_pool"])


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


def parse_move_pool(text, move_names):
    requested = [move.strip() for move in text.split(",") if move.strip()]
    if not move_names:
        return requested, []
    valid = []
    unknown = []
    for move in requested:
        if move in move_names:
            valid.append(move)
        else:
            unknown.append(move)
    return valid, unknown


def parse_learnset(text, move_names, move_pool):
    entries = []
    unknown = []
    invalid = 0
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" not in part:
            invalid += 1
            continue
        level_text, move_name = part.split(":", 1)
        move_name = move_name.strip()
        try:
            level_value = int(level_text.strip())
        except ValueError:
            invalid += 1
            continue
        if move_names and move_name not in move_names:
            unknown.append(move_name)
            continue
        entries.append({"level": level_value, "move": move_name})
    if not entries:
        entries = [{"level": 1, "move": move} for move in move_pool]
    return entries, unknown, invalid


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
    move_pool = monster.get("move_pool", [])
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

    moves_title = small_font.render("Move Pool:", True, config.BLACK)
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
    move_names = load_move_names()

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
        Button((right_panel_x, button_y + button_height + button_spacing, button_width, button_height), "Edit Move Pool", action="edit_moves"),
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
                            result = prompt_text(screen, "Enter monster type", selected_monster.get("type", ""))
                            if result is not None:
                                selected_monster["type"] = result.strip() or selected_monster.get("type", "")
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
                            selected_monster["max_hp"] = selected_monster["base_stats"]["max_hp"]
                            selected_monster["attack"] = selected_monster["base_stats"]["attack"]
                            selected_monster["defense"] = selected_monster["base_stats"]["defense"]
                        elif action == "edit_moves":
                            current_pool = ", ".join(selected_monster.get("move_pool", []))
                            result = prompt_text(screen, "Move pool (comma-separated)", current_pool)
                            if result is None:
                                continue
                            new_pool, unknown = parse_move_pool(result, move_names)
                            if new_pool:
                                selected_monster["move_pool"] = new_pool
                                selected_monster["moves"] = list(new_pool)
                                selected_monster["learnset"] = [{"level": 1, "move": move} for move in new_pool]
                            if unknown:
                                status_message = f"Unknown moves ignored: {', '.join(unknown)}"
                                status_until = pygame.time.get_ticks() + STATUS_DURATION_MS
                        elif action == "edit_learnset":
                            current_learnset = summarize_learnset(selected_monster.get("learnset", []))
                            result = prompt_text(screen, "Learnset: level:move, level:move", current_learnset)
                            if result is None:
                                continue
                            entries, unknown, invalid = parse_learnset(result, move_names, selected_monster.get("move_pool", []))
                            selected_monster["learnset"] = entries
                            move_pool = list(selected_monster.get("move_pool", []))
                            for entry in entries:
                                move_name = entry.get("move")
                                if move_name and move_name not in move_pool:
                                    move_pool.append(move_name)
                            selected_monster["move_pool"] = move_pool
                            selected_monster["moves"] = list(move_pool)
                            if unknown or invalid:
                                message_parts = []
                                if unknown:
                                    message_parts.append(f"Unknown moves ignored: {', '.join(unknown)}")
                                if invalid:
                                    message_parts.append(f"Skipped {invalid} invalid entries")
                                status_message = "; ".join(message_parts)
                                status_until = pygame.time.get_ticks() + STATUS_DURATION_MS
                        ensure_monster_structure(selected_monster)
                        break

        clock.tick(config.FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
