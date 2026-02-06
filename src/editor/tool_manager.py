# tool_manager.py

"""Manages different editing tools (Draw, Fill, Paste, etc.) for the pixel editor."""

import pygame
# from ..core import config # Relative import
from src.core import config # Absolute import
# Need SpriteEditor for type hinting potentially, or direct manipulation
# from .sprite_editor import SpriteEditor # Relative import
from src.editor.sprite_editor import SpriteEditor # Absolute import


def _screen_to_background_pos(editor, screen_pos):
    """Convert a screen-space click to a background-surface pixel position."""
    if not editor.canvas_rect:
        return None

    zoom = float(getattr(editor, "editor_zoom", 0.0) or 0.0)
    if zoom <= 0:
        return None

    screen_x_rel = screen_pos[0] - editor.canvas_rect.x
    screen_y_rel = screen_pos[1] - editor.canvas_rect.y
    original_x = int((screen_x_rel + editor.view_offset_x) / zoom)
    original_y = int((screen_y_rel + editor.view_offset_y) / zoom)
    return (original_x, original_y)


def _normalize_rgba(color):
    """Return an RGBA tuple for tuple-like colors."""
    if color is None:
        return None
    if len(color) >= 4:
        return (int(color[0]), int(color[1]), int(color[2]), int(color[3]))
    if len(color) == 3:
        return (int(color[0]), int(color[1]), int(color[2]), 255)
    return None


# --- Base Tool --- (Optional, but good for structure)
class BaseTool:
    def __init__(self, name):
        self.name = name

    def handle_click(self, editor, pos):
        """Handles a mouse click event at the given position."""
        raise NotImplementedError

    def handle_drag(self, editor, pos):
        """Handles a mouse drag event at the given position."""
        # Default behavior for many tools might be same as click
        self.handle_click(editor, pos)

    def activate(self, editor):
        """Called when the tool becomes active."""
        pass

    def deactivate(self, editor):
        """Called when the tool is deactivated."""
        pass

# --- Draw/Erase Tool ---
class DrawTool(BaseTool):
    def __init__(self):
        super().__init__("Draw/Erase")

    def _get_target(self, editor, pos):
        """Helper to get the target sprite editor or background surface."""
        if editor.edit_mode == 'monster':
            return editor._get_sprite_editor_at_pos(pos)
        elif editor.edit_mode == 'tile':
            return editor._get_sprite_editor_at_pos(pos)
        elif editor.edit_mode == 'background' and editor.canvas_rect and editor.current_background:
            if editor.canvas_rect.collidepoint(pos):
                return editor.current_background # Return the surface
        return None

    def _draw_on_sprite(self, editor, sprite_editor, grid_pos):
        """Handles drawing/erasing on a SpriteEditor."""
        color = (*config.BLACK[:3], 0) if editor.eraser_mode else editor.current_color
        half_brush = (editor.brush_size - 1) // 2
        for dy in range(-half_brush, half_brush + 1):
            for dx in range(-half_brush, half_brush + 1):
                # Optional: Add check for circular brush shape if desired
                # if dx*dx + dy*dy <= half_brush*half_brush:
                draw_x = grid_pos[0] + dx
                draw_y = grid_pos[1] + dy
                if 0 <= draw_x < config.NATIVE_SPRITE_RESOLUTION[0] and 0 <= draw_y < config.NATIVE_SPRITE_RESOLUTION[1]:
                    sprite_editor.draw_pixel((draw_x, draw_y), color)

    def _draw_on_background(self, editor, background_surface, pos):
        """Handles drawing/erasing on the background surface."""
        if not editor.canvas_rect: return

        # Calculate position relative to the background canvas top-left
        screen_x_rel = pos[0] - editor.canvas_rect.x
        screen_y_rel = pos[1] - editor.canvas_rect.y
        
        # Convert screen coordinates within canvas_rect to coordinates on the original surface
        original_x = int((screen_x_rel + editor.view_offset_x) / editor.editor_zoom)
        original_y = int((screen_y_rel + editor.view_offset_y) / editor.editor_zoom)
        
        # Check if calculated coordinates are within the original background bounds
        bg_width, bg_height = background_surface.get_size()
        if 0 <= original_x < bg_width and 0 <= original_y < bg_height:
            color = config.WHITE if editor.eraser_mode else editor.current_color[:3] # Use opaque colors for BG
            # Scale the brush radius based on zoom
            scaled_radius = max(1, int((editor.brush_size / 2) / editor.editor_zoom))
            pygame.draw.circle(background_surface, color, (original_x, original_y), scaled_radius)


    def handle_click(self, editor, pos):
        target = self._get_target(editor, pos)
        if not target: 
            return

        if isinstance(target, SpriteEditor): # Target is SpriteEditor
            sprite_editor = target
            grid_pos = sprite_editor.get_grid_position(pos)
            if grid_pos:
                self._draw_on_sprite(editor, sprite_editor, grid_pos)
        elif isinstance(target, pygame.Surface): # Target is background Surface
            self._draw_on_background(editor, target, pos)

