import unittest
from unittest.mock import MagicMock, patch
import pygame
import os
import sys


# Now import the necessary modules
from src.core import config
from src.editor.tool_manager import DrawTool, FillTool, PasteTool, ToolManager
from src.editor.sprite_editor import SpriteEditor
from src.editor.selection_manager import SelectionTool

class TestDrawTool(unittest.TestCase):

    def setUp(self):
        self.draw_tool = DrawTool()
        self.mock_editor = MagicMock()
        # Common editor attributes needed by DrawTool
        self.mock_editor.edit_mode = 'monster'
        self.mock_editor.current_color = (255, 0, 0, 255) # Red
        self.mock_editor.eraser_mode = False
        self.mock_editor.brush_size = 1
        # Mock SpriteEditor related things
        self.mock_sprite_editor = MagicMock(spec=SpriteEditor)
        self.mock_sprite_editor.position = (50, 50) # Example position
        self.mock_sprite_editor.display_width = config.EDITOR_GRID_SIZE * config.EDITOR_PIXEL_SIZE
        self.mock_sprite_editor.display_height = config.EDITOR_GRID_SIZE * config.EDITOR_PIXEL_SIZE
        self.mock_editor._get_sprite_editor_at_pos.return_value = self.mock_sprite_editor
        self.mock_sprite_editor.get_grid_position.return_value = (10, 10) # Mock grid pos
        
        # Mock Background related things - Make canvas_rect a MagicMock
        self.mock_editor.canvas_rect = MagicMock(spec=pygame.Rect)
        # Set necessary Rect attributes used by the code (optional but safer)
        self.mock_editor.canvas_rect.x = 100
        self.mock_editor.canvas_rect.y = 100
        self.mock_editor.canvas_rect.width = 200
        self.mock_editor.canvas_rect.height = 200
        # We will set collidepoint's return value in specific tests
        
        self.mock_editor.current_background = MagicMock(spec=pygame.Surface)
        self.mock_editor.current_background.get_size.return_value = (400, 400) # Example size
        self.mock_editor.view_offset_x = 0
        self.mock_editor.view_offset_y = 0
        self.mock_editor.editor_zoom = 1.0

    # --- Tests for _get_target ---
    def test_get_target_monster_mode_hit(self):
        """Test _get_target returns sprite editor in monster mode."""
        self.mock_editor.edit_mode = 'monster'
        self.mock_editor._get_sprite_editor_at_pos.return_value = self.mock_sprite_editor
        target = self.draw_tool._get_target(self.mock_editor, (60, 60)) # Pos within mock sprite editor
        self.assertEqual(target, self.mock_sprite_editor)

    def test_get_target_monster_mode_miss(self):
        """Test _get_target returns None in monster mode if no sprite editor hit."""
        self.mock_editor.edit_mode = 'monster'
        self.mock_editor._get_sprite_editor_at_pos.return_value = None
        target = self.draw_tool._get_target(self.mock_editor, (10, 10)) # Pos outside mock sprite editor
        self.assertIsNone(target)

    def test_get_target_background_mode_hit(self):
        """Test _get_target returns background surface in background mode."""
        self.mock_editor.edit_mode = 'background'
        # Mock canvas_rect.collidepoint to return True
        self.mock_editor.canvas_rect.collidepoint = MagicMock(return_value=True)
        target = self.draw_tool._get_target(self.mock_editor, (150, 150)) # Pos within mock canvas
        self.assertEqual(target, self.mock_editor.current_background)
        self.mock_editor.canvas_rect.collidepoint.assert_called_once_with((150, 150))

    def test_get_target_background_mode_miss(self):
        """Test _get_target returns None in background mode if outside canvas."""
        self.mock_editor.edit_mode = 'background'
        self.mock_editor.canvas_rect.collidepoint = MagicMock(return_value=False)
        target = self.draw_tool._get_target(self.mock_editor, (10, 10)) # Pos outside mock canvas
        self.assertIsNone(target)
        self.mock_editor.canvas_rect.collidepoint.assert_called_once_with((10, 10))

    # --- Tests for _draw_on_sprite ---
    def test_draw_on_sprite_single_pixel(self):
        """Test drawing a single pixel on sprite."""
        grid_pos = (5, 5)
        self.mock_editor.brush_size = 1
        self.mock_editor.eraser_mode = False
        self.draw_tool._draw_on_sprite(self.mock_editor, self.mock_sprite_editor, grid_pos)
        self.mock_sprite_editor.draw_pixel.assert_called_once_with(grid_pos, self.mock_editor.current_color)

    def test_erase_on_sprite_single_pixel(self):
        """Test erasing a single pixel on sprite."""
        grid_pos = (6, 6)
        self.mock_editor.brush_size = 1
        self.mock_editor.eraser_mode = True
        expected_erase_color = (*config.BLACK[:3], 0)
        self.draw_tool._draw_on_sprite(self.mock_editor, self.mock_sprite_editor, grid_pos)
        self.mock_sprite_editor.draw_pixel.assert_called_once_with(grid_pos, expected_erase_color)

    def test_draw_on_sprite_brush_size_3(self):
        """Test drawing with brush size 3 on sprite."""
        grid_pos = (10, 10)
        self.mock_editor.brush_size = 3
        self.mock_editor.eraser_mode = False
        self.draw_tool._draw_on_sprite(self.mock_editor, self.mock_sprite_editor, grid_pos)
        # Expect 3x3 = 9 calls
        self.assertEqual(self.mock_sprite_editor.draw_pixel.call_count, 9)
        # Check one of the calls (e.g., center)
        self.mock_sprite_editor.draw_pixel.assert_any_call(grid_pos, self.mock_editor.current_color)
        # Check another call (e.g., top-left of brush)
        self.mock_sprite_editor.draw_pixel.assert_any_call((9, 9), self.mock_editor.current_color)

    # --- Tests for _draw_on_background ---
    @patch('pygame.draw.circle')
    def test_draw_on_background_no_zoom(self, mock_draw_circle):
        """Test drawing on background with default zoom/pan."""
        screen_pos = (150, 150) # Within canvas_rect
        self.mock_editor.brush_size = 1
        self.mock_editor.eraser_mode = False
        self.mock_editor.editor_zoom = 1.0
        self.mock_editor.view_offset_x = 0
        self.mock_editor.view_offset_y = 0
        
        self.draw_tool._draw_on_background(self.mock_editor, self.mock_editor.current_background, screen_pos)
        
        # Expected original coordinates
        expected_orig_x = 150 - 100 # screen_pos.x - canvas_rect.x
        expected_orig_y = 150 - 100 # screen_pos.y - canvas_rect.y
        expected_radius = 1 # brush_size 1 -> radius 0.5 -> scaled_radius 1
        expected_color = self.mock_editor.current_color[:3] # RGB
        
        mock_draw_circle.assert_called_once_with(self.mock_editor.current_background, 
                                               expected_color, 
                                               (expected_orig_x, expected_orig_y), 
                                               expected_radius)

    @patch('pygame.draw.circle')
    def test_erase_on_background_zoomed_panned(self, mock_draw_circle):
        """Test erasing on background with zoom and pan."""
        screen_pos = (110, 120) # Within canvas_rect
        self.mock_editor.brush_size = 5
        self.mock_editor.eraser_mode = True
        self.mock_editor.editor_zoom = 2.0
        self.mock_editor.view_offset_x = 20
        self.mock_editor.view_offset_y = 40
        
        self.draw_tool._draw_on_background(self.mock_editor, self.mock_editor.current_background, screen_pos)
        
        # Expected original coordinates: ( (screen_x_rel + offset_x) / zoom )
        expected_orig_x = int(((110 - 100) + 20) / 2.0) # ((10) + 20) / 2 = 15
        expected_orig_y = int(((120 - 100) + 40) / 2.0) # ((20) + 40) / 2 = 30
        # Expected radius: max(1, int((brush_size / 2) / zoom)) = max(1, int(2.5 / 2.0)) = max(1, 1) = 1
        expected_radius = 1 
        expected_color = config.WHITE # Eraser color for background
        
        mock_draw_circle.assert_called_once_with(self.mock_editor.current_background, 
                                               expected_color, 
                                               (expected_orig_x, expected_orig_y), 
                                               expected_radius)

    # --- Tests for handle_click ---
    @patch.object(DrawTool, '_draw_on_sprite')
    def test_handle_click_delegates_to_sprite(self, mock_draw_on_sprite):
        """Test handle_click calls _draw_on_sprite correctly."""
        self.mock_editor.edit_mode = 'monster'
        click_pos = (60, 60)
        grid_pos = (10, 10)
        self.mock_editor._get_sprite_editor_at_pos.return_value = self.mock_sprite_editor
        self.mock_sprite_editor.get_grid_position.return_value = grid_pos
        
        self.draw_tool.handle_click(self.mock_editor, click_pos)
        
        mock_draw_on_sprite.assert_called_once_with(self.mock_editor, self.mock_sprite_editor, grid_pos)

    @patch.object(DrawTool, '_draw_on_background')
    def test_handle_click_delegates_to_background(self, mock_draw_on_background):
        """Test handle_click calls _draw_on_background correctly."""
        self.mock_editor.edit_mode = 'background'
        click_pos = (150, 150)
        self.mock_editor.canvas_rect.collidepoint = MagicMock(return_value=True)
        
        self.draw_tool.handle_click(self.mock_editor, click_pos)
        
        mock_draw_on_background.assert_called_once_with(self.mock_editor, self.mock_editor.current_background, click_pos)


