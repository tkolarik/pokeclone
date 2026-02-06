import os
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional

import pygame

from src.core import config
from src.core.tileset import list_tileset_files
from src.editor.editor_ui import Button


@dataclass
class DialogState:
    dialog_mode: Optional[str] = None
    dialog_prompt: str = ""
    dialog_options: List[Any] = field(default_factory=list)
    dialog_callback: Optional[Callable[[Any], None]] = None
    dialog_input_text: str = ""
    dialog_input_active: bool = False
    dialog_input_rect: Optional[pygame.Rect] = None
    dialog_input_max_length: int = 50
    dialog_file_list: List[Any] = field(default_factory=list)
    dialog_file_scroll_offset: int = 0
    dialog_selected_file_index: int = -1
    dialog_file_labels: List[str] = field(default_factory=list)
    dialog_file_list_rect: Optional[pygame.Rect] = None
    dialog_file_page_size: int = 0
    dialog_file_scrollbar_rect: Optional[pygame.Rect] = None
    dialog_file_scroll_thumb_rect: Optional[pygame.Rect] = None
    dialog_file_dragging_scrollbar: bool = False
    dialog_quick_dirs: List[Any] = field(default_factory=list)
    dialog_quick_dir_rects: List[Any] = field(default_factory=list)
    dialog_current_dir: str = ""
    dialog_sort_recent: bool = True
    dialog_color_picker_hue: int = 0
    dialog_color_picker_sat: float = 1
    dialog_color_picker_val: float = 1
    dialog_color_picker_rects: dict = field(default_factory=dict)

    def reset(self) -> None:
        self.dialog_mode = None
        self.dialog_prompt = ""
        self.dialog_options = []
        self.dialog_callback = None
        self.dialog_input_text = ""
        self.dialog_input_active = False
        self.dialog_input_rect = None
        self.dialog_file_list = []
        self.dialog_file_scroll_offset = 0
        self.dialog_selected_file_index = -1
        self.dialog_file_labels = []
        self.dialog_file_list_rect = None
        self.dialog_file_page_size = 0
        self.dialog_file_scrollbar_rect = None
        self.dialog_file_scroll_thumb_rect = None
        self.dialog_file_dragging_scrollbar = False
        self.dialog_quick_dirs = []
        self.dialog_quick_dir_rects = []
        self.dialog_current_dir = ""
        self.dialog_sort_recent = True
        self.dialog_color_picker_hue = 0
        self.dialog_color_picker_sat = 1
        self.dialog_color_picker_val = 1
        self.dialog_color_picker_rects = {}


