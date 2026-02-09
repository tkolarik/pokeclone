from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pygame

from src.editor.move_animation_state import MoveAnimationState, OnionSkinSettings

STAGE_BG = (24, 28, 38)
PANEL_BG = (38, 44, 56)
PANEL_BORDER = (12, 15, 20)
TEXT_COLOR = (230, 235, 240)
SUBTEXT_COLOR = (175, 182, 192)
HIGHLIGHT = (82, 165, 255)
ACTIVE_FRAME_BG = (66, 84, 124)
CHECKER_1 = (210, 210, 210)
CHECKER_2 = (180, 180, 180)
TINT_PREVIOUS = (80, 130, 255, 90)
TINT_NEXT = (255, 90, 90, 90)

ATTACKER_ANCHOR_SCALE = 3


@dataclass
class MoveAnimationLayout:
    top_bar_rect: pygame.Rect
    stage_rect: pygame.Rect
    canvas_rect: pygame.Rect
    object_panel_rect: pygame.Rect
    timeline_rect: pygame.Rect
    status_rect: pygame.Rect


def compute_layout(screen_size: tuple[int, int]) -> MoveAnimationLayout:
    width, height = screen_size
    margin = 12
    gap = 12
    top_bar_h = 56
    timeline_h = 168
    status_h = 26
    right_panel_w = 270

    top_bar_rect = pygame.Rect(margin, margin, width - (margin * 2), top_bar_h)
    main_top = top_bar_rect.bottom + gap
    main_bottom = height - margin - timeline_h - gap - status_h - gap
    main_h = max(100, main_bottom - main_top)
    main_w = width - (margin * 2) - right_panel_w - gap

    stage_w = int(main_w * 0.56)
    stage_rect = pygame.Rect(margin, main_top, stage_w, main_h)
    canvas_rect = pygame.Rect(stage_rect.right + gap, main_top, main_w - stage_w - gap, main_h)
    object_panel_rect = pygame.Rect(canvas_rect.right + gap, main_top, right_panel_w, main_h)
    timeline_rect = pygame.Rect(margin, main_bottom + gap, width - (margin * 2), timeline_h)
    status_rect = pygame.Rect(margin, timeline_rect.bottom + gap, width - (margin * 2), status_h)

    return MoveAnimationLayout(
        top_bar_rect=top_bar_rect,
        stage_rect=stage_rect,
        canvas_rect=canvas_rect,
        object_panel_rect=object_panel_rect,
        timeline_rect=timeline_rect,
        status_rect=status_rect,
    )


def _draw_panel(surface: pygame.Surface, rect: pygame.Rect, *, title: str | None, font: pygame.font.Font) -> None:
    pygame.draw.rect(surface, PANEL_BG, rect)
    pygame.draw.rect(surface, PANEL_BORDER, rect, 1)
    if title:
        label = font.render(title, True, TEXT_COLOR)
        surface.blit(label, (rect.x + 8, rect.y + 6))


def draw_top_buttons(
    surface: pygame.Surface,
    rect: pygame.Rect,
    font: pygame.font.Font,
    buttons: list[dict[str, Any]],
) -> dict[str, pygame.Rect]:
    _draw_panel(surface, rect, title=None, font=font)
    button_rects: dict[str, pygame.Rect] = {}
    cursor_x = rect.x + 8
    cursor_y = rect.y + 10
    row_h = 34
    for button in buttons:
        label = str(button.get("label", "Button"))
        button_id = str(button.get("id", label))
        active = bool(button.get("active", False))
        disabled = bool(button.get("disabled", False))
        width = max(62, font.size(label)[0] + 18)
        if cursor_x + width > rect.right - 8:
            cursor_x = rect.x + 8
            cursor_y += row_h
        button_rect = pygame.Rect(cursor_x, cursor_y, width, 26)
        fill = (70, 88, 124) if active else (60, 64, 74)
        if disabled:
            fill = (45, 48, 56)
        pygame.draw.rect(surface, fill, button_rect, border_radius=4)
        pygame.draw.rect(surface, HIGHLIGHT if active else PANEL_BORDER, button_rect, 1, border_radius=4)
        text_color = TEXT_COLOR if not disabled else SUBTEXT_COLOR
        text_surf = font.render(label, True, text_color)
        surface.blit(text_surf, text_surf.get_rect(center=button_rect.center))
        button_rects[button_id] = button_rect
        cursor_x += width + 8
    return button_rects


