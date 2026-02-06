from __future__ import annotations

import pygame

from src.core import config
from src.core.scene_manager import Scene, SceneManager


APP_WINDOW_SIZE = (
    max(config.MENU_WIDTH, config.BATTLE_WIDTH, config.OVERWORLD_WIDTH),
    max(config.MENU_HEIGHT, config.BATTLE_HEIGHT, config.OVERWORLD_HEIGHT),
)


class GameApp:
    """Top-level unified app runtime owning one pygame window and loop."""

    def __init__(
        self,
        initial_scene: Scene,
        *,
        title: str = "PokeClone",
        window_size: tuple[int, int] = APP_WINDOW_SIZE,
    ) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode(window_size)
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        self.scene_manager = SceneManager(screen=self.screen)
        self.scene_manager.push(initial_scene)

    def run(self) -> None:
        while self.scene_manager.is_running:
            dt_seconds = self.clock.tick(config.FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.scene_manager.stop()
                    break
                self.scene_manager.handle_event(event)
                if not self.scene_manager.is_running:
                    break

            if not self.scene_manager.is_running:
                break

            self.scene_manager.update(dt_seconds)
            if not self.scene_manager.is_running:
                break

            self.scene_manager.draw(self.screen)
            pygame.display.flip()

        self.scene_manager.clear()
        pygame.quit()
