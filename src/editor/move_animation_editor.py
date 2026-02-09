from __future__ import annotations

import argparse
import os
from typing import Callable

import pygame

from src.core import config
from src.editor.move_animation_io import (
    SurfaceMap,
    create_new_move_animation,
    list_move_animation_files,
    load_move_animation,
    save_move_animation,
)
from src.editor.move_animation_state import (
    MoveAnimationState,
    OnionSkinSettings,
)
from src.editor.move_animation_ui import (
    ATTACKER_ANCHOR_SCALE,
    MoveAnimationLayout,
    compute_layout,
    draw_object_canvas,
    draw_object_panel,
    draw_stage_preview,
    draw_status_bar,
    draw_timeline,
    draw_top_buttons,
)

WINDOW_TITLE = "Move Animation Editor"
BACKGROUND = (26, 30, 40)
ANCHOR_ORDER = ["attacker", "defender", "screen"]
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp")


class MoveAnimationEditor:
    def __init__(self, initial_ref: str | None = None, *, start_new_id: str | None = None) -> None:
        self.state, self.surfaces = self._initial_state(initial_ref=initial_ref, start_new_id=start_new_id)

        pygame.init()
        self.screen = pygame.display.set_mode((config.EDITOR_WIDTH, config.EDITOR_HEIGHT))
        pygame.display.set_caption(WINDOW_TITLE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(config.DEFAULT_FONT, 16)
        self.font_small = pygame.font.Font(config.DEFAULT_FONT, 13)

        self.layout: MoveAnimationLayout = compute_layout(self.screen.get_size())

        self.current_frame = 0
        self.active_object_id = self.state.objects[0].object_id
        self.selected_color = (255, 120, 70, 255)

        self.onion_skin = OnionSkinSettings()
        self.apply_to_all_frames = False
        self.loop_playback = True
        self.playing = False
        self.playback_elapsed_ms = 0

        self.status_text = ""
        self.status_expires = 0

        self.button_rects: dict[str, pygame.Rect] = {}
        self.object_rows: list[tuple[str, pygame.Rect]] = []
        self.frame_rects: list[pygame.Rect] = []
        self.stage_object_rects: dict[str, pygame.Rect] = {}
        self.object_canvas_rect = pygame.Rect(0, 0, 0, 0)

        self.dragging_object_id: str | None = None
        self.drag_residual_x = 0.0
        self.drag_residual_y = 0.0
        self.timeline_drag_index: int | None = None
        self.painting = False
        self.paint_button = 1

        self.reference_image: pygame.Surface | None = None
        self.reference_image_path: str | None = None
        self.reference_alpha = 120
        self.reference_scale = 1.0
        self.reference_offset = pygame.Vector2(0, 0)
        self.reference_panning = False
        self._last_reference_index = -1
        self._last_open_index = -1

        # Pygame modal file dialog state (Tk-free).
        self.dialog_mode: str | None = None
        self.dialog_prompt = ""
        self.dialog_file_list: list[str] = []
        self.dialog_file_labels: list[str] = []
        self.dialog_selected_file_index = -1
        self.dialog_file_scroll_offset = 0
        self.dialog_file_page_size = 0
        self.dialog_file_list_rect: pygame.Rect | None = None
        self.dialog_file_scrollbar_rect: pygame.Rect | None = None
        self.dialog_file_scroll_thumb_rect: pygame.Rect | None = None
        self.dialog_file_dragging_scrollbar = False
        self.dialog_quick_dirs: list[tuple[str, str]] = []
        self.dialog_quick_dir_rects: list[tuple[pygame.Rect, str]] = []
        self.dialog_current_dir = ""
        self.dialog_sort_recent = True
        self.dialog_load_button_rect: pygame.Rect | None = None
        self.dialog_cancel_button_rect: pygame.Rect | None = None

    def _next_new_animation_id(self, base_id: str = "new_animation") -> str:
        existing = set()
        try:
            existing.update(self._available_animation_ids())
        except Exception:
            pass
        if base_id not in existing:
            return base_id
        idx = 2
        while True:
            candidate = f"{base_id}_{idx}"
            if candidate not in existing:
                return candidate
            idx += 1

    def _available_animation_ids(self) -> list[str]:
        ids: list[str] = []
        for path in list_move_animation_files():
            ids.append(os.path.splitext(os.path.basename(path))[0])
        return ids

    def _fallback_reference_image_path(self) -> str | None:
        roots = self._reference_search_dirs()
        files = self._discover_image_files(roots)
        if not files:
            return None
        if self.reference_image_path and self.reference_image_path in files:
            idx = files.index(self.reference_image_path)
        else:
            idx = self._last_reference_index
        next_idx = (idx + 1) % len(files)
        self._last_reference_index = next_idx
        return files[next_idx]

    def _reference_search_dirs(self) -> list[str]:
        dirs: list[str] = []
        home = os.path.expanduser("~")
        for candidate in [
            config.REFERENCE_IMAGE_DIR,
            config.SPRITE_DIR,
            config.BACKGROUND_DIR,
            os.path.join(home, "Desktop"),
            os.path.join(home, "Downloads"),
        ]:
            if os.path.isdir(candidate):
                dirs.append(candidate)
        return dirs

    def _discover_image_files(self, roots: list[str]) -> list[str]:
        seen: set[str] = set()
        files: list[str] = []
        for root in roots:
            if not os.path.isdir(root):
                continue
            for name in sorted(os.listdir(root)):
                if not name.lower().endswith(IMAGE_EXTENSIONS):
                    continue
                full = os.path.join(root, name)
                if not os.path.isfile(full):
                    continue
                if full in seen:
                    continue
                seen.add(full)
                files.append(full)
        return files

    def _initial_state(
        self,
        *,
        initial_ref: str | None,
        start_new_id: str | None,
    ) -> tuple[MoveAnimationState, SurfaceMap]:
        if start_new_id:
            return create_new_move_animation(start_new_id)
        if initial_ref:
            try:
                state, surfaces = load_move_animation(initial_ref)
                return state, surfaces
            except FileNotFoundError:
                pass
        picked = self._prompt_startup()
        if picked:
            kind, value = picked
            if kind == "open":
                return load_move_animation(value)
            return create_new_move_animation(value)
        return create_new_move_animation(self._next_new_animation_id("new_animation"))

    def _prompt_startup(self) -> tuple[str, str] | None:
        files = list_move_animation_files()
        if files:
            return ("open", files[0])
        return ("new", self._next_new_animation_id("new_animation"))

    def _reset_dialog(self) -> None:
        self.dialog_mode = None
        self.dialog_prompt = ""
        self.dialog_file_list = []
        self.dialog_file_labels = []
        self.dialog_selected_file_index = -1
        self.dialog_file_scroll_offset = 0
        self.dialog_file_page_size = 0
        self.dialog_file_list_rect = None
        self.dialog_file_scrollbar_rect = None
        self.dialog_file_scroll_thumb_rect = None
        self.dialog_file_dragging_scrollbar = False
        self.dialog_quick_dirs = []
        self.dialog_quick_dir_rects = []
        self.dialog_current_dir = ""
        self.dialog_load_button_rect = None
        self.dialog_cancel_button_rect = None

    def _set_dialog_directory(self, directory: str) -> None:
        if not directory:
            return
        if not os.path.isdir(directory):
            self.dialog_current_dir = ""
            self.dialog_file_list = []
            self.dialog_file_labels = []
            self.dialog_selected_file_index = -1
            return

        self.dialog_current_dir = directory
        files = self._discover_image_files([directory])
        if self.dialog_sort_recent:
            def _mtime_or_zero(path: str) -> float:
                try:
                    return os.path.getmtime(path)
                except OSError:
                    return 0
            files.sort(key=_mtime_or_zero, reverse=True)
        else:
            files.sort(key=lambda p: os.path.basename(p).lower())
        self.dialog_file_list = files
        self.dialog_file_labels = [os.path.basename(path) for path in files]
        self.dialog_file_scroll_offset = 0
        self.dialog_selected_file_index = 0 if files else -1

    def _update_dialog_scrollbar_from_offset(self) -> None:
        if not self.dialog_file_scrollbar_rect:
            return
        total = len(self.dialog_file_list)
        visible = max(1, self.dialog_file_page_size)
        if total <= visible:
            self.dialog_file_scroll_thumb_rect = pygame.Rect(
                self.dialog_file_scrollbar_rect.x,
                self.dialog_file_scrollbar_rect.y,
                self.dialog_file_scrollbar_rect.width,
                self.dialog_file_scrollbar_rect.height,
            )
            return
        ratio = visible / total
        thumb_height = max(20, int(self.dialog_file_scrollbar_rect.height * ratio))
        max_offset = total - visible
        top = self.dialog_file_scrollbar_rect.y
        if max_offset > 0:
            top += int((self.dialog_file_scroll_offset / max_offset) * (self.dialog_file_scrollbar_rect.height - thumb_height))
        self.dialog_file_scroll_thumb_rect = pygame.Rect(
            self.dialog_file_scrollbar_rect.x,
            top,
            self.dialog_file_scrollbar_rect.width,
            thumb_height,
        )

    def _set_dialog_scroll_offset_from_thumb(self, thumb_center_y: int) -> None:
        total = len(self.dialog_file_list)
        visible = max(1, self.dialog_file_page_size)
        if total <= visible or not self.dialog_file_scrollbar_rect:
            return
        max_offset = total - visible
        track_height = self.dialog_file_scrollbar_rect.height
        thumb_height = self.dialog_file_scroll_thumb_rect.height if self.dialog_file_scroll_thumb_rect else 20
        usable = max(1, track_height - thumb_height)
        relative = thumb_center_y - self.dialog_file_scrollbar_rect.y - (thumb_height // 2)
        relative = max(0, min(relative, usable))
        self.dialog_file_scroll_offset = int(round((relative / usable) * max_offset))

    def _ensure_dialog_scroll(self) -> None:
        if self.dialog_file_page_size <= 0:
            return
        if self.dialog_selected_file_index < self.dialog_file_scroll_offset:
            self.dialog_file_scroll_offset = self.dialog_selected_file_index
        elif self.dialog_selected_file_index >= self.dialog_file_scroll_offset + self.dialog_file_page_size:
            self.dialog_file_scroll_offset = self.dialog_selected_file_index - self.dialog_file_page_size + 1

    def _open_animation_dialog(self) -> None:
        self._reset_dialog()
        self.dialog_mode = "open_animation"
        self.dialog_prompt = "Select Move Animation:"
        self.dialog_file_list = list_move_animation_files()
        self.dialog_file_labels = [os.path.basename(path) for path in self.dialog_file_list]
        self.dialog_selected_file_index = 0 if self.dialog_file_list else -1
        self.dialog_sort_recent = True

    def _open_reference_dialog(self) -> None:
        self._reset_dialog()
        self.dialog_mode = "load_ref"
        self.dialog_prompt = "Select Reference Image:"
        self.dialog_sort_recent = True
        path_to_label = {
            config.REFERENCE_IMAGE_DIR: "References",
            config.SPRITE_DIR: "Sprites",
            config.BACKGROUND_DIR: "Backgrounds",
        }
        home = os.path.expanduser("~")
        desktop_dir = os.path.join(home, "Desktop")
        downloads_dir = os.path.join(home, "Downloads")
        path_to_label[desktop_dir] = "Desktop"
        path_to_label[downloads_dir] = "Downloads"

        search_dirs = self._reference_search_dirs()
        for path in search_dirs:
            self.dialog_quick_dirs.append((path_to_label.get(path, os.path.basename(path) or path), path))

        default_dir = config.REFERENCE_IMAGE_DIR if config.REFERENCE_IMAGE_DIR in search_dirs else ""
        if not default_dir and self.dialog_quick_dirs:
            default_dir = self.dialog_quick_dirs[0][1]
        self._set_dialog_directory(default_dir)

    def _confirm_dialog_selection(self) -> None:
        if not (0 <= self.dialog_selected_file_index < len(self.dialog_file_list)):
            self._set_status("No file selected.")
            return
        selected = self.dialog_file_list[self.dialog_selected_file_index]
        if self.dialog_mode == "open_animation":
            self._load_selected_animation(selected)
        elif self.dialog_mode == "load_ref":
            self._load_selected_reference(selected)
        self._reset_dialog()

    def _load_selected_animation(self, path: str) -> None:
        self.state, self.surfaces = load_move_animation(path)
        self.current_frame = 0
        self.active_object_id = self.state.objects[0].object_id
        self.playing = False
        self.playback_elapsed_ms = 0
        self._set_status(f"Loaded {os.path.basename(path)}")

    def _load_selected_reference(self, path: str) -> None:
        try:
            loaded = pygame.image.load(path)
            self.reference_image = loaded.convert_alpha() if pygame.display.get_surface() else loaded
            self.reference_image_path = path
            self.reference_scale = 1.0
            self.reference_offset.update(0, 0)
            self._set_status(f"Reference loaded: {os.path.basename(path)}")
        except pygame.error:
            self._set_status("Failed to load reference image.")

    def _set_status(self, text: str, ttl_ms: int = 2500) -> None:
        self.status_text = text
        self.status_expires = pygame.time.get_ticks() + max(0, int(ttl_ms))

    @property
    def active_object(self):
        obj = self.state.get_object(self.active_object_id)
        if obj is None:
            self.active_object_id = self.state.objects[0].object_id
            obj = self.state.objects[0]
        return obj

    def _get_surface(self, object_id: str, frame_index: int) -> pygame.Surface:
        obj = self.state.get_object(object_id)
        if obj is None:
            raise KeyError(object_id)
        key = (object_id, frame_index)
        if key not in self.surfaces:
            surface = pygame.Surface((obj.size_w, obj.size_h), pygame.SRCALPHA)
            surface.fill((0, 0, 0, 0))
            self.surfaces[key] = surface
        surface = self.surfaces[key]
        if surface.get_size() != (obj.size_w, obj.size_h):
            surface = pygame.transform.scale(surface, (obj.size_w, obj.size_h))
            self.surfaces[key] = surface
        return surface

    def _capture_surface_lists(self, frame_count: int) -> dict[str, list[pygame.Surface]]:
        captured: dict[str, list[pygame.Surface]] = {}
        for obj in self.state.objects:
            frames: list[pygame.Surface] = []
            for idx in range(frame_count):
                frames.append(self._get_surface(obj.object_id, idx))
            captured[obj.object_id] = frames
        return captured

    def _apply_surface_lists(self, frame_surfaces: dict[str, list[pygame.Surface]]) -> None:
        remapped: SurfaceMap = {}
        for obj in self.state.objects:
            target_size = (obj.size_w, obj.size_h)
            source_list = frame_surfaces.get(obj.object_id, [])
            for idx in range(self.state.frame_count):
                if idx < len(source_list):
                    surf = source_list[idx]
                else:
                    surf = pygame.Surface(target_size, pygame.SRCALPHA)
                    surf.fill((0, 0, 0, 0))
                if surf.get_size() != target_size:
                    surf = pygame.transform.scale(surf, target_size)
                remapped[(obj.object_id, idx)] = surf
        self.surfaces = remapped

    def _reorder_frame_surfaces(self, old_index: int, new_index: int) -> None:
        old_count = self.state.frame_count
        old_index = max(0, min(old_index, old_count - 1))
        new_index = max(0, min(new_index, old_count - 1))
        if old_index == new_index:
            return
        snapshot = self._capture_surface_lists(old_count)
        order = list(range(old_count))
        moved = order.pop(old_index)
        order.insert(new_index, moved)
        remapped: dict[str, list[pygame.Surface]] = {}
        for obj in self.state.objects:
            old_list = snapshot[obj.object_id]
            remapped[obj.object_id] = [old_list[old_i] for old_i in order]
        self._apply_surface_lists(remapped)

    def _add_frame(self) -> None:
        old_count = self.state.frame_count
        snapshot = self._capture_surface_lists(old_count)
        new_index = self.state.append_frame(copy_transforms=True, copy_images=False)
        for obj in self.state.objects:
            blank = pygame.Surface((obj.size_w, obj.size_h), pygame.SRCALPHA)
            blank.fill((0, 0, 0, 0))
            snapshot[obj.object_id].append(blank)
        self._apply_surface_lists(snapshot)
        self.current_frame = new_index
        self._set_status("Frame added.")

    def _duplicate_frame(self) -> None:
        old_count = self.state.frame_count
        source_index = self.current_frame
        snapshot = self._capture_surface_lists(old_count)
        insert_at = self.state.duplicate_frame(source_index)
        remapped: dict[str, list[pygame.Surface]] = {}
        for obj in self.state.objects:
            old_list = snapshot[obj.object_id]
            new_list: list[pygame.Surface] = []
            for idx in range(old_count + 1):
                if idx < insert_at:
                    new_list.append(old_list[idx])
                elif idx == insert_at:
                    new_list.append(old_list[source_index].copy())
                else:
                    new_list.append(old_list[idx - 1])
            remapped[obj.object_id] = new_list
        self._apply_surface_lists(remapped)
        self.current_frame = insert_at
        self._set_status("Frame duplicated.")

    def _delete_frame(self) -> None:
        old_count = self.state.frame_count
        if old_count <= 1:
            self._set_status("At least one frame is required.")
            return
        remove_index = self.current_frame
        snapshot = self._capture_surface_lists(old_count)
        if not self.state.delete_frame(remove_index):
            self._set_status("Frame delete blocked.")
            return
        remapped: dict[str, list[pygame.Surface]] = {}
        for obj in self.state.objects:
            old_list = snapshot[obj.object_id]
            new_list = [old_list[idx] for idx in range(old_count) if idx != remove_index]
            remapped[obj.object_id] = new_list
        self._apply_surface_lists(remapped)
        self.current_frame = max(0, min(self.current_frame, self.state.frame_count - 1))
        self._set_status("Frame deleted.")

    def _move_frame(self, old_index: int, new_index: int) -> None:
        old_index = max(0, min(old_index, self.state.frame_count - 1))
        new_index = max(0, min(new_index, self.state.frame_count - 1))
        if old_index == new_index:
            return
        self._reorder_frame_surfaces(old_index, new_index)
        self.state.move_frame(old_index, new_index)
        self.current_frame = new_index
        self._set_status(f"Frame moved: {old_index + 1} -> {new_index + 1}")

    def _add_object(self) -> None:
        obj = self.state.add_object(
            name=f"Object {len(self.state.objects) + 1}",
            anchor="attacker",
            size=(self.state.canvas_w, self.state.canvas_h),
        )
        for idx in range(self.state.frame_count):
            blank = pygame.Surface((obj.size_w, obj.size_h), pygame.SRCALPHA)
            blank.fill((0, 0, 0, 0))
            self.surfaces[(obj.object_id, idx)] = blank
        self.active_object_id = obj.object_id
        self._set_status(f"Added object '{obj.name}'.")

    def _remove_object(self) -> None:
        target = self.active_object_id
        if not self.state.remove_object(target):
            self._set_status("At least one object is required.")
            return
        self.surfaces = {
            key: value
            for key, value in self.surfaces.items()
            if key[0] != target
        }
        self.active_object_id = self.state.objects[0].object_id
        self._set_status("Object removed.")

    def _cycle_anchor(self) -> None:
        obj = self.active_object
        idx = ANCHOR_ORDER.index(obj.anchor)
        obj.anchor = ANCHOR_ORDER[(idx + 1) % len(ANCHOR_ORDER)]
        self._set_status(f"Anchor set to '{obj.anchor}'.")

    def _toggle_visibility(self) -> None:
        frame = self.active_object.frames[self.current_frame]
        frame.visible = not frame.visible
        self._set_status(f"Object frame visibility: {'on' if frame.visible else 'off'}.")

    def _save(self) -> None:
        path = save_move_animation(self.state, self.surfaces)
        self._set_status(f"Saved {os.path.basename(path)}", ttl_ms=3000)

    def _open_existing(self) -> None:
        self._open_animation_dialog()
        if not self.dialog_file_list:
            self._set_status("No move animation files found.")
            self._reset_dialog()

    def _new_animation(self) -> None:
        new_id = self._next_new_animation_id("new_animation")
        self.state, self.surfaces = create_new_move_animation(new_id)
        self.current_frame = 0
        self.active_object_id = self.state.objects[0].object_id
        self.playing = False
        self.playback_elapsed_ms = 0
        self._set_status(f"Created {new_id}. Use --new-id to pick custom IDs.")

    def _load_reference_image(self) -> None:
        self._open_reference_dialog()
        if not self.dialog_file_list:
            self._set_status("No reference image found.")
            self._reset_dialog()

    def _clear_reference_image(self) -> None:
        self.reference_image = None
        self.reference_offset.update(0, 0)
        self.reference_scale = 1.0
        self._set_status("Reference image cleared.")

    def _pick_color(self) -> None:
        # Deterministic non-Tk fallback cycle.
        if self.selected_color[0] == 255 and self.selected_color[1] < 200:
            self.selected_color = (40, 180, 255, 255)
        elif self.selected_color[1] > 100:
            self.selected_color = (110, 255, 120, 255)
        else:
            self.selected_color = (255, 120, 70, 255)
        self._set_status("Color cycled.")

    def _toggle_play(self) -> None:
        self.playing = not self.playing
        if self.playing:
            self.playback_elapsed_ms = 0
        self._set_status("Playback running." if self.playing else "Playback paused.")

    def _step_frame(self, delta: int) -> None:
        self.current_frame = max(0, min(self.current_frame + delta, self.state.frame_count - 1))
        self.playing = False
        self.playback_elapsed_ms = 0

    def _jump_frames(self, delta: int) -> None:
        self._step_frame(delta)

    def _set_current_frame(self, index: int) -> None:
        self.current_frame = max(0, min(index, self.state.frame_count - 1))

    def _update(self, dt_ms: int) -> None:
        if not self.playing:
            return
        if self.state.frame_count == 0:
            return
        self.playback_elapsed_ms += dt_ms
        while self.playback_elapsed_ms >= self.state.frames[self.current_frame].duration_ms:
            self.playback_elapsed_ms -= self.state.frames[self.current_frame].duration_ms
            if self.current_frame + 1 >= self.state.frame_count:
                if self.loop_playback:
                    self.current_frame = 0
                else:
                    self.playing = False
                    self.current_frame = self.state.frame_count - 1
                    break
            else:
                self.current_frame += 1

    def _compose_reference_surface(self) -> pygame.Surface | None:
        if self.reference_image is None:
            return None
        obj = self.active_object
        target = pygame.Surface((obj.size_w, obj.size_h), pygame.SRCALPHA)
        target.fill((0, 0, 0, 0))
        scaled_w = max(1, int(self.reference_image.get_width() * self.reference_scale))
        scaled_h = max(1, int(self.reference_image.get_height() * self.reference_scale))
        scaled = pygame.transform.smoothscale(self.reference_image, (scaled_w, scaled_h))
        scaled.set_alpha(max(0, min(255, int(self.reference_alpha))))
        x = (obj.size_w - scaled_w) // 2 + int(self.reference_offset.x)
        y = (obj.size_h - scaled_h) // 2 + int(self.reference_offset.y)
        target.blit(scaled, (x, y))
        return target

    def _canvas_pos_to_pixel(self, pos: tuple[int, int]) -> tuple[int, int] | None:
        if not self.object_canvas_rect.collidepoint(pos):
            return None
        obj = self.active_object
        rel_x = pos[0] - self.object_canvas_rect.x
        rel_y = pos[1] - self.object_canvas_rect.y
        px = int((rel_x / max(1, self.object_canvas_rect.width)) * obj.size_w)
        py = int((rel_y / max(1, self.object_canvas_rect.height)) * obj.size_h)
        px = max(0, min(px, obj.size_w - 1))
        py = max(0, min(py, obj.size_h - 1))
        return (px, py)

    def _paint_at(self, pos: tuple[int, int], button: int) -> bool:
        pixel = self._canvas_pos_to_pixel(pos)
        if pixel is None:
            return False
        target = self._get_surface(self.active_object_id, self.current_frame)
        if button == 3:
            target.set_at(pixel, (0, 0, 0, 0))
        else:
            target.set_at(pixel, self.selected_color)
        return True

    def _nudge_active_object(self, dx: int, dy: int) -> None:
        obj = self.active_object
        frames = obj.frames if self.apply_to_all_frames else [obj.frames[self.current_frame]]
        for frame in frames:
            frame.x += dx
            frame.y += dy

    def _apply_drag_motion(self, rel_x: int, rel_y: int) -> None:
        if not self.dragging_object_id:
            return
        obj = self.state.get_object(self.dragging_object_id)
        if obj is None:
            return
        self.drag_residual_x += rel_x
        self.drag_residual_y += rel_y
        scale = ATTACKER_ANCHOR_SCALE if obj.anchor in {"attacker", "defender"} else 1
        if obj.anchor in {"attacker", "defender"}:
            dx_units = int(self.drag_residual_x / scale)
            dy_units = int(self.drag_residual_y / scale)
            if dx_units == 0 and dy_units == 0:
                return
            self.drag_residual_x -= dx_units * scale
            self.drag_residual_y -= dy_units * scale
            delta_stage_x = dx_units * scale
            delta_stage_y = dy_units * scale
        else:
            dx_units = int(round(self.drag_residual_x))
            dy_units = int(round(self.drag_residual_y))
            if dx_units == 0 and dy_units == 0:
                return
            self.drag_residual_x -= dx_units
            self.drag_residual_y -= dy_units
            delta_stage_x = dx_units
            delta_stage_y = dy_units
        self.state.apply_drag_delta(
            self.dragging_object_id,
            frame_index=self.current_frame,
            delta_x_stage=delta_stage_x,
            delta_y_stage=delta_stage_y,
            apply_to_all_frames=self.apply_to_all_frames,
            sprite_scale=ATTACKER_ANCHOR_SCALE,
        )

    def _handle_top_button(self, button_id: str) -> None:
        actions: dict[str, Callable[[], None]] = {
            "new": self._new_animation,
            "open": self._open_existing,
            "save": self._save,
            "add_frame": self._add_frame,
            "dup_frame": self._duplicate_frame,
            "del_frame": self._delete_frame,
            "add_obj": self._add_object,
            "del_obj": self._remove_object,
            "play": self._toggle_play,
            "loop": lambda: setattr(self, "loop_playback", not self.loop_playback),
            "onion_prev": lambda: setattr(self.onion_skin, "previous_enabled", not self.onion_skin.previous_enabled),
            "onion_next": lambda: setattr(self.onion_skin, "next_enabled", not self.onion_skin.next_enabled),
            "onion_active": lambda: setattr(
                self.onion_skin,
                "active_object_only",
                not self.onion_skin.active_object_only,
            ),
            "apply_all": lambda: setattr(self, "apply_to_all_frames", not self.apply_to_all_frames),
            "anchor": self._cycle_anchor,
            "visible": self._toggle_visibility,
            "color": self._pick_color,
            "load_ref": self._load_reference_image,
            "clear_ref": self._clear_reference_image,
            "duration_minus": lambda: self.state.set_frame_duration(
                self.current_frame,
                self.state.frames[self.current_frame].duration_ms - 10,
            ),
            "duration_plus": lambda: self.state.set_frame_duration(
                self.current_frame,
                self.state.frames[self.current_frame].duration_ms + 10,
            ),
        }
        action = actions.get(button_id)
        if action:
            action()
        if button_id == "loop":
            self._set_status(f"Loop {'on' if self.loop_playback else 'off'}.")
        elif button_id.startswith("onion_"):
            self._set_status("Updated onion-skin settings.")
        elif button_id == "apply_all":
            self._set_status(f"Apply to all frames: {'on' if self.apply_to_all_frames else 'off'}.")
        elif button_id in {"duration_plus", "duration_minus"}:
            self._set_status(f"Frame duration: {self.state.frames[self.current_frame].duration_ms}ms")

    def _handle_mouse_down(self, event: pygame.event.Event) -> None:
        if event.button not in {1, 3}:
            return
        pos = event.pos

        for button_id, rect in self.button_rects.items():
            if rect.collidepoint(pos):
                self._handle_top_button(button_id)
                return

        for object_id, row_rect in self.object_rows:
            if row_rect.collidepoint(pos):
                self.active_object_id = object_id
                return

        for idx, frame_rect in enumerate(self.frame_rects):
            if frame_rect.collidepoint(pos):
                self._set_current_frame(idx)
                if event.button == 1:
                    self.timeline_drag_index = idx
                return

        for object_id, stage_rect in self.stage_object_rects.items():
            if stage_rect.collidepoint(pos):
                self.active_object_id = object_id
                if event.button == 1:
                    self.dragging_object_id = object_id
                    self.drag_residual_x = 0.0
                    self.drag_residual_y = 0.0
                return

        mods = pygame.key.get_mods()
        if self.object_canvas_rect.collidepoint(pos):
            if event.button == 1 and (mods & pygame.KMOD_ALT) and self.reference_image is not None:
                self.reference_panning = True
                return
            self.painting = self._paint_at(pos, event.button)
            self.paint_button = event.button
            return

    def _handle_mouse_up(self, event: pygame.event.Event) -> None:
        if event.button == 1:
            self.dragging_object_id = None
            self.timeline_drag_index = None
            self.painting = False
            self.reference_panning = False
        if event.button == 3:
            self.painting = False

    def _handle_mouse_motion(self, event: pygame.event.Event) -> None:
        if self.reference_panning and self.reference_image is not None:
            obj = self.active_object
            scale_x = obj.size_w / max(1, self.object_canvas_rect.width)
            scale_y = obj.size_h / max(1, self.object_canvas_rect.height)
            self.reference_offset.x += event.rel[0] * scale_x
            self.reference_offset.y += event.rel[1] * scale_y
            return

        if self.dragging_object_id and event.buttons[0] == 1:
            self._apply_drag_motion(event.rel[0], event.rel[1])
            return

        if self.timeline_drag_index is not None and event.buttons[0] == 1:
            for idx, frame_rect in enumerate(self.frame_rects):
                if idx != self.timeline_drag_index and frame_rect.collidepoint(event.pos):
                    old_index = self.timeline_drag_index
                    self._move_frame(old_index, idx)
                    self.timeline_drag_index = idx
                    break
            return

        if self.painting:
            button = 1 if event.buttons[0] else 3
            self._paint_at(event.pos, button)

    def _handle_mouse_wheel(self, event: pygame.event.Event) -> None:
        mods = pygame.key.get_mods()
        if (mods & pygame.KMOD_ALT) and self.object_canvas_rect.collidepoint(pygame.mouse.get_pos()):
            factor = 1.1 if event.y > 0 else (1 / 1.1)
            self.reference_scale = max(0.1, min(8.0, self.reference_scale * factor))
            self._set_status(f"Reference scale: {self.reference_scale:.2f}x")
            return
        if self.frame_rects:
            if event.y > 0:
                self._step_frame(-1)
            elif event.y < 0:
                self._step_frame(1)

    def _handle_dialog_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            if self.dialog_load_button_rect and self.dialog_load_button_rect.collidepoint(pos):
                self._confirm_dialog_selection()
                return True
            if self.dialog_cancel_button_rect and self.dialog_cancel_button_rect.collidepoint(pos):
                self._reset_dialog()
                return True
            if self.dialog_file_list_rect and self.dialog_file_list_rect.collidepoint(pos):
                line_height = self.font.get_linesize()
                relative_y = pos[1] - self.dialog_file_list_rect.y
                idx = self.dialog_file_scroll_offset + (relative_y // line_height)
                if 0 <= idx < len(self.dialog_file_list):
                    self.dialog_selected_file_index = idx
                    self._ensure_dialog_scroll()
                return True
            if self.dialog_file_scrollbar_rect and self.dialog_file_scrollbar_rect.collidepoint(pos):
                self.dialog_file_dragging_scrollbar = True
                self._set_dialog_scroll_offset_from_thumb(pos[1])
                return True
            for rect, path in self.dialog_quick_dir_rects:
                if rect.collidepoint(pos):
                    self._set_dialog_directory(path)
                    return True
            return True

        if event.type == pygame.MOUSEMOTION and self.dialog_file_dragging_scrollbar:
            self._set_dialog_scroll_offset_from_thumb(event.pos[1])
            return True

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dialog_file_dragging_scrollbar = False
            return True

        if event.type == pygame.MOUSEWHEEL:
            if self.dialog_file_page_size > 0 and len(self.dialog_file_list) > self.dialog_file_page_size:
                max_offset = len(self.dialog_file_list) - self.dialog_file_page_size
                self.dialog_file_scroll_offset = max(
                    0,
                    min(self.dialog_file_scroll_offset - event.y, max_offset),
                )
            return True

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._reset_dialog()
                return True
            if event.key == pygame.K_RETURN:
                self._confirm_dialog_selection()
                return True
            if event.key == pygame.K_UP:
                if self.dialog_selected_file_index > 0:
                    self.dialog_selected_file_index -= 1
                    self._ensure_dialog_scroll()
                return True
            if event.key == pygame.K_DOWN:
                if self.dialog_selected_file_index < len(self.dialog_file_list) - 1:
                    self.dialog_selected_file_index += 1
                    self._ensure_dialog_scroll()
                return True
            return True

        return True

    def _handle_key_down(self, event: pygame.event.Event) -> bool:
        mods = pygame.key.get_mods()
        ctrl = bool(mods & (pygame.KMOD_CTRL | pygame.KMOD_META))
        shift = bool(mods & pygame.KMOD_SHIFT)

        if ctrl and event.key == pygame.K_s:
            self._save()
            return True
        if ctrl and event.key == pygame.K_o:
            self._open_existing()
            return True
        if ctrl and event.key == pygame.K_n:
            self._new_animation()
            return True

        if event.key == pygame.K_SPACE:
            self._toggle_play()
            return True
        if event.key == pygame.K_COMMA:
            self._jump_frames(-5 if shift else -1)
            return True
        if event.key == pygame.K_PERIOD:
            self._jump_frames(5 if shift else 1)
            return True
        if event.key in {pygame.K_DELETE, pygame.K_BACKSPACE}:
            self._delete_frame()
            return True
        if event.key == pygame.K_n:
            self._add_frame()
            return True
        if event.key == pygame.K_d:
            self._duplicate_frame()
            return True
        if event.key == pygame.K_v:
            self._toggle_visibility()
            return True
        if event.key == pygame.K_o:
            self.onion_skin.previous_enabled = not self.onion_skin.previous_enabled
            return True
        if event.key == pygame.K_p:
            self.onion_skin.next_enabled = not self.onion_skin.next_enabled
            return True
        if event.key == pygame.K_i:
            self.onion_skin.active_object_only = not self.onion_skin.active_object_only
            return True
        if event.key == pygame.K_c:
            self._pick_color()
            return True
        if event.key == pygame.K_r:
            self._load_reference_image()
            return True
        if event.key == pygame.K_ESCAPE:
            self.dragging_object_id = None
            self.reference_panning = False
            self.playing = False
            return True

        move_step = 5 if shift else 1
        if event.key == pygame.K_LEFT:
            self._nudge_active_object(-move_step, 0)
            return True
        if event.key == pygame.K_RIGHT:
            self._nudge_active_object(move_step, 0)
            return True
        if event.key == pygame.K_UP:
            self._nudge_active_object(0, -move_step)
            return True
        if event.key == pygame.K_DOWN:
            self._nudge_active_object(0, move_step)
            return True

        return False

    def handle_event(self, event: pygame.event.Event) -> bool:
        if self.dialog_mode:
            return self._handle_dialog_event(event)

        if event.type == pygame.MOUSEBUTTONDOWN:
            self._handle_mouse_down(event)
            return True
        if event.type == pygame.MOUSEBUTTONUP:
            self._handle_mouse_up(event)
            return True
        if event.type == pygame.MOUSEMOTION:
            self._handle_mouse_motion(event)
            return True
        if event.type == pygame.MOUSEWHEEL:
            self._handle_mouse_wheel(event)
            return True
        if event.type == pygame.KEYDOWN:
            return self._handle_key_down(event)
        return False

    def _draw(self) -> None:
        self.layout = compute_layout(self.screen.get_size())
        self.screen.fill(BACKGROUND)
        active_obj = self.active_object
        active_frame = active_obj.frames[self.current_frame]
        frame_duration = self.state.frames[self.current_frame].duration_ms

        top_buttons = [
            {"id": "new", "label": "New"},
            {"id": "open", "label": "Open"},
            {"id": "save", "label": "Save"},
            {"id": "add_frame", "label": "+Frame"},
            {"id": "dup_frame", "label": "Duplicate"},
            {"id": "del_frame", "label": "Delete"},
            {"id": "add_obj", "label": "+Object"},
            {"id": "del_obj", "label": "-Object"},
            {"id": "play", "label": "Pause" if self.playing else "Play", "active": self.playing},
            {"id": "loop", "label": "Loop", "active": self.loop_playback},
            {"id": "onion_prev", "label": "Onion Prev", "active": self.onion_skin.previous_enabled},
            {"id": "onion_next", "label": "Onion Next", "active": self.onion_skin.next_enabled},
            {"id": "onion_active", "label": "Active Only", "active": self.onion_skin.active_object_only},
            {"id": "apply_all", "label": "Apply All", "active": self.apply_to_all_frames},
            {"id": "anchor", "label": f"Anchor: {active_obj.anchor}"},
            {"id": "visible", "label": "Visible", "active": active_frame.visible},
            {"id": "duration_minus", "label": "-10ms"},
            {"id": "duration_plus", "label": "+10ms"},
            {"id": "color", "label": "Color"},
            {"id": "load_ref", "label": "Load Ref"},
            {"id": "clear_ref", "label": "Clear Ref"},
        ]
        self.button_rects = draw_top_buttons(self.screen, self.layout.top_bar_rect, self.font_small, top_buttons)

        self.stage_object_rects = draw_stage_preview(
            self.screen,
            self.layout,
            self.font,
            state=self.state,
            surfaces=self.surfaces,
            frame_index=self.current_frame,
            active_object_id=self.active_object_id,
            onion_skin=self.onion_skin,
        )

        reference_surface = self._compose_reference_surface()
        self.object_canvas_rect = draw_object_canvas(
            self.screen,
            self.layout.canvas_rect,
            self.font,
            object_surface=self._get_surface(self.active_object_id, self.current_frame),
            reference_surface=reference_surface,
        )

        self.object_rows = draw_object_panel(
            self.screen,
            self.layout.object_panel_rect,
            self.font_small,
            state=self.state,
            active_object_id=self.active_object_id,
            frame_index=self.current_frame,
        )

        self.frame_rects = draw_timeline(
            self.screen,
            self.layout.timeline_rect,
            self.font_small,
            state=self.state,
            surfaces=self.surfaces,
            frame_index=self.current_frame,
            active_object_id=self.active_object_id,
        )

        fps = int(1000 / max(1, frame_duration))
        status = (
            f"{self.state.animation_id} | Frame {self.current_frame + 1}/{self.state.frame_count}"
            f" | Duration {frame_duration}ms (~{fps}fps)"
            f" | Pos ({active_frame.x}, {active_frame.y})"
            f" | Color {self.selected_color[:3]}"
        )
        if self.status_text and pygame.time.get_ticks() <= self.status_expires:
            status = f"{self.status_text} | {status}"
        draw_status_bar(self.screen, self.layout.status_rect, self.font_small, status)

    def _draw_dialog(self) -> None:
        if not self.dialog_mode:
            return
        surface = self.screen
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((*config.BLACK[:3], 180))
        surface.blit(overlay, (0, 0))

        dialog_w = 540
        dialog_h = 420
        dialog_rect = pygame.Rect(0, 0, dialog_w, dialog_h)
        dialog_rect.center = surface.get_rect().center
        pygame.draw.rect(surface, config.WHITE, dialog_rect, border_radius=6)
        pygame.draw.rect(surface, config.BLACK, dialog_rect, 2, border_radius=6)

        prompt_surf = self.font.render(self.dialog_prompt, True, config.BLACK)
        prompt_rect = prompt_surf.get_rect(midtop=(dialog_rect.centerx, dialog_rect.top + 14))
        surface.blit(prompt_surf, prompt_rect)

        list_rect = pygame.Rect(dialog_rect.x + 20, prompt_rect.bottom + 10, dialog_rect.width - 40, 210)
        self.dialog_file_list_rect = list_rect
        pygame.draw.rect(surface, config.GRAY_LIGHT, list_rect)
        pygame.draw.rect(surface, config.BLACK, list_rect, 1)

        line_height = self.font.get_linesize()
        self.dialog_file_page_size = max(1, list_rect.height // line_height)
        max_offset = max(0, len(self.dialog_file_list) - self.dialog_file_page_size)
        self.dialog_file_scroll_offset = max(0, min(self.dialog_file_scroll_offset, max_offset))
        self.dialog_file_scrollbar_rect = pygame.Rect(list_rect.right - 12, list_rect.y, 12, list_rect.height)
        pygame.draw.rect(surface, config.GRAY_MEDIUM, self.dialog_file_scrollbar_rect)
        end_index = min(self.dialog_file_scroll_offset + self.dialog_file_page_size, len(self.dialog_file_list))
        for row, index in enumerate(range(self.dialog_file_scroll_offset, end_index)):
            label = (
                self.dialog_file_labels[index]
                if index < len(self.dialog_file_labels)
                else os.path.basename(self.dialog_file_list[index])
            )
            text_color = config.WHITE if index == self.dialog_selected_file_index else config.BLACK
            if index == self.dialog_selected_file_index:
                highlight = pygame.Rect(list_rect.x, list_rect.y + row * line_height, list_rect.width, line_height)
                pygame.draw.rect(surface, config.BLUE, highlight)
            text_surf = self.font.render(label, True, text_color)
            surface.blit(text_surf, (list_rect.x + 6, list_rect.y + row * line_height))

        self._update_dialog_scrollbar_from_offset()
        if self.dialog_file_scroll_thumb_rect:
            pygame.draw.rect(surface, config.GRAY_DARK, self.dialog_file_scroll_thumb_rect)

        quick_y = list_rect.bottom + 10
        quick_x = list_rect.x
        self.dialog_quick_dir_rects = []
        if self.dialog_mode == "load_ref":
            for label, path in self.dialog_quick_dirs:
                text_surf = self.font_small.render(label, True, config.BLACK)
                text_rect = text_surf.get_rect(topleft=(quick_x + 4, quick_y + 3))
                button_rect = pygame.Rect(quick_x, quick_y, text_rect.width + 8, text_rect.height + 6)
                active = path == self.dialog_current_dir
                pygame.draw.rect(surface, config.BLUE if active else config.GRAY_LIGHT, button_rect)
                pygame.draw.rect(surface, config.BLACK, button_rect, 1)
                if active:
                    text_surf = self.font_small.render(label, True, config.WHITE)
                surface.blit(text_surf, text_rect)
                self.dialog_quick_dir_rects.append((button_rect, path))
                quick_x += button_rect.width + 8

        buttons_y = dialog_rect.bottom - 56
        self.dialog_load_button_rect = pygame.Rect(dialog_rect.centerx - 120, buttons_y, 100, 34)
        self.dialog_cancel_button_rect = pygame.Rect(dialog_rect.centerx + 20, buttons_y, 100, 34)
        for rect, label in [
            (self.dialog_load_button_rect, "Load"),
            (self.dialog_cancel_button_rect, "Cancel"),
        ]:
            pygame.draw.rect(surface, config.GRAY_LIGHT, rect)
            pygame.draw.rect(surface, config.BLACK, rect, 1)
            text = self.font.render(label, True, config.BLACK)
            surface.blit(text, text.get_rect(center=rect.center))

    def run(self) -> None:
        running = True
        while running:
            dt_ms = self.clock.tick(config.FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    continue
                self.handle_event(event)
            self._update(dt_ms)
            self._draw()
            self._draw_dialog()
            pygame.display.flip()
        pygame.quit()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", help="Move animation id or JSON path to load.")
    parser.add_argument("--new-id", help="Create a new animation with this id.")
    args = parser.parse_args(argv)

    editor = MoveAnimationEditor(initial_ref=args.id, start_new_id=args.new_id)
    editor.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
