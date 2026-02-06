from src.core.scene_manager import Scene, SceneManager


class DummyScene(Scene):
    def __init__(self, name: str):
        self.name = name
        self.enter_count = 0
        self.exit_count = 0
        self.update_count = 0
        self.draw_count = 0
        self.events = []
        self.counter = 0

    def on_enter(self, manager: SceneManager) -> None:
        self.enter_count += 1

    def on_exit(self, manager: SceneManager) -> None:
        self.exit_count += 1

    def handle_event(self, manager: SceneManager, event: object) -> None:
        self.events.append(event)

    def update(self, manager: SceneManager, dt_seconds: float) -> None:
        self.update_count += 1
        self.counter += 1

    def draw(self, manager: SceneManager, screen: object) -> None:
        self.draw_count += 1


def test_scene_stack_push_pop_replace_transitions():
    manager = SceneManager(screen=object())
    menu = DummyScene("menu")
    overworld = DummyScene("overworld")
    battle = DummyScene("battle")

    manager.push(menu)
    assert manager.current_scene is menu
    assert menu.enter_count == 1

    manager.push(overworld)
    assert menu.exit_count == 1
    assert overworld.enter_count == 1
    assert manager.current_scene is overworld
    assert manager.stack_size == 2

    manager.replace(battle)
    assert overworld.exit_count == 1
    assert battle.enter_count == 1
    assert manager.current_scene is battle
    assert manager.stack_size == 2

    manager.pop()
    assert battle.exit_count == 1
    assert manager.current_scene is menu
    assert menu.enter_count == 2


def test_scene_resume_retains_state_after_push_and_pop():
    manager = SceneManager(screen=object())
    overworld = DummyScene("overworld")
    battle = DummyScene("battle")

    manager.push(overworld)
    manager.update(0.016)
    manager.draw()
    saved_counter = overworld.counter

    manager.push(battle)
    manager.update(0.016)
    manager.update(0.016)
    assert overworld.counter == saved_counter
    assert overworld.update_count == 1

    manager.pop()
    manager.update(0.016)
    manager.draw()
    assert manager.current_scene is overworld
    assert overworld.enter_count == 2
    assert overworld.counter == saved_counter + 1
    assert battle.exit_count == 1


def test_scene_manager_stops_when_stack_becomes_empty():
    manager = SceneManager(screen=object())
    menu = DummyScene("menu")
    manager.push(menu)
    manager.pop()
    assert manager.current_scene is None
    assert manager.is_running is False
