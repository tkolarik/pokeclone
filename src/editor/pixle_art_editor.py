import pygame
from pygame.locals import *
import tkinter as tk
from tkinter import filedialog, colorchooser
import sys
import os
import json
import copy
import colorsys

# Import the centralized config
from src.core import config

# Import newly created modules
from src.core.event_handler import EventHandler
from src.editor.editor_ui import Button, Palette, PALETTE
from src.editor.selection_manager import SelectionTool
from src.editor.sprite_editor import SpriteEditor
from src.editor.tool_manager import ToolManager

# Initialize Tkinter root window and hide it
root = None # Keep module-level variable as None, Editor will manage its own instance

# --- Initialize Tkinter Root FIRST --- 
tk_root = None
tkinter_error = None
try:
    print("Attempting to initialize tk.Tk() globally...")
    tk_root = tk.Tk()
    tk_root.withdraw() # Hide the main window
    print("Global tk.Tk() initialized successfully.")
except Exception as e:
    # Store error if Tkinter fails to initialize globally
    print(f"ERROR: Global Tkinter initialization failed: {e}")
    tkinter_error = e 
# --- End Tkinter Init ---

# Now import and initialize Pygame
pygame.init()

# Constants are now in config.py
# WIDTH, HEIGHT = 1300, 800
# EDITOR_GRID_SIZE = 32 # Visual grid size for editing
# PIXEL_SIZE = 15  # Visual size of each 'pixel' in the editor grid
# NATIVE_SPRITE_RESOLUTION = (32, 32) # Actual resolution of the sprite data
# FPS = 60
# BACKGROUND_WIDTH, BACKGROUND_HEIGHT = 1600, 800
# MAX_BRUSH_SIZE = 20
# PALETTE_COLS = 20
# PALETTE_ROWS = 8

# Setup
screen = pygame.display.set_mode((config.EDITOR_WIDTH, config.EDITOR_HEIGHT))
pygame.display.set_caption("Advanced Pixel Art Sprite Editor with Enhanced Features")
clock = pygame.time.Clock()

# Load monster data
def load_monsters():
    """
    Load monster data from the 'monsters.json' file.

    This function reads the 'monsters.json' file, which contains information about
    various monsters, including their names, types, max HP, and moves. The data
    is used to populate the editor with monster sprites and their attributes.

    Returns:
        list: A list of dictionaries, each representing a monster with its attributes.
    """
    # Use path from config
    monsters_file = os.path.join(config.DATA_DIR, "monsters.json")

    try:
        with open(monsters_file, "r") as f:
            monsters = json.load(f)
        if not isinstance(monsters, list):
            raise ValueError("monsters.json should contain a list of monsters.")
        return monsters
    except FileNotFoundError:
        print(f"Error: Could not find monsters.json in {os.path.dirname(monsters_file)}")
        print("Make sure you've created the data directory and added the monsters.json file.")
        pygame.quit()
        sys.exit(1)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error: {e}")
        pygame.quit()
        sys.exit(1)

monsters = load_monsters()

