from unittest import mock

from src.battle import battle_simulator


def _make_creature(name: str):
    move = battle_simulator.Move("Tackle", "Normal", 40)
    sprite = mock.Mock()
    return battle_simulator.Creature(name, "Normal", 20, 10, 10, [move], sprite)


def test_battle_scene_prompts_for_team_when_no_preconfigured_inputs(monkeypatch):
    scene = battle_simulator.BattleScene(payload={})
    manager = mock.Mock()
    manager.screen = object()
    creatures = [_make_creature("A"), _make_creature("B"), _make_creature("C")]

    called = {"prompt": 0, "select": 0}

    monkeypatch.delenv("POKECLONE_OPPONENT_ID", raising=False)
    monkeypatch.setattr(battle_simulator, "initialize_battle_runtime", lambda *args, **kwargs: None)
    monkeypatch.setattr(battle_simulator.pygame.display, "set_caption", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(battle_simulator, "_get_font", lambda: mock.Mock())
    monkeypatch.setattr(battle_simulator, "load_moves", lambda: {})
    monkeypatch.setattr(battle_simulator, "load_creatures", lambda _moves: creatures)
    monkeypatch.setattr(battle_simulator, "parse_team_env", lambda _name: None)
    monkeypatch.setattr(
        battle_simulator,
        "prompt_for_team_size",
        lambda *_args, **_kwargs: called.__setitem__("prompt", called["prompt"] + 1) or 2,
    )
    monkeypatch.setattr(
        battle_simulator,
        "select_team",
        lambda *_args, **_kwargs: called.__setitem__("select", called["select"] + 1) or ["A"],
    )
    monkeypatch.setattr(battle_simulator, "build_battle_team", lambda entries, _moves: [object() for _ in entries])
    monkeypatch.setattr(
        battle_simulator,
        "build_team_entries",
        lambda *_args, **_kwargs: [("template", battle_simulator.config.DEFAULT_TEAM_LEVEL)],
    )
    monkeypatch.setattr(
        battle_simulator,
        "build_random_team",
        lambda _creatures, size, _level: [("template", battle_simulator.config.DEFAULT_TEAM_LEVEL)] * size,
    )
    monkeypatch.setattr(
        battle_simulator.BattleScene,
        "_start_round",
        lambda self: setattr(self, "state", "battle_started"),
    )

    scene.on_enter(manager)

    assert called["prompt"] == 1
    assert called["select"] == 1
    assert scene.state == "battle_started"


def test_battle_scene_skips_prompts_when_payload_preconfigures_opponent(monkeypatch):
    scene = battle_simulator.BattleScene(payload={"opponent_id": "rival_1"})
    manager = mock.Mock()
    manager.screen = object()
    creatures = [_make_creature("A"), _make_creature("B")]
    called = {"scene_teams": 0}

    monkeypatch.setattr(battle_simulator, "initialize_battle_runtime", lambda *args, **kwargs: None)
    monkeypatch.setattr(battle_simulator.pygame.display, "set_caption", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(battle_simulator, "_get_font", lambda: mock.Mock())
    monkeypatch.setattr(battle_simulator, "load_moves", lambda: {})
    monkeypatch.setattr(battle_simulator, "load_creatures", lambda _moves: creatures)
    monkeypatch.setattr(
        battle_simulator,
        "_build_scene_teams",
        lambda *_args, **_kwargs: called.__setitem__("scene_teams", called["scene_teams"] + 1) or ([object()], [object()]),
    )
    monkeypatch.setattr(
        battle_simulator,
        "prompt_for_team_size",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("prompt_for_team_size should not be called")),
    )
    monkeypatch.setattr(
        battle_simulator,
        "select_team",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("select_team should not be called")),
    )
    monkeypatch.setattr(
        battle_simulator.BattleScene,
        "_start_round",
        lambda self: setattr(self, "state", "battle_started"),
    )

    scene.on_enter(manager)

    assert called["scene_teams"] == 1
    assert scene.state == "battle_started"


def test_draw_battle_clears_surface_before_blitting_background(monkeypatch):
    screen = mock.Mock()
    font = mock.Mock()
    text_surface = mock.Mock()
    text_surface.get_rect.return_value = mock.Mock()
    font.render.return_value = text_surface

    monster_a = _make_creature("A")
    monster_b = _make_creature("B")
    monster_a.current_hp = monster_a.max_hp
    monster_b.current_hp = monster_b.max_hp
    background = mock.Mock()

    monkeypatch.setattr(battle_simulator, "_get_screen", lambda: screen)
    monkeypatch.setattr(battle_simulator, "_get_font", lambda: font)
    monkeypatch.setattr(battle_simulator.RESOURCE_MANAGER, "get_font", lambda *_args, **_kwargs: font)
    monkeypatch.setattr(battle_simulator.pygame.transform, "scale", lambda surface, _size: surface)
    monkeypatch.setattr(battle_simulator.pygame.draw, "rect", lambda *_args, **_kwargs: None)

    battle_simulator.draw_battle(monster_a, monster_b, [], background, flip_display=False)

    screen.fill.assert_called_with(battle_simulator.config.BATTLE_BG_COLOR)
    screen.blit.assert_any_call(background, (0, 0))