# --- Tests for FillTool ---
class TestFillTool(unittest.TestCase):

    def setUp(self):
        self.fill_tool = FillTool()
        self.mock_editor = MagicMock()
        # Common editor attributes needed by FillTool
        self.mock_editor.edit_mode = 'monster'
        self.mock_editor.current_color = (0, 255, 0, 255) # Green (fill color)
        # Mock SpriteEditor related things
        self.mock_sprite_editor = MagicMock(spec=SpriteEditor)
        self.mock_editor._get_sprite_editor_at_pos.return_value = self.mock_sprite_editor
        self.mock_sprite_editor.get_grid_position.return_value = (5, 5) # Mock start grid pos
        
        # Mock pixel access - Need a way to simulate the changing colors during fill
        # Let's use a dictionary to represent a small grid state
        self.mock_grid_state = {
            (5, 5): (255, 0, 0, 255), # Target color (Red)
            (5, 6): (255, 0, 0, 255), # Target color
            (6, 5): (255, 0, 0, 255), # Target color
            (6, 6): (0, 0, 255, 255), # Different color (Blue)
        }
        DEFAULT_COLOR = (0,0,0,0) # Transparent black for other pixels

        def mock_get_pixel(pos):
            return self.mock_grid_state.get(pos, DEFAULT_COLOR)

        def mock_draw_pixel(pos, color):
            # Update the mock grid state when drawing
            if pos in self.mock_grid_state: # Only update tracked pixels for simplicity
                self.mock_grid_state[pos] = color
            # Print for debugging test state if needed:
            # print(f"Mock draw_pixel at {pos} with {color}")
            # print(f" Grid state: {self.mock_grid_state}")

        self.mock_sprite_editor.get_pixel_color.side_effect = mock_get_pixel
        self.mock_sprite_editor.draw_pixel.side_effect = mock_draw_pixel

        # Background-related attributes
        self.mock_editor.canvas_rect = pygame.Rect(100, 100, 200, 200)
        self.mock_editor.current_background = pygame.Surface((16, 16), pygame.SRCALPHA)
        self.mock_editor.view_offset_x = 0
        self.mock_editor.view_offset_y = 0
        self.mock_editor.editor_zoom = 1.0

    @patch.object(FillTool, '_flood_fill_sprite')
    def test_handle_click_calls_flood_fill_sprite(self, mock_flood_fill_sprite):
        """Test handle_click calls _flood_fill_sprite in monster mode."""
        self.mock_editor.edit_mode = 'monster'
        click_pos = (100, 100) # Example screen pos
        start_grid_pos = (5, 5)
        self.mock_sprite_editor.get_grid_position.return_value = start_grid_pos
        
        self.fill_tool.handle_click(self.mock_editor, click_pos)
        
        mock_flood_fill_sprite.assert_called_once_with(self.mock_sprite_editor, 
                                                      start_grid_pos, 
                                                      self.mock_editor.current_color)

    @patch.object(FillTool, '_flood_fill_background')
    def test_handle_click_calls_flood_fill_background(self, mock_flood_fill_background):
        """Test handle_click calls _flood_fill_background in background mode."""
        self.mock_editor.edit_mode = 'background'
        click_pos = (150, 150) # Example screen pos within mock canvas
        
        self.fill_tool.handle_click(self.mock_editor, click_pos)
        
        expected_bg_color = self.mock_editor.current_color[:3] # RGB for background
        mock_flood_fill_background.assert_called_once_with(self.mock_editor,
                                                         self.mock_editor.current_background, 
                                                         click_pos, 
                                                         expected_bg_color)

    def test_flood_fill_sprite_area(self):
        """Test _flood_fill_sprite actually fills contiguous area."""
        start_pos = (5, 5)
        fill_color = self.mock_editor.current_color # Green
        target_color = (255, 0, 0, 255) # Red
        other_color = (0, 0, 255, 255) # Blue

        # Ensure initial state
        self.assertEqual(self.mock_sprite_editor.get_pixel_color(start_pos), target_color)
        self.assertEqual(self.mock_sprite_editor.get_pixel_color((5, 6)), target_color)
        self.assertEqual(self.mock_sprite_editor.get_pixel_color((6, 5)), target_color)
        self.assertEqual(self.mock_sprite_editor.get_pixel_color((6, 6)), other_color)

        # Perform the fill
        self.fill_tool._flood_fill_sprite(self.mock_sprite_editor, start_pos, fill_color)

        # Check final state - Red pixels should now be Green
        self.assertEqual(self.mock_sprite_editor.get_pixel_color(start_pos), fill_color)
        self.assertEqual(self.mock_sprite_editor.get_pixel_color((5, 6)), fill_color)
        self.assertEqual(self.mock_sprite_editor.get_pixel_color((6, 5)), fill_color)
        # Blue pixel should remain unchanged
        self.assertEqual(self.mock_sprite_editor.get_pixel_color((6, 6)), other_color)

    def test_flood_fill_sprite_no_change_needed(self):
        """Test _flood_fill_sprite when start pixel is already fill color."""
        start_pos = (5, 5)
        fill_color = (255, 0, 0, 255) # Red (same as initial target)
        self.mock_editor.current_color = fill_color # Make editor color same
        self.mock_grid_state[start_pos] = fill_color # Set start pixel to fill color
        
        initial_state = self.mock_grid_state.copy()

        self.fill_tool._flood_fill_sprite(self.mock_sprite_editor, start_pos, fill_color)
        
        # Assert draw_pixel was never called
        self.mock_sprite_editor.draw_pixel.assert_not_called()
        # Assert grid state is unchanged
        self.assertEqual(self.mock_grid_state, initial_state)

    def test_flood_fill_background_with_zoom_and_pan(self):
        """Background flood fill should target the correct source pixel with zoom/pan."""
        background = pygame.Surface((8, 8), pygame.SRCALPHA)
        background.fill((0, 0, 255, 255))
        # Build a small connected red region plus one non-connected red pixel.
        background.set_at((2, 1), (255, 0, 0, 255))
        background.set_at((3, 1), (255, 0, 0, 255))
        background.set_at((2, 2), (255, 0, 0, 255))
        background.set_at((6, 6), (255, 0, 0, 255))

        self.mock_editor.current_background = background
        self.mock_editor.editor_zoom = 2.0
        self.mock_editor.view_offset_x = 4
        self.mock_editor.view_offset_y = 2

        # With rect=(100,100), zoom=2, offsets=(4,2), screen (100,100) maps to bg (2,1).
        self.fill_tool._flood_fill_background(
            self.mock_editor,
            background,
            (100, 100),
            (0, 255, 0),
        )

        self.assertEqual(background.get_at((2, 1))[:3], (0, 255, 0))
        self.assertEqual(background.get_at((3, 1))[:3], (0, 255, 0))
        self.assertEqual(background.get_at((2, 2))[:3], (0, 255, 0))
        # Non-connected region and non-target colors remain unchanged.
        self.assertEqual(background.get_at((6, 6))[:3], (255, 0, 0))
        self.assertEqual(background.get_at((0, 0))[:3], (0, 0, 255))

    def test_handle_drag_does_nothing(self):
        """Verify handle_drag for FillTool does nothing."""
        # Just call it and ensure no errors and no relevant mocks were called
        try:
            self.fill_tool.handle_drag(self.mock_editor, (1,1))
        except Exception as e:
            self.fail(f"FillTool.handle_drag raised exception: {e}")
        # Ensure no drawing methods were called
        self.mock_sprite_editor.draw_pixel.assert_not_called()