# --- Fill Tool ---
class FillTool(BaseTool):
    def __init__(self):
        super().__init__("Fill")

    def _flood_fill_sprite(self, sprite_editor, start_pos, fill_color):
        """Perform flood fill on the sprite editor's frame."""
        native_res = config.NATIVE_SPRITE_RESOLUTION
        target_color = sprite_editor.get_pixel_color(start_pos)

        if target_color == fill_color:
            return # No need to fill

        stack = [start_pos]
        visited = {start_pos}

        while stack:
            x, y = stack.pop()
            # Check color again in case it was changed by another path
            current_pixel_color = sprite_editor.get_pixel_color((x, y))
            if current_pixel_color == target_color:
                sprite_editor.draw_pixel((x, y), fill_color)
                # Check neighbors
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < native_res[0] and 0 <= ny < native_res[1]:
                        neighbor_pos = (nx, ny)
                        if neighbor_pos not in visited:
                             stack.append(neighbor_pos)
                             visited.add(neighbor_pos)
        print("Fill complete.")
        # Note: editor.save_state() should be called *before* invoking the tool's handle_click

    def _flood_fill_background(self, editor, background_surface, start_screen_pos, fill_color):
        """Perform flood fill on the background surface."""
        start_pos = _screen_to_background_pos(editor, start_screen_pos)
        if not start_pos:
            return

        bg_width, bg_height = background_surface.get_size()
        start_x, start_y = start_pos
        if not (0 <= start_x < bg_width and 0 <= start_y < bg_height):
            return

        target_color = _normalize_rgba(background_surface.get_at(start_pos))
        fill_color_rgba = _normalize_rgba(fill_color)
        if fill_color_rgba is None:
            return
        if target_color == fill_color_rgba:
            return

        visited = bytearray(bg_width * bg_height)
        stack = [start_pos]

        background_surface.lock()
        try:
            while stack:
                x, y = stack.pop()
                idx = y * bg_width + x
                if visited[idx]:
                    continue
                visited[idx] = 1

                if _normalize_rgba(background_surface.get_at((x, y))) != target_color:
                    continue

                background_surface.set_at((x, y), fill_color_rgba)

                if x > 0:
                    stack.append((x - 1, y))
                if x + 1 < bg_width:
                    stack.append((x + 1, y))
                if y > 0:
                    stack.append((x, y - 1))
                if y + 1 < bg_height:
                    stack.append((x, y + 1))
        finally:
            background_surface.unlock()
        print("Background fill complete.")

    def handle_click(self, editor, pos):
        if editor.edit_mode in ['monster', 'tile']:
            sprite_editor = editor._get_sprite_editor_at_pos(pos)
            if sprite_editor:
                grid_pos = sprite_editor.get_grid_position(pos)
                if grid_pos:
                    fill_color_rgba = editor.current_color # Use full RGBA
                    self._flood_fill_sprite(sprite_editor, grid_pos, fill_color_rgba)
        elif editor.edit_mode == 'background' and editor.canvas_rect and editor.current_background:
             if editor.canvas_rect.collidepoint(pos):
                 fill_color_rgb = editor.current_color[:3] # Use RGB for background
                 self._flood_fill_background(editor, editor.current_background, pos, fill_color_rgb)
        
    # Drag usually doesn't make sense for fill
    def handle_drag(self, editor, pos):
        pass 