def _blit_tinted(surface: pygame.Surface, image: pygame.Surface, rect: pygame.Rect, tint: tuple[int, int, int, int]) -> None:
    tinted = image.copy()
    overlay = pygame.Surface(tinted.get_size(), pygame.SRCALPHA)
    overlay.fill(tint)
    tinted.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
    tinted.set_alpha(tint[3])
    surface.blit(tinted, rect.topleft)


def _object_stage_rect(
    layout: MoveAnimationLayout,
    object_anchor: str,
    object_size: tuple[int, int],
    x: int,
    y: int,
) -> pygame.Rect:
    attacker_base = (layout.stage_rect.x + 70, layout.stage_rect.bottom - (32 * ATTACKER_ANCHOR_SCALE) - 70)
    defender_base = (layout.stage_rect.right - (32 * ATTACKER_ANCHOR_SCALE) - 70, layout.stage_rect.y + 70)

    if object_anchor == "attacker":
        return pygame.Rect(
            attacker_base[0] + (x * ATTACKER_ANCHOR_SCALE),
            attacker_base[1] + (y * ATTACKER_ANCHOR_SCALE),
            object_size[0] * ATTACKER_ANCHOR_SCALE,
            object_size[1] * ATTACKER_ANCHOR_SCALE,
        )
    if object_anchor == "defender":
        return pygame.Rect(
            defender_base[0] + (x * ATTACKER_ANCHOR_SCALE),
            defender_base[1] + (y * ATTACKER_ANCHOR_SCALE),
            object_size[0] * ATTACKER_ANCHOR_SCALE,
            object_size[1] * ATTACKER_ANCHOR_SCALE,
        )
    return pygame.Rect(layout.stage_rect.x + x, layout.stage_rect.y + y, object_size[0], object_size[1])


