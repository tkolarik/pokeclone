import json

import pygame

from src.core.input_actions import InputActionMap, load_action_map


def test_default_bindings_support_multiple_equivalent_keys():
    actions = InputActionMap()
    confirm_keys = actions.keys_for_action("confirm")
    assert pygame.K_RETURN in confirm_keys
    assert pygame.K_SPACE in confirm_keys
    assert pygame.K_KP_ENTER in confirm_keys

    assert "move_up" in actions.actions_for_key(pygame.K_w)
    assert "move_up" in actions.actions_for_key(pygame.K_UP)


def test_event_resolution_matches_expected_action():
    actions = InputActionMap()
    event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_s, unicode="s")
    assert actions.matches(event, "move_down")
    assert not actions.matches(event, "down")


def test_override_file_supports_key_name_tokens(tmp_path):
    binding_path = tmp_path / "input_bindings.json"
    binding_path.write_text(
        json.dumps(
            {
                "confirm": ["f", "K_g"],
                "move_up": ["up", "i"],
            }
        ),
        encoding="utf-8",
    )

    actions = load_action_map(str(binding_path))
    assert pygame.K_f in actions.keys_for_action("confirm")
    assert pygame.K_g in actions.keys_for_action("confirm")
    assert pygame.K_i in actions.keys_for_action("move_up")


def test_conflict_detection_flags_exclusive_action_overlap():
    actions = InputActionMap(
        {
            "up": [pygame.K_w],
            "down": [pygame.K_w],
        }
    )
    conflicts = actions.detect_conflicts()
    assert conflicts
    assert any(pygame.K_w == key and set(overlap) == {"up", "down"} for key, overlap in conflicts)
