import runpy

import pygame

from src.core import config

MENU_OPTIONS = [
    ("Overworld", "src.overworld.overworld"),
    ("Battle Simulator", "src.battle.battle_simulator"),
    ("Pixel Art Editor", "src.editor.pixle_art_editor"),
    ("Monster Editor", "src.editor.monster_editor"),
    ("Map Editor", "src.overworld.map_editor"),
    ("Quit", None),
]


def init_menu():
    pygame.init()
    screen = pygame.display.set_mode((config.MENU_WIDTH, config.MENU_HEIGHT))
    pygame.display.set_caption("PokeClone")
    title_font = pygame.font.Font(config.DEFAULT_FONT, config.MENU_TITLE_FONT_SIZE)
    option_font = pygame.font.Font(config.DEFAULT_FONT, config.MENU_OPTION_FONT_SIZE)
    clock = pygame.time.Clock()
    return screen, title_font, option_font, clock


def run_module(module_name: str) -> None:
    try:
        runpy.run_module(module_name, run_name="__main__")
    except SystemExit:
        pass


def draw_menu(screen, title_font, option_font, selected_index):
    screen.fill(config.MENU_BG_COLOR)
    title_surf = title_font.render("PokeClone", True, config.MENU_TEXT_COLOR)
    title_rect = title_surf.get_rect(center=(config.MENU_WIDTH // 2, 120))
    screen.blit(title_surf, title_rect)

    option_rects = []
    start_y = 240
    spacing = 55
    for i, (label, _) in enumerate(MENU_OPTIONS):
        color = config.MENU_HIGHLIGHT_COLOR if i == selected_index else config.MENU_TEXT_COLOR
        option_surf = option_font.render(label, True, color)
        option_rect = option_surf.get_rect(center=(config.MENU_WIDTH // 2, start_y + i * spacing))
        screen.blit(option_surf, option_rect)
        option_rects.append(option_rect)

    pygame.display.flip()
    return option_rects


def main() -> None:
    screen, title_font, option_font, clock = init_menu()
    selected_index = 0
    running = True

    while running:
        option_rects = draw_menu(screen, title_font, option_font, selected_index)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_DOWN, pygame.K_s):
                    selected_index = (selected_index + 1) % len(MENU_OPTIONS)
                elif event.key in (pygame.K_UP, pygame.K_w):
                    selected_index = (selected_index - 1) % len(MENU_OPTIONS)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    label, module_name = MENU_OPTIONS[selected_index]
                    if module_name is None:
                        running = False
                    else:
                        run_module(module_name)
                        screen, title_font, option_font, clock = init_menu()
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, rect in enumerate(option_rects):
                    if rect.collidepoint(event.pos):
                        selected_index = i
                        label, module_name = MENU_OPTIONS[i]
                        if module_name is None:
                            running = False
                        else:
                            run_module(module_name)
                            screen, title_font, option_font, clock = init_menu()
                        break

        clock.tick(config.FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