# --- Paste Tool ---
class PasteTool(BaseTool):
    def __init__(self):
        super().__init__("Paste")

    def _apply_paste_sprite(self, editor, sprite_editor, top_left_grid_pos):
        """Pastes the editor's copy_buffer onto the sprite_editor frame."""
        if not editor.copy_buffer:
            print("Paste Error: Copy buffer is empty.")
            return

        start_x, start_y = top_left_grid_pos
        for (rel_x, rel_y), color in editor.copy_buffer.items():
            abs_x = start_x + rel_x
            abs_y = start_y + rel_y
            # Check bounds before attempting to draw
            if 0 <= abs_x < config.NATIVE_SPRITE_RESOLUTION[0] and 0 <= abs_y < config.NATIVE_SPRITE_RESOLUTION[1]:
                # Only paste non-transparent pixels.
                if color[3] > 0:
                    sprite_editor.draw_pixel((abs_x, abs_y), color)
        print("Pasted selection.")
        # Paste mode typically allows multiple pastes until cancelled/switched
        # We might not want to deactivate immediately after one click.
        # This depends on desired UX. For now, clicking just pastes once.

    def _apply_paste_background(self, editor, background_surface, top_left_screen_pos):
        """Pastes the editor's copy_buffer onto the background frame."""
        if not editor.copy_buffer:
            print("Paste Error: Copy buffer is empty.")
            return

        top_left_pos = _screen_to_background_pos(editor, top_left_screen_pos)
        if not top_left_pos:
            return

        bg_width, bg_height = background_surface.get_size()
        start_x, start_y = top_left_pos
        pasted_count = 0

        for (rel_x, rel_y), color in editor.copy_buffer.items():
            rgba = _normalize_rgba(color)
            if rgba is None:
                continue
            alpha = rgba[3]
            if alpha <= 0:
                continue

            abs_x = start_x + rel_x
            abs_y = start_y + rel_y
            if not (0 <= abs_x < bg_width and 0 <= abs_y < bg_height):
                continue

            if alpha >= 255:
                background_surface.set_at((abs_x, abs_y), (rgba[0], rgba[1], rgba[2], 255))
            else:
                existing = _normalize_rgba(background_surface.get_at((abs_x, abs_y)))
                inv_alpha = 255 - alpha
                blended = (
                    (rgba[0] * alpha + existing[0] * inv_alpha) // 255,
                    (rgba[1] * alpha + existing[1] * inv_alpha) // 255,
                    (rgba[2] * alpha + existing[2] * inv_alpha) // 255,
                    255,
                )
                background_surface.set_at((abs_x, abs_y), blended)
            pasted_count += 1

        print(f"Pasted {pasted_count} pixel(s) onto background.")

    def handle_click(self, editor, pos):
        if not editor.copy_buffer:
             print("Cannot paste: Copy buffer is empty.")
             editor.tool_manager.set_active_tool('draw') # Switch back to draw if buffer empty
             return
             
        if editor.edit_mode in ['monster', 'tile']:
            sprite_editor = editor._get_sprite_editor_at_pos(pos)
            if sprite_editor:
                grid_pos = sprite_editor.get_grid_position(pos)
                if grid_pos:
                    self._apply_paste_sprite(editor, sprite_editor, grid_pos)
                    # Optional: Deactivate paste mode after one paste? 
                    # editor.tool_manager.set_active_tool('draw') 
        elif editor.edit_mode == 'background' and editor.canvas_rect and editor.current_background:
             if editor.canvas_rect.collidepoint(pos):
                 self._apply_paste_background(editor, editor.current_background, pos)
                 # Optional: Deactivate paste mode after one paste?
                 # editor.tool_manager.set_active_tool('draw') 

    # Drag usually doesn't make sense for paste
    def handle_drag(self, editor, pos):
        pass


class EyedropperTool(BaseTool):
    def __init__(self):
        super().__init__("Eyedropper")

    def handle_click(self, editor, pos):
        if not editor.pick_color_at_pos(pos):
            print("Eyedropper: No color found at that position.")


# --- Tool Manager ---
class ToolManager:
    def __init__(self, editor):
        self.editor = editor
        self.tools = {
            'draw': DrawTool(),
            'fill': FillTool(),    # <<< Add FillTool
            'paste': PasteTool(),   # <<< Add PasteTool
            'eyedropper': EyedropperTool(),
            # 'select': SelectionTool() # Selection might be managed differently
        }
        self.active_tool_name = 'draw' # Default tool
        self.active_tool = self.tools[self.active_tool_name]
        self.active_tool.activate(self.editor)

    def set_active_tool(self, tool_name):
        if tool_name in self.tools and tool_name != self.active_tool_name:
            if self.active_tool:
                self.active_tool.deactivate(self.editor)
            
            self.active_tool_name = tool_name
            self.active_tool = self.tools[tool_name]
            self.active_tool.activate(self.editor)

            # Reset tool flags when switching active tool.
            self.editor.eraser_mode = False
            self.editor.fill_mode = False 
            self.editor.paste_mode = False
            if self.editor.mode == 'select':
                self.editor.mode = 'draw' 
                self.editor.selection.selecting = False

    def handle_click(self, pos):
        if self.active_tool:
            # Need to pass the editor instance to the tool method
            self.active_tool.handle_click(self.editor, pos)

    def handle_drag(self, pos):
        if self.active_tool:
            # Need to pass the editor instance to the tool method
            self.active_tool.handle_drag(self.editor, pos)