# Editor Class with Enhanced Features
class Editor:
    """
    The main controller class for the pixel art editor application.

    This class orchestrates the entire pixel art editing experience, managing
    sprite editors, color palettes, tool selection, and user interactions. It
    handles both monster sprite editing and background editing modes.

    Attributes:
        current_color (tuple): The currently selected color (R, G, B, A).
        current_monster_index (int): Index of the currently edited monster.
        drawing (bool): Flag indicating if drawing is currently active.
        eraser_mode (bool): Flag for eraser tool activation.
        fill_mode (bool): Flag for fill tool activation.
        current_sprite (str): Identifier of the currently active sprite ('front' or 'back').
        sprites (dict): Dictionary of SpriteEditor instances for each sprite type.
        palette (Palette): The color palette instance.
        brush_size (int): Current brush size for drawing.
        selection (SelectionTool): The selection tool instance.
        copy_buffer (dict): Buffer for copied pixel data.
        mode (str): Current editing mode ('draw' or 'select').
        backgrounds (list): List of available background images.
        edit_mode (str): Current editing mode ('monster' or 'background').
        editor_zoom (float): Current zoom level of the editor.

    Methods:
        handle_event(event: pygame.event.Event) -> bool
        draw_ui() -> None
        save_current() -> None
        load_session() -> None
        undo() -> None
        redo() -> None
        # ... (other methods)
    """

    def __init__(self):
        """
        Initialize a new Editor instance.
        """
        self.current_color = PALETTE[0] # <<< Uses imported PALETTE
        self.current_monster_index = 0
        self.eraser_mode = False # Keep temporarily? DrawTool uses it.
        self.fill_mode = False # Keep temporarily? Needed for FillTool logic later.
        self.paste_mode = False # Keep temporarily? Needed for PasteTool logic later.
        self.current_sprite = 'front'
        self.sprites = {
            'front': SpriteEditor((50, 110), 'front', config.SPRITE_DIR),
            'back': SpriteEditor((575, 110), 'back', config.SPRITE_DIR) 
        }
        self.palette = Palette((50, config.EDITOR_HEIGHT - 180))
        self.brush_size = 1
        self.adjusting_brush = False
        self.selection = SelectionTool(self) # SelectionTool might become a tool in ToolManager later
        self.copy_buffer = None
        self.mode = 'draw'  # Keep? Or manage via ToolManager? Keep for 'select' vs other tools for now.
        self.backgrounds = self.load_backgrounds()
        self.current_background_index = 0 if self.backgrounds else -1
        self.edit_mode = None
        self.editor_zoom = 1.0
        self.view_offset_x = 0 
        self.view_offset_y = 0
        self.panning = False

        # Instantiate the EventHandler
        self.event_handler = EventHandler(self)

        # Instantiate the ToolManager <<< NEW
        self.tool_manager = ToolManager(self)

        self.current_background = None
        self.canvas_rect = None

        # Undo/Redo stacks
        self.undo_stack = []
        self.redo_stack = []

        self.buttons = [] # Start with empty buttons

        self.font = pygame.font.Font(config.DEFAULT_FONT, config.EDITOR_INFO_FONT_SIZE)

        self.brush_slider = pygame.Rect(50, config.EDITOR_HEIGHT - 40, 200, 20)

        # --- Reference Image Attributes ---
        self.reference_image_path = None
        self.reference_image = None # Original loaded surface
        self.scaled_reference_image = None # Scaled and alpha-applied surface for display
        self.reference_alpha = 128 # Default alpha (50% opaque)
        self.adjusting_alpha = False # Flag for slider interaction
        self.subject_alpha = 255 # << Add subject alpha (fully opaque default)
        self.adjusting_subject_alpha = False # << Add flag for subject slider

        # Define slider rect (adjust position/size as needed)
        # Reference Alpha Slider
        ref_slider_x = 300 # Position next to brush slider for now
        ref_slider_y = config.EDITOR_HEIGHT - 40
        ref_slider_width = 150
        ref_slider_height = 20
        self.ref_alpha_slider_rect = pygame.Rect(ref_slider_x, ref_slider_y, ref_slider_width, ref_slider_height)
        ref_knob_slider_width = self.ref_alpha_slider_rect.width - 10 # Available track width
        initial_ref_knob_x = self.ref_alpha_slider_rect.x + int((self.reference_alpha / 255) * ref_knob_slider_width)
        self.ref_alpha_knob_rect = pygame.Rect(initial_ref_knob_x, ref_slider_y, 10, ref_slider_height)

        # Subject Alpha Slider (Position below reference slider)
        subj_slider_x = ref_slider_x 
        subj_slider_y = ref_slider_y + ref_slider_height + 10 # Place below ref slider
        subj_slider_width = ref_slider_width
        subj_slider_height = ref_slider_height
        self.subj_alpha_slider_rect = pygame.Rect(subj_slider_x, subj_slider_y, subj_slider_width, subj_slider_height)
        subj_knob_slider_width = self.subj_alpha_slider_rect.width - 10
        initial_subj_knob_x = self.subj_alpha_slider_rect.x + int((self.subject_alpha / 255) * subj_knob_slider_width)
        self.subj_alpha_knob_rect = pygame.Rect(initial_subj_knob_x, subj_slider_y, 10, subj_slider_height)

        # --- Dialog State ---
        self.dialog_mode = None # e.g., 'choose_edit_mode', 'choose_bg_action', 'save_bg', 'load_bg', 'color_picker', 'input_text'
        self.dialog_prompt = ""
        self.dialog_options = [] # List of tuples: (text, value) or Button objects
        self.dialog_callback = None # Function to call with the chosen value
        self.dialog_input_text = "" # For text input dialogs
        self.dialog_input_active = False # Is the text input active?
        self.dialog_input_rect = None # Rect for the input field
        self.dialog_input_max_length = 50 # Max chars for filename
        self.dialog_file_list = [] # List of files for file browser dialog
        self.dialog_file_scroll_offset = 0 # Scroll offset for file list
        self.dialog_selected_file_index = -1 # Index of selected file in list
        self.dialog_color_picker_hue = 0 # Hue for HSV color picker
        self.dialog_color_picker_sat = 1 # Saturation for HSV
        self.dialog_color_picker_val = 1 # Value for HSV
        self.dialog_color_picker_rects = {} # Rects for color picker elements
        # --- End Dialog State ---

        self.tk_root = None # Initialize instance variable for Tkinter root

        # <<< --- ADD THE CALL HERE --- >>>
        self.choose_edit_mode() # Setup the initial dialog state AFTER resetting dialog attrs

    def _ensure_tkinter_root(self):
        """Check if the global Tkinter root was initialized successfully."""
        # Access the global tk_root variable
        global tk_root, tkinter_error 
        if tk_root is None:
             print(f"Tkinter root unavailable. Global init error: {tkinter_error}")
             return False
        # If global root exists, return True
        return True

    def choose_edit_mode(self):
        """
        Set up the dialog state to choose the editing mode (monster or background).
        The actual choice will be handled in the main loop via dialog state.
    
        Returns:
            None: Sets the initial dialog state instead of returning the mode directly.
        """
        self.dialog_mode = 'choose_edit_mode'
        self.dialog_prompt = "Choose Edit Mode:"

        # Calculate positions for vertically stacked buttons centered
        dialog_center_x = config.EDITOR_WIDTH // 2
        dialog_center_y = config.EDITOR_HEIGHT // 2
        button_width = 150
        button_height = 40
        button_padding = 10
        monster_button_y = dialog_center_y - button_height - button_padding // 2
        background_button_y = dialog_center_y + button_padding // 2
        button_x = dialog_center_x - button_width // 2

        self.dialog_options = [
            Button(pygame.Rect(button_x, monster_button_y, button_width, button_height), "Monster", value="monster"), # No action, store value
            Button(pygame.Rect(button_x, background_button_y, button_width, button_height), "Background", value="background"), # No action, store value
        ]
        self.dialog_callback = self._set_edit_mode_and_continue
        # print(f"DEBUG: choose_edit_mode finished. self.dialog_mode = {self.dialog_mode}") # DEBUG

        # <<< --- REMOVE THIS RETURN --- >>>
        # return "monster" # Default to monster initially

    def _set_edit_mode_and_continue(self, mode):
        """Callback after choosing edit mode."""
        # print(f"DEBUG: Start _set_edit_mode_and_continue(mode='{mode}')") # DEBUG 4 - REMOVE
        self.edit_mode = mode # Set mode FIRST
        if mode == 'background':
            # --- Setup for Background Mode --- 
            self.canvas_rect = pygame.Rect(50, 100, config.DEFAULT_BACKGROUND_WIDTH, config.DEFAULT_BACKGROUND_HEIGHT)
            self.current_background = pygame.Surface(self.canvas_rect.size, pygame.SRCALPHA)
            self.current_background.fill(config.WHITE) # Default to white
            # --- End Setup ---
            # Now trigger the background action choice (new/edit)
            # print(f"DEBUG: Before calling choose_background_action()") # DEBUG 5 - REMOVE
            self.choose_background_action()
        else: # Monster mode
            # If monster mode, initialization is complete
            # Clear potential background canvas rect
            self.canvas_rect = None
            self.current_background = None
            self.load_monster() # Ensure monster is loaded if chosen
            self.buttons = self.create_buttons() # Recreate buttons for the correct mode
            # --- ADD CLEARING LOGIC FOR MONSTER MODE --- 
            self.dialog_mode = None 
            self.dialog_prompt = ""
            self.dialog_options = []
            self.dialog_callback = None
        # print(f"DEBUG: End _set_edit_mode_and_continue. dialog_mode={self.dialog_mode}") # DEBUG 6 - REMOVE

    def _handle_dialog_choice(self, value):
        """Internal handler for dialog button values or direct calls."""
        # print(f"DEBUG: Start _handle_dialog_choice(value={repr(value)})") # DEBUG 1 - REMOVE
        callback_to_call = self.dialog_callback # Store before potential modification
        if callback_to_call:
            if value is None: # Cancel Path
                 print("Dialog action cancelled by user.")
                 self.dialog_mode = None
                 self.dialog_prompt = ""
                 self.dialog_options = []
                 # Set back to None
                 # if hasattr(self, 'dialog_callback'):
                 #     del self.dialog_callback 
                 self.dialog_callback = None # <<< REVERT TO THIS
                 # Reset input-specific state too
                 self.dialog_input_text = ""
                 # ... rest of cancel path clearing ...
            else: # Value is not None (Confirm Path)
                 try:
                     # print(f"DEBUG: Before calling callback {getattr(callback_to_call, '__name__', 'unknown')}") # DEBUG 2 - REMOVE
                     callback_to_call(value)
                     # Callback handles its own state transitions now
                 except Exception as e:
                     print(f"ERROR during dialog callback {getattr(callback_to_call, '__name__', 'unknown')}: {e}")
                     # Clear dialog on error
                     self.dialog_mode = None
                     # ... clear other stuff ...
        # print(f"DEBUG: End _handle_dialog_choice. dialog_mode={self.dialog_mode}") # DEBUG 3 - REMOVE

    def refocus_pygame_window(self):
        """
        Refocus the Pygame window - REMOVED as Tkinter is gone.
        """
        # pygame.display.iconify() - REMOVED
        # pygame.display.set_mode((config.EDITOR_WIDTH, config.EDITOR_HEIGHT)) - REMOVED
        # print("Editor window refocused.") - REMOVED
        pass # No longer needed

    def create_buttons(self):
        """
        Create the buttons for the editor UI.

        This method creates the buttons for the editor UI based on the current
        edit mode. It returns a list of Button instances.

        Returns:
            list: A list of Button instances.
        """
        buttons = []
        button_width = 100
        button_height = 30
        padding = 5
        start_x = config.EDITOR_WIDTH - button_width - padding
        start_y = 50

        # Determine the correct save action based on the edit mode
        save_action = None
        if self.edit_mode == 'monster':
            save_action = self.save_current_monster_sprites
        elif self.edit_mode == 'background':
            save_action = self.save_background
        else:
            # Default or error handling if mode is unexpected during init
            print(f"Warning: Unknown edit mode '{self.edit_mode}' during button creation. Save button disabled.")
            save_action = lambda: print("Save disabled.") # No-op action

        all_buttons = [
            ("Save", save_action), # Use the determined action
            ("Load", self.trigger_load_background_dialog if self.edit_mode == 'background' else lambda: print("Load BG only in BG mode")),
            ("Clear", self.clear_current),
            ("Color Picker", self.open_color_picker),
            ("Eraser", self.toggle_eraser),
            ("Fill", self.toggle_fill),
            ("Select", self.toggle_selection_mode),
            ("Copy", self.copy_selection),
            ("Paste", self.paste_selection),
            ("Mirror", self.mirror_selection),
            ("Rotate", self.rotate_selection),
            ("Undo", self.undo),
            ("Redo", self.redo),
            # Add Reference Image Buttons (only relevant in monster mode?)
            ("Load Ref Img", self.load_reference_image if self.edit_mode == 'monster' else lambda: print("Ref Img only in Monster mode")),
            ("Clear Ref Img", self.clear_reference_image if self.edit_mode == 'monster' else lambda: print("Ref Img only in Monster mode")),
        ]

        if self.edit_mode == 'monster':
            all_buttons += [
                ("Prev Monster", self.previous_monster),
                ("Next Monster", self.next_monster),
                ("Switch Sprite", self.switch_sprite),
            ]
        elif self.edit_mode == 'background':
            all_buttons += [
                ("Zoom In", self.zoom_in),
                ("Zoom Out", self.zoom_out),
                ("Brush +", self.increase_brush_size),
                ("Brush -", self.decrease_brush_size),
                ("Prev BG", self.previous_background),
                ("Next BG", self.next_background),
                # Add Panning Buttons
                ("Pan Up", self.pan_up),
                ("Pan Down", self.pan_down),
                ("Pan Left", self.pan_left),
                ("Pan Right", self.pan_right),
            ]

        for i, (text, action) in enumerate(all_buttons):
            rect = (start_x, start_y + i * (button_height + padding), button_width, button_height)
            buttons.append(Button(rect, text, action))

        return buttons

    def save_current_monster_sprites(self):
        """Saves both front and back sprites for the current monster."""
        try:
            # Ensure monsters list and index are valid
            if not hasattr(config, 'monsters') or not isinstance(config.monsters, list):
                print("Error: Monster data not loaded or invalid. Cannot save.")
                return
            if not (0 <= self.current_monster_index < len(config.monsters)):
                print(f"Error: current_monster_index {self.current_monster_index} out of range. Cannot save.")
                return

            monster_name = config.monsters[self.current_monster_index].get('name')
            if not monster_name:
                print(f"Error: Monster name not found at index {self.current_monster_index}. Cannot save.")
                return

            # Save both front and back sprites
            self.sprites['front'].save_sprite(monster_name)
            self.sprites['back'].save_sprite(monster_name)
            print(f"Saved sprites for {monster_name}")

        except Exception as e:
            print(f"An unexpected error occurred during save_current_monster_sprites: {e}")

    def clear_current(self):
        """Clears the currently active editing area (sprite or background)."""
        self.save_state() # Save state before clearing
        if self.edit_mode == 'monster':
            sprite = self.sprites.get(self.current_sprite)
            if sprite:
                sprite.frame.fill((*config.BLACK[:3], 0)) # Fill with transparent black
                print(f"Cleared {self.current_sprite} sprite.")
            else:
                print(f"Error: Could not find sprite editor for {self.current_sprite} to clear.")
        elif self.edit_mode == 'background':
            if self.current_background:
                # Assuming default background is white, fill with that
                # Or could use a different default clear color if needed
                self.current_background.fill((*config.WHITE, 255)) # Fill with opaque white
                print("Cleared current background.")
            else:
                print("Error: No current background loaded to clear.")
        else:
            print(f"Warning: Unknown edit mode '{self.edit_mode}' for clear operation.")

    def toggle_eraser(self):
        """Toggle eraser mode (now handled by DrawTool state)."""
        # If already draw tool, just toggle erase_mode
        if self.tool_manager.active_tool_name == 'draw':
             self.eraser_mode = not self.eraser_mode
             print(f"Eraser mode: {self.eraser_mode}")
             # Ensure other potentially conflicting modes are off
             self.fill_mode = False 
             self.paste_mode = False
        else:
             # If switching from another tool, activate draw tool and set erase mode
             self.tool_manager.set_active_tool('draw')
             self.eraser_mode = True
             print(f"Eraser mode: {self.eraser_mode}")
        # No longer need to manage select mode here, set_active_tool does it

    def toggle_fill(self):
        """Activate fill tool."""
        # self.fill_mode = not self.fill_mode # OLD
        # self.eraser_mode = False # OLD
        # self.paste_mode = False # OLD
        # if self.mode == 'select': # OLD
        #     self.mode = 'draw' # OLD
        #     self.selection.selecting = False # OLD
        #     self.selection.active = False # OLD
        # print(f"Fill mode: {self.fill_mode}") # OLD
        self.tool_manager.set_active_tool('fill') # <<< NEW
        # We might need flags like self.fill_mode if FillTool needs them?
        # For now, assume activating the tool is sufficient.
        # ToolManager.set_active_tool handles turning off other flags.
        self.fill_mode = True # Keep flag for now until FillTool state is internal
        self.eraser_mode = False
        self.paste_mode = False

    def toggle_selection_mode(self):
        """Toggle selection mode."""
        # Selection is not yet a formal tool in ToolManager
        # Keep existing logic for now
        if self.mode == 'select':
            self.mode = 'draw'
            self.selection.selecting = False
            self.selection.active = False
            # Ensure draw tool is active when exiting select mode
            self.tool_manager.set_active_tool('draw') 
            print("Switched to Draw mode.")
        else:
            self.mode = 'select'
            self.selection.toggle() # Activate selection tool logic
            # Deactivate other tools implicitly by switching mode (handled by event handler checks)
            self.eraser_mode = False
            self.fill_mode = False
            self.paste_mode = False
            # Maybe explicitly deactivate the ToolManager's tool?
            if self.tool_manager.active_tool:
                 self.tool_manager.active_tool.deactivate(self)
            print("Switched to Select mode.")

    def copy_selection(self):
        """Copy the selected pixels to the buffer."""
        if self.mode == 'select' and self.selection.active:
            # Get the currently active sprite editor
            sprite_editor = self.sprites.get(self.current_sprite)
            if not sprite_editor:
                 print("Copy failed: Cannot find active sprite editor.")
                 return
                 
            # Pass the sprite_editor instance
            self.copy_buffer = self.selection.get_selected_pixels(sprite_editor)
            
            if self.copy_buffer:
                 print(f"Copied {len(self.copy_buffer)} pixels.")
            else:
                 print("Copy failed: No pixels selected or error getting pixels.")
        else:
            print("Copy failed: No active selection.")

    def paste_selection(self):
        """Activate paste mode with the buffered pixels."""
        if self.copy_buffer:
            # self.paste_mode = True # OLD
            # self.mode = 'draw' # Exit select mode implicitly # OLD
            # self.selection.active = False # OLD
            # self.eraser_mode = False # OLD
            # self.fill_mode = False # OLD
            # print("Paste mode activated. Click to place.") # OLD
            self.tool_manager.set_active_tool('paste') # <<< NEW
            # Keep flags for now until PasteTool state is internal?
            self.paste_mode = True 
            self.eraser_mode = False
            self.fill_mode = False
        else:
            print("Paste failed: Copy buffer is empty.")

    def mirror_selection(self):
        """Mirror the selected pixels horizontally in-place."""
        if self.mode != 'select' or not self.selection.active:
            print("Mirror failed: Make an active selection first.")
            return

        sprite_editor = self.sprites.get(self.current_sprite)
        if not sprite_editor:
            print("Mirror failed: Active sprite editor not found.")
            return

        self.save_state() # Save state before modifying
        selection_rect = self.selection.rect

        # Create a subsurface referencing the selected area (no copy needed yet)
        try:
             original_area = sprite_editor.frame.subsurface(selection_rect)
             mirrored_area = pygame.transform.flip(original_area, True, False) # Flip horizontal
        except ValueError as e:
             print(f"Error creating subsurface for mirroring: {e}")
             self.undo_stack.pop() # Remove the state we just saved
             return

        # ---> ADD THIS LINE: Clear the original area first <---
        sprite_editor.frame.fill((*config.BLACK[:3], 0), selection_rect)

        # Blit mirrored surface back onto the main frame
        sprite_editor.frame.blit(mirrored_area, selection_rect.topleft)
        print("Selection mirrored.")
        # Keep selection active

    def rotate_selection(self):
        """Rotate the selected pixels 90 degrees clockwise in-place."""
        if self.mode != 'select' or not self.selection.active:
            print("Rotate failed: Make an active selection first.")
            return

        sprite_editor = self.sprites.get(self.current_sprite)
        if not sprite_editor:
            print("Rotate failed: Active sprite editor not found.")
            return

        self.save_state() # Save state before modifying
        selection_rect = self.selection.rect

        # Create a subsurface and rotate it
        try:
            original_area = sprite_editor.frame.subsurface(selection_rect)
            # Rotating might change dimensions, so handle carefully
            rotated_area = pygame.transform.rotate(original_area, -90) # Clockwise
        except ValueError as e:
            print(f"Error creating subsurface for rotation (maybe 0 size?): {e}")
            return

        # Clear original area ONLY IF rotation doesn't change size AND it fits
        # A simpler approach for now: Overwrite with rotated, centered.
        # Clear original area first
        sprite_editor.frame.fill((*config.BLACK[:3], 0), selection_rect)

        # Blit rotated surface back, centered in the original rect bounds
        blit_pos = rotated_area.get_rect(center=selection_rect.center)
        sprite_editor.frame.blit(rotated_area, blit_pos)
        print("Selection rotated 90 degrees clockwise.")
        # Keep selection active, rect might be slightly off if not square

    def zoom_in(self):
        """Zoom in on the background canvas."""
        if self.edit_mode == 'background':
            # Increase zoom level, potentially up to a max limit
            self.editor_zoom *= 1.2 # Example: Increase by 20%
            max_zoom = 8.0 # Example maximum zoom
            self.editor_zoom = min(self.editor_zoom, max_zoom)
            print(f"Zoom In: Level {self.editor_zoom:.2f}x")
            # TODO: Adjust view offset based on mouse position
        else:
            print("Zoom only available in background mode.")

    def zoom_out(self):
        """Zoom out on the background canvas."""
        if self.edit_mode == 'background':
            # Decrease zoom level, potentially down to a min limit
            self.editor_zoom /= 1.2 # Example: Decrease by 20%
            min_zoom = 0.25 # Example minimum zoom
            self.editor_zoom = max(self.editor_zoom, min_zoom)
            print(f"Zoom Out: Level {self.editor_zoom:.2f}x")
            # TODO: Adjust view offset based on mouse position
        else:
             print("Zoom only available in background mode.")

    def increase_brush_size(self):
        """Increase brush size."""
        if self.brush_size < config.MAX_BRUSH_SIZE:
            self.brush_size += 1
            print(f"Brush size: {self.brush_size}")
        else:
             print("Max brush size reached.")

    def decrease_brush_size(self):
        """Decrease brush size."""
        if self.brush_size > 1:
            self.brush_size -= 1
            print(f"Brush size: {self.brush_size}")
        else:
             print("Min brush size reached.")

    def previous_background(self):
        """Switch to the previous background image."""
        if self.edit_mode == 'background' and self.backgrounds:
            if self.current_background_index > 0:
                self.current_background_index -= 1
                self.current_background = self.backgrounds[self.current_background_index][1].copy()
                self.undo_stack = [] # Reset undo/redo for new image
                self.redo_stack = []
                print(f"Switched to previous background: {self.backgrounds[self.current_background_index][0]}")
            else:
                print("Already at the first background.")
        else:
             print("Previous background only available in background mode with existing backgrounds.")

    def next_background(self):
        """Switch to the next background image."""
        if self.edit_mode == 'background' and self.backgrounds:
            if self.current_background_index < len(self.backgrounds) - 1:
                self.current_background_index += 1
                self.current_background = self.backgrounds[self.current_background_index][1].copy()
                self.undo_stack = [] # Reset undo/redo for new image
                self.redo_stack = []
                print(f"Switched to next background: {self.backgrounds[self.current_background_index][0]}")
            else:
                print("Already at the last background.")
        else:
             print("Next background only available in background mode with existing backgrounds.")

    def open_color_picker(self):
        """Open the system's native color picker dialog using Tkinter."""
        if not self._ensure_tkinter_root():
            # Message already printed by _ensure_tkinter_root
            return

        # Convert current color to Tkinter format (hex string)
        initial_color_hex = "#{:02x}{:02x}{:02x}".format(*self.current_color[:3])

        # Open the dialog, passing the global root as parent
        try:
             # Use the global tk_root directly
             chosen_color = colorchooser.askcolor(parent=tk_root, color=initial_color_hex, title="Select Color")
        except tk.TclError as e:
             print(f"Error opening native color picker: {e}")
             chosen_color = None
        except Exception as e: # Catch other potential errors
             print(f"Unexpected error during color chooser: {e}")
             chosen_color = None

        # Bring Pygame window back to focus might be needed here too if dialog issues persist

        if chosen_color and chosen_color[1] is not None: 
            rgb, _ = chosen_color
            new_color_rgba = (int(rgb[0]), int(rgb[1]), int(rgb[2]), 255) # Add full alpha
            self.select_color(new_color_rgba)
            print(f"Color selected via native picker: {new_color_rgba}")
        else:
            print("Color selection cancelled or failed.")

    def _get_current_picker_color(self):
        # ... This method is now only relevant for a potential Pygame fallback ...
        pass

    def _color_picker_callback(self, color):
        # ... This method is now only relevant for a potential Pygame fallback ...
        pass

    def select_color(self, color):
        """
        Select a color from the palette.

        This method sets the currently selected color based on the provided color
        tuple. It also deactivates the eraser and fill modes.

        Args:
            color (tuple): The RGBA color tuple to select.
        """
        if color is not None:
            self.current_color = color
            self.eraser_mode = False # Keep? DrawTool uses this
            self.fill_mode = False   # Keep? FillTool might need later?
            self.paste_mode = False  # Explicitly set paste mode flag off
            
            # Switch back to draw tool if another tool was active
            if self.tool_manager.active_tool_name != 'draw':
                self.tool_manager.set_active_tool('draw')
            
            # Also ensure selection mode is off
            if self.mode == 'select':
                self.mode = 'draw' # Already handled by set_active_tool if needed
                self.selection.selecting = False
                self.selection.active = False
            print(f"Selected color: {color}")

    def load_backgrounds(self):
        """
        Load available background images from the 'backgrounds' directory.

        This method scans the 'backgrounds' directory for PNG files and attempts
        to load them as background images. It returns a list of tuples, where each
        tuple contains the filename and the corresponding Pygame Surface.

        Returns:
            list: A list of tuples, each containing a filename and a Pygame Surface.
        """
        backgrounds = []
        # config should ensure BACKGROUND_DIR exists
        # if not os.path.exists(config.BACKGROUND_DIR):
        #     os.makedirs(config.BACKGROUND_DIR)
        for filename in os.listdir(config.BACKGROUND_DIR):
            if filename.endswith('.png'):
                path = os.path.join(config.BACKGROUND_DIR, filename)
                try:
                    bg = pygame.image.load(path).convert_alpha()
                    backgrounds.append((filename, bg))
                except pygame.error as e:
                    print(f"Failed to load background {filename}: {e}")
        return backgrounds

    def show_edit_mode_dialog(self):
        """
        Display a dialog to choose the editing mode - REMOVED / Replaced by dialog state.
        """
        # REMOVED Tkinter dialog code
        print("DEBUG: show_edit_mode_dialog was called but is replaced by dialog state.")
        return "monster" # Return default, logic moved to choose_edit_mode

    def show_background_action_dialog(self):
        """
        Display a dialog to choose the background action - REMOVED / Replaced by dialog state.
        """
        # REMOVED Tkinter dialog code
        print("DEBUG: show_background_action_dialog was called but is replaced by dialog state.")
        return "new" # Return default, logic moved to choose_background_action

    def choose_background_action(self):
        """
        Handle background-specific actions (new or edit) using dialog state.
        """
        # print(f"DEBUG: Start choose_background_action()") # DEBUG 7 - REMOVE
        if not self.backgrounds:
            print("No existing backgrounds. Creating a new one.")
            # print(f"DEBUG: Before calling create_new_background()") # DEBUG 8 - REMOVE
            self.create_new_background()
        else:
            self.dialog_mode = 'choose_bg_action'
            self.dialog_prompt = "Choose Background Action:"
            # --- Calculate positions --- Needed if creating buttons here
            dialog_center_x = config.EDITOR_WIDTH // 2
            dialog_center_y = config.EDITOR_HEIGHT // 2
            button_width = 150
            button_height = 40
            button_padding = 10
            new_button_y = dialog_center_y - button_height - button_padding // 2
            edit_button_y = dialog_center_y + button_padding // 2
            button_x = dialog_center_x - button_width // 2
            # --- UNCOMMENT AND SETUP DIALOG OPTIONS --- 
            self.dialog_options = [
                Button(pygame.Rect(button_x, new_button_y, button_width, button_height), "New", value="new"),
                Button(pygame.Rect(button_x, edit_button_y, button_width, button_height), "Edit Existing", value="edit")
            ]
            self.dialog_callback = self._handle_background_action_choice
        # print(f"DEBUG: End choose_background_action. dialog_mode={self.dialog_mode}") # DEBUG 9 - REMOVE

    def _handle_background_action_choice(self, action):
        """Callback after choosing background action."""
        print(f"Background action chosen: {action}")
        if action == 'new':
            self.create_new_background() # This sets dialog_mode = 'input_text'
            # Don't clear dialog state here, let the next step handle it
        elif action == 'edit' and self.backgrounds:
            self.current_background_index = 0
            self.current_background = self.backgrounds[self.current_background_index][1].copy()
            print(f"Editing background: {self.backgrounds[self.current_background_index][0]}")
            self.buttons = self.create_buttons() # Recreate buttons for the correct mode
            # --- ADD CLEARING LOGIC FOR EDIT BACKGROUND --- 
            self.dialog_mode = None 
            self.dialog_prompt = ""
            self.dialog_options = []
            self.dialog_callback = None
        else:
            print("Invalid action or no backgrounds to edit. Creating new.")
            self.create_new_background() # This sets dialog_mode = 'input_text'
            # Don't clear dialog state here

    def create_new_background(self):
        """
        Create a new background image.
        """
        # print(f"DEBUG: Start create_new_background()") # DEBUG 10 - REMOVE
        self.dialog_mode = 'input_text'
        # print(f"DEBUG: Set dialog_mode='{self.dialog_mode}' in create_new_background") # DEBUG 11 - REMOVE
        self.dialog_prompt = "Enter filename for new background (.png):"
        self.dialog_input_text = "new_background.png" # Default text
        self.dialog_input_active = True
        self.dialog_options = [
            Button(pygame.Rect(0,0, 100, 40), "Save", action=lambda: self._handle_dialog_choice(self.dialog_input_text)),
            Button(pygame.Rect(0,0, 100, 40), "Cancel", action=lambda: self._handle_dialog_choice(None))
        ]
        self.dialog_callback = self._create_new_background_callback
        # print(f"DEBUG: End create_new_background. dialog_mode={self.dialog_mode}") # DEBUG 12 - REMOVE

    def _create_new_background_callback(self, filename):
        """Callback after getting filename for new background."""
        # We don't clear dialog state here immediately, as _handle_dialog_choice handles cancel
        if filename:
            if not filename.endswith('.png'):
                filename += '.png'
            # Ensure filename is just the base name, save to BACKGROUND_DIR
            base_filename = os.path.basename(filename)
            full_path = os.path.join(config.BACKGROUND_DIR, base_filename)

            self.current_background = pygame.Surface((config.DEFAULT_BACKGROUND_WIDTH, config.DEFAULT_BACKGROUND_HEIGHT), pygame.SRCALPHA)
            self.current_background.fill((*config.WHITE, 255))  # Set to white with full opacity
            try:
                pygame.image.save(self.current_background, full_path)
                print(f"Saved background as {full_path}")
            except pygame.error as e:
                 print(f"Error saving new background {full_path}: {e}")
                 # Handle error, maybe show message? For now, just print.

            # Reload backgrounds to include the new one
            self.backgrounds = self.load_backgrounds()
            self.current_background_index = next(
                (i for i, (name, _) in enumerate(self.backgrounds) if name == base_filename),
                -1 # Should find it if save succeeded
            )
            # Ensure buttons are created/updated for the correct mode
            self.buttons = self.create_buttons()
            # --- ADD CLEARING LOGIC ON SUCCESS --- 
            self.dialog_mode = None 
            self.dialog_prompt = ""
            self.dialog_options = []
            self.dialog_callback = None
        else:
            print("New background creation cancelled.")
            # If cancellation happened during initial setup, decide what to do.
            # Maybe default to the first existing background or quit?
            # For now, just print. If edit_mode wasn't fully set, it might be unstable.
            if self.edit_mode == 'background' and self.current_background_index == -1:
                 print("Warning: No background loaded after cancellation.")
                 # Optionally load a default or the first available one
                 if self.backgrounds:
                      self.current_background_index = 0
                      self.current_background = self.backgrounds[0][1].copy()
                      self.buttons = self.create_buttons()
                 else:
                      # Handle case with absolutely no backgrounds - maybe quit or show error message
                      pass

    def save_background(self, filename=None):
        """
        Save the current background image.
        Uses Pygame input dialog if no filename provided or saving new.
        """
        current_filename = None
        # Corrected Indentation:
        if self.current_background_index >= 0 and self.backgrounds:
            current_filename = self.backgrounds[self.current_background_index][0]

        if not filename:
            # Use current filename if available, otherwise prompt
            filename_to_save = current_filename
            if not filename_to_save:
                 # Trigger input dialog for saving a potentially new file
                 self.dialog_mode = 'input_text'
                 self.dialog_prompt = "Enter filename to save background (.png):"
                 self.dialog_input_text = "background.png"
                 self.dialog_input_active = True
                 self.dialog_options = [
                     Button(pygame.Rect(0,0, 100, 40), "Save", action=lambda: self._handle_dialog_choice(self.dialog_input_text)),
                     Button(pygame.Rect(0,0, 100, 40), "Cancel", action=lambda: self._handle_dialog_choice(None))
                 ]
                 self.dialog_callback = self._save_background_callback
                 return # Exit function, wait for dialog callback
            else:
                 # If we have a current filename, save directly without dialog
                 self._save_background_callback(filename_to_save)
        else:
             # If a specific filename is passed (e.g., for "Save As"), use it
             # This might also need a dialog in a full implementation, but for now save directly
             print(f"Warning: Direct saving to specified filename '{filename}' without dialog.")
             self._save_background_callback(filename)

    def _save_background_callback(self, filename):
        """Callback after getting filename for saving background."""
        # We don't clear dialog state here immediately
        if filename:
            if not filename.endswith('.png'):
                filename += '.png'
            # Ensure filename is just the base name, save to BACKGROUND_DIR
            base_filename = os.path.basename(filename)
            full_path = os.path.join(config.BACKGROUND_DIR, base_filename)
            try:
                 pygame.image.save(self.current_background, full_path)
                 print(f"Saved background as {full_path}")
            except pygame.error as e:
                 print(f"Error saving background {full_path}: {e}")
                 return # Don't update index if save failed
                 
            # Reload and find index only after successful save
            self.backgrounds = self.load_backgrounds()
            self.current_background_index = next(
                (i for i, (name, _) in enumerate(self.backgrounds) if name == base_filename),
                -1 # Should be found
            )
            # Update buttons if needed (though likely already correct)
            self.buttons = self.create_buttons()
            # --- ADD CLEARING LOGIC ON SUCCESS --- 
            self.dialog_mode = None 
            self.dialog_prompt = ""
            self.dialog_options = []
            self.dialog_callback = None
        else:
            print("Background save cancelled.")

    def load_monster(self):
        """
        Load the current monster's sprites.

        This method loads the sprites for the currently selected monster. It updates
        the sprite frames and prints a status message.
        """
        try:
            # Ensure monsters list and index are valid
            if not hasattr(config, 'monsters') or not isinstance(config.monsters, list):
                print("Error: Monster data not loaded or invalid.")
                return
            if not (0 <= self.current_monster_index < len(config.monsters)):
                print(f"Error: current_monster_index {self.current_monster_index} out of range.")
                return

            monster_name = config.monsters[self.current_monster_index]['name']
            # Corrected Indentation:
            for sprite in self.sprites.values():
                sprite.load_sprite(monster_name) # Pass monster_name here
            print(f"Loaded monster: {monster_name}")
        except KeyError:
             print(f"Error: Monster data missing 'name' key at index {self.current_monster_index}.")
        except Exception as e:
             print(f"An unexpected error occurred during load_monster: {e}")

    def switch_sprite(self):
        """
        Switch between the front and back sprites.

        This method toggles between the front and back sprites for the current
        monster. It updates the current sprite and deactivates the selection.
        """
        self.current_sprite = 'back' if self.current_sprite == 'front' else 'front'
        print(f"Switched to sprite: {self.current_sprite}")
        self.selection.active = False  # Deactivate selection on sprite switch

    def previous_monster(self):
        """
        Switch to the previous monster in the list.

        This method decrements the current monster index and loads the previous
        monster's sprites. It prints a status message.
        """
        if self.current_monster_index > 0:
            self.current_monster_index -= 1
            self.load_monster()
            print(f"Switched to previous monster: {config.monsters[self.current_monster_index]['name']}")
        else:
            print("Already at the first monster.")

    def next_monster(self):
        """
        Switch to the next monster in the list.

        This method increments the current monster index and loads the next
        monster's sprites. It prints a status message.
        """
        # Ensure monsters list is loaded and valid
        if not hasattr(config, 'monsters') or not isinstance(config.monsters, list):
            print("Error: Monster data not loaded or invalid. Cannot switch.")
            return
        
        if self.current_monster_index < len(config.monsters) - 1:
            self.current_monster_index += 1
            self.load_monster()
            print(f"Switched to next monster: {config.monsters[self.current_monster_index].get('name', 'Unknown')}")
        else:
            print("Already at the last monster.")

    def _get_background_files(self):
        """Helper to get list of .png files in background directory."""
        try:
            return [f for f in os.listdir(config.BACKGROUND_DIR) if f.endswith('.png')]
        except FileNotFoundError:
            print(f"Warning: Background directory {config.BACKGROUND_DIR} not found.")
            return []

    def trigger_load_background_dialog(self):
        """Initiates the dialog for loading a background file."""
        # Ensure we are in background mode, otherwise this button shouldn't be active/visible
        if self.edit_mode != 'background':
            print("Load background only available in background edit mode.")
            return

        self.dialog_mode = 'load_bg'
        self.dialog_prompt = "Select Background to Load:"
        self.dialog_file_list = self._get_background_files() # Get the list of files
        self.dialog_file_scroll_offset = 0
        self.dialog_selected_file_index = -1

        # Define buttons for the dialog (Load and Cancel)
        # Actions will call _handle_dialog_choice with filename or None
        self.dialog_options = [
            # Buttons are positioned dynamically in draw_dialog
            Button(pygame.Rect(0, 0, 100, 40), "Load", action=lambda: self._handle_dialog_choice(
                self.dialog_file_list[self.dialog_selected_file_index] if 0 <= self.dialog_selected_file_index < len(self.dialog_file_list) else None
            )),
            Button(pygame.Rect(0, 0, 100, 40), "Cancel", action=lambda: self._handle_dialog_choice(None))
        ]
        self.dialog_callback = self._load_selected_background_callback

    def _load_selected_background_callback(self, filename):
        """Callback after selecting a background file to load."""
        # We don't clear dialog state here immediately
        if filename:
            full_path = os.path.join(config.BACKGROUND_DIR, filename)
            try:
                loaded_bg = pygame.image.load(full_path).convert_alpha()
                # Find the index in the self.backgrounds list (which contains Surfaces)
                found_index = -1
                for i, (name, _) in enumerate(self.backgrounds):
                    if name == filename:
                        found_index = i
                        break
                
                if found_index != -1:
                    self.current_background_index = found_index
                    self.current_background = self.backgrounds[found_index][1].copy() # Load from pre-loaded list
                    print(f"Loaded background: {filename}")
                else:
                    # If not found in pre-loaded list (shouldn't happen if list is up-to-date)
                    # Load it directly and add it (or maybe just load directly?)
                    self.current_background = loaded_bg
                    # Add to list if desired, or just use the directly loaded one
                    # For simplicity, let's just use the loaded one and reset index
                    self.backgrounds.append((filename, loaded_bg))
                    self.current_background_index = len(self.backgrounds) - 1
                    print(f"Loaded background {filename} directly.")
                
                # Reset undo/redo for the new background
                self.undo_stack = []
                self.redo_stack = []
                # Potentially save initial state for undo here if desired

            except pygame.error as e:
                print(f"Error loading background {full_path}: {e}")
            except FileNotFoundError:
                print(f"Error: Background file {full_path} not found.")
            # --- ADD CLEARING LOGIC ON SUCCESS --- 
            self.dialog_mode = None 
            self.dialog_prompt = ""
            self.dialog_options = []
            self.dialog_callback = None
        else:
            print("Background load cancelled.")

    def save_state(self):
        """Save the current state of the active canvas to the undo stack."""
        # Limit stack size if desired (optional)
        # if len(self.undo_stack) > MAX_UNDO_STEPS:
        #     self.undo_stack.pop(0)

        current_state = None
        if self.edit_mode == 'monster':
            sprite = self.sprites.get(self.current_sprite)
            if sprite:
                # Store a copy of the frame and which sprite it belongs to
                current_state = ('monster', self.current_sprite, sprite.frame.copy())
        elif self.edit_mode == 'background':
            if self.current_background:
                current_state = ('background', self.current_background_index, self.current_background.copy())

        if current_state:
            self.undo_stack.append(current_state)
            self.redo_stack.clear() # Clear redo stack on new action
            # print(f"State saved. Undo stack size: {len(self.undo_stack)}") # Debug
        # else: # Debug
            # print("Save state failed: No valid state to save.")

    def undo(self):
        """Revert to the previous state from the undo stack."""
        if not self.undo_stack:
            print("Nothing to undo.")
            return

        # Get the state to restore
        state_to_restore = self.undo_stack.pop()
        state_type, state_id, state_surface = state_to_restore

        # Save current state to redo stack BEFORE restoring
        current_state_for_redo = None
        if self.edit_mode == 'monster':
            sprite = self.sprites.get(self.current_sprite)
            if sprite:
                 current_state_for_redo = ('monster', self.current_sprite, sprite.frame.copy())
        elif self.edit_mode == 'background':
             if self.current_background:
                  current_state_for_redo = ('background', self.current_background_index, self.current_background.copy())
        
        if current_state_for_redo:
             self.redo_stack.append(current_state_for_redo)

        # Restore the popped state
        if state_type == 'monster':
            sprite = self.sprites.get(state_id)
            if sprite:
                sprite.frame = state_surface.copy() # Use copy to avoid issues
                # Ensure the editor is focused on the restored sprite if it changed
                self.current_sprite = state_id 
                self.edit_mode = 'monster' # Ensure mode is correct
                print(f"Undid action for sprite: {state_id}")
            else: # Corrected indent for this else
                 print(f"Undo failed: Could not find sprite editor '{state_id}' to restore state.")
                 # Put the state back on the undo stack? Or discard?
                 self.undo_stack.append(state_to_restore) # Re-add for now
                 # Check if redo_stack is not empty before popping
                 if self.redo_stack: self.redo_stack.pop() # Remove the state we just added
        elif state_type == 'background':
            self.current_background = state_surface.copy() # Use copy
            self.current_background_index = state_id # Restore index too
            self.edit_mode = 'background' # Ensure mode is correct
            print(f"Undid action for background index: {state_id}")
        else:
            print("Undo failed: Unknown state type in stack.")
            self.undo_stack.append(state_to_restore) # Re-add
            if self.redo_stack: self.redo_stack.pop() # Remove corresponding redo

        # Update buttons if mode changed
        self.buttons = self.create_buttons()

    def redo(self):
        """Reapply the last undone action from the redo stack."""
        if not self.redo_stack:
            print("Nothing to redo.")
            return

        # Get the state to restore from redo stack
        state_to_restore = self.redo_stack.pop()
        state_type, state_id, state_surface = state_to_restore

        # Save current state to undo stack BEFORE restoring
        current_state_for_undo = None
        if self.edit_mode == 'monster':
             sprite = self.sprites.get(self.current_sprite)
             if sprite:
                  current_state_for_undo = ('monster', self.current_sprite, sprite.frame.copy())
        elif self.edit_mode == 'background':
             if self.current_background:
                  current_state_for_undo = ('background', self.current_background_index, self.current_background.copy())

        if current_state_for_undo:
             self.undo_stack.append(current_state_for_undo)

        # Restore the popped state from redo stack
        if state_type == 'monster':
            sprite = self.sprites.get(state_id)
            if sprite:
                sprite.frame = state_surface.copy()
                self.current_sprite = state_id
                self.edit_mode = 'monster'
                print(f"Redid action for sprite: {state_id}")
            else:
                 print(f"Redo failed: Could not find sprite editor '{state_id}' to restore state.")
                 self.redo_stack.append(state_to_restore) # Re-add
                 self.undo_stack.pop() # Remove corresponding undo
        elif state_type == 'background':
            self.current_background = state_surface.copy()
            self.current_background_index = state_id
            self.edit_mode = 'background'
            print(f"Redid action for background index: {state_id}")
        else:
            print("Redo failed: Unknown state type in stack.")
            self.redo_stack.append(state_to_restore) # Re-add
            if self.undo_stack: self.undo_stack.pop() # Remove corresponding undo

        # Update buttons if mode changed
        self.buttons = self.create_buttons()

    def _get_sprite_editor_at_pos(self, pos):
        """Return the SpriteEditor instance at the given screen position, or None."""
        if self.edit_mode == 'monster':
            for name, sprite_editor in self.sprites.items():
                editor_rect = pygame.Rect(sprite_editor.position, (sprite_editor.display_width, sprite_editor.display_height))
                if editor_rect.collidepoint(pos):
                    return sprite_editor
        return None

    def handle_event(self, event):
        """Process a single Pygame event by delegating to the EventHandler."""
        return self.event_handler.process_event(event)

    def load_reference_image(self):
        """Opens a dialog to select a reference image, loads and scales it."""
        if not self._ensure_tkinter_root():
            # Message already printed by _ensure_tkinter_root
            return

        try:
            # Use the global tk_root directly
            file_path = filedialog.askopenfilename(
                parent=tk_root, # Explicitly set parent
                title="Select Reference Image",
                filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All Files", "*.*")]
            )
        except tk.TclError as e:
            print(f"Error opening file dialog: {e}")
            file_path = None
        except Exception as e: # Catch other potential errors
             print(f"Unexpected error during file dialog: {e}")
             file_path = None

        # Bring Pygame window back to focus might be needed here too if dialog issues persist

        if file_path and os.path.exists(file_path):
            try:
                self.reference_image = pygame.image.load(file_path).convert_alpha()
                self.reference_image_path = file_path
                print(f"Loaded reference image: {file_path}")
                self._scale_reference_image() 
                self.apply_reference_alpha() 
            except pygame.error as e:
                print(f"Error loading image {file_path}: {e}")
                self.reference_image = None
                self.reference_image_path = None
                self.scaled_reference_image = None
            except Exception as e: 
                print(f"An unexpected error occurred during reference image loading: {e}")
                self.reference_image = None
                self.reference_image_path = None
                self.scaled_reference_image = None
        else:
            # Only print cancel message if file_path was initially valid but selection was cancelled
            # Avoids printing cancel if the dialog itself failed to open
            if file_path is not None:
                 print("Reference image loading cancelled or file not found.")

    def _scale_reference_image(self):
        """Scales the loaded reference image using Aspect Fit (Option B)
           and prepares it for display behind the active editor."""
        if not self.reference_image:
            self.scaled_reference_image = None
            return

        # Target dimensions are the display size of the sprite editor grid
        # Use the 'front' sprite editor dimensions as reference (assuming both are same size)
        sprite_editor = self.sprites.get('front') # Get dimensions from one editor
        if not sprite_editor:
            print("Error: Cannot scale reference image, sprite editor 'front' not found.")
            self.scaled_reference_image = None
            return

        canvas_w = sprite_editor.display_width
        canvas_h = sprite_editor.display_height
        orig_w, orig_h = self.reference_image.get_size()

        if orig_w == 0 or orig_h == 0:
             print("Warning: Reference image has zero dimension. Cannot scale.")
             self.scaled_reference_image = None
             return

        # Calculate aspect fit scale
        scale_w = canvas_w / orig_w
        scale_h = canvas_h / orig_h
        scale = min(scale_w, scale_h)

        scaled_w = int(orig_w * scale)
        scaled_h = int(orig_h * scale)

        # Prevent scaling to zero size
        if scaled_w <= 0 or scaled_h <= 0:
             print("Warning: Calculated scaled size is zero or negative. Cannot scale.")
             self.scaled_reference_image = None
             return

        try:
            aspect_scaled_surf = pygame.transform.smoothscale(self.reference_image, (scaled_w, scaled_h))

            # Create the final surface matching canvas size, transparent background
            # This surface will have the scaled image centered on it.
            final_display_surf = pygame.Surface((canvas_w, canvas_h), pygame.SRCALPHA)
            final_display_surf.fill((0, 0, 0, 0)) # Fully transparent

            # Calculate centering position
            blit_x = (canvas_w - scaled_w) // 2
            blit_y = (canvas_h - scaled_h) // 2

            # Blit the aspect-scaled image onto the transparent canvas
            final_display_surf.blit(aspect_scaled_surf, (blit_x, blit_y))

            # Store this potentially un-alpha'd surface before applying alpha
            self.scaled_reference_image = final_display_surf

            # Apply the current alpha value (apply_reference_alpha will be called after this, or now)
            self.apply_reference_alpha() # Apply alpha immediately after scaling

        except pygame.error as e:
            print(f"Error during reference image scaling: {e}")
            self.scaled_reference_image = None
        except ValueError as e: # Catch potential issues with smoothscale (e.g., zero dimensions)
            print(f"Error during reference image scaling (ValueError): {e}")
            self.scaled_reference_image = None


    def clear_reference_image(self):
        """Removes the current reference image."""
        self.reference_image_path = None
        self.reference_image = None
        self.scaled_reference_image = None
        print("Reference image cleared.")

    def set_reference_alpha(self, alpha_value):
        """Sets the alpha value (0-255) for the reference image."""
        new_alpha = max(0, min(255, int(alpha_value))) # Clamp value
        if new_alpha != self.reference_alpha:
            self.reference_alpha = new_alpha
            #print(f"Set reference alpha to: {self.reference_alpha}") # Debug
            self.apply_reference_alpha()

    def apply_reference_alpha(self):
        """Applies the current alpha value to the scaled reference image surface."""
        # This logic needs refinement. set_alpha modifies the surface in-place.
        # We need to re-apply alpha if the base scaled image changes or alpha changes.
        # Let's re-scale if the reference_image exists but scaled is None
        if self.reference_image and not self.scaled_reference_image:
             self._scale_reference_image()
             # _scale_reference_image now calls apply_reference_alpha internally at the end
             return # Scaling handles alpha application

        # If scaled image exists, just set its alpha
        if self.scaled_reference_image:
            try:
                # Create a fresh scaled surface if it doesn't exist (should be handled above)
                # if not self.scaled_reference_image: self._scale_reference_image()
                # If still none, exit
                # if not self.scaled_reference_image: return

                # Apply alpha to the existing scaled surface
                self.scaled_reference_image.set_alpha(self.reference_alpha)

                # Update knob position based on new alpha
                slider_width = self.ref_alpha_slider_rect.width - self.ref_alpha_knob_rect.width
                # Ensure slider_width is not zero to avoid division error
                if slider_width > 0:
                    knob_x = self.ref_alpha_slider_rect.x + int((self.reference_alpha / 255) * slider_width)
                    self.ref_alpha_knob_rect.x = knob_x
                else: # Handle edge case where slider is too small
                    self.ref_alpha_knob_rect.x = self.ref_alpha_slider_rect.x

            except pygame.error as e:
                print(f"Error applying alpha to reference image: {e}")
            except AttributeError:
                 # Handle case where scaled_reference_image might be None unexpectedly
                 print("Warning: Tried to apply alpha but scaled_reference_image is None.")

    def set_subject_alpha(self, alpha_value):
        """Sets the alpha value (0-255) for the subject sprite being edited."""
        new_alpha = max(0, min(255, int(alpha_value))) # Clamp value
        if new_alpha != self.subject_alpha:
            self.subject_alpha = new_alpha
            # Update knob position
            slider_width = self.subj_alpha_slider_rect.width - self.subj_alpha_knob_rect.width
            if slider_width > 0:
                knob_x = self.subj_alpha_slider_rect.x + int((self.subject_alpha / 255) * slider_width)
                self.subj_alpha_knob_rect.x = knob_x
            else:
                self.subj_alpha_knob_rect.x = self.subj_alpha_slider_rect.x
            # No need to call apply_alpha here, draw_ui will use the value
            
    def draw_ui(self):
        """Draw the entire editor UI onto the screen."""
        screen.fill(config.EDITOR_BG_COLOR)
        # print(f"DEBUG: draw_ui start. self.dialog_mode = {self.dialog_mode}") # REMOVE EXCESSIVE PRINT

        # --- Draw Dialog FIRST if active --- 
        if self.dialog_mode:
            self.draw_dialog(screen)
            # Don't draw the rest of the UI while a dialog is fully obscuring it
            # (Except maybe a background blur/tint, already handled by draw_dialog overlay)
            return # Stop drawing here if a dialog is active

        # --- Draw Main UI (Only if no dialog active and mode is set) ---
        if self.edit_mode is None:
             # This state should ideally not persist after the initial dialog
             # If we reach here, something might be wrong with dialog flow
             # Maybe draw a "Loading..." or error message?
             loading_font = pygame.font.Font(config.DEFAULT_FONT, 30)
             loading_surf = loading_font.render("Waiting for mode selection...", True, config.BLACK)
             loading_rect = loading_surf.get_rect(center=screen.get_rect().center)
             screen.blit(loading_surf, loading_rect)
             return # Don't draw buttons etc. if mode not set

        # Draw based on mode
        if self.edit_mode == 'monster':
            # 1. Draw Editor Backgrounds (Checkerboards) for BOTH editors
            for sprite_editor in self.sprites.values():
                sprite_editor.draw_background(screen)

            # 2. Draw Reference Image (if active) behind the ACTIVE editor
            if self.scaled_reference_image:
                active_sprite_editor = self.sprites.get(self.current_sprite)
                if active_sprite_editor:
                    screen.blit(self.scaled_reference_image, active_sprite_editor.position)

            # 3. Draw Sprite Pixels for BOTH editors (on top of checkerboard and ref image)
            for name, sprite_editor in self.sprites.items():
                # --- Apply Subject Alpha --- 
                # Create a temporary surface with the subject alpha applied
                display_surface = sprite_editor.frame.copy() # Get the native sprite data
                # Scale it up first for display
                scaled_display_frame = pygame.transform.scale(display_surface, (sprite_editor.display_width, sprite_editor.display_height))
                # Apply the subject alpha to the scaled surface
                scaled_display_frame.set_alpha(self.subject_alpha) 
                # Blit the alpha-modified scaled surface
                screen.blit(scaled_display_frame, sprite_editor.position)
                # --- End Apply Subject Alpha ---
            
            # 4. Draw Highlight for the ACTIVE editor
            active_sprite_editor = self.sprites.get(self.current_sprite)
            if active_sprite_editor:
                active_sprite_editor.draw_highlight(screen, self.current_sprite) # Pass current_sprite

            # Draw Palette & Info Text (Existing)
            self.palette.draw(screen, self.current_color) # Pass current_color
            monster_name = config.monsters[self.current_monster_index].get('name', 'Unknown')
            info_text = f"Editing: {monster_name} ({self.current_sprite})" 
            info_surf = self.font.render(info_text, True, config.BLACK)
            screen.blit(info_surf, (50, 50))

        elif self.edit_mode == 'background':
            # Draw background canvas with zoom and pan
            if self.current_background:
                # 1. Calculate the scaled size of the full background image
                scaled_width = int(self.current_background.get_width() * self.editor_zoom)
                scaled_height = int(self.current_background.get_height() * self.editor_zoom)
                
                # Prevent scaling to zero size
                if scaled_width <= 0 or scaled_height <= 0:
                    print("Warning: Invalid zoom level resulting in zero size.")
                else:
                    # 2. Scale the original background to the zoomed size (consider performance for large images)
                    # Using pygame.transform.smoothscale might be slow; regular scale is faster for pixel art feel if needed.
                    zoomed_bg = pygame.transform.scale(self.current_background, (scaled_width, scaled_height))
                    
                    # 3. Define the source rect (area from zoomed_bg to display)
                    # Clamp view_offset to prevent scrolling beyond image boundaries
                    max_offset_x = max(0, scaled_width - self.canvas_rect.width)
                    max_offset_y = max(0, scaled_height - self.canvas_rect.height)
                    self.view_offset_x = max(0, min(self.view_offset_x, max_offset_x))
                    self.view_offset_y = max(0, min(self.view_offset_y, max_offset_y))
                    
                    source_rect = pygame.Rect(self.view_offset_x, self.view_offset_y, 
                                            self.canvas_rect.width, self.canvas_rect.height)
                                            
                    # 4. Blit the visible portion (source_rect) to the canvas destination rect
                    screen.blit(zoomed_bg, self.canvas_rect.topleft, source_rect)
            
            # Draw border around the canvas view area
            pygame.draw.rect(screen, config.BLACK, self.canvas_rect, 1) 
            
            # Draw Palette
            self.palette.draw(screen, self.current_color)
            # Draw Info Text
            bg_name = self.backgrounds[self.current_background_index][0] if self.current_background_index != -1 else "New BG"
            info_text = f"Editing BG: {bg_name} | Brush: {self.brush_size} | Zoom: {self.editor_zoom:.2f}x"
            info_surf = self.font.render(info_text, True, config.BLACK)
            screen.blit(info_surf, (50, 50))

        # Draw common elements (Buttons, Selection, Slider)
        if hasattr(self, 'buttons') and self.buttons:
             for button in self.buttons:
                  button.draw(screen)
        else:
             print("Warning: edit_mode is set but self.buttons not found in draw_ui")

        # Only draw selection if in monster mode and select mode is active
        if self.edit_mode == 'monster' and self.mode == 'select':
            active_sprite_editor = self.sprites.get(self.current_sprite)
            if active_sprite_editor: # Ensure we have the editor
                self.selection.draw(screen, active_sprite_editor.position)
            # else: # Optional: Handle case where current_sprite is somehow invalid
            #     print(f"Warning: Cannot draw selection, invalid current_sprite: {self.current_sprite}")

        # Draw Brush Size Slider (Existing)
        pygame.draw.rect(screen, config.GRAY_LIGHT, self.brush_slider)
        pygame.draw.rect(screen, config.BLACK, self.brush_slider, 1)
        # Draw brush size knob/indicator (if needed)
        # Add Label for Brush Slider <<<<<< NEW
        brush_text = f"Brush: {self.brush_size}"
        brush_surf = self.font.render(brush_text, True, config.BLACK)
        brush_rect = brush_surf.get_rect(midleft=(self.brush_slider.right + 10, self.brush_slider.centery))
        screen.blit(brush_surf, brush_rect)

        # --- Draw Reference Alpha Slider --- (Existing)
        # Draw slider track
        pygame.draw.rect(screen, config.GRAY_LIGHT, self.ref_alpha_slider_rect)
        pygame.draw.rect(screen, config.BLACK, self.ref_alpha_slider_rect, 1)
        # Draw slider knob
        pygame.draw.rect(screen, config.BLUE, self.ref_alpha_knob_rect) # Use a distinct color for knob
        # Draw alpha value text near slider
        alpha_text = f"Ref Alpha: {self.reference_alpha}"
        alpha_surf = self.font.render(alpha_text, True, config.BLACK)
        alpha_rect = alpha_surf.get_rect(midleft=(self.ref_alpha_slider_rect.right + 10, self.ref_alpha_slider_rect.centery))
        screen.blit(alpha_surf, alpha_rect)

        # --- Draw Subject Alpha Slider (only in monster mode) --- 
        if self.edit_mode == 'monster':
            # Draw slider track
            pygame.draw.rect(screen, config.GRAY_LIGHT, self.subj_alpha_slider_rect)
            pygame.draw.rect(screen, config.BLACK, self.subj_alpha_slider_rect, 1)
            # Draw slider knob
            pygame.draw.rect(screen, config.RED, self.subj_alpha_knob_rect) # Use a different color? Red for now
            # Draw alpha value text near slider
            subj_alpha_text = f"Subj Alpha: {self.subject_alpha}"
            subj_alpha_surf = self.font.render(subj_alpha_text, True, config.BLACK)
            subj_alpha_rect = subj_alpha_surf.get_rect(midleft=(self.subj_alpha_slider_rect.right + 10, self.subj_alpha_slider_rect.centery))
            screen.blit(subj_alpha_surf, subj_alpha_rect)
        
        # ... (draw dialog) ...

    def draw_dialog(self, surface):
        """Draws the current dialog box overlay."""
        # Placeholder - needs full implementation for different dialog types
        # Basic semi-transparent overlay
        overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        overlay.fill((*config.BLACK[:3], 180))
        surface.blit(overlay, (0, 0))

        # Simple box and prompt
        dialog_width = 400
        dialog_height = 300
        dialog_rect = pygame.Rect(0, 0, dialog_width, dialog_height)
        dialog_rect.center = surface.get_rect().center
        pygame.draw.rect(surface, config.WHITE, dialog_rect, border_radius=5)
        pygame.draw.rect(surface, config.BLACK, dialog_rect, 2, border_radius=5)

        prompt_surf = self.font.render(self.dialog_prompt, True, config.BLACK)
        prompt_rect = prompt_surf.get_rect(midtop=(dialog_rect.centerx, dialog_rect.top + 20))
        surface.blit(prompt_surf, prompt_rect)

        # Draw options (buttons) - needs proper layout
        button_y = prompt_rect.bottom + 30
        for i, option in enumerate(self.dialog_options):
             if isinstance(option, Button):
                  # REMOVED incorrect re-centering. Buttons have correct Rects already.
                  # option.rect.center = (dialog_rect.centerx, button_y + i * (option.rect.height + 10))
                  option.draw(surface) # Draw using the button's own Rect
        # Add rendering for other dialog elements (text input, file list, color picker)

    def run(self):
        """Main application loop."""
        running = True
        while running:
            # Event handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                self.handle_event(event) # Pass event to editor

            # Drawing
            self.draw_ui()

            # Update display
            pygame.display.flip()

            # Cap frame rate
            clock.tick(config.FPS)

        pygame.quit()

    # --- Add Panning Methods --- 
    def _pan_view(self, dx=0, dy=0):
        """Helper method to adjust view offset and clamp values."""
        if self.edit_mode != 'background':
            return
            
        self.view_offset_x += dx
        self.view_offset_y += dy

        # Clamp view offset
        if self.current_background:
            scaled_width = int(self.current_background.get_width() * self.editor_zoom)
            scaled_height = int(self.current_background.get_height() * self.editor_zoom)
            max_offset_x = max(0, scaled_width - self.canvas_rect.width)
            max_offset_y = max(0, scaled_height - self.canvas_rect.height)
            self.view_offset_x = max(0, min(self.view_offset_x, max_offset_x))
            self.view_offset_y = max(0, min(self.view_offset_y, max_offset_y))

    def pan_up(self):
        self._pan_view(dy=-config.PAN_SPEED_PIXELS)

    def pan_down(self):
        self._pan_view(dy=config.PAN_SPEED_PIXELS)

    def pan_left(self):
        self._pan_view(dx=-config.PAN_SPEED_PIXELS)

    def pan_right(self):
        self._pan_view(dx=config.PAN_SPEED_PIXELS)
    # --- End Panning Methods --- 

