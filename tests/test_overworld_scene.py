from unittest import mock

from src.overworld.overworld import OverworldScene


def test_overworld_scene_battle_launcher_pushes_battle_scene(monkeypatch):
    scene = OverworldScene()
    manager = mock.Mock()
    scene._manager = manager
    payload = {"team": [{"name": "Embercub"}], "opponent_id": "trainer_1"}

    created = []

    class FakeBattleScene:
        def __init__(self, payload=None):
            self.payload = payload
            created.append(self)

    monkeypatch.setattr("src.battle.battle_simulator.BattleScene", FakeBattleScene)

    scene._launch_battle(payload)

    manager.push.assert_called_once()
    pushed_scene = manager.push.call_args[0][0]
    assert isinstance(pushed_scene, FakeBattleScene)
    assert created and created[0].payload == payload
    assert pushed_scene.payload == payload