# --- Tests for PasteTool ---
class TestPasteTool(unittest.TestCase):

    def setUp(self):
        self.paste_tool = PasteTool()
        self.mock_editor = MagicMock()
        # Attributes needed by PasteTool
        self.mock_editor.edit_mode = 'monster'
        self.mock_editor.copy_buffer = {
            (0, 0): (1, 1, 1, 255), # Pixel 1
            (1, 0): (2, 2, 2, 255), # Pixel 2
            (0, 1): (0, 0, 0, 0),   # Pixel 3 (transparent)
        }
        self.mock_editor.tool_manager = MagicMock(spec=ToolManager) # Needed for auto-switch on empty buffer
        # Mock SpriteEditor related things
        self.mock_sprite_editor = MagicMock(spec=SpriteEditor)
        self.mock_editor._get_sprite_editor_at_pos.return_value = self.mock_sprite_editor
        self.mock_sprite_editor.get_grid_position.return_value = (10, 10) # Mock paste target pos

        # Background-related attributes
        self.mock_editor.canvas_rect = pygame.Rect(100, 50, 200, 200)
        self.mock_editor.current_background = pygame.Surface((16, 16), pygame.SRCALPHA)
        self.mock_editor.view_offset_x = 0
        self.mock_editor.view_offset_y = 0
        self.mock_editor.editor_zoom = 1.0

    @patch.object(PasteTool, '_apply_paste_sprite')
    def test_handle_click_calls_apply_paste_sprite(self, mock_apply_paste_sprite):
        """Test handle_click calls _apply_paste_sprite in monster mode."""
        self.mock_editor.edit_mode = 'monster'
        click_pos = (100, 100)
        paste_grid_pos = (10, 10)
        self.mock_sprite_editor.get_grid_position.return_value = paste_grid_pos
        
        self.paste_tool.handle_click(self.mock_editor, click_pos)
        
        mock_apply_paste_sprite.assert_called_once_with(self.mock_editor, 
                                                      self.mock_sprite_editor, 
                                                      paste_grid_pos)

    @patch.object(PasteTool, '_apply_paste_background')
    def test_handle_click_calls_apply_paste_background(self, mock_apply_paste_background):
        """Test handle_click calls _apply_paste_background in background mode."""
        self.mock_editor.edit_mode = 'background'
        click_pos = (150, 150)
        
        self.paste_tool.handle_click(self.mock_editor, click_pos)
        
        mock_apply_paste_background.assert_called_once_with(self.mock_editor,
                                                          self.mock_editor.current_background, 
                                                          click_pos)

    def test_handle_click_empty_buffer_switches_tool(self):
        """Test handle_click switches to draw tool if copy_buffer is empty."""
        self.mock_editor.copy_buffer = None # Empty buffer
        click_pos = (100, 100)

        self.paste_tool.handle_click(self.mock_editor, click_pos)

        # Assert tool manager was called to switch tool
        self.mock_editor.tool_manager.set_active_tool.assert_called_once_with('draw')
        # Assert draw_pixel wasn't called
        self.mock_sprite_editor.draw_pixel.assert_not_called()

    def test_apply_paste_sprite_logic(self):
        """Test the logic of _apply_paste_sprite."""
        paste_grid_pos = (10, 10)
        
        self.paste_tool._apply_paste_sprite(self.mock_editor, self.mock_sprite_editor, paste_grid_pos)

        # Expect draw_pixel to be called for non-transparent pixels in buffer
        expected_calls = [
            unittest.mock.call((10, 10), (1, 1, 1, 255)), # Pastes (0,0) from buffer at (10,10)
            unittest.mock.call((11, 10), (2, 2, 2, 255)), # Pastes (1,0) from buffer at (11,10)
            # Pixel at (0,1) is transparent, so no call for (10, 11)
        ]
        self.mock_sprite_editor.draw_pixel.assert_has_calls(expected_calls, any_order=True)
        # Ensure exactly 2 calls (only non-transparent pixels)
        self.assertEqual(self.mock_sprite_editor.draw_pixel.call_count, 2)

    def test_apply_paste_sprite_empty_buffer(self):
        """Test _apply_paste_sprite does nothing with empty buffer."""
        self.mock_editor.copy_buffer = None
        paste_grid_pos = (10, 10)

        self.paste_tool._apply_paste_sprite(self.mock_editor, self.mock_sprite_editor, paste_grid_pos)

        self.mock_sprite_editor.draw_pixel.assert_not_called()

    def test_apply_paste_background_with_zoom_pan_and_alpha(self):
        """Background paste should map through zoom/pan and blend semi-transparent pixels."""
        self.mock_editor.copy_buffer = {
            (0, 0): (100, 0, 0, 255),
            (1, 0): (0, 100, 0, 128),
            (0, 1): (255, 255, 255, 0),
        }
        background = pygame.Surface((10, 10), pygame.SRCALPHA)
        background.fill((10, 20, 30, 255))
        self.mock_editor.current_background = background
        self.mock_editor.editor_zoom = 2.0
        self.mock_editor.view_offset_x = 4
        self.mock_editor.view_offset_y = 2

        # With rect=(100,50), zoom=2, offsets=(4,2), screen (102,56) maps to bg (3,4).
        self.paste_tool._apply_paste_background(self.mock_editor, background, (102, 56))

        self.assertEqual(background.get_at((3, 4))[:3], (100, 0, 0))
        expected_blend = (
            (0 * 128 + 10 * 127) // 255,
            (100 * 128 + 20 * 127) // 255,
            (0 * 128 + 30 * 127) // 255,
        )
        self.assertEqual(background.get_at((4, 4))[:3], expected_blend)
        # Transparent source pixel should not change destination.
        self.assertEqual(background.get_at((3, 5))[:3], (10, 20, 30))

    def test_handle_drag_does_nothing(self):
        """Verify handle_drag for PasteTool does nothing."""
        try:
            self.paste_tool.handle_drag(self.mock_editor, (1,1))
        except Exception as e:
            self.fail(f"PasteTool.handle_drag raised exception: {e}")
        self.mock_sprite_editor.draw_pixel.assert_not_called()