# Main execution block
if __name__ == "__main__":
    # --- Initialize Tkinter Root HERE --- 
    try:
        print("Attempting to initialize tk.Tk() for main execution...")
        tk_root = tk.Tk()
        tk_root.withdraw() # Hide the main window
        print("Main execution tk.Tk() initialized successfully.")
    except Exception as e:
        print(f"ERROR: Main execution Tkinter initialization failed: {e}")
        tkinter_error = e
    # --- End Tkinter Init --- 

    # Set up necessary directories if they don't exist
    # ... (directory setup code remains the same) ...
    if not os.path.exists(config.SPRITE_DIR):
        os.makedirs(config.SPRITE_DIR)
        print(f"Created missing directory: {config.SPRITE_DIR}")
    if not os.path.exists(config.BACKGROUND_DIR):
        os.makedirs(config.BACKGROUND_DIR)
        print(f"Created missing directory: {config.BACKGROUND_DIR}")
    if not os.path.exists(config.DATA_DIR):
         os.makedirs(config.DATA_DIR)
         print(f"Created missing directory: {config.DATA_DIR}")

    # Ensure monster data is loaded globally for the Editor
    # ... (monster loading code remains the same) ...
    if 'monsters' not in globals() or not monsters:
         print("Reloading monster data for main execution...")
         monsters = load_monsters() 
         if not monsters:
              print("Fatal: Could not load monster data. Exiting.")
              sys.exit(1)
    config.monsters = monsters 

    editor = Editor()
    editor.run()
