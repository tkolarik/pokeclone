from __future__ import annotations

from typing import List, Optional


class Scene:
    """Base scene contract for the unified runtime stack."""

    def on_enter(self, manager: "SceneManager") -> None:
        return

    def on_exit(self, manager: "SceneManager") -> None:
        return

    def handle_event(self, manager: "SceneManager", event: object) -> None:
        return

    def update(self, manager: "SceneManager", dt_seconds: float) -> None:
        return

    def draw(self, manager: "SceneManager", screen: object) -> None:
        return


class SceneManager:
    """Deterministic stack-based scene manager."""

    def __init__(self, *, screen: object | None = None) -> None:
        self.screen = screen
        self._stack: List[Scene] = []
        self._running = True

    @property
    def current_scene(self) -> Optional[Scene]:
        return self._stack[-1] if self._stack else None

    @property
    def stack_size(self) -> int:
        return len(self._stack)

    @property
    def is_running(self) -> bool:
        return self._running and bool(self._stack)

    def stop(self) -> None:
        self._running = False

    def push(self, scene: Scene) -> None:
        current = self.current_scene
        if current is not None:
            current.on_exit(self)
        self._stack.append(scene)
        scene.on_enter(self)

    def pop(self) -> Optional[Scene]:
        if not self._stack:
            self._running = False
            return None
        exiting = self._stack.pop()
        exiting.on_exit(self)
        current = self.current_scene
        if current is not None:
            current.on_enter(self)
        else:
            self._running = False
        return exiting

    def replace(self, scene: Scene) -> None:
        if self._stack:
            exiting = self._stack.pop()
            exiting.on_exit(self)
        self._stack.append(scene)
        scene.on_enter(self)

    def clear(self) -> None:
        while self._stack:
            scene = self._stack.pop()
            scene.on_exit(self)
        self._running = False

    def handle_event(self, event: object) -> None:
        scene = self.current_scene
        if scene is not None:
            scene.handle_event(self, event)

    def update(self, dt_seconds: float) -> None:
        scene = self.current_scene
        if scene is not None:
            scene.update(self, dt_seconds)

    def draw(self, screen: object | None = None) -> None:
        target = screen if screen is not None else self.screen
        scene = self.current_scene
        if scene is not None and target is not None:
            scene.draw(self, target)