def draw_stage_preview(
    surface: pygame.Surface,
    layout: MoveAnimationLayout,
    font: pygame.font.Font,
    *,
    state: MoveAnimationState,
    surfaces: dict[tuple[str, int], pygame.Surface],
    frame_index: int,
    active_object_id: str | None,
    onion_skin: OnionSkinSettings,
) -> dict[str, pygame.Rect]:
    _draw_panel(surface, layout.stage_rect, title="Stage Preview", font=font)
    stage_body = layout.stage_rect.inflate(-16, -34)
    stage_body.y += 20
    stage_body.height -= 14
    pygame.draw.rect(surface, STAGE_BG, stage_body)
    pygame.draw.rect(surface, PANEL_BORDER, stage_body, 1)

    attacker_rect = pygame.Rect(
        stage_body.x + 36,
        stage_body.bottom - (32 * ATTACKER_ANCHOR_SCALE) - 34,
        32 * ATTACKER_ANCHOR_SCALE,
        32 * ATTACKER_ANCHOR_SCALE,
    )
    defender_rect = pygame.Rect(
        stage_body.right - (32 * ATTACKER_ANCHOR_SCALE) - 36,
        stage_body.y + 32,
        32 * ATTACKER_ANCHOR_SCALE,
        32 * ATTACKER_ANCHOR_SCALE,
    )
    pygame.draw.rect(surface, (95, 110, 130), attacker_rect)
    pygame.draw.rect(surface, (95, 110, 130), defender_rect)
    pygame.draw.rect(surface, PANEL_BORDER, attacker_rect, 1)
    pygame.draw.rect(surface, PANEL_BORDER, defender_rect, 1)

    frame_index = max(0, min(frame_index, state.frame_count - 1))
    indices = MoveAnimationState.onion_skin_indices(
        frame_index,
        state.frame_count,
        previous_enabled=onion_skin.previous_enabled,
        next_enabled=onion_skin.next_enabled,
    )
    object_rects: dict[str, pygame.Rect] = {}

    for obj in state.objects:
        if onion_skin.active_object_only and active_object_id and obj.object_id != active_object_id:
            pass
        else:
            if indices["previous"] is not None:
                prev_frame = obj.frames[indices["previous"]]
                if prev_frame.visible:
                    prev_surf = surfaces.get((obj.object_id, indices["previous"]))
                    if prev_surf is not None:
                        prev_rect = _object_stage_rect(
                            layout,
                            obj.anchor,
                            (obj.size_w, obj.size_h),
                            prev_frame.x,
                            prev_frame.y,
                        )
                        prev_scaled = pygame.transform.scale(prev_surf, prev_rect.size)
                        _blit_tinted(surface, prev_scaled, prev_rect, TINT_PREVIOUS)
            if indices["next"] is not None:
                next_frame = obj.frames[indices["next"]]
                if next_frame.visible:
                    next_surf = surfaces.get((obj.object_id, indices["next"]))
                    if next_surf is not None:
                        next_rect = _object_stage_rect(
                            layout,
                            obj.anchor,
                            (obj.size_w, obj.size_h),
                            next_frame.x,
                            next_frame.y,
                        )
                        next_scaled = pygame.transform.scale(next_surf, next_rect.size)
                        _blit_tinted(surface, next_scaled, next_rect, TINT_NEXT)

    for obj in state.objects:
        frame = obj.frames[frame_index]
        if not frame.visible:
            continue
        current = surfaces.get((obj.object_id, frame_index))
        if current is None:
            continue
        object_rect = _object_stage_rect(
            layout,
            obj.anchor,
            (obj.size_w, obj.size_h),
            frame.x,
            frame.y,
        )
        scaled = pygame.transform.scale(current, object_rect.size)
        surface.blit(scaled, object_rect.topleft)
        outline = HIGHLIGHT if obj.object_id == active_object_id else PANEL_BORDER
        pygame.draw.rect(surface, outline, object_rect, 1)
        object_rects[obj.object_id] = object_rect

    info = font.render("Drag objects on stage. Space to play/pause.", True, SUBTEXT_COLOR)
    surface.blit(info, (stage_body.x + 8, stage_body.bottom - 24))
    return object_rects