class DialogManager:
    def __init__(self, editor):
        self.editor = editor
        self.state = DialogState()

    def choose_edit_mode(self):
        state = self.state
        state.dialog_mode = 'choose_edit_mode'
        state.dialog_prompt = "Choose Edit Mode:"

        dialog_center_x = config.EDITOR_WIDTH // 2
        dialog_center_y = config.EDITOR_HEIGHT // 2
        button_width = 150
        button_height = 40
        button_padding = 10
        monster_button_y = dialog_center_y - button_height - button_padding
        tile_button_y = dialog_center_y
        background_button_y = dialog_center_y + button_height + button_padding
        button_x = dialog_center_x - button_width // 2

        state.dialog_options = [
            Button(pygame.Rect(button_x, monster_button_y, button_width, button_height), "Monster", value="monster"),
            Button(pygame.Rect(button_x, tile_button_y, button_width, button_height), "Tiles", value="tile"),
            Button(pygame.Rect(button_x, background_button_y, button_width, button_height), "Background", value="background"),
        ]
        state.dialog_callback = self.editor._set_edit_mode_and_continue

    def _handle_dialog_choice(self, value):
        state = self.state
        callback_to_call = state.dialog_callback
        if callback_to_call:
            if value is None:
                print("Dialog action cancelled by user.")
                state.reset()
            else:
                try:
                    callback_to_call(value)
                except Exception as e:
                    print(f"ERROR during dialog callback {getattr(callback_to_call, '__name__', 'unknown')}: {e}")
                    state.reset()

    def choose_background_action(self):
        state = self.state
        if not self.editor.backgrounds:
            print("No existing backgrounds. Creating a new one.")
            self.create_new_background()
            return

        state.dialog_mode = 'choose_bg_action'
        state.dialog_prompt = "Choose Background Action:"
        dialog_center_x = config.EDITOR_WIDTH // 2
        dialog_center_y = config.EDITOR_HEIGHT // 2
        button_width = 150
        button_height = 40
        button_padding = 10
        new_button_y = dialog_center_y - button_height - button_padding // 2
        edit_button_y = dialog_center_y + button_padding // 2
        button_x = dialog_center_x - button_width // 2
        state.dialog_options = [
            Button(pygame.Rect(button_x, new_button_y, button_width, button_height), "New", value="new"),
            Button(pygame.Rect(button_x, edit_button_y, button_width, button_height), "Edit Existing", value="edit"),
        ]
        state.dialog_callback = self._handle_background_action_choice

    def _handle_background_action_choice(self, action):
        state = self.state
        print(f"Background action chosen: {action}")
        if action == 'new':
            self.create_new_background()
        elif action == 'edit' and self.editor.backgrounds:
            self.editor.current_background_index = 0
            self.editor.current_background = self.editor.backgrounds[self.editor.current_background_index][1].copy()
            print(f"Editing background: {self.editor.backgrounds[self.editor.current_background_index][0]}")
            self.editor.buttons = self.editor.create_buttons()
            state.reset()
        else:
            print("Invalid action or no backgrounds to edit. Creating new.")
            self.create_new_background()

    def create_new_background(self):
        state = self.state
        state.dialog_mode = 'input_text'
        state.dialog_prompt = "Enter filename for new background (.png):"
        state.dialog_input_text = "new_background.png"
        state.dialog_input_active = True
        state.dialog_options = [
            Button(pygame.Rect(0, 0, 100, 40), "Save", action=lambda: self._handle_dialog_choice(state.dialog_input_text)),
            Button(pygame.Rect(0, 0, 100, 40), "Cancel", action=lambda: self._handle_dialog_choice(None)),
        ]
        state.dialog_callback = self._create_new_background_callback

    def _create_new_background_callback(self, filename):
        state = self.state
        if filename:
            surface = pygame.Surface((config.DEFAULT_BACKGROUND_WIDTH, config.DEFAULT_BACKGROUND_HEIGHT), pygame.SRCALPHA)
            surface.fill((*config.WHITE, 255))
            full_path = self.editor.file_io.save_background(surface, filename)
            if full_path:
                print(f"Saved background as {full_path}")
                self.editor.current_background = surface
                self.editor.backgrounds = self.editor.file_io.load_backgrounds()
                base_filename = os.path.basename(full_path)
                self.editor.current_background_index = next(
                    (i for i, (name, _) in enumerate(self.editor.backgrounds) if name == base_filename),
                    -1,
                )
                self.editor.buttons = self.editor.create_buttons()
                state.reset()
            else:
                print("Error saving new background.")
        else:
            print("New background creation cancelled.")
            if self.editor.edit_mode == 'background' and self.editor.current_background_index == -1:
                if self.editor.backgrounds:
                    self.editor.current_background_index = 0
                    self.editor.current_background = self.editor.backgrounds[0][1].copy()
                    self.editor.buttons = self.editor.create_buttons()

    def save_background(self, filename=None):
        state = self.state
        current_filename = None
        if self.editor.current_background_index >= 0 and self.editor.backgrounds:
            current_filename = self.editor.backgrounds[self.editor.current_background_index][0]

        if not filename:
            filename_to_save = current_filename
            if not filename_to_save:
                state.dialog_mode = 'input_text'
                state.dialog_prompt = "Enter filename to save background (.png):"
                state.dialog_input_text = "background.png"
                state.dialog_input_active = True
                state.dialog_options = [
                    Button(pygame.Rect(0, 0, 100, 40), "Save", action=lambda: self._handle_dialog_choice(state.dialog_input_text)),
                    Button(pygame.Rect(0, 0, 100, 40), "Cancel", action=lambda: self._handle_dialog_choice(None)),
                ]
                state.dialog_callback = self._save_background_callback
                return
            self._save_background_callback(filename_to_save)
        else:
            print(f"Warning: Direct saving to specified filename '{filename}' without dialog.")
            self._save_background_callback(filename)

    def _save_background_callback(self, filename):
        state = self.state
        if filename:
            if not self.editor.current_background:
                print("No background to save.")
                return
            full_path = self.editor.file_io.save_background(self.editor.current_background, filename)
            if not full_path:
                return
            print(f"Saved background as {full_path}")
            self.editor.backgrounds = self.editor.file_io.load_backgrounds()
            base_filename = os.path.basename(full_path)
            self.editor.current_background_index = next(
                (i for i, (name, _) in enumerate(self.editor.backgrounds) if name == base_filename),
                -1,
            )
            self.editor.buttons = self.editor.create_buttons()
            state.reset()
        else:
            print("Background save cancelled.")

    def trigger_load_tileset_dialog(self):
        state = self.state
        if self.editor.edit_mode != 'tile':
            print("Tileset loading only available in tile edit mode.")
            return

        state.dialog_mode = 'load_tileset'
        state.dialog_prompt = "Select Tileset to Load:"
        state.dialog_file_list = list_tileset_files()
        state.dialog_file_scroll_offset = 0
        state.dialog_selected_file_index = -1
        state.dialog_file_labels = [os.path.basename(path) for path in state.dialog_file_list]
        state.dialog_quick_dirs = []
        state.dialog_quick_dir_rects = []

        state.dialog_options = [
            Button(
                pygame.Rect(0, 0, 100, 40),
                "Load",
                action=lambda: self._handle_dialog_choice(
                    state.dialog_file_list[state.dialog_selected_file_index]
                    if 0 <= state.dialog_selected_file_index < len(state.dialog_file_list)
                    else None
                ),
            ),
            Button(pygame.Rect(0, 0, 100, 40), "Cancel", action=lambda: self._handle_dialog_choice(None)),
        ]
        state.dialog_callback = self._load_selected_tileset_callback

    def trigger_load_background_dialog(self):
        state = self.state
        if self.editor.edit_mode != 'background':
            print("Load background only available in background edit mode.")
            return

        state.dialog_mode = 'load_bg'
        state.dialog_prompt = "Select Background to Load:"
        state.dialog_file_list = self._get_background_files()
        state.dialog_file_scroll_offset = 0
        state.dialog_selected_file_index = -1
        state.dialog_file_labels = list(state.dialog_file_list)
        state.dialog_quick_dirs = []
        state.dialog_quick_dir_rects = []

        state.dialog_options = [
            Button(
                pygame.Rect(0, 0, 100, 40),
                "Load",
                action=lambda: self._handle_dialog_choice(
                    state.dialog_file_list[state.dialog_selected_file_index]
                    if 0 <= state.dialog_selected_file_index < len(state.dialog_file_list)
                    else None
                ),
            ),
            Button(pygame.Rect(0, 0, 100, 40), "Cancel", action=lambda: self._handle_dialog_choice(None)),
        ]
        state.dialog_callback = self._load_selected_background_callback

    def trigger_load_reference_dialog(self):
        state = self.state
        if self.editor.edit_mode not in ['monster', 'tile']:
            print("Reference images only available in monster or tile edit mode.")
            return

        state.dialog_mode = 'load_ref'
        state.dialog_prompt = "Select Reference Image:"
        state.dialog_file_scroll_offset = 0
        state.dialog_selected_file_index = -1
        state.dialog_sort_recent = True
        state.dialog_quick_dirs = []
        home_dir = os.path.expanduser("~")
        desktop_dir = os.path.join(home_dir, "Desktop")
        downloads_dir = os.path.join(home_dir, "Downloads")
        for label, path in [
            ("Desktop", desktop_dir),
            ("Downloads", downloads_dir),
            ("References", config.REFERENCE_IMAGE_DIR),
            ("Sprites", config.SPRITE_DIR),
            ("Backgrounds", config.BACKGROUND_DIR),
        ]:
            if os.path.isdir(path):
                state.dialog_quick_dirs.append((label, path))

        default_dir = config.REFERENCE_IMAGE_DIR
        if not os.path.isdir(default_dir) and state.dialog_quick_dirs:
            default_dir = state.dialog_quick_dirs[0][1]
        self._set_dialog_directory(default_dir)

        state.dialog_options = [
            Button(
                pygame.Rect(0, 0, 100, 40),
                "Load",
                action=lambda: self._handle_dialog_choice(
                    state.dialog_file_list[state.dialog_selected_file_index]
                    if 0 <= state.dialog_selected_file_index < len(state.dialog_file_list)
                    else None
                ),
            ),
            Button(pygame.Rect(0, 0, 100, 40), "Cancel", action=lambda: self._handle_dialog_choice(None)),
        ]
        state.dialog_callback = self._load_selected_reference_callback

    def _load_selected_reference_callback(self, file_path):
        state = self.state
        if file_path:
            if not os.path.exists(file_path):
                print(f"Error: Reference file {file_path} not found.")
                return
            loaded = self.editor.file_io.load_reference_image(file_path)
            if loaded:
                self.editor.reference_image = loaded
                self.editor.reference_image_path = file_path
                print(f"Loaded reference image: {file_path}")
                self.editor._scale_reference_image()
                self.editor.apply_reference_alpha()
            else:
                self.editor.reference_image = None
                self.editor.reference_image_path = None
                self.editor.scaled_reference_image = None
            state.reset()
        else:
            print("Reference image load cancelled.")

    def _load_selected_tileset_callback(self, filename_or_path):
        state = self.state
        if filename_or_path:
            path = filename_or_path
            if not os.path.isabs(path):
                path = os.path.join(config.TILESET_DIR, filename_or_path)
            if not os.path.exists(path):
                print(f"Tileset file {path} not found.")
            else:
                self.editor.load_tileset(path)
                self.editor.buttons = self.editor.create_buttons()
            state.reset()
        else:
            print("Tileset load cancelled.")

    def _load_selected_background_callback(self, filename):
        state = self.state
        if filename:
            loaded_bg = self.editor.file_io.load_background(filename)
            if loaded_bg is None:
                return

            found_index = -1
            for i, (name, _) in enumerate(self.editor.backgrounds):
                if name == filename:
                    found_index = i
                    break

            if found_index != -1:
                self.editor.current_background_index = found_index
                self.editor.current_background = self.editor.backgrounds[found_index][1].copy()
                print(f"Loaded background: {filename}")
            else:
                self.editor.current_background = loaded_bg
                self.editor.backgrounds.append((filename, loaded_bg))
                self.editor.current_background_index = len(self.editor.backgrounds) - 1
                print(f"Loaded background {filename} directly.")

            self.editor.undo_stack = []
            self.editor.redo_stack = []
            state.reset()
        else:
            print("Background load cancelled.")

    def _get_background_files(self):
        try:
            return [f for f in os.listdir(config.BACKGROUND_DIR) if f.endswith('.png')]
        except (FileNotFoundError, PermissionError, OSError) as e:
            print(f"Warning: cannot read background directory {config.BACKGROUND_DIR}: {e}")
            return []

    def _get_reference_files(self, directory):
        image_exts = ('.png', '.jpg', '.jpeg', '.bmp', '.gif')
        file_paths = []
        try:
            for name in os.listdir(directory):
                path = os.path.join(directory, name)
                if os.path.isfile(path) and name.lower().endswith(image_exts):
                    file_paths.append(path)
        except (FileNotFoundError, PermissionError, OSError):
            return []
        return file_paths

    def _set_dialog_directory(self, directory):
        state = self.state
        if not directory:
            return
        if not os.path.isdir(directory):
            print(f"Directory unavailable: {directory}")
            state.dialog_file_list = []
            state.dialog_file_labels = []
            state.dialog_selected_file_index = -1
            return
        state.dialog_current_dir = directory
        files = self._get_reference_files(directory)
        if state.dialog_sort_recent:
            def _mtime_or_zero(path):
                try:
                    return os.path.getmtime(path)
                except OSError:
                    return 0
            files.sort(key=_mtime_or_zero, reverse=True)
        else:
            files.sort(key=lambda p: os.path.basename(p).lower())
        state.dialog_file_list = files
        state.dialog_file_labels = [os.path.basename(path) for path in files]
        state.dialog_file_scroll_offset = 0
        state.dialog_selected_file_index = 0 if files else -1

    def _update_scrollbar_from_offset(self):
        state = self.state
        if not state.dialog_file_scrollbar_rect:
            return
        total = len(state.dialog_file_list)
        visible = max(1, state.dialog_file_page_size)
        if total <= visible:
            state.dialog_file_scroll_thumb_rect = pygame.Rect(
                state.dialog_file_scrollbar_rect.x,
                state.dialog_file_scrollbar_rect.y,
                state.dialog_file_scrollbar_rect.width,
                state.dialog_file_scrollbar_rect.height,
            )
            return
        ratio = visible / total
        thumb_height = max(20, int(state.dialog_file_scrollbar_rect.height * ratio))
        max_offset = total - visible
        top = state.dialog_file_scrollbar_rect.y
        if max_offset > 0:
            top += int((state.dialog_file_scroll_offset / max_offset) * (state.dialog_file_scrollbar_rect.height - thumb_height))
        state.dialog_file_scroll_thumb_rect = pygame.Rect(
            state.dialog_file_scrollbar_rect.x,
            top,
            state.dialog_file_scrollbar_rect.width,
            thumb_height,
        )

    def _set_scroll_offset_from_thumb(self, thumb_center_y):
        state = self.state
        total = len(state.dialog_file_list)
        visible = max(1, state.dialog_file_page_size)
        if total <= visible or not state.dialog_file_scrollbar_rect:
            return
        max_offset = total - visible
        track_height = state.dialog_file_scrollbar_rect.height
        thumb_height = state.dialog_file_scroll_thumb_rect.height if state.dialog_file_scroll_thumb_rect else 20
        usable = max(1, track_height - thumb_height)
        relative = thumb_center_y - state.dialog_file_scrollbar_rect.y - (thumb_height // 2)
        relative = max(0, min(relative, usable))
        state.dialog_file_scroll_offset = int(round((relative / usable) * max_offset))

    def _ensure_dialog_scroll(self):
        state = self.state
        if state.dialog_file_page_size <= 0:
            return
        if state.dialog_selected_file_index < state.dialog_file_scroll_offset:
            state.dialog_file_scroll_offset = state.dialog_selected_file_index
        elif state.dialog_selected_file_index >= state.dialog_file_scroll_offset + state.dialog_file_page_size:
            state.dialog_file_scroll_offset = state.dialog_selected_file_index - state.dialog_file_page_size + 1

    def draw_dialog(self, surface):
        state = self.state
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((*config.BLACK[:3], 180))
        surface.blit(overlay, (0, 0))

        dialog_width = 400
        dialog_height = 300
        dialog_rect = pygame.Rect(0, 0, dialog_width, dialog_height)
        dialog_rect.center = surface.get_rect().center
        pygame.draw.rect(surface, config.WHITE, dialog_rect, border_radius=5)
        pygame.draw.rect(surface, config.BLACK, dialog_rect, 2, border_radius=5)

        prompt_surf = self.editor.font.render(state.dialog_prompt, True, config.BLACK)
        prompt_rect = prompt_surf.get_rect(midtop=(dialog_rect.centerx, dialog_rect.top + 20))
        surface.blit(prompt_surf, prompt_rect)

        list_top = prompt_rect.bottom + 10
        list_height = 150
        button_y = prompt_rect.bottom + 30
        if state.dialog_mode in ['load_bg', 'load_ref', 'load_tileset']:
            list_rect = pygame.Rect(
                dialog_rect.x + 20,
                list_top,
                dialog_rect.width - 40,
                list_height,
            )
            state.dialog_file_list_rect = list_rect
            pygame.draw.rect(surface, config.GRAY_LIGHT, list_rect)
            pygame.draw.rect(surface, config.BLACK, list_rect, 1)

            line_height = self.editor.font.get_linesize()
            state.dialog_file_page_size = max(1, list_rect.height // line_height)
            scrollbar_width = 12
            state.dialog_file_scrollbar_rect = pygame.Rect(
                list_rect.right - scrollbar_width,
                list_rect.y,
                scrollbar_width,
                list_rect.height,
            )
            pygame.draw.rect(surface, config.GRAY_MEDIUM, state.dialog_file_scrollbar_rect)
            end_index = min(
                state.dialog_file_scroll_offset + state.dialog_file_page_size,
                len(state.dialog_file_list),
            )
            for row, index in enumerate(range(state.dialog_file_scroll_offset, end_index)):
                label = (
                    state.dialog_file_labels[index]
                    if index < len(state.dialog_file_labels)
                    else str(state.dialog_file_list[index])
                )
                text_color = config.WHITE if index == state.dialog_selected_file_index else config.BLACK
                if index == state.dialog_selected_file_index:
                    highlight_rect = pygame.Rect(
                        list_rect.x,
                        list_rect.y + row * line_height,
                        list_rect.width,
                        line_height,
                    )
                    pygame.draw.rect(surface, config.BLUE, highlight_rect)
                text_surf = self.editor.font.render(label, True, text_color)
                surface.blit(text_surf, (list_rect.x + 6, list_rect.y + row * line_height))

            quick_y = list_rect.bottom + 10
            quick_x = list_rect.x
            quick_padding = 8
            state.dialog_quick_dir_rects = []
            for label, path in state.dialog_quick_dirs:
                quick_surf = self.editor.font.render(label, True, config.BLACK)
                quick_rect = quick_surf.get_rect()
                quick_rect.topleft = (quick_x, quick_y)
                pygame.draw.rect(surface, config.GRAY_LIGHT, quick_rect.inflate(8, 6))
                pygame.draw.rect(surface, config.BLACK, quick_rect.inflate(8, 6), 1)
                surface.blit(quick_surf, quick_rect)
                state.dialog_quick_dir_rects.append((quick_rect.inflate(8, 6), path))
                quick_x += quick_rect.width + quick_padding + 8

            self._update_scrollbar_from_offset()
            if state.dialog_file_scroll_thumb_rect:
                pygame.draw.rect(surface, config.GRAY_DARK, state.dialog_file_scroll_thumb_rect)

            button_y = list_rect.bottom + 50
        else:
            state.dialog_file_list_rect = None
            state.dialog_file_page_size = 0
            state.dialog_file_scrollbar_rect = None
            state.dialog_file_scroll_thumb_rect = None
            if state.dialog_mode == 'input_text':
                input_rect = pygame.Rect(dialog_rect.x + 40, prompt_rect.bottom + 20, dialog_rect.width - 80, 40)
                pygame.draw.rect(surface, config.WHITE, input_rect)
                pygame.draw.rect(surface, config.BLACK, input_rect, 1)
                text_surf = self.editor.font.render(state.dialog_input_text, True, config.BLACK)
                surface.blit(text_surf, (input_rect.x + 8, input_rect.y + 8))
                button_y = input_rect.bottom + 20

        for i, option in enumerate(state.dialog_options):
            if isinstance(option, Button):
                option.rect.centerx = dialog_rect.centerx
                option.rect.top = button_y + i * (option.rect.height + 10)
                option.draw(surface)
