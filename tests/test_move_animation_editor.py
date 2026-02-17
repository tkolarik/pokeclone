from unittest import mock

import pygame

from src.editor.move_animation_editor import MoveAnimationEditor


def _prime_editor_dialog_state(editor: MoveAnimationEditor) -> None:
    editor.dialog_mode = None
    editor.dialog_prompt = ""
    editor.dialog_file_list = []
    editor.dialog_file_labels = []
    editor.dialog_selected_file_index = -1
    editor.dialog_file_scroll_offset = 0
    editor.dialog_file_page_size = 0
    editor.dialog_file_list_rect = None
    editor.dialog_file_scrollbar_rect = None
    editor.dialog_file_scroll_thumb_rect = None
    editor.dialog_file_dragging_scrollbar = False
    editor.dialog_quick_dirs = []
    editor.dialog_quick_dir_rects = []
    editor.dialog_current_dir = ""
    editor.dialog_sort_recent = True
    editor.dialog_load_button_rect = None
    editor.dialog_cancel_button_rect = None
    editor.status_text = ""
    editor.status_expires = 0


def test_discover_image_files_filters_non_images(tmp_path):
    ref_dir = tmp_path / "refs"
    bg_dir = tmp_path / "bgs"
    ref_dir.mkdir()
    bg_dir.mkdir()

    img_a = ref_dir / "a.png"
    img_b = bg_dir / "b.jpg"
    non_image = ref_dir / "notes.txt"

    img_a.write_bytes(b"\x89PNG\r\n\x1a\n")
    img_b.write_bytes(b"\xff\xd8\xff")
    non_image.write_text("ignore me", encoding="utf-8")

    editor = MoveAnimationEditor.__new__(MoveAnimationEditor)
    files = editor._discover_image_files([str(ref_dir), str(bg_dir)])

    assert str(img_a) in files
    assert str(img_b) in files
    assert str(non_image) not in files


def test_open_existing_starts_dialog_with_file_list():
    editor = MoveAnimationEditor.__new__(MoveAnimationEditor)
    _prime_editor_dialog_state(editor)
    fake_files = ["/tmp/a.json", "/tmp/b.json"]

    with mock.patch("src.editor.move_animation_editor.list_move_animation_files", return_value=fake_files):
        editor._open_existing()

    assert editor.dialog_mode == "open_animation"
    assert editor.dialog_file_list == fake_files
    assert editor.dialog_file_labels == ["a.json", "b.json"]
    assert editor.dialog_selected_file_index == 0


def test_load_reference_starts_dialog_with_discovered_images(tmp_path):
    ref_dir = tmp_path / "refs"
    ref_dir.mkdir()
    image_file = ref_dir / "ref.png"
    image_file.write_bytes(b"\x89PNG\r\n\x1a\n")

    editor = MoveAnimationEditor.__new__(MoveAnimationEditor)
    _prime_editor_dialog_state(editor)
    editor._reference_search_dirs = lambda: [str(ref_dir)]

    editor._load_reference_image()

    assert editor.dialog_mode == "load_ref"
    assert str(image_file) in editor.dialog_file_list
    assert editor.dialog_selected_file_index == 0


def test_open_existing_keeps_dialog_visible_when_file_list_is_empty():
    editor = MoveAnimationEditor.__new__(MoveAnimationEditor)
    _prime_editor_dialog_state(editor)
    statuses = []
    editor._set_status = statuses.append

    with mock.patch("src.editor.move_animation_editor.list_move_animation_files", return_value=[]):
        editor._open_existing()

    assert editor.dialog_mode == "open_animation"
    assert editor.dialog_file_list == []
    assert editor.dialog_selected_file_index == -1
    assert statuses == ["No move animation files found."]


def test_load_reference_keeps_dialog_visible_when_file_list_is_empty(tmp_path):
    empty_dir = tmp_path / "empty_refs"
    empty_dir.mkdir()

    editor = MoveAnimationEditor.__new__(MoveAnimationEditor)
    _prime_editor_dialog_state(editor)
    editor._reference_search_dirs = lambda: [str(empty_dir)]
    statuses = []
    editor._set_status = statuses.append

    editor._load_reference_image()

    assert editor.dialog_mode == "load_ref"
    assert editor.dialog_file_list == []
    assert editor.dialog_selected_file_index == -1
    assert statuses == ["No reference image found."]


def test_confirm_dialog_selection_routes_open_animation_mode():
    editor = MoveAnimationEditor.__new__(MoveAnimationEditor)
    _prime_editor_dialog_state(editor)
    editor.dialog_mode = "open_animation"
    editor.dialog_file_list = ["/tmp/a.json", "/tmp/b.json"]
    editor.dialog_selected_file_index = 1

    loaded = []
    editor._load_selected_animation = loaded.append
    editor._load_selected_reference = lambda _path: None

    editor._confirm_dialog_selection()

    assert loaded == ["/tmp/b.json"]
    assert editor.dialog_mode is None


def test_confirm_dialog_selection_routes_load_ref_mode():
    editor = MoveAnimationEditor.__new__(MoveAnimationEditor)
    _prime_editor_dialog_state(editor)
    editor.dialog_mode = "load_ref"
    editor.dialog_file_list = ["/tmp/ref.png"]
    editor.dialog_selected_file_index = 0

    loaded = []
    editor._load_selected_reference = loaded.append
    editor._load_selected_animation = lambda _path: None

    editor._confirm_dialog_selection()

    assert loaded == ["/tmp/ref.png"]
    assert editor.dialog_mode is None


def test_confirm_dialog_selection_with_empty_list_sets_status_without_closing():
    editor = MoveAnimationEditor.__new__(MoveAnimationEditor)
    _prime_editor_dialog_state(editor)
    editor.dialog_mode = "open_animation"
    editor.dialog_file_list = []
    editor.dialog_selected_file_index = -1

    statuses = []
    editor._set_status = statuses.append

    editor._confirm_dialog_selection()

    assert statuses == ["No file selected."]
    assert editor.dialog_mode == "open_animation"


def test_dialog_keyboard_navigation_and_confirm_flow():
    editor = MoveAnimationEditor.__new__(MoveAnimationEditor)
    _prime_editor_dialog_state(editor)
    editor.dialog_mode = "open_animation"
    editor.dialog_file_list = ["/tmp/a.json", "/tmp/b.json"]
    editor.dialog_selected_file_index = 0

    confirm_calls = []
    editor._confirm_dialog_selection = lambda: confirm_calls.append(True)

    down_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN)
    editor._handle_dialog_event(down_event)
    assert editor.dialog_selected_file_index == 1

    up_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_UP)
    editor._handle_dialog_event(up_event)
    assert editor.dialog_selected_file_index == 0

    enter_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)
    editor._handle_dialog_event(enter_event)
    assert confirm_calls == [True]


def test_dialog_escape_closes_dialog():
    editor = MoveAnimationEditor.__new__(MoveAnimationEditor)
    _prime_editor_dialog_state(editor)
    editor.dialog_mode = "load_ref"
    editor.dialog_file_list = ["/tmp/ref.png"]
    editor.dialog_selected_file_index = 0

    escape_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)
    editor._handle_dialog_event(escape_event)

    assert editor.dialog_mode is None
