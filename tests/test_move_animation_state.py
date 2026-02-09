from src.editor.move_animation_state import MoveAnimationState


def test_frame_order_operations_keep_object_frame_alignment():
    state = MoveAnimationState.new("ember_strike", object_count=1)
    obj = state.objects[0]

    state.append_frame()
    state.append_frame()
    for idx in range(state.frame_count):
        obj.frames[idx].x = idx * 10
        state.frames[idx].duration_ms = 100 + idx * 50

    insert_idx = state.duplicate_frame(1)
    assert insert_idx == 2
    assert state.frame_count == 4
    assert obj.frames[2].x == obj.frames[1].x == 10
    assert state.frames[2].duration_ms == state.frames[1].duration_ms == 150

    moved_idx = state.move_frame(0, 3)
    assert moved_idx == 3
    assert [frame.x for frame in obj.frames] == [10, 10, 20, 0]

    removed = state.delete_frame(1)
    assert removed is True
    assert state.frame_count == 3
    assert [frame.x for frame in obj.frames] == [10, 20, 0]


def test_onion_skin_indices_follow_toggles_and_edges():
    middle = MoveAnimationState.onion_skin_indices(2, 5, previous_enabled=True, next_enabled=True)
    assert middle == {"previous": 1, "next": 3}

    first = MoveAnimationState.onion_skin_indices(0, 5, previous_enabled=True, next_enabled=True)
    assert first == {"previous": None, "next": 1}

    prev_only = MoveAnimationState.onion_skin_indices(4, 5, previous_enabled=True, next_enabled=False)
    assert prev_only == {"previous": 3, "next": None}


def test_drag_transform_uses_anchor_conversion_and_apply_all():
    state = MoveAnimationState.new("ember_strike", object_count=1)
    obj = state.objects[0]
    state.append_frame()
    state.append_frame()
    assert state.frame_count == 3

    obj.anchor = "attacker"
    dx, dy = state.apply_drag_delta(
        obj.object_id,
        frame_index=1,
        delta_x_stage=9,
        delta_y_stage=6,
        apply_to_all_frames=False,
        sprite_scale=3,
    )
    assert (dx, dy) == (3, 2)
    assert (obj.frames[1].x, obj.frames[1].y) == (3, 2)
    assert (obj.frames[0].x, obj.frames[0].y) == (0, 0)

    dx_all, dy_all = state.apply_drag_delta(
        obj.object_id,
        frame_index=1,
        delta_x_stage=3,
        delta_y_stage=3,
        apply_to_all_frames=True,
        sprite_scale=3,
    )
    assert (dx_all, dy_all) == (1, 1)
    assert [(frame.x, frame.y) for frame in obj.frames] == [(1, 1), (4, 3), (1, 1)]

    obj.anchor = "screen"
    state.apply_drag_delta(
        obj.object_id,
        frame_index=0,
        delta_x_stage=5,
        delta_y_stage=-2,
        apply_to_all_frames=False,
        sprite_scale=3,
    )
    assert (obj.frames[0].x, obj.frames[0].y) == (6, -1)
