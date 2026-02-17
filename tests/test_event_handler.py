import unittest
from unittest.mock import MagicMock, patch
import pygame
import os
import sys


# Now import the necessary modules
from src.core import config
from src.core.event_handler import EventHandler
# Need Palette for position/size calculation, even if mocked
from src.editor.editor_ui import Palette, Button
from src.editor.tool_manager import ToolManager
from src.editor.sprite_editor import SpriteEditor


# Use a class decorator to patch pygame.key.get_mods for all tests in this class
# @patch('pygame.key.get_mods', return_value=0) # Mock get_mods to return 0 (no mods pressed)
class TestEventHandlerPaletteInteraction(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Minimal Pygame setup needed for Rect/Event/Font
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        pygame.display.init()
        pygame.font.init() 

    @classmethod
    def tearDownClass(cls):
        pygame.display.quit()
        pygame.font.quit()

    def setUp(self):
        self.get_mods_patcher = patch("pygame.key.get_mods", return_value=0)
        self.get_mods_patcher.start()
        # Mock the Editor
        self.mock_editor = MagicMock()
        self.mock_editor.dialog_mode = None # Ensure no dialog is active
        self.mock_editor.buttons = []
        self.mock_editor.adjusting_alpha = False
        self.mock_editor.adjusting_subject_alpha = False
        self.mock_editor.tile_frame_dragging_scrollbar = False
        self.mock_editor.npc_state_dragging_scrollbar = False
        self.mock_editor.npc_angle_dragging_scrollbar = False
        self.mock_editor.panning = False
        self.mock_editor.scroll_tile_panel = MagicMock(return_value=False)
        self.mock_editor.scroll_button_panel = MagicMock(return_value=False)
        self.mock_editor.cancel_paste_mode = MagicMock(return_value=False)
        self.mock_editor._exit_selection_mode = MagicMock()

        # --- Mock Palette --- 
        self.mock_editor.palette = MagicMock(spec=Palette)
        self.palette_pos = (50, 600) 
        self.mock_editor.palette.position = self.palette_pos
        self.mock_editor.palette.block_size = getattr(config, 'PALETTE_BLOCK_SIZE', 15)
        self.mock_editor.palette.padding = getattr(config, 'PALETTE_PADDING', 2)

        # --- Mock Sliders (to prevent EventHandler from handling clicks on them) ---
        # Mock ref alpha slider rect
        self.mock_editor.ref_alpha_slider_rect = MagicMock(spec=pygame.Rect)
        self.mock_editor.ref_alpha_slider_rect.collidepoint.return_value = False
        self.mock_editor.ref_alpha_slider_rect.width = 150 # Provide a width for comparison
        
        # Mock subject alpha slider rect (even if not always used, safer for the check)
        self.mock_editor.subj_alpha_slider_rect = MagicMock(spec=pygame.Rect)
        self.mock_editor.subj_alpha_slider_rect.collidepoint.return_value = False
        self.mock_editor.subj_alpha_slider_rect.width = 150 # Provide a width

        # Mock edit_mode for slider checks in EventHandler
        self.mock_editor.edit_mode = 'monster' # Assume monster mode for simplicity

        # The handle_click method on the mock palette is automatically a MagicMock

        # Create the real EventHandler instance with the mock Editor
        self.event_handler = EventHandler(self.mock_editor)

    def tearDown(self):
        self.get_mods_patcher.stop()

    def test_handle_mouse_down_calls_palette_click_correctly(self):
        """Verify EventHandler calls Palette.handle_click with correct args on palette click."""
        # Calculate a click position within the mocked palette area
        # (Simplified - assumes top-left block is clickable)
        click_x = self.palette_pos[0] + self.mock_editor.palette.block_size // 2
        click_y = self.palette_pos[1] + self.mock_editor.palette.block_size // 2
        click_pos = (click_x, click_y)

        # Create a mock MOUSEBUTTONDOWN event
        mock_event = MagicMock(spec=pygame.event.Event)
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.button = 1 # Left click
        mock_event.pos = click_pos

        # Call the method under test (can call process_event or the specific handler)
        # Calling process_event is slightly more integrated
        self.event_handler.process_event(mock_event)
        # Or: self.event_handler._handle_mouse_button_down(mock_event)

        # Assert: palette.handle_click was called once with (event.pos, editor)
        self.mock_editor.palette.handle_click.assert_called_once_with(click_pos, self.mock_editor)

    def test_mouse_wheel_scrolls_palette(self):
        """Verify MOUSEWHEEL uses event.y to scroll the palette."""
        self.mock_editor.palette.scroll_offset = 1
        self.mock_editor.palette.total_pages = 3
        mouse_pos = (
            self.palette_pos[0] + self.mock_editor.palette.block_size // 2,
            self.palette_pos[1] + self.mock_editor.palette.block_size // 2,
        )
        with patch("pygame.mouse.get_pos", return_value=mouse_pos):
            wheel_event = pygame.event.Event(pygame.MOUSEWHEEL, {"y": 1, "x": 0})
            self.event_handler.process_event(wheel_event)

        self.assertEqual(self.mock_editor.palette.scroll_offset, 0)

    def test_mouse_wheel_uses_precise_delta_for_reference_zoom(self):
        """Verify high-resolution wheel delta is routed to reference zoom."""
        active_canvas = MagicMock()
        active_canvas.position = (0, 0)
        active_canvas.display_width = 200
        active_canvas.display_height = 200
        self.mock_editor.get_active_canvas = MagicMock(return_value=active_canvas)
        self.mock_editor.adjust_reference_scale = MagicMock(return_value=True)
        self.mock_editor.ref_img_scale = 1.234
        self.mock_editor._set_status = MagicMock()

        with patch("pygame.mouse.get_pos", return_value=(10, 10)), patch(
            "pygame.key.get_mods", return_value=pygame.KMOD_ALT
        ):
            wheel_event = pygame.event.Event(
                pygame.MOUSEWHEEL,
                {"y": 1, "x": 0, "precise_y": 0.25},
            )
            self.event_handler.process_event(wheel_event)

        self.mock_editor.adjust_reference_scale.assert_called_once_with(0.25, fine=False)
        self.mock_editor._set_status.assert_called_once()

    def test_mouse_wheel_shift_alt_enables_fine_reference_zoom(self):
        """Verify Shift+Alt wheel requests fine reference zoom mode."""
        active_canvas = MagicMock()
        active_canvas.position = (0, 0)
        active_canvas.display_width = 200
        active_canvas.display_height = 200
        self.mock_editor.get_active_canvas = MagicMock(return_value=active_canvas)
        self.mock_editor.adjust_reference_scale = MagicMock(return_value=True)
        self.mock_editor.ref_img_scale = 0.987
        self.mock_editor._set_status = MagicMock()

        with patch("pygame.mouse.get_pos", return_value=(15, 15)), patch(
            "pygame.key.get_mods", return_value=pygame.KMOD_ALT | pygame.KMOD_SHIFT
        ):
            wheel_event = pygame.event.Event(
                pygame.MOUSEWHEEL,
                {"y": 1, "x": 0, "precise_y": 0.5},
            )
            self.event_handler.process_event(wheel_event)

        self.mock_editor.adjust_reference_scale.assert_called_once_with(0.5, fine=True)
        status_message = self.mock_editor._set_status.call_args.args[0]
        self.assertIn("(fine)", status_message)

    def test_mouse_up_resets_left_button_during_dialog(self):
        """Ensure mouse-up clears left_mouse_button_down even with dialog active."""
        self.event_handler.left_mouse_button_down = True
        self.mock_editor.dialog_mode = "load_ref"
        mouse_up = pygame.event.Event(pygame.MOUSEBUTTONUP, {"button": 1, "pos": (10, 10)})
        self.event_handler.process_event(mouse_up)
        self.assertFalse(self.event_handler.left_mouse_button_down)

# TODO: Add more tests for EventHandler logic (button clicks, canvas clicks, key presses etc.)

# Use a class decorator to patch pygame.key.get_mods for all tests in this class
# @patch('pygame.key.get_mods', return_value=0) # Mock get_mods to return 0 (no mods pressed)
class TestEventHandlerOtherInteractions(unittest.TestCase):
    # Separate class for different setup/focus

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        pygame.display.init()
        pygame.font.init()

    @classmethod
    def tearDownClass(cls):
        pygame.display.quit()
        pygame.font.quit()

    def setUp(self):
        self.get_mods_patcher = patch("pygame.key.get_mods", return_value=0)
        self.get_mods_patcher.start()
        self.mock_editor = MagicMock()
        self.mock_editor.dialog_mode = None
        self.mock_editor.edit_mode = 'monster' # Default to monster

        # Mock ToolManager
        self.mock_editor.tool_manager = MagicMock(spec=ToolManager)
        self.mock_editor.tool_manager.active_tool_name = "draw"

        # Mock Buttons (list of mock buttons)
        self.mock_button_action = MagicMock() # Action for the button
        self.mock_button = MagicMock(spec=Button)
        self.mock_button.rect = pygame.Rect(500, 10, 100, 30)
        self.mock_button.action = self.mock_button_action
        # Mock is_clicked behavior
        # We'll control its return value in the test
        self.mock_button.is_clicked = MagicMock(return_value=False) 
        self.mock_editor.buttons = [self.mock_button]

        # Mock SpriteEditor related things for canvas click
        self.mock_sprite_editor = MagicMock(spec=SpriteEditor)
        self.mock_editor._get_sprite_editor_at_pos = MagicMock(return_value=None) # Default to miss
        
        # Mock Background related things for canvas click
        self.mock_editor.canvas_rect = MagicMock(spec=pygame.Rect)
        self.mock_editor.canvas_rect.collidepoint = MagicMock(return_value=False) # Default to miss

        # Mock Selection related things
        self.mock_editor.mode = 'draw' # Default to draw mode
        self.mock_editor.selection = MagicMock()
        self.mock_editor.selection.selecting = False

        # Mock sliders to prevent interference
        self.mock_editor.ref_alpha_slider_rect = MagicMock(spec=pygame.Rect)
        self.mock_editor.ref_alpha_slider_rect.collidepoint.return_value = False
        self.mock_editor.ref_alpha_slider_rect.width = 150 # Provide a width
        self.mock_editor.subj_alpha_slider_rect = MagicMock(spec=pygame.Rect)
        self.mock_editor.subj_alpha_slider_rect.collidepoint.return_value = False
        self.mock_editor.subj_alpha_slider_rect.width = 150 # Provide a width
        self.mock_editor.adjusting_alpha = False # <<< Add mock attribute
        self.mock_editor.adjusting_subject_alpha = False # <<< Add mock attribute
        self.mock_editor.tile_frame_dragging_scrollbar = False
        self.mock_editor.npc_state_dragging_scrollbar = False
        self.mock_editor.npc_angle_dragging_scrollbar = False
        self.mock_editor.panning = False
        self.mock_editor.scroll_tile_panel = MagicMock(return_value=False)
        self.mock_editor.scroll_button_panel = MagicMock(return_value=False)

        # Mock Palette interaction to prevent interference
        self.mock_editor.palette = MagicMock(spec=Palette)
        # Need to mock the rect calculation used in EventHandler
        # Or ensure the test click pos is outside the palette rect
        self.mock_editor.palette.position = (1000, 1000) # Position it off-screen
        self.mock_editor.palette.block_size = 15
        self.mock_editor.palette.padding = 2
        
        # Create EventHandler
        self.event_handler = EventHandler(self.mock_editor)

    def tearDown(self):
        self.get_mods_patcher.stop()

    def test_button_click_calls_action(self):
        """Verify clicking a button calls its action."""
        click_pos = self.mock_button.rect.center
        mock_event = MagicMock(spec=pygame.event.Event)
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.button = 1
        mock_event.pos = click_pos

        # Configure the mock button's is_clicked to return True for this event
        self.mock_button.is_clicked.return_value = True 

        # Process the event
        self.event_handler.process_event(mock_event)

        # Assert
        self.mock_button.is_clicked.assert_called_once_with(mock_event)
        self.mock_button_action.assert_called_once()

    def test_canvas_click_calls_tool_manager(self):
        """Verify clicking the canvas calls tool_manager.handle_click."""
        # Simulate clicking on a sprite editor
        self.mock_editor._get_sprite_editor_at_pos.return_value = self.mock_sprite_editor
        click_pos = (60, 60) # Assume this hits the sprite editor
        self.mock_editor.mode = 'draw' # Ensure not in select mode

        mock_event = MagicMock(spec=pygame.event.Event)
        mock_event.type = pygame.MOUSEBUTTONDOWN
        mock_event.button = 1
        mock_event.pos = click_pos
        
        self.event_handler.process_event(mock_event)

        # Assert tool manager was called
        self.mock_editor.tool_manager.handle_click.assert_called_once_with(click_pos)
        # Ensure save_state was called (since not in select mode)
        self.mock_editor.save_state.assert_called_once()

    def test_canvas_drag_calls_tool_manager(self):
        """Verify dragging on the canvas calls tool_manager.handle_drag."""
        drag_pos = (70, 70)
        self.mock_editor.mode = 'draw' # Ensure not in select mode
        
        # Simulate mouse button being down before motion
        self.event_handler.left_mouse_button_down = True

        mock_event = MagicMock(spec=pygame.event.Event)
        mock_event.type = pygame.MOUSEMOTION
        mock_event.buttons = (1, 0, 0) # Left button held
        mock_event.pos = drag_pos
        
        self.event_handler.process_event(mock_event)

        # Assert tool manager drag was called
        self.mock_editor.tool_manager.handle_drag.assert_called_once_with(drag_pos)

    def test_canvas_drag_ignored_in_select_mode(self):
        """Verify canvas drag is ignored by tool manager in select mode."""
        drag_pos = (70, 70)
        self.mock_editor.mode = 'select' # In select mode
        
        # Simulate mouse button being down before motion
        self.event_handler.left_mouse_button_down = True
        
        mock_event = MagicMock(spec=pygame.event.Event)
        mock_event.type = pygame.MOUSEMOTION
        mock_event.buttons = (1, 0, 0) # Left button held
        mock_event.pos = drag_pos
        
        self.event_handler.process_event(mock_event)

        # Assert tool manager drag was NOT called
        self.mock_editor.tool_manager.handle_drag.assert_not_called()

    def test_escape_cancels_paste_mode(self):
        self.mock_editor.cancel_paste_mode.return_value = True
        key_event = MagicMock(spec=pygame.event.Event)
        key_event.type = pygame.KEYDOWN
        key_event.mod = 0
        key_event.key = pygame.K_ESCAPE
        self.event_handler.process_event(key_event)
        self.mock_editor.cancel_paste_mode.assert_called_once()


if __name__ == '__main__':
    unittest.main() 