# --- Tests for ToolManager ---
class TestToolManager(unittest.TestCase):

    def setUp(self):
        self.mock_editor = MagicMock()
        
        # Mock the actual tool instances
        self.mock_draw_tool = MagicMock(spec=DrawTool)
        self.mock_fill_tool = MagicMock(spec=FillTool)
        self.mock_paste_tool = MagicMock(spec=PasteTool)
        # self.mock_select_tool = MagicMock(spec=SelectionTool) # Select not part of manager yet
        
        # Initialize ToolManager - it will create real tools temporarily
        self.manager = ToolManager(self.mock_editor)
        
        # NOW, replace the instance's tools dict with our mocks
        self.manager.tools = {
            'draw': self.mock_draw_tool,
            'fill': self.mock_fill_tool,
            'paste': self.mock_paste_tool,
            # 'select': self.mock_select_tool
        }
        # Set the active tool to the mock draw tool (matching the default)
        self.manager.active_tool = self.mock_draw_tool
        self.manager.active_tool_name = 'draw'

        # Reset the mocks used in initialization by the real tools
        # (Mainly activate call on the real draw tool)
        # It's cleaner to just verify calls within each test.

    def test_init_default_tool(self):
        """Test ToolManager initializes with the default tool active."""
        # For init test, create a separate instance to check initial state
        temp_manager = ToolManager(self.mock_editor)
        self.assertEqual(temp_manager.active_tool_name, 'draw')
        # Check that the *type* of the active tool is DrawTool
        self.assertIsInstance(temp_manager.active_tool, DrawTool)

    def test_set_active_tool(self):
        """Test switching the active tool calls activate/deactivate."""
        # Reset mocks before test, as setUp involves activate call on real tool
        self.mock_draw_tool.reset_mock()
        self.mock_fill_tool.reset_mock()
        initial_tool_mock = self.manager.active_tool # Should be mock_draw_tool

        self.manager.set_active_tool('fill')

        self.assertEqual(self.manager.active_tool_name, 'fill')
        self.assertEqual(self.manager.active_tool, self.mock_fill_tool)
        # Check deactivate was called on the mock draw tool
        initial_tool_mock.deactivate.assert_called_once_with(self.mock_editor)
        # Check activate was called on the mock fill tool
        self.mock_fill_tool.activate.assert_called_once_with(self.mock_editor)

    def test_set_invalid_tool(self):
        """Test setting an invalid tool name does not change the active tool."""
        initial_tool_mock = self.manager.active_tool
        initial_name = self.manager.active_tool_name
        # Reset mocks that might have been called during setup/previous tests
        self.mock_draw_tool.reset_mock()
        self.mock_fill_tool.reset_mock()
        self.mock_paste_tool.reset_mock()

        self.manager.set_active_tool('invalid_tool_name')

        # Assert tool and name remain unchanged
        self.assertEqual(self.manager.active_tool, initial_tool_mock)
        self.assertEqual(self.manager.active_tool_name, initial_name)
        # Ensure no activate/deactivate calls happened on our mocks
        self.mock_draw_tool.deactivate.assert_not_called()
        self.mock_fill_tool.activate.assert_not_called()
        self.mock_paste_tool.activate.assert_not_called()
        self.mock_paste_tool.deactivate.assert_not_called()

    def test_handle_click_delegation(self):
        """Test handle_click delegates to the active tool."""
        click_pos = (50, 60)
        # Set active tool to fill using the method
        self.manager.set_active_tool('fill')
        # Reset mocks called during set_active_tool
        self.mock_draw_tool.reset_mock()
        self.mock_fill_tool.reset_mock()

        self.manager.handle_click(click_pos)

        # Check fill tool's handle_click was called
        self.mock_fill_tool.handle_click.assert_called_once_with(self.mock_editor, click_pos)
        # Ensure other tools weren't called
        self.mock_draw_tool.handle_click.assert_not_called()
        self.mock_paste_tool.handle_click.assert_not_called()

    def test_handle_drag_delegation(self):
        """Test handle_drag delegates to the active tool."""
        drag_pos = (70, 80)
        # Active tool is 'draw' after setUp
        # Reset mocks before test
        self.mock_draw_tool.reset_mock()
        self.mock_fill_tool.reset_mock()
        self.mock_paste_tool.reset_mock()

        self.manager.handle_drag(drag_pos)

        # Check draw tool's handle_drag was called
        self.mock_draw_tool.handle_drag.assert_called_once_with(self.mock_editor, drag_pos)
        # Ensure other tools weren't called
        self.mock_fill_tool.handle_drag.assert_not_called()
        self.mock_paste_tool.handle_drag.assert_not_called()

# Run tests if this file is executed directly
if __name__ == '__main__':
    unittest.main() 