def draw_object_canvas(
    surface: pygame.Surface,
    rect: pygame.Rect,
    font: pygame.font.Font,
    *,
    object_surface: pygame.Surface,
    reference_surface: pygame.Surface | None = None,
) -> pygame.Rect:
    _draw_panel(surface, rect, title="Object Canvas", font=font)
    canvas = rect.inflate(-20, -42)
    canvas.y += 18
    pygame.draw.rect(surface, PANEL_BORDER, canvas)

    checker = pygame.Surface((max(4, canvas.width), max(4, canvas.height)))
    block = 12
    for y in range(0, checker.get_height(), block):
        for x in range(0, checker.get_width(), block):
            color = CHECKER_1 if ((x // block) + (y // block)) % 2 == 0 else CHECKER_2
            pygame.draw.rect(checker, color, pygame.Rect(x, y, block, block))
    surface.blit(checker, canvas.topleft)

    if reference_surface is not None:
        ref_scaled = pygame.transform.scale(reference_surface, canvas.size)
        surface.blit(ref_scaled, canvas.topleft)

    sprite_scaled = pygame.transform.scale(object_surface, canvas.size)
    surface.blit(sprite_scaled, canvas.topleft)

    # Pixel grid for precise editing.
    px_w = max(1, object_surface.get_width())
    px_h = max(1, object_surface.get_height())
    step_x = canvas.width / px_w
    step_y = canvas.height / px_h
    for x in range(px_w + 1):
        line_x = int(canvas.x + x * step_x)
        pygame.draw.line(surface, (120, 120, 120), (line_x, canvas.y), (line_x, canvas.bottom), 1)
    for y in range(px_h + 1):
        line_y = int(canvas.y + y * step_y)
        pygame.draw.line(surface, (120, 120, 120), (canvas.x, line_y), (canvas.right, line_y), 1)

    return canvas


def draw_timeline(
    surface: pygame.Surface,
    rect: pygame.Rect,
    font: pygame.font.Font,
    *,
    state: MoveAnimationState,
    surfaces: dict[tuple[str, int], pygame.Surface],
    frame_index: int,
    active_object_id: str | None,
) -> list[pygame.Rect]:
    _draw_panel(surface, rect, title="Timeline", font=font)
    tray = rect.inflate(-14, -34)
    tray.y += 20
    pygame.draw.rect(surface, STAGE_BG, tray)
    pygame.draw.rect(surface, PANEL_BORDER, tray, 1)

    thumb_size = (88, 66)
    spacing = 8
    cursor_x = tray.x + 8
    cursor_y = tray.y + 8
    frame_rects: list[pygame.Rect] = []
    for idx, frame in enumerate(state.frames):
        if cursor_x + thumb_size[0] > tray.right - 8:
            cursor_x = tray.x + 8
            cursor_y += thumb_size[1] + 28
        frame_rect = pygame.Rect(cursor_x, cursor_y, thumb_size[0], thumb_size[1])
        frame_rects.append(frame_rect)
        fill = ACTIVE_FRAME_BG if idx == frame_index else (58, 62, 72)
        pygame.draw.rect(surface, fill, frame_rect, border_radius=3)
        pygame.draw.rect(surface, HIGHLIGHT if idx == frame_index else PANEL_BORDER, frame_rect, 1, border_radius=3)

        if active_object_id is not None:
            source = surfaces.get((active_object_id, idx))
            if source is not None:
                thumb = pygame.transform.scale(source, frame_rect.size)
                surface.blit(thumb, frame_rect.topleft)

        caption = font.render(f"{idx + 1}: {frame.duration_ms}ms", True, TEXT_COLOR)
        surface.blit(caption, (frame_rect.x, frame_rect.bottom + 4))
        cursor_x += thumb_size[0] + spacing

    return frame_rects


def draw_object_panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    font: pygame.font.Font,
    *,
    state: MoveAnimationState,
    active_object_id: str | None,
    frame_index: int,
) -> list[tuple[str, pygame.Rect]]:
    _draw_panel(surface, rect, title="Objects", font=font)
    list_rect = rect.inflate(-14, -70)
    list_rect.y += 24
    list_rect.height -= 80
    pygame.draw.rect(surface, STAGE_BG, list_rect)
    pygame.draw.rect(surface, PANEL_BORDER, list_rect, 1)

    row_h = 28
    object_rows: list[tuple[str, pygame.Rect]] = []
    for idx, obj in enumerate(state.objects):
        row = pygame.Rect(list_rect.x + 6, list_rect.y + 6 + idx * row_h, list_rect.width - 12, row_h - 4)
        row_active = obj.object_id == active_object_id
        pygame.draw.rect(surface, (74, 88, 122) if row_active else (64, 68, 78), row, border_radius=3)
        pygame.draw.rect(surface, HIGHLIGHT if row_active else PANEL_BORDER, row, 1, border_radius=3)
        label = font.render(f"{obj.name} [{obj.anchor}]", True, TEXT_COLOR)
        surface.blit(label, (row.x + 6, row.y + 5))
        object_rows.append((obj.object_id, row))

    if active_object_id:
        active_obj = state.get_object(active_object_id)
        if active_obj:
            frame = active_obj.frames[max(0, min(frame_index, state.frame_count - 1))]
            info_lines = [
                f"Frame: {frame_index + 1}/{state.frame_count}",
                f"Pos: ({frame.x}, {frame.y})",
                f"Visible: {'Yes' if frame.visible else 'No'}",
            ]
            text_y = list_rect.bottom + 10
            for line in info_lines:
                surf = font.render(line, True, SUBTEXT_COLOR)
                surface.blit(surf, (list_rect.x + 4, text_y))
                text_y += 18

    return object_rows


def draw_status_bar(
    surface: pygame.Surface,
    rect: pygame.Rect,
    font: pygame.font.Font,
    text: str,
) -> None:
    pygame.draw.rect(surface, PANEL_BG, rect)
    pygame.draw.rect(surface, PANEL_BORDER, rect, 1)
    status = font.render(text, True, TEXT_COLOR)
    surface.blit(status, (rect.x + 8, rect.y + 4))
