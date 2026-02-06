import os
import runpy
import sys

import pygame

from src.core import config
from src.core.input_actions import load_action_map
from src.core.launcher import run_module as launch_module
from src.core.resource_manager import get_resource_manager
from src.core.scene_manager import Scene, SceneManager
from src.ui.game_app import GameApp

MENU_OPTIONS = [
    ("Overworld", "__overworld__"),
    ("Battle Simulator", "__battle__"),
    ("Pixel Art Editor", "src.editor.pixle_art_editor"),
    ("Monster Editor", "src.editor.monster_editor"),
    ("Map Editor", "src.overworld.map_editor"),
    ("Quit", None),
]


def init_menu(screen: pygame.Surface | None = None):
    if screen is None:
        pygame.init()
        screen = pygame.display.set_mode((config.MENU_WIDTH, config.MENU_HEIGHT))
        pygame.display.set_caption("PokeClone")
    resource_manager = get_resource_manager()
    # Sub-apps can call pygame.quit(); clear cached assets so fonts/surfaces
    # are recreated against the active pygame subsystems on re-entry.
    resource_manager.clear()
    title_font = resource_manager.get_font(config.DEFAULT_FONT, config.MENU_TITLE_FONT_SIZE)
    option_font = resource_manager.get_font(config.DEFAULT_FONT, config.MENU_OPTION_FONT_SIZE)
    clock = pygame.time.Clock()
    return screen, title_font, option_font, clock


def run_module(module_name: str) -> None:
    try:
        runpy.run_module(module_name, run_name="__main__")
    except SystemExit:
        pass


def _dispatch_module_from_cli() -> bool:
    module_name = None
    module_args = []
    if "--run-module" in sys.argv:
        idx = sys.argv.index("--run-module")
        if idx + 1 >= len(sys.argv):
            raise SystemExit("Missing module name for --run-module")
        module_name = sys.argv[idx + 1]
        module_args = sys.argv[idx + 2 :]
        if module_args[:1] == ["--"]:
            module_args = module_args[1:]
    else:
        module_name = os.environ.get("POKECLONE_RUN_MODULE")

    if not module_name:
        return False

    sys.argv = [module_name] + module_args
    run_module(module_name)
    return True


def draw_menu(
    screen: pygame.Surface,
    title_font: pygame.font.Font,
    option_font: pygame.font.Font,
    selected_index: int,
    *,
    flip_display: bool = True,
):
    screen.fill(config.MENU_BG_COLOR)
    screen_w, screen_h = screen.get_size()

    title_surf = title_font.render("PokeClone", True, config.MENU_TEXT_COLOR)
    title_rect = title_surf.get_rect(center=(screen_w // 2, 120))
    screen.blit(title_surf, title_rect)

    option_rects = []
    start_y = max(220, screen_h // 3)
    spacing = 55
    for i, (label, _) in enumerate(MENU_OPTIONS):
        color = config.MENU_HIGHLIGHT_COLOR if i == selected_index else config.MENU_TEXT_COLOR
        option_surf = option_font.render(label, True, color)
        option_rect = option_surf.get_rect(center=(screen_w // 2, start_y + i * spacing))
        screen.blit(option_surf, option_rect)
        option_rects.append(option_rect)

    if flip_display:
        pygame.display.flip()
    return option_rects


class MainMenuScene(Scene):
    def __init__(self) -> None:
        self.selected_index = 0
        self.actions = load_action_map()
        self.option_rects: list[pygame.Rect] = []
        self.title_font: pygame.font.Font | None = None
        self.option_font: pygame.font.Font | None = None

    def on_enter(self, manager: SceneManager) -> None:
        pygame.display.set_caption("PokeClone")
        _screen, title_font, option_font, _clock = init_menu(screen=manager.screen)
        self.title_font = title_font
        self.option_font = option_font

    def _activate_selected(self, manager: SceneManager) -> None:
        _label, target = MENU_OPTIONS[self.selected_index]
        if target is None:
            manager.stop()
            return

        if target == "__overworld__":
            from src.overworld.overworld import OverworldScene

            manager.push(OverworldScene())
            return

        if target == "__battle__":
            from src.battle.battle_simulator import BattleScene

            manager.push(BattleScene())
            return

        launch_module(target)
        pygame.display.set_caption("PokeClone")

    def handle_event(self, manager: SceneManager, event: object) -> None:
        if event is None:
            return
        if event.type == pygame.KEYDOWN:
            if self.actions.matches(event, "down") or self.actions.matches(event, "move_down"):
                self.selected_index = (self.selected_index + 1) % len(MENU_OPTIONS)
            elif self.actions.matches(event, "up") or self.actions.matches(event, "move_up"):
                self.selected_index = (self.selected_index - 1) % len(MENU_OPTIONS)
            elif self.actions.matches(event, "confirm"):
                self._activate_selected(manager)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.option_rects):
                if rect.collidepoint(event.pos):
                    self.selected_index = i
                    self._activate_selected(manager)
                    break

    def update(self, manager: SceneManager, dt_seconds: float) -> None:
        return

    def draw(self, manager: SceneManager, screen: pygame.Surface) -> None:
        if self.title_font is None or self.option_font is None:
            self.on_enter(manager)
        self.option_rects = draw_menu(
            screen,
            self.title_font,
            self.option_font,
            self.selected_index,
            flip_display=False,
        )


def main() -> None:
    if _dispatch_module_from_cli():
        return
    app = GameApp(MainMenuScene())
    app.run()


if __name__ == "__main__":
    main()
