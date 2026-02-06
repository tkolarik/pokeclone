import argparse
import pygame
from pygame.locals import *
import tkinter as tk
from tkinter import filedialog, colorchooser
import os
from typing import Optional

# Import the centralized config
from src.core import config
from src.core.tileset import TileDefinition, TileSet, list_tileset_files, NPCSprite

# Import newly created modules
from src.core.event_handler import EventHandler
from src.editor.editor_ui import Button, Palette, PALETTE
from src.editor.editor_state import EditorState
from src.editor.dialog_manager import DialogManager
from src.editor.file_io import FileIOManager, load_monsters
from src.editor.selection_manager import SelectionTool
from src.editor.sprite_editor import SpriteEditor
from src.editor.tool_manager import ToolManager
from src.editor.undo_redo_manager import UndoRedoManager
from src.editor.clipboard_manager import ClipboardManager

NPC_STATES = ["standing", "walking"]
NPC_ANGLES = ["south", "west", "east", "north"]
PLAYER_NPC_ID = "player"
PLAYER_NPC_NAME = "Player"

# Tkinter root is initialized lazily to avoid import-time crashes during test discovery.
_tk_root_instance = None
_tk_init_error = None


def _get_tk_root():
    global _tk_root_instance, _tk_init_error
    if _tk_root_instance:
        return _tk_root_instance
    if _tk_init_error is not None:
        return None
    if os.environ.get("POKECLONE_DISABLE_TK", "").lower() in {"1", "true", "yes"}:
        _tk_init_error = RuntimeError("Tk disabled by POKECLONE_DISABLE_TK.")
        return None
    try:
        _tk_root_instance = tk.Tk()
        _tk_root_instance.withdraw()
        return _tk_root_instance
    except Exception as e:
        print(f"ERROR: Tkinter initialization failed: {e}")
        _tk_init_error = e
        _tk_root_instance = None
        return None

# Initialize Pygame Globally
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

    def __getattr__(self, name):
        state = self.__dict__.get("state")
        if state is not None and hasattr(state, name):
            return getattr(state, name)
        dialog_manager = self.__dict__.get("dialog_manager")
        if dialog_manager is not None and hasattr(dialog_manager.state, name):
            return getattr(dialog_manager.state, name)
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        state = self.__dict__.get("state")
        if state is not None and hasattr(state, name):
            setattr(state, name, value)
            return
        dialog_manager = self.__dict__.get("dialog_manager")
        if dialog_manager is not None and hasattr(dialog_manager.state, name):
            setattr(dialog_manager.state, name, value)
            return
        object.__setattr__(self, name, value)

    def __init__(self, monsters, skip_initial_dialog: bool = False):
        """
        Initialize a new Editor instance.
        """
        self.monsters = monsters if isinstance(monsters, list) else []
        self.state = EditorState()
        self.clipboard = ClipboardManager(config.CLIPBOARD_HISTORY_LIMIT, config.CLIPBOARD_FAVORITES_FILE)
        self.file_io = FileIOManager(self)
        self.undo_redo = UndoRedoManager(self)
        self.dialog_manager = DialogManager(self)
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
        self.backgrounds = self.file_io.load_backgrounds()
        self.current_background_index = 0 if self.backgrounds else -1
        self.edit_mode = None
        self.editor_zoom = 1.0
        self.view_offset_x = 0 
        self.view_offset_y = 0
        self.panning = False

        # --- Tile Mode State ---
        self.tile_set = None
        self.tile_canvas = SpriteEditor((50, 110), 'tile', config.TILE_IMAGE_DIR)
        self.current_tile_index = -1
        self.selected_tile_id = None
        self.tile_preview_cache = {}
        self.tile_list_scroll = 0
        panel_width = config.EDITOR_TILE_PANEL_WIDTH
        panel_x = (
            config.EDITOR_SIDE_BUTTON_START_X
            - panel_width
            - config.EDITOR_TILE_PANEL_GAP_FROM_BUTTONS
        )
        panel_height = config.EDITOR_HEIGHT - (
            config.EDITOR_TILE_PANEL_TOP + config.EDITOR_TILE_PANEL_BOTTOM_MARGIN
        )
        self.tile_panel_rect = pygame.Rect(panel_x, config.EDITOR_TILE_PANEL_TOP, panel_width, panel_height)
        self.tile_button_rects = []
        self.current_tile_frame_index = 0
        self.tile_frame_scroll = 0
        self.tile_frame_button_rects = []
        self.tile_frame_tray_rect = None
        self.tile_frame_scrollbar_rect = None
        self.tile_frame_scroll_thumb_rect = None
        self.tile_frame_dragging_scrollbar = False
        self.tile_frame_visible = 0
        self.asset_edit_target = 'tile'  # 'tile' or 'npc'
        self.tile_anim_last_tick = 0

        # NPC editing state
        self.npc_list_scroll = 0
        self.npc_button_rects = []
        self.selected_npc_id = None
        self.current_npc_state = "standing"
        self.current_npc_angle = "south"
        self.current_npc_frame_index = 0
        self.npc_state_scroll = 0
        self.npc_angle_scroll = 0
        self.npc_state_button_rects = []
        self.npc_angle_button_rects = []
        self.npc_state_tray_rect = None
        self.npc_angle_tray_rect = None
        self.npc_state_scrollbar_rect = None
        self.npc_state_scroll_thumb_rect = None
        self.npc_state_dragging_scrollbar = False
        self.npc_state_visible = 0
        self.npc_angle_scrollbar_rect = None
        self.npc_angle_scroll_thumb_rect = None
        self.npc_angle_dragging_scrollbar = False
        self.npc_angle_visible = 0

        # Instantiate the EventHandler
        self.event_handler = EventHandler(self)

        # Instantiate the ToolManager <<< NEW
        self.tool_manager = ToolManager(self)

        self.current_background = None
        self.canvas_rect = None

        self.buttons = [] # Start with empty buttons
        self.button_panel_rect = None
        self.button_panel_content_height = 0
        self.button_scroll_offset = 0
        self.button_scroll_max = 0
        self.button_scroll_step = 0
        self._button_panel_context = None
        self.button_scrollbar_rect = None
        self.button_scroll_thumb_rect = None

        self.font = pygame.font.Font(config.DEFAULT_FONT, config.EDITOR_INFO_FONT_SIZE)
        self.font_small = pygame.font.Font(config.DEFAULT_FONT, config.PALETTE_FONT_SIZE - 2)
        self.status_message = ""
        self.status_message_expire_tick = 0

        # --- Reference Image Attributes ---
        self.reference_image_path = None
        self.reference_image = None # Original loaded surface
        self.scaled_reference_image = None # Scaled and alpha-applied surface for display
        self.reference_alpha = 128 # Default alpha (50% opaque)
        self.adjusting_alpha = False # Flag for slider interaction
        self.subject_alpha = 255 # << Add subject alpha (fully opaque default)
        self.adjusting_subject_alpha = False # << Add flag for subject slider

        # --- Reference Image Panning/Scaling State ---
        self.ref_img_offset = pygame.Vector2(0, 0) # Pan offset (x, y)
        self.ref_img_scale = 1.0 # Scale factor

        # Slider layout (brush/ref/subject alpha)
        self._configure_sliders()

        self.tk_root = None # Initialize instance variable for Tkinter root
        self._load_clipboard_favorites()

        if not skip_initial_dialog:
            self.dialog_manager.choose_edit_mode() # Setup the initial dialog state

    def _ensure_tkinter_root(self):
        """Return a Tkinter root if available, otherwise None."""
        tk_root = _get_tk_root()
        if tk_root is None and _tk_init_error is not None:
            print(f"Tkinter root unavailable. Init error: {_tk_init_error}")
        return tk_root

    def _set_status(self, message, ttl_ms=2200):
        self.status_message = message or ""
        self.status_message_expire_tick = pygame.time.get_ticks() + max(0, int(ttl_ms))
        if message:
            print(message)

    def _set_draw_mode(self, eraser=False):
        self.mode = 'draw'
        self.selection.selecting = False
        self.tool_manager.set_active_tool('draw')
        self.paste_mode = False
        self.fill_mode = False
        self.eraser_mode = bool(eraser)

    def _set_fill_mode(self):
        self.mode = 'draw'
        self.selection.selecting = False
        self.selection.active = False
        self.tool_manager.set_active_tool('fill')
        self.fill_mode = True
        self.eraser_mode = False
        self.paste_mode = False

    def _set_paste_mode(self):
        self.mode = 'draw'
        self.selection.selecting = False
        self.tool_manager.set_active_tool('paste')
        self.fill_mode = False
        self.eraser_mode = False
        self.paste_mode = True

    def _enter_selection_mode(self):
        self.tool_manager.set_active_tool('draw')
        self.mode = 'select'
        self.selection.toggle()
        self.fill_mode = False
        self.eraser_mode = False
        self.paste_mode = False

    def _exit_selection_mode(self, clear_selection=False):
        self.mode = 'draw'
        self.selection.selecting = False
        if clear_selection:
            self.selection.active = False
        self.tool_manager.set_active_tool('draw')

    def cancel_paste_mode(self):
        if self.tool_manager.active_tool_name == 'paste' or self.paste_mode:
            self._set_draw_mode(eraser=False)
            self._set_status("Paste mode cancelled.")
            return True
        return False

    def _load_clipboard_favorites(self):
        loaded = self.clipboard.load_favorites()
        if loaded:
            self.copy_buffer = self.clipboard.get_active_pixels()
            self._set_status(f"Loaded {loaded} clipboard favorite(s).", ttl_ms=1500)

    def _save_clipboard_favorites(self):
        if not self.clipboard.save_favorites():
            self._set_status("Failed to save clipboard favorites.", ttl_ms=2400)

    def _push_clipboard(self, pixels, favorite=False):
        entry = self.clipboard.push(pixels=pixels, favorite=favorite)
        if entry:
            self.copy_buffer = self.clipboard.get_active_pixels()
        return entry

    def _activate_clipboard_entry(self, entry, activate_paste=False):
        if not entry:
            self._set_status("Clipboard is empty.")
            return False
        self.copy_buffer = self.clipboard.get_active_pixels()
        if activate_paste:
            self._set_paste_mode()
        label = "favorite" if entry.favorite else "history"
        self._set_status(
            f"Selected {label} clipboard item ({self.clipboard.active_index + 1}/{len(self.clipboard.history)}).",
            ttl_ms=1400,
        )
        return True

    def select_previous_clipboard_item(self):
        entry = self.clipboard.cycle(-1)
        self._activate_clipboard_entry(entry, activate_paste=False)

    def select_next_clipboard_item(self):
        entry = self.clipboard.cycle(1)
        self._activate_clipboard_entry(entry, activate_paste=False)

    def toggle_current_clipboard_favorite(self):
        entry = self.clipboard.toggle_active_favorite()
        if not entry:
            self._set_status("No clipboard item selected.")
            return
        self._save_clipboard_favorites()
        self.buttons = self.create_buttons()
        state = "favorited" if entry.favorite else "removed from favorites"
        self._set_status(f"Clipboard item {state}.", ttl_ms=1400)

    def _configure_sliders(self):
        slider_height = config.EDITOR_SLIDER_HEIGHT
        slider_gap = config.EDITOR_SLIDER_GAP
        bottom_padding = config.EDITOR_SLIDER_BOTTOM_PADDING
        ref_slider_y = config.EDITOR_HEIGHT - bottom_padding - (slider_height * 2 + slider_gap)
        ref_slider_x = config.EDITOR_REF_SLIDER_X
        ref_slider_width = config.EDITOR_REF_SLIDER_WIDTH
        brush_slider_x = config.EDITOR_BRUSH_SLIDER_X
        brush_slider_width = config.EDITOR_BRUSH_SLIDER_WIDTH

        self.brush_slider = pygame.Rect(brush_slider_x, ref_slider_y, brush_slider_width, slider_height)

        self.ref_alpha_slider_rect = pygame.Rect(ref_slider_x, ref_slider_y, ref_slider_width, slider_height)
        ref_knob_slider_width = self.ref_alpha_slider_rect.width - config.EDITOR_SLIDER_KNOB_WIDTH
        initial_ref_knob_x = self.ref_alpha_slider_rect.x + int((self.reference_alpha / 255) * ref_knob_slider_width)
        self.ref_alpha_knob_rect = pygame.Rect(initial_ref_knob_x, ref_slider_y, config.EDITOR_SLIDER_KNOB_WIDTH, slider_height)

        subj_slider_y = ref_slider_y + slider_height + slider_gap
        self.subj_alpha_slider_rect = pygame.Rect(ref_slider_x, subj_slider_y, ref_slider_width, slider_height)
        subj_knob_slider_width = self.subj_alpha_slider_rect.width - config.EDITOR_SLIDER_KNOB_WIDTH
        initial_subj_knob_x = self.subj_alpha_slider_rect.x + int((self.subject_alpha / 255) * subj_knob_slider_width)
        self.subj_alpha_knob_rect = pygame.Rect(initial_subj_knob_x, subj_slider_y, config.EDITOR_SLIDER_KNOB_WIDTH, slider_height)

    def choose_edit_mode(self):
        """
        Set up the dialog state to choose the editing mode (monster or background).
        The actual choice will be handled in the main loop via dialog state.
    
        Returns:
            None: Sets the initial dialog state instead of returning the mode directly.
        """
        self.dialog_manager.choose_edit_mode()

    def _set_edit_mode_and_continue(self, mode):
        """Callback after choosing edit mode."""
        # print(f"DEBUG: Start _set_edit_mode_and_continue(mode='{mode}')") # DEBUG 4 - REMOVE
        self.state.set_edit_mode(mode) # Set mode FIRST
        if mode == 'background':
            # --- Setup for Background Mode --- 
            self.canvas_rect = pygame.Rect(50, 100, config.DEFAULT_BACKGROUND_WIDTH, config.DEFAULT_BACKGROUND_HEIGHT)
            self.current_background = pygame.Surface(self.canvas_rect.size, pygame.SRCALPHA)
            self.current_background.fill(config.WHITE) # Default to white
            # --- End Setup ---
            # Now trigger the background action choice (new/edit)
            # print(f"DEBUG: Before calling choose_background_action()") # DEBUG 5 - REMOVE
            self.choose_background_action()
        elif mode == 'tile':
            self.setup_tile_mode()
        else: # Monster mode
            # If monster mode, initialization is complete
            # Clear potential background canvas rect
            self.canvas_rect = None
            self.current_background = None
            self.load_monster() # Ensure monster is loaded if chosen
            self.buttons = self.create_buttons() # Recreate buttons for the correct mode
            if self.reference_image:
                self._scale_reference_image()
            # --- ADD CLEARING LOGIC FOR MONSTER MODE --- 
            self.dialog_mode = None 
            self.dialog_prompt = ""
            self.dialog_options = []
            self.dialog_callback = None
        # print(f"DEBUG: End _set_edit_mode_and_continue. dialog_mode={self.dialog_mode}") # DEBUG 6 - REMOVE

    def setup_tile_mode(self):
        """Initialize tile editing state and load a tileset."""
        default_path = os.path.join(config.TILESET_DIR, f"{config.DEFAULT_TILESET_ID}.json")
        self.load_tileset(default_path if os.path.exists(default_path) else None)
        self.asset_edit_target = 'tile'
        self.buttons = self.create_buttons()
        if self.reference_image:
            self._scale_reference_image()
        self.dialog_mode = None
        self.dialog_prompt = ""
        self.dialog_options = []
        self.dialog_callback = None

    def load_tileset(self, path=None):
        """Load a tileset from disk or create a new one if none are found."""
        chosen_path = path
        if not chosen_path:
            files = list_tileset_files()
            if files:
                chosen_path = files[0]
        if chosen_path and os.path.exists(chosen_path):
            try:
                self.tile_set = TileSet.load(chosen_path)
                print(f"Loaded tileset: {os.path.basename(chosen_path)}")
            except Exception as e:
                print(f"Failed to load tileset {chosen_path}: {e}")
                self.tile_set = None
        if not self.tile_set:
            tileset_id = config.DEFAULT_TILESET_ID
            self.tile_set = TileSet(tileset_id, "New Tileset", config.OVERWORLD_TILE_SIZE)
            default_tile = TileDefinition(id="tile_01", name="Tile 01", filename="tile_01.png", frames=["tile_01.png"], properties={"walkable": True, "color": [180, 180, 180, 255]})
            self.tile_set.add_or_update_tile(default_tile)
            self.tile_set.ensure_assets()
            self.tile_set.save(os.path.join(config.TILESET_DIR, f"{tileset_id}.json"))
            print(f"Created default tileset at {os.path.join(config.TILESET_DIR, f'{tileset_id}.json')}")

        # Ensure we have at least one tile selected
        self.current_tile_index = 0 if self.tile_set.tiles else -1
        self.selected_tile_id = self.tile_set.tiles[0].id if self.tile_set.tiles else None
        self.current_tile_frame_index = 0
        self.selected_npc_id = self.tile_set.npcs[0].id if self.tile_set.npcs else None
        self.current_npc_state = NPC_STATES[0]
        self.current_npc_angle = NPC_ANGLES[0]
        self.current_npc_frame_index = 0
        self.tile_preview_cache = {}
        self.tile_list_scroll = 0
        self.npc_list_scroll = 0
        self.npc_button_rects = []
        self._load_current_tile_to_canvas()

    def _load_current_tile_to_canvas(self):
        """Load the currently selected tile image into the editing canvas."""
        self.tile_canvas.frame.fill((*config.BLACK[:3], 0))
        tile = self.current_tile()
        if not tile:
            return
        self.tile_set.ensure_assets()
        if not tile.frames:
            tile.frames = [tile.filename]
        if self.current_tile_frame_index >= len(tile.frames):
            self.current_tile_frame_index = 0
        path = self.tile_set.tile_image_path(tile, self.current_tile_frame_index)
        try:
            loaded = pygame.image.load(path).convert_alpha()
            if loaded.get_size() != config.NATIVE_SPRITE_RESOLUTION:
                loaded = pygame.transform.smoothscale(loaded, config.NATIVE_SPRITE_RESOLUTION)
            self.tile_canvas.frame.blit(loaded, (0, 0))
        except pygame.error as e:
            print(f"Error loading tile image {path}: {e}")

    def current_tile(self):
        if self.tile_set and 0 <= self.current_tile_index < len(self.tile_set.tiles):
            return self.tile_set.tiles[self.current_tile_index]
        return None

    def next_tile(self):
        if self.tile_set and self.tile_set.tiles:
            self.current_tile_index = (self.current_tile_index + 1) % len(self.tile_set.tiles)
            self.selected_tile_id = self.tile_set.tiles[self.current_tile_index].id
            self.current_tile_frame_index = 0
            self._load_current_tile_to_canvas()
            print(f"Selected tile: {self.selected_tile_id}")

    def previous_tile(self):
        if self.tile_set and self.tile_set.tiles:
            self.current_tile_index = (self.current_tile_index - 1) % len(self.tile_set.tiles)
            self.selected_tile_id = self.tile_set.tiles[self.current_tile_index].id
            self.current_tile_frame_index = 0
            self._load_current_tile_to_canvas()
            print(f"Selected tile: {self.selected_tile_id}")

    def next_tile_frame(self):
        tile = self.current_tile()
        if not tile or not tile.frames:
            return
        self.current_tile_frame_index = (self.current_tile_frame_index + 1) % len(tile.frames)
        self._load_current_tile_to_canvas()
        print(f"Tile '{tile.id}' frame {self.current_tile_frame_index + 1}/{len(tile.frames)}")

    def previous_tile_frame(self):
        tile = self.current_tile()
        if not tile or not tile.frames:
            return
        self.current_tile_frame_index = (self.current_tile_frame_index - 1) % len(tile.frames)
        self._load_current_tile_to_canvas()
        print(f"Tile '{tile.id}' frame {self.current_tile_frame_index + 1}/{len(tile.frames)}")

    def add_tile_frame(self):
        tile = self.current_tile()
        if not tile:
            print("No tile selected.")
            return
        if not tile.frames:
            tile.frames = [tile.filename]
        new_index = len(tile.frames) + 1
        new_frame_name = f"{tile.id}_f{new_index:02d}.png"
        tile.frames.append(new_frame_name)
        self.current_tile_frame_index = len(tile.frames) - 1
        self.tile_canvas.frame.fill((*config.BLACK[:3], 0))
        self.save_tile()  # save blank frame
        self.tile_set.ensure_assets()
        self._refresh_tile_previews()
        print(f"Added frame {self.current_tile_frame_index + 1} to tile '{tile.id}'")

    # --- NPC Editing ---
    def current_npc(self):
        if self.tile_set and self.tile_set.npcs and self.selected_npc_id:
            for npc in self.tile_set.npcs:
                if npc.id == self.selected_npc_id:
                    return npc
        return self.tile_set.npcs[0] if self.tile_set and self.tile_set.npcs else None

    def _ensure_npc_state_angle(self, npc: NPCSprite):
        npc.states.setdefault(self.current_npc_state, {})
        npc.states[self.current_npc_state].setdefault(self.current_npc_angle, [f"{npc.id}_{self.current_npc_state}_{self.current_npc_angle}.png"])

    def _ensure_player_npc(self) -> Optional[NPCSprite]:
        if not self.tile_set:
            print("No tileset loaded.")
            return None
        player_npc = None
        for npc in self.tile_set.npcs:
            if npc.id == PLAYER_NPC_ID:
                player_npc = npc
                break
        if not player_npc:
            player_npc = NPCSprite(id=PLAYER_NPC_ID, name=PLAYER_NPC_NAME, states={})
            # Keep player at the top of the list for quick access.
            self.tile_set.npcs.insert(0, player_npc)
        if not player_npc.name:
            player_npc.name = PLAYER_NPC_NAME
        for state in NPC_STATES:
            player_npc.states.setdefault(state, {})
            for angle in NPC_ANGLES:
                player_npc.states[state].setdefault(
                    angle,
                    [f"{PLAYER_NPC_ID}_{state}_{angle}.png"],
                )
        self.tile_set.ensure_assets()
        return player_npc

    def edit_player_sprite(self):
        player_npc = self._ensure_player_npc()
        if not player_npc:
            return
        self.selected_npc_id = player_npc.id
        self.current_npc_state = NPC_STATES[0]
        self.current_npc_angle = NPC_ANGLES[0]
        self.current_npc_frame_index = 0
        self._load_current_npc_frame()
        print("Selected player sprite for editing.")

    def _load_current_npc_frame(self):
        self.tile_canvas.frame.fill((*config.BLACK[:3], 0))
        if not self.tile_set:
            return
        npc = self.current_npc()
        if not npc:
            return
        self._ensure_npc_state_angle(npc)
        frames = npc.states[self.current_npc_state][self.current_npc_angle]
        if not frames:
            frames.append(f"{npc.id}_{self.current_npc_state}_{self.current_npc_angle}.png")
        if self.current_npc_frame_index >= len(frames):
            self.current_npc_frame_index = 0
        path = self.tile_set.npc_image_path(npc, self.current_npc_state, self.current_npc_angle, self.current_npc_frame_index)
        try:
            loaded = pygame.image.load(path).convert_alpha()
            if loaded.get_size() != config.NATIVE_SPRITE_RESOLUTION:
                loaded = pygame.transform.smoothscale(loaded, config.NATIVE_SPRITE_RESOLUTION)
            self.tile_canvas.frame.blit(loaded, (0, 0))
        except pygame.error as e:
            print(f"Error loading NPC frame {path}: {e}")

    def save_npc_frame(self):
        npc = self.current_npc()
        if not npc:
            print("No NPC selected.")
            return
        self._ensure_npc_state_angle(npc)
        frames = npc.states[self.current_npc_state][self.current_npc_angle]
        if not frames:
            frames.append(f"{npc.id}_{self.current_npc_state}_{self.current_npc_angle}.png")
        if self.current_npc_frame_index >= len(frames):
            self.current_npc_frame_index = 0
        path = self.tile_set.npc_image_path(npc, self.current_npc_state, self.current_npc_angle, self.current_npc_frame_index)
        try:
            pygame.image.save(self.tile_canvas.frame, path)
            print(f"Saved NPC '{npc.id}' state {self.current_npc_state} angle {self.current_npc_angle} frame {self.current_npc_frame_index+1}")
        except pygame.error as e:
            print(f"Error saving NPC frame: {e}")

    def add_npc_frame(self):
        npc = self.current_npc()
        if not npc:
            print("No NPC selected.")
            return
        self._ensure_npc_state_angle(npc)
        frames = npc.states[self.current_npc_state][self.current_npc_angle]
        new_index = len(frames) + 1
        new_name = f"{npc.id}_{self.current_npc_state}_{self.current_npc_angle}_f{new_index:02d}.png"
        frames.append(new_name)
        self.current_npc_frame_index = len(frames) - 1
        self.tile_canvas.frame.fill((*config.BLACK[:3], 0))
        self.save_npc_frame()
        print(f"Added NPC frame {self.current_npc_frame_index+1} for {npc.id}")

    def next_npc(self):
        if not self.tile_set or not self.tile_set.npcs:
            return
        ids = [n.id for n in self.tile_set.npcs]
        if self.selected_npc_id not in ids:
            self.selected_npc_id = ids[0]
        else:
            idx = ids.index(self.selected_npc_id)
            self.selected_npc_id = ids[(idx + 1) % len(ids)]
        self.current_npc_frame_index = 0
        self._load_current_npc_frame()
        print(f"Selected NPC: {self.selected_npc_id}")

    def previous_npc(self):
        if not self.tile_set or not self.tile_set.npcs:
            return
        ids = [n.id for n in self.tile_set.npcs]
        if self.selected_npc_id not in ids:
            self.selected_npc_id = ids[0]
        else:
            idx = ids.index(self.selected_npc_id)
            self.selected_npc_id = ids[(idx - 1) % len(ids)]
        self.current_npc_frame_index = 0
        self._load_current_npc_frame()
        print(f"Selected NPC: {self.selected_npc_id}")

    def next_npc_frame(self):
        npc = self.current_npc()
        if not npc:
            return
        frames = npc.states.get(self.current_npc_state, {}).get(self.current_npc_angle, [])
        if not frames:
            return
        self.current_npc_frame_index = (self.current_npc_frame_index + 1) % len(frames)
        self._load_current_npc_frame()

    def previous_npc_frame(self):
        npc = self.current_npc()
        if not npc:
            return
        frames = npc.states.get(self.current_npc_state, {}).get(self.current_npc_angle, [])
        if not frames:
            return
        self.current_npc_frame_index = (self.current_npc_frame_index - 1) % len(frames)
        self._load_current_npc_frame()

    def set_npc_state(self, state: str):
        if state not in NPC_STATES:
            return
        self.current_npc_state = state
        self.current_npc_frame_index = 0
        self._load_current_npc_frame()

    def set_npc_angle(self, angle: str):
        if angle not in NPC_ANGLES:
            return
        self.current_npc_angle = angle
        self.current_npc_frame_index = 0
        self._load_current_npc_frame()

    def start_new_npc_dialog(self):
        self.dialog_mode = 'input_text'
        self.dialog_prompt = "Enter new NPC ID:"
        count = len(self.tile_set.npcs) + 1 if self.tile_set else 1
        self.dialog_input_text = f"npc_{count:02d}"
        self.dialog_input_active = True
        self.dialog_options = [
            Button(pygame.Rect(0,0, 100, 40), "Create", action=lambda: self._handle_dialog_choice(self.dialog_input_text)),
            Button(pygame.Rect(0,0, 100, 40), "Cancel", action=lambda: self._handle_dialog_choice(None))
        ]
        self.dialog_callback = self._create_npc_from_dialog

    def _create_npc_from_dialog(self, npc_id):
        if not npc_id:
            print("NPC creation cancelled.")
            return
        npc_id = npc_id.strip()
        if not npc_id:
            print("NPC id cannot be empty.")
            return
        if any(n.id == npc_id for n in self.tile_set.npcs):
            print(f"NPC '{npc_id}' already exists.")
            self.selected_npc_id = npc_id
            self.dialog_mode = None
            self.dialog_callback = None
            self.dialog_options = []
            return
        npc = NPCSprite(id=npc_id, name=npc_id, states={
            "standing": {
                "south": [f"{npc_id}_standing_south.png"]
            }
        })
        self.tile_set.add_or_update_npc(npc)
        self.tile_set.ensure_assets()
        self.selected_npc_id = npc_id
        self.current_npc_state = "standing"
        self.current_npc_angle = "south"
        self.current_npc_frame_index = 0
        self._load_current_npc_frame()
        self.buttons = self.create_buttons()
        self.dialog_mode = None
        self.dialog_callback = None
        self.dialog_options = []
        print(f"Created NPC '{npc_id}'")

    def _ensure_tile_preview(self, tile: TileDefinition):
        """Cache a small preview surface for the tile manager list."""
        if tile.id in self.tile_preview_cache:
            return
        self.tile_set.ensure_assets()
        preview_size = 48
        previews = []
        frames = tile.frames or [tile.filename]
        for idx in range(len(frames)):
            path = self.tile_set.tile_image_path(tile, idx)
            try:
                surf = pygame.image.load(path).convert_alpha()
            except pygame.error:
                surf = pygame.Surface((self.tile_set.tile_size, self.tile_set.tile_size), pygame.SRCALPHA)
                surf.fill((*config.RED, 255))
            previews.append(pygame.transform.scale(surf, (preview_size, preview_size)))
        self.tile_preview_cache[tile.id] = previews

    def _refresh_tile_previews(self):
        self.tile_preview_cache = {}
        if not self.tile_set:
            return
        for tile in self.tile_set.tiles:
            self._ensure_tile_preview(tile)

    def save_tileset(self):
        if not self.tile_set:
            print("No tileset loaded.")
            return
        path = self.tile_set.save()
        print(f"Saved tileset to {path}")

    def save_tile(self):
        tile = self.current_tile()
        if not tile:
            print("No tile selected to save.")
            return
        self.tile_set.ensure_assets()
        if not tile.frames:
            tile.frames = [tile.filename]
        if self.current_tile_frame_index >= len(tile.frames):
            self.current_tile_frame_index = 0
        path = self.tile_set.tile_image_path(tile, self.current_tile_frame_index)
        try:
            pygame.image.save(self.tile_canvas.frame, path)
            print(f"Saved tile '{tile.id}' to {path}")
            self._ensure_tile_preview(tile)
        except pygame.error as e:
            print(f"Error saving tile {tile.id}: {e}")

    def start_new_tile_dialog(self):
        """Prompt for a new tile id and create the tile."""
        self.dialog_mode = 'input_text'
        self.dialog_prompt = "Enter new tile ID:"
        next_id = len(self.tile_set.tiles) + 1 if self.tile_set else 1
        self.dialog_input_text = f"tile_{next_id:02d}"
        self.dialog_input_active = True
        self.dialog_options = [
            Button(pygame.Rect(0,0, 100, 40), "Create", action=lambda: self._handle_dialog_choice(self.dialog_input_text)),
            Button(pygame.Rect(0,0, 100, 40), "Cancel", action=lambda: self._handle_dialog_choice(None))
        ]
        self.dialog_callback = self._create_tile_from_dialog

    def _create_tile_from_dialog(self, tile_id):
        if not tile_id:
            print("Tile creation cancelled.")
            return
        tile_id = tile_id.strip()
        if not tile_id:
            print("Tile id cannot be empty.")
            return
        if self.tile_set.get_tile(tile_id):
            print(f"Tile '{tile_id}' already exists. Selecting existing tile.")
            self.select_tile_by_id(tile_id)
            self.dialog_mode = None
            self.dialog_callback = None
            self.dialog_options = []
            return
        filename = f"{tile_id}.png"
        new_tile = TileDefinition(id=tile_id, name=tile_id, filename=filename, frames=[filename], properties={"walkable": True, "color": [200, 200, 200, 255]})
        self.tile_set.add_or_update_tile(new_tile)
        self.tile_set.ensure_assets()
        self.current_tile_index = len(self.tile_set.tiles) - 1
        self.selected_tile_id = new_tile.id
        self.tile_canvas.frame.fill((*config.BLACK[:3], 0))
        self.save_tile() # Save blank tile so it exists on disk
        self._refresh_tile_previews()
        self.buttons = self.create_buttons()
        self.dialog_mode = None
        self.dialog_callback = None
        self.dialog_options = []
        print(f"Created new tile '{tile_id}'")

    def start_new_tileset_dialog(self):
        """Prompt for a new tileset id and initialize it."""
        self.dialog_mode = 'input_text'
        self.dialog_prompt = "Enter new tileset ID:"
        self.dialog_input_text = "tileset"
        self.dialog_input_active = True
        self.dialog_options = [
            Button(pygame.Rect(0,0, 100, 40), "Create", action=lambda: self._handle_dialog_choice(self.dialog_input_text)),
            Button(pygame.Rect(0,0, 100, 40), "Cancel", action=lambda: self._handle_dialog_choice(None))
        ]
        self.dialog_callback = self._create_tileset_from_dialog

    def _create_tileset_from_dialog(self, tileset_id):
        if not tileset_id:
            print("Tileset creation cancelled.")
            return
        tileset_id = tileset_id.strip()
        if not tileset_id:
            print("Tileset id cannot be empty.")
            return
        self.tile_set = TileSet(tileset_id, tileset_id, config.OVERWORLD_TILE_SIZE)
        starter_tile = TileDefinition(id="tile_01", name="Tile 01", filename="tile_01.png", frames=["tile_01.png"], properties={"walkable": True, "color": [180, 180, 180, 255]})
        self.tile_set.add_or_update_tile(starter_tile)
        self.tile_set.ensure_assets()
        self.tile_set.save(os.path.join(config.TILESET_DIR, f"{tileset_id}.json"))
        self.current_tile_index = 0
        self.selected_tile_id = starter_tile.id
        self.tile_canvas.frame.fill((*config.BLACK[:3], 0))
        self.save_tile()
        self._refresh_tile_previews()
        self.buttons = self.create_buttons()
        self.dialog_mode = None
        self.dialog_callback = None
        self.dialog_options = []
        print(f"Created new tileset '{tileset_id}'")

    def toggle_tile_walkable(self):
        tile = self.current_tile()
        if not tile:
            print("No tile selected.")
            return
        current = bool(tile.properties.get("walkable", True))
        tile.properties["walkable"] = not current
        state = "walkable" if tile.properties["walkable"] else "blocked"
        print(f"Tile '{tile.id}' marked as {state}.")

    def select_tile_by_id(self, tile_id):
        if not self.tile_set:
            return
        for idx, tile in enumerate(self.tile_set.tiles):
            if tile.id == tile_id:
                self.current_tile_index = idx
                self.selected_tile_id = tile_id
                self.current_tile_frame_index = 0
                self._load_current_tile_to_canvas()
                return

    def draw_tile_panel(self, surface):
        """Render the tile manager panel with previews."""
        if not self.tile_set:
            return
        panel = self.tile_panel_rect
        pygame.draw.rect(surface, config.GRAY_LIGHT, panel)
        pygame.draw.rect(surface, config.BLACK, panel, 1)
        header_font = pygame.font.Font(config.DEFAULT_FONT, 18)
        header = header_font.render(self.tile_set.name, True, config.BLACK)
        surface.blit(header, (panel.x + 8, panel.y + 6))

        start_y = panel.y + 30
        tray_height = 110
        list_height = panel.height - tray_height - 20
        item_height = 60
        visible = max(1, list_height // item_height)
        total_tiles = len(self.tile_set.tiles)
        self.tile_list_scroll = max(0, min(self.tile_list_scroll, max(0, total_tiles - visible)))
        self.tile_button_rects = []

        for row, idx in enumerate(range(self.tile_list_scroll, min(total_tiles, self.tile_list_scroll + visible))):
            tile = self.tile_set.tiles[idx]
            self._ensure_tile_preview(tile)
            item_rect = pygame.Rect(panel.x + 8, start_y + row * item_height, panel.width - 16, item_height - 8)
            is_selected = tile.id == self.selected_tile_id
            pygame.draw.rect(surface, config.WHITE if is_selected else config.GRAY_MEDIUM, item_rect)
            pygame.draw.rect(surface, config.BLACK, item_rect, 1)
            previews = self.tile_preview_cache.get(tile.id, [])
            if previews:
                ticks = pygame.time.get_ticks()
                frame_idx = (ticks // max(1, tile.frame_duration_ms)) % len(previews)
                surface.blit(previews[frame_idx], (item_rect.x + 4, item_rect.y + 6))
            name_surf = self.font.render(tile.name, True, config.BLACK)
            id_text = tile.id
            if tile.properties.get("type"):
                id_text += f" ({tile.properties.get('type')})"
            id_surf = self.font.render(id_text, True, config.BLUE if is_selected else config.BLACK)
            surface.blit(name_surf, (item_rect.x + 60, item_rect.y + 8))
            surface.blit(id_surf, (item_rect.x + 60, item_rect.y + 30))
            self.tile_button_rects.append((item_rect, tile.id))

        self._draw_tile_frame_tray(surface, pygame.Rect(panel.x + 8, panel.bottom - tray_height, panel.width - 16, tray_height - 8))

    def handle_tile_panel_click(self, pos):
        if not self.tile_set or not self.tile_panel_rect.collidepoint(pos):
            return False
        if self.tile_frame_tray_rect and self.tile_frame_tray_rect.collidepoint(pos):
            if self.tile_frame_scrollbar_rect and self.tile_frame_scrollbar_rect.collidepoint(pos):
                frames = self.current_tile().frames if self.current_tile() else []
                if self.tile_frame_scroll_thumb_rect and self.tile_frame_scroll_thumb_rect.collidepoint(pos):
                    self.tile_frame_dragging_scrollbar = True
                thumb_height = self.tile_frame_scroll_thumb_rect.height if self.tile_frame_scroll_thumb_rect else 20
                self.tile_frame_scroll = self._set_tray_scroll_from_thumb(
                    pos[1],
                    len(frames),
                    self.tile_frame_visible,
                    self.tile_frame_scrollbar_rect,
                    thumb_height,
                )
                return True
            margin = 10
            if pos[1] < self.tile_frame_tray_rect.y + margin and self.tile_frame_scroll > 0:
                self.tile_frame_scroll -= 1
                return True
            frames = self.current_tile().frames if self.current_tile() else []
            if pos[1] > self.tile_frame_tray_rect.bottom - margin and self.tile_frame_scroll < max(0, len(frames) - 1):
                self.tile_frame_scroll += 1
                return True
        # frame tray click
        for rect, frame_index in self.tile_frame_button_rects:
            if rect.collidepoint(pos):
                self.current_tile_frame_index = frame_index
                self._load_current_tile_to_canvas()
                return True
        for rect, tile_id in self.tile_button_rects:
            if rect.collidepoint(pos):
                self.select_tile_by_id(tile_id)
                print(f"Selected tile: {tile_id}")
                return True
        # Handle simple scroll if clicked at top/bottom margins
        margin = 20
        if pos[1] < self.tile_panel_rect.y + margin and self.tile_list_scroll > 0:
            self.tile_list_scroll -= 1
            return True
        if pos[1] > self.tile_panel_rect.bottom - margin and self.tile_list_scroll < max(0, len(self.tile_set.tiles) - 1):
            self.tile_list_scroll += 1
            return True
        return False

    def scroll_tile_panel(self, direction, pos):
        """Handle mouse wheel scrolling for tile/NPC panels."""
        if self.edit_mode != 'tile' or not self.tile_panel_rect or not self.tile_panel_rect.collidepoint(pos):
            return False
        if self.asset_edit_target == 'tile':
            if self.tile_frame_tray_rect and self.tile_frame_tray_rect.collidepoint(pos):
                return self._scroll_tile_frames(direction)
            return self._scroll_tile_list(direction)
        if self.npc_state_tray_rect and self.npc_state_tray_rect.collidepoint(pos):
            return self._scroll_npc_states(direction)
        if self.npc_angle_tray_rect and self.npc_angle_tray_rect.collidepoint(pos):
            return self._scroll_npc_angles(direction)
        return self._scroll_npc_list(direction)

    def _scroll_tile_list(self, direction):
        if not self.tile_set:
            return False
        tray_height = 110
        list_height = self.tile_panel_rect.height - tray_height - 20
        item_height = 60
        visible = max(1, list_height // item_height)
        max_scroll = max(0, len(self.tile_set.tiles) - visible)
        if max_scroll <= 0:
            return False
        delta = -1 if direction > 0 else 1
        new_scroll = max(0, min(self.tile_list_scroll + delta, max_scroll))
        if new_scroll == self.tile_list_scroll:
            return False
        self.tile_list_scroll = new_scroll
        return True

    def _scroll_tile_frames(self, direction):
        tile = self.current_tile()
        if not tile or not self.tile_frame_tray_rect:
            return False
        frames = tile.frames or []
        if not frames:
            return False
        visible = self.tile_frame_visible
        if visible <= 0:
            item_size = 48
            padding = 6
            usable_width = self.tile_frame_tray_rect.width - 12
            cols = max(1, usable_width // (item_size + padding))
            rows_visible = max(1, (self.tile_frame_tray_rect.height - 30) // (item_size + padding))
            visible = cols * rows_visible
        max_scroll = max(0, len(frames) - visible)
        if max_scroll <= 0:
            return False
        delta = -1 if direction > 0 else 1
        new_scroll = max(0, min(self.tile_frame_scroll + delta, max_scroll))
        if new_scroll == self.tile_frame_scroll:
            return False
        self.tile_frame_scroll = new_scroll
        return True

    def draw_npc_panel(self, surface):
        """Render NPC list and basic info."""
        if not self.tile_set:
            return
        panel = self.tile_panel_rect
        pygame.draw.rect(surface, config.GRAY_LIGHT, panel)
        pygame.draw.rect(surface, config.BLACK, panel, 1)
        header_font = pygame.font.Font(config.DEFAULT_FONT, 18)
        header = header_font.render("NPC Sprites", True, config.BLACK)
        surface.blit(header, (panel.x + 8, panel.y + 6))

        start_y = panel.y + 30
        tray_height = 160
        list_height = panel.height - tray_height - 20
        item_height = 60
        visible = max(1, list_height // item_height)
        total = len(self.tile_set.npcs)
        self.npc_list_scroll = max(0, min(self.npc_list_scroll, max(0, total - visible)))
        self.npc_button_rects = []

        for row, idx in enumerate(range(self.npc_list_scroll, min(total, self.npc_list_scroll + visible))):
            npc = self.tile_set.npcs[idx]
            item_rect = pygame.Rect(panel.x + 8, start_y + row * item_height, panel.width - 16, item_height - 8)
            is_selected = npc.id == self.selected_npc_id
            pygame.draw.rect(surface, config.WHITE if is_selected else config.GRAY_MEDIUM, item_rect)
            pygame.draw.rect(surface, config.BLACK, item_rect, 1)
            # preview: load first available frame
            preview = None
            for state_dict in npc.states.values():
                for angle_frames in state_dict.values():
                    if angle_frames:
                        path = self.tile_set.npc_image_path(npc, self.current_npc_state if self.current_npc_state in npc.states else list(npc.states.keys())[0],
                                                            self.current_npc_angle if self.current_npc_angle in state_dict else list(state_dict.keys())[0], 0)
                        try:
                            surf = pygame.image.load(path).convert_alpha()
                            preview = pygame.transform.scale(surf, (48, 48))
                        except pygame.error:
                            pass
                        break
                if preview:
                    break
            if preview:
                surface.blit(preview, (item_rect.x + 4, item_rect.y + 6))
            name_surf = self.font.render(npc.name, True, config.BLACK)
            id_surf = self.font.render(npc.id, True, config.BLUE if is_selected else config.BLACK)
            surface.blit(name_surf, (item_rect.x + 60, item_rect.y + 8))
            surface.blit(id_surf, (item_rect.x + 60, item_rect.y + 30))
            self.npc_button_rects.append((item_rect, npc.id))

        tray_top = panel.bottom - tray_height
        state_rect = pygame.Rect(panel.x + 8, tray_top, panel.width - 16, 70)
        angle_rect = pygame.Rect(panel.x + 8, tray_top + 80, panel.width - 16, 70)
        self._draw_npc_state_tray(surface, state_rect)
        self._draw_npc_angle_tray(surface, angle_rect)

    def handle_npc_panel_click(self, pos):
        if not self.tile_set or not self.tile_panel_rect.collidepoint(pos):
            return False
        if self.npc_state_tray_rect and self.npc_state_tray_rect.collidepoint(pos):
            if self.npc_state_scrollbar_rect and self.npc_state_scrollbar_rect.collidepoint(pos):
                states = list(self.current_npc().states.keys()) if self.current_npc() else []
                if self.npc_state_scroll_thumb_rect and self.npc_state_scroll_thumb_rect.collidepoint(pos):
                    self.npc_state_dragging_scrollbar = True
                thumb_height = self.npc_state_scroll_thumb_rect.height if self.npc_state_scroll_thumb_rect else 20
                self.npc_state_scroll = self._set_tray_scroll_from_thumb(
                    pos[1],
                    len(states),
                    self.npc_state_visible,
                    self.npc_state_scrollbar_rect,
                    thumb_height,
                )
                return True
            margin = 10
            states = list(self.current_npc().states.keys()) if self.current_npc() else []
            if pos[1] < self.npc_state_tray_rect.y + margin and self.npc_state_scroll > 0:
                self.npc_state_scroll -= 1
                return True
            if pos[1] > self.npc_state_tray_rect.bottom - margin and self.npc_state_scroll < max(0, len(states) - 1):
                self.npc_state_scroll += 1
                return True
        if self.npc_angle_tray_rect and self.npc_angle_tray_rect.collidepoint(pos):
            if self.npc_angle_scrollbar_rect and self.npc_angle_scrollbar_rect.collidepoint(pos):
                angles = list(self.current_npc().states.get(self.current_npc_state, {}).keys()) if self.current_npc() else []
                if self.npc_angle_scroll_thumb_rect and self.npc_angle_scroll_thumb_rect.collidepoint(pos):
                    self.npc_angle_dragging_scrollbar = True
                thumb_height = self.npc_angle_scroll_thumb_rect.height if self.npc_angle_scroll_thumb_rect else 20
                self.npc_angle_scroll = self._set_tray_scroll_from_thumb(
                    pos[1],
                    len(angles),
                    self.npc_angle_visible,
                    self.npc_angle_scrollbar_rect,
                    thumb_height,
                )
                return True
            margin = 10
            angles = list(self.current_npc().states.get(self.current_npc_state, {}).keys()) if self.current_npc() else []
            if pos[1] < self.npc_angle_tray_rect.y + margin and self.npc_angle_scroll > 0:
                self.npc_angle_scroll -= 1
                return True
            if pos[1] > self.npc_angle_tray_rect.bottom - margin and self.npc_angle_scroll < max(0, len(angles) - 1):
                self.npc_angle_scroll += 1
                return True
        for rect, state_name in self.npc_state_button_rects:
            if rect.collidepoint(pos):
                self.set_npc_state(state_name)
                return True
        for rect, angle_name in self.npc_angle_button_rects:
            if rect.collidepoint(pos):
                self.set_npc_angle(angle_name)
                return True
        for rect, npc_id in self.npc_button_rects:
            if rect.collidepoint(pos):
                self.selected_npc_id = npc_id
                self.current_npc_frame_index = 0
                self._load_current_npc_frame()
                print(f"Selected NPC: {npc_id}")
                return True
        margin = 20
        if pos[1] < self.tile_panel_rect.y + margin and self.npc_list_scroll > 0:
            self.npc_list_scroll -= 1
            return True
        if pos[1] > self.tile_panel_rect.bottom - margin and self.npc_list_scroll < max(0, len(self.tile_set.npcs) - 1):
            self.npc_list_scroll += 1
            return True
        return False

    def _draw_tile_frame_tray(self, surface, tray_rect):
        tile = self.current_tile()
        self.tile_frame_button_rects = []
        self.tile_frame_tray_rect = tray_rect
        self.tile_frame_scrollbar_rect = None
        self.tile_frame_scroll_thumb_rect = None
        self.tile_frame_visible = 0
        if not tile:
            return
        pygame.draw.rect(surface, config.GRAY_DARK, tray_rect)
        pygame.draw.rect(surface, config.BLACK, tray_rect, 1)
        label = self.font.render("Frames", True, config.WHITE)
        surface.blit(label, (tray_rect.x + 6, tray_rect.y + 4))
        frames = tile.frames or []
        if not frames:
            return
        item_size = 48
        padding = 6
        start_x = tray_rect.x + 6
        start_y = tray_rect.y + 24
        usable_width = tray_rect.width - 12
        cols = max(1, usable_width // (item_size + padding))
        rows_visible = max(1, (tray_rect.height - 30) // (item_size + padding))
        visible = cols * rows_visible
        if len(frames) > visible:
            scrollbar_width = 8
            usable_width = max(1, usable_width - scrollbar_width - padding)
            cols = max(1, usable_width // (item_size + padding))
            visible = cols * rows_visible
        self.tile_frame_visible = visible
        self.tile_frame_scroll = max(0, min(self.tile_frame_scroll, max(0, len(frames) - visible)))
        for idx in range(self.tile_frame_scroll, min(len(frames), self.tile_frame_scroll + visible)):
            row = (idx - self.tile_frame_scroll) // cols
            col = (idx - self.tile_frame_scroll) % cols
            rect = pygame.Rect(
                start_x + col * (item_size + padding),
                start_y + row * (item_size + padding),
                item_size,
                item_size,
            )
            is_selected = idx == self.current_tile_frame_index
            pygame.draw.rect(surface, config.WHITE if is_selected else config.GRAY_MEDIUM, rect)
            pygame.draw.rect(surface, config.BLACK, rect, 1)
            try:
                path = self.tile_set.tile_image_path(tile, idx)
                preview = pygame.image.load(path).convert_alpha()
                preview = pygame.transform.scale(preview, (item_size - 6, item_size - 6))
                surface.blit(preview, (rect.x + 3, rect.y + 3))
            except pygame.error:
                pass
            self.tile_frame_button_rects.append((rect, idx))
        content_top = tray_rect.y + 24
        self.tile_frame_scrollbar_rect, self.tile_frame_scroll_thumb_rect = self._make_tray_scrollbar(
            tray_rect,
            content_top,
            len(frames),
            visible,
            self.tile_frame_scroll,
        )
        if self.tile_frame_scrollbar_rect:
            pygame.draw.rect(surface, config.GRAY_MEDIUM, self.tile_frame_scrollbar_rect)
            if self.tile_frame_scroll_thumb_rect:
                pygame.draw.rect(surface, config.GRAY_DARK, self.tile_frame_scroll_thumb_rect)

    def _draw_npc_state_tray(self, surface, tray_rect):
        npc = self.current_npc()
        self.npc_state_button_rects = []
        self.npc_state_tray_rect = tray_rect
        self.npc_state_scrollbar_rect = None
        self.npc_state_scroll_thumb_rect = None
        self.npc_state_visible = 0
        if not npc:
            return
        pygame.draw.rect(surface, config.GRAY_DARK, tray_rect)
        pygame.draw.rect(surface, config.BLACK, tray_rect, 1)
        label = self.font.render("States", True, config.WHITE)
        surface.blit(label, (tray_rect.x + 6, tray_rect.y + 4))
        states = list(npc.states.keys())
        if not states:
            return
        item_height = 28
        start_y = tray_rect.y + 24
        visible = max(1, (tray_rect.height - 24) // item_height)
        if len(states) > visible:
            visible_width = tray_rect.width - 12 - 8
        else:
            visible_width = tray_rect.width - 12
        self.npc_state_visible = visible
        self.npc_state_scroll = max(0, min(self.npc_state_scroll, max(0, len(states) - visible)))
        for row, idx in enumerate(range(self.npc_state_scroll, min(len(states), self.npc_state_scroll + visible))):
            state = states[idx]
            rect = pygame.Rect(tray_rect.x + 6, start_y + row * item_height, visible_width, item_height - 4)
            is_selected = state == self.current_npc_state
            pygame.draw.rect(surface, config.WHITE if is_selected else config.GRAY_MEDIUM, rect)
            pygame.draw.rect(surface, config.BLACK, rect, 1)
            text = self.font.render(state, True, config.BLUE if is_selected else config.BLACK)
            surface.blit(text, (rect.x + 6, rect.y + 4))
            self.npc_state_button_rects.append((rect, state))
        content_top = tray_rect.y + 24
        self.npc_state_scrollbar_rect, self.npc_state_scroll_thumb_rect = self._make_tray_scrollbar(
            tray_rect,
            content_top,
            len(states),
            visible,
            self.npc_state_scroll,
        )
        if self.npc_state_scrollbar_rect:
            pygame.draw.rect(surface, config.GRAY_MEDIUM, self.npc_state_scrollbar_rect)
            if self.npc_state_scroll_thumb_rect:
                pygame.draw.rect(surface, config.GRAY_DARK, self.npc_state_scroll_thumb_rect)

    def _draw_npc_angle_tray(self, surface, tray_rect):
        npc = self.current_npc()
        self.npc_angle_button_rects = []
        self.npc_angle_tray_rect = tray_rect
        self.npc_angle_scrollbar_rect = None
        self.npc_angle_scroll_thumb_rect = None
        self.npc_angle_visible = 0
        if not npc:
            return
        pygame.draw.rect(surface, config.GRAY_DARK, tray_rect)
        pygame.draw.rect(surface, config.BLACK, tray_rect, 1)
        label = self.font.render("Angles", True, config.WHITE)
        surface.blit(label, (tray_rect.x + 6, tray_rect.y + 4))
        angles = list(npc.states.get(self.current_npc_state, {}).keys())
        if not angles:
            return
        item_size = 48
        padding = 6
        start_x = tray_rect.x + 6
        start_y = tray_rect.y + 24
        usable_width = tray_rect.width - 12
        cols = max(1, usable_width // (item_size + padding))
        rows_visible = max(1, (tray_rect.height - 30) // (item_size + padding))
        visible = cols * rows_visible
        if len(angles) > visible:
            scrollbar_width = 8
            usable_width = max(1, usable_width - scrollbar_width - padding)
            cols = max(1, usable_width // (item_size + padding))
            visible = cols * rows_visible
        self.npc_angle_visible = visible
        self.npc_angle_scroll = max(0, min(self.npc_angle_scroll, max(0, len(angles) - visible)))
        for idx in range(self.npc_angle_scroll, min(len(angles), self.npc_angle_scroll + visible)):
            row = (idx - self.npc_angle_scroll) // cols
            col = (idx - self.npc_angle_scroll) % cols
            angle = angles[idx]
            rect = pygame.Rect(start_x + col * (item_size + padding), start_y + row * (item_size + padding), item_size, item_size)
            is_selected = angle == self.current_npc_angle
            pygame.draw.rect(surface, config.WHITE if is_selected else config.GRAY_MEDIUM, rect)
            pygame.draw.rect(surface, config.BLACK, rect, 1)
            # preview
            frames = npc.states.get(self.current_npc_state, {}).get(angle, [])
            if frames:
                try:
                    path = self.tile_set.npc_image_path(npc, self.current_npc_state, angle, 0)
                    preview = pygame.image.load(path).convert_alpha()
                    preview = pygame.transform.scale(preview, (item_size - 6, item_size - 6))
                    surface.blit(preview, (rect.x + 3, rect.y + 3))
                except pygame.error:
                    pass
            text = self.font_small.render(angle[0].upper(), True, config.BLACK)
            surface.blit(text, (rect.x + 2, rect.y + 2))
            self.npc_angle_button_rects.append((rect, angle))
        content_top = tray_rect.y + 24
        self.npc_angle_scrollbar_rect, self.npc_angle_scroll_thumb_rect = self._make_tray_scrollbar(
            tray_rect,
            content_top,
            len(angles),
            visible,
            self.npc_angle_scroll,
        )
        if self.npc_angle_scrollbar_rect:
            pygame.draw.rect(surface, config.GRAY_MEDIUM, self.npc_angle_scrollbar_rect)
            if self.npc_angle_scroll_thumb_rect:
                pygame.draw.rect(surface, config.GRAY_DARK, self.npc_angle_scroll_thumb_rect)

    def _scroll_npc_list(self, direction):
        if not self.tile_set or not self.tile_panel_rect:
            return False
        tray_height = 160
        list_height = self.tile_panel_rect.height - tray_height - 20
        item_height = 60
        visible = max(1, list_height // item_height)
        max_scroll = max(0, len(self.tile_set.npcs) - visible)
        if max_scroll <= 0:
            return False
        delta = -1 if direction > 0 else 1
        new_scroll = max(0, min(self.npc_list_scroll + delta, max_scroll))
        if new_scroll == self.npc_list_scroll:
            return False
        self.npc_list_scroll = new_scroll
        return True

    def _scroll_npc_states(self, direction):
        npc = self.current_npc()
        if not npc or not self.npc_state_tray_rect:
            return False
        states = list(npc.states.keys())
        if not states:
            return False
        item_height = 28
        visible = max(1, (self.npc_state_tray_rect.height - 24) // item_height)
        max_scroll = max(0, len(states) - visible)
        if max_scroll <= 0:
            return False
        delta = -1 if direction > 0 else 1
        new_scroll = max(0, min(self.npc_state_scroll + delta, max_scroll))
        if new_scroll == self.npc_state_scroll:
            return False
        self.npc_state_scroll = new_scroll
        return True

    def _scroll_npc_angles(self, direction):
        npc = self.current_npc()
        if not npc or not self.npc_angle_tray_rect:
            return False
        angles = list(npc.states.get(self.current_npc_state, {}).keys())
        if not angles:
            return False
        visible = self.npc_angle_visible
        if visible <= 0:
            item_size = 48
            padding = 6
            usable_width = self.npc_angle_tray_rect.width - 12
            cols = max(1, usable_width // (item_size + padding))
            rows_visible = max(1, (self.npc_angle_tray_rect.height - 30) // (item_size + padding))
            visible = cols * rows_visible
        max_scroll = max(0, len(angles) - visible)
        if max_scroll <= 0:
            return False
        delta = -1 if direction > 0 else 1
        new_scroll = max(0, min(self.npc_angle_scroll + delta, max_scroll))
        if new_scroll == self.npc_angle_scroll:
            return False
        self.npc_angle_scroll = new_scroll
        return True

    def set_asset_edit_target(self, target: str):
        if target not in ['tile', 'npc']:
            return
        if self.asset_edit_target != target:
            self.asset_edit_target = target
            if target == 'tile':
                self._load_current_tile_to_canvas()
            else:
                if not self.selected_npc_id and self.tile_set and self.tile_set.npcs:
                    self.selected_npc_id = self.tile_set.npcs[0].id
                self._load_current_npc_frame()
            self.buttons = self.create_buttons()

    def _handle_dialog_choice(self, value):
        """Internal handler for dialog button values or direct calls."""
        self.dialog_manager._handle_dialog_choice(value)

    def refocus_pygame_window(self):
        """
        Refocus the Pygame window - REMOVED as Tkinter is gone.
        """
        # pygame.display.iconify() - REMOVED
        # pygame.display.set_mode((config.EDITOR_WIDTH, config.EDITOR_HEIGHT)) - REMOVED
        # print("Editor window refocused.") - REMOVED
        pass # No longer needed

    def _button_panel_context_key(self):
        return (self.edit_mode, getattr(self, "asset_edit_target", None))

    def _apply_button_scroll(self, buttons):
        for button in buttons:
            if hasattr(button, "base_rect"):
                button.rect = button.base_rect.move(0, -self.button_scroll_offset)

    def _set_button_scroll_offset(self, buttons, offset):
        if self.button_scroll_max <= 0:
            self.button_scroll_offset = 0
            self._apply_button_scroll(buttons)
            return False
        clamped = max(0, min(offset, self.button_scroll_max))
        if clamped == self.button_scroll_offset:
            return False
        self.button_scroll_offset = clamped
        self._apply_button_scroll(buttons)
        return True

    def _configure_button_panel(self, buttons, start_x, start_y, button_width, button_height, padding):
        context = self._button_panel_context_key()
        if context != self._button_panel_context:
            self.button_scroll_offset = 0
            self._button_panel_context = context

        bottom_limit = None
        if isinstance(getattr(self, "brush_slider", None), pygame.Rect):
            bottom_limit = self.brush_slider.top - config.EDITOR_PANEL_PADDING
        if bottom_limit is None:
            bottom_limit = config.EDITOR_HEIGHT - (config.EDITOR_SLIDER_HEIGHT * 3)
        panel_height = max(0, bottom_limit - start_y)
        self.button_panel_rect = pygame.Rect(start_x, start_y, button_width, panel_height)
        self.button_scroll_step = button_height + padding

        if buttons:
            last_bottom = max(button.base_rect.bottom for button in buttons)
            self.button_panel_content_height = last_bottom - start_y
        else:
            self.button_panel_content_height = 0

        self.button_scroll_max = max(0, self.button_panel_content_height - panel_height)
        self._set_button_scroll_offset(buttons, self.button_scroll_offset)

    def scroll_button_panel(self, pos, direction):
        if not isinstance(getattr(self, "button_panel_rect", None), pygame.Rect):
            return False
        if not self.button_panel_rect.collidepoint(pos):
            return False
        if self.button_scroll_max <= 0:
            return False
        step = self.button_scroll_step or 1
        new_offset = self.button_scroll_offset - (direction * step)
        return self._set_button_scroll_offset(self.buttons, new_offset)

    def _draw_button_panel(self, surface):
        if not self.buttons:
            return
        if not isinstance(getattr(self, "button_panel_rect", None), pygame.Rect):
            for button in self.buttons:
                button.draw(surface)
            return

        panel_rect = self.button_panel_rect
        pygame.draw.rect(surface, config.GRAY_LIGHT, panel_rect)
        pygame.draw.rect(surface, config.BLACK, panel_rect, 1)

        prior_clip = surface.get_clip()
        surface.set_clip(panel_rect)
        for button in self.buttons:
            if panel_rect.colliderect(button.rect):
                button.draw(surface)
        surface.set_clip(prior_clip)

        if self.button_scroll_max > 0:
            track_width = 4
            track_rect = pygame.Rect(panel_rect.right + 1, panel_rect.top + 2, track_width, panel_rect.height - 4)
            pygame.draw.rect(surface, config.GRAY_LIGHT, track_rect)
            thumb_height = max(20, int(track_rect.height * (panel_rect.height / self.button_panel_content_height)))
            max_thumb_travel = max(1, track_rect.height - thumb_height)
            thumb_y = track_rect.top
            if self.button_scroll_max > 0:
                thumb_y = track_rect.top + int((self.button_scroll_offset / self.button_scroll_max) * max_thumb_travel)
            self.button_scrollbar_rect = track_rect
            self.button_scroll_thumb_rect = pygame.Rect(track_rect.x, thumb_y, track_rect.width, thumb_height)
            pygame.draw.rect(surface, config.GRAY_MEDIUM, self.button_scroll_thumb_rect)

    def create_buttons(self):
        """
        Create the buttons for the editor UI.

        This method creates the buttons for the editor UI based on the current
        edit mode. It returns a list of Button instances.

        Returns:
            list: A list of Button instances.
        """
        buttons = []
        button_width = config.EDITOR_SIDE_BUTTON_WIDTH
        button_height = config.EDITOR_SIDE_BUTTON_HEIGHT
        padding = config.EDITOR_SIDE_BUTTON_PADDING
        start_x = config.EDITOR_SIDE_BUTTON_START_X
        start_y = config.EDITOR_SIDE_BUTTON_START_Y
        def _tool_active(name):
            tool_manager = getattr(self, "tool_manager", None)
            return tool_manager is not None and tool_manager.active_tool_name == name
        def _clipboard_active():
            return len(self.clipboard.history) > 0

        active_predicates = {
            "Eyedropper": lambda: _tool_active("eyedropper"),
            "Fill": lambda: _tool_active("fill"),
            "Paste": lambda: _tool_active("paste"),
            "Select": lambda: self.mode == "select",
            "Eraser": lambda: _tool_active("draw") and self.eraser_mode,
            "Hist Prev": _clipboard_active,
            "Hist Next": _clipboard_active,
            "Fav Clip": lambda: (
                bool(self.clipboard.get_active_entry()) and bool(self.clipboard.get_active_entry().favorite)
            ),
            "Cancel Paste": lambda: _tool_active("paste"),
            "Edit Tiles": lambda: self.edit_mode == "tile" and self.asset_edit_target == "tile",
            "Edit NPCs": lambda: self.edit_mode == "tile" and self.asset_edit_target == "npc",
        }

        shared_buttons = [
            ("Clear", self.clear_current),
            ("Color Picker", self.open_color_picker),
            ("Eyedropper", self.activate_eyedropper),
            ("Eraser", self.toggle_eraser),
            ("Fill", self.toggle_fill),
            ("Select", self.toggle_selection_mode),
            ("Copy", self.copy_selection),
            ("Paste", self.paste_selection),
            ("Hist Prev", self.select_previous_clipboard_item),
            ("Hist Next", self.select_next_clipboard_item),
            ("Fav Clip", self.toggle_current_clipboard_favorite),
            ("Mirror", self.mirror_selection),
            ("Rotate", self.rotate_selection),
            ("Cancel Paste", self.cancel_paste_mode),
            ("Undo", self.undo),
            ("Redo", self.redo),
        ]

        mode_buttons = []
        if self.edit_mode == 'monster':
            mode_buttons = [
                ("Save Sprites", self.save_current_monster_sprites),
                ("Prev Monster", self.previous_monster),
                ("Next Monster", self.next_monster),
                ("Switch Sprite", self.switch_sprite),
                ("Load Ref Img", self.load_reference_image),
                ("Clear Ref Img", self.clear_reference_image),
                ("Import Ref", self.import_reference_to_canvas),
            ]
        elif self.edit_mode == 'background':
            mode_buttons = [
                ("Save BG", self.save_background),
                ("Load BG", self.trigger_load_background_dialog),
                ("Zoom In", self.zoom_in),
                ("Zoom Out", self.zoom_out),
                ("Brush +", self.increase_brush_size),
                ("Brush -", self.decrease_brush_size),
                ("Prev BG", self.previous_background),
                ("Next BG", self.next_background),
                ("Pan Up", self.pan_up),
                ("Pan Down", self.pan_down),
                ("Pan Left", self.pan_left),
                ("Pan Right", self.pan_right),
            ]
        elif self.edit_mode == 'tile':
            switch_buttons = [
                ("Edit Tiles", lambda: self.set_asset_edit_target('tile')),
                ("Edit NPCs", lambda: self.set_asset_edit_target('npc')),
            ]
            if self.asset_edit_target == 'tile':
                mode_buttons = [
                    ("Save Tile", self.save_tile),
                    ("Save Tileset", self.save_tileset),
                    ("Load Tileset", self.trigger_load_tileset_dialog),
                    ("Load Ref Img", self.load_reference_image),
                    ("Clear Ref Img", self.clear_reference_image),
                    ("Import Ref", self.import_reference_to_canvas),
                    ("New Tile", self.start_new_tile_dialog),
                    ("New Tileset", self.start_new_tileset_dialog),
                    ("Toggle Walk", self.toggle_tile_walkable),
                    ("Brush +", self.increase_brush_size),
                    ("Brush -", self.decrease_brush_size),
                    ("Prev Tile", self.previous_tile),
                    ("Next Tile", self.next_tile),
                    ("Prev Frame", self.previous_tile_frame),
                    ("Next Frame", self.next_tile_frame),
                    ("Add Frame", self.add_tile_frame),
                ]
            else:
                mode_buttons = [
                    ("Save Tileset", self.save_tileset),
                    ("Save NPC", self.save_npc_frame),
                    ("Load Tileset", self.trigger_load_tileset_dialog),
                    ("Load Ref Img", self.load_reference_image),
                    ("Clear Ref Img", self.clear_reference_image),
                    ("Import Ref", self.import_reference_to_canvas),
                    ("Edit Player", self.edit_player_sprite),
                    ("New NPC", self.start_new_npc_dialog),
                    ("Prev NPC", self.previous_npc),
                    ("Next NPC", self.next_npc),
                    ("Prev Frame", self.previous_npc_frame),
                    ("Next Frame", self.next_npc_frame),
                    ("Add Frame", self.add_npc_frame),
                ]
            mode_buttons = switch_buttons + mode_buttons
        else:
            mode_buttons = [("Save", lambda: print("Save disabled."))]

        all_buttons = mode_buttons + shared_buttons

        for i, (text, action) in enumerate(all_buttons):
            rect = (start_x, start_y + i * (button_height + padding), button_width, button_height)
            buttons.append(Button(rect, text, action, is_active=active_predicates.get(text)))

        self._configure_button_panel(buttons, start_x, start_y, button_width, button_height, padding)
        return buttons

    def save_current_monster_sprites(self):
        """Saves both front and back sprites for the current monster."""
        try:
            # Ensure monsters list and index are valid
            if not isinstance(self.monsters, list) or not self.monsters:
                print("Error: Monster data not loaded or invalid. Cannot save.")
                return
            if not (0 <= self.current_monster_index < len(self.monsters)):
                print(f"Error: current_monster_index {self.current_monster_index} out of range. Cannot save.")
                return

            monster_name = self.monsters[self.current_monster_index].get('name')
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
        elif self.edit_mode == 'tile':
            self.tile_canvas.frame.fill((*config.BLACK[:3], 0))
            print("Cleared current tile.")
        else:
            print(f"Warning: Unknown edit mode '{self.edit_mode}' for clear operation.")

    def toggle_eraser(self):
        """Toggle eraser mode using centralized tool-state transitions."""
        enable_eraser = not (self.tool_manager.active_tool_name == 'draw' and self.eraser_mode)
        self._set_draw_mode(eraser=enable_eraser)
        self._set_status(f"Eraser {'enabled' if enable_eraser else 'disabled'}.", ttl_ms=1200)

    def toggle_fill(self):
        """Activate fill tool."""
        self._set_fill_mode()
        self._set_status("Fill tool enabled.", ttl_ms=1200)

    def toggle_selection_mode(self):
        """Toggle selection mode with explicit transitions."""
        if self.mode == 'select':
            self._exit_selection_mode(clear_selection=False)
            self._set_status("Switched to draw mode.", ttl_ms=1200)
        else:
            self._enter_selection_mode()
            self._set_status("Switched to selection mode.", ttl_ms=1200)

    def copy_selection(self):
        """Copy the selected pixels to the buffer."""
        if self.selection.active:
            sprite_editor = self.get_active_canvas()
            if not sprite_editor:
                self._set_status("Copy failed: No active canvas.")
                return

            self.copy_buffer = self.selection.get_selected_pixels(sprite_editor)
            if self.copy_buffer:
                entry = self._push_clipboard(self.copy_buffer, favorite=False)
                if entry:
                    self._set_status(f"Copied {len(self.copy_buffer)} pixels.", ttl_ms=1200)
                    self.buttons = self.create_buttons()
            else:
                self._set_status("Copy failed: Selection is empty.")
        else:
            self._set_status("Copy failed: No active selection.")

    def paste_selection(self):
        """Activate paste mode with the buffered pixels."""
        if self.copy_buffer:
            self._set_paste_mode()
            self._set_status("Paste mode active. Click canvas to place. Esc to cancel.", ttl_ms=1800)
        else:
            self._set_status("Paste failed: Clipboard is empty.")

    def mirror_selection(self):
        """Mirror the selected pixels horizontally in-place."""
        if not self.selection.active:
            self._set_status("Mirror failed: make a selection first.")
            return

        sprite_editor = self.get_active_canvas()
        if not sprite_editor:
            self._set_status("Mirror failed: active canvas not found.")
            return

        self.save_state() # Save state before modifying
        selection_rect = self.selection.rect

        # Create a subsurface referencing the selected area (no copy needed yet)
        try:
             original_area = sprite_editor.frame.subsurface(selection_rect)
             mirrored_area = pygame.transform.flip(original_area, True, False) # Flip horizontal
        except ValueError as e:
             self._set_status(f"Mirror failed: {e}")
             self.undo_stack.pop() # Remove the state we just saved
             return

        sprite_editor.frame.fill((*config.BLACK[:3], 0), selection_rect)
        sprite_editor.frame.blit(mirrored_area, selection_rect.topleft)
        self._set_status("Selection mirrored.", ttl_ms=1200)

    def rotate_selection(self):
        """Rotate the selected pixels 90 degrees clockwise in-place."""
        if not self.selection.active:
            self._set_status("Rotate failed: make a selection first.")
            return

        sprite_editor = self.get_active_canvas()
        if not sprite_editor:
            self._set_status("Rotate failed: active canvas not found.")
            return

        self.save_state() # Save state before modifying
        selection_rect = self.selection.rect

        # Create a subsurface and rotate it
        try:
            original_area = sprite_editor.frame.subsurface(selection_rect)
            rotated_area = pygame.transform.rotate(original_area, -90) # Clockwise
        except ValueError as e:
            self._set_status(f"Rotate failed: {e}")
            return

        sprite_editor.frame.fill((*config.BLACK[:3], 0), selection_rect)
        blit_pos = rotated_area.get_rect(center=selection_rect.center)
        sprite_editor.frame.blit(rotated_area, blit_pos)
        self._set_status("Selection rotated clockwise.", ttl_ms=1200)

    def zoom_in(self):
        """Zoom in on the background canvas."""
        if self.edit_mode == 'background':
            self.adjust_zoom(1.2)
            print(f"Zoom In: Level {self.editor_zoom:.2f}x")
        else:
            print("Zoom only available in background mode.")

    def zoom_out(self):
        """Zoom out on the background canvas."""
        if self.edit_mode == 'background':
            self.adjust_zoom(1 / 1.2)
            print(f"Zoom Out: Level {self.editor_zoom:.2f}x")
        else:
             print("Zoom only available in background mode.")

    def _clamp_view_offset(self):
        if not self.current_background or not self.canvas_rect:
            return
        scaled_width = int(self.current_background.get_width() * self.editor_zoom)
        scaled_height = int(self.current_background.get_height() * self.editor_zoom)
        max_offset_x = max(0, scaled_width - self.canvas_rect.width)
        max_offset_y = max(0, scaled_height - self.canvas_rect.height)
        self.view_offset_x = max(0, min(self.view_offset_x, max_offset_x))
        self.view_offset_y = max(0, min(self.view_offset_y, max_offset_y))

    def adjust_zoom(self, zoom_factor, focus_pos=None):
        """Adjust background zoom while keeping the focus position stable."""
        if self.edit_mode != 'background' or not self.canvas_rect or not self.current_background:
            return
        old_zoom = self.editor_zoom
        min_zoom = 0.25
        max_zoom = 8.0
        new_zoom = max(min(old_zoom * zoom_factor, max_zoom), min_zoom)
        if new_zoom == old_zoom:
            return

        if focus_pos is None or not self.canvas_rect.collidepoint(focus_pos):
            focus_pos = self.canvas_rect.center

        screen_x_rel = focus_pos[0] - self.canvas_rect.x
        screen_y_rel = focus_pos[1] - self.canvas_rect.y
        world_x = (screen_x_rel + self.view_offset_x) / old_zoom
        world_y = (screen_y_rel + self.view_offset_y) / old_zoom

        self.editor_zoom = new_zoom
        self.view_offset_x = world_x * new_zoom - screen_x_rel
        self.view_offset_y = world_y * new_zoom - screen_y_rel
        self._clamp_view_offset()

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
        tk_root = self._ensure_tkinter_root()
        if not tk_root:
            self._set_status("Color picker unavailable. Eyedropper enabled.", ttl_ms=2200)
            self.activate_eyedropper()
            return

        # Convert current color to Tkinter format (hex string)
        initial_color_hex = "#{:02x}{:02x}{:02x}".format(*self.current_color[:3])

        # Open the dialog, passing the global root as parent
        try:
            chosen_color = colorchooser.askcolor(parent=tk_root, color=initial_color_hex, title="Select Color")
        except tk.TclError as e:
            self._set_status(f"Color picker error: {e}", ttl_ms=2200)
            chosen_color = None
        except Exception as e:
            self._set_status(f"Color picker error: {e}", ttl_ms=2200)
            chosen_color = None

        if chosen_color and chosen_color[1] is not None: 
            rgb, _ = chosen_color
            new_color_rgba = (int(rgb[0]), int(rgb[1]), int(rgb[2]), 255)
            self.select_color(new_color_rgba)
        else:
            self._set_status("Color selection cancelled.", ttl_ms=1000)

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
            self.state.set_color(color)
            self._set_draw_mode(eraser=False)
            self.selection.active = False
            self._set_status(f"Selected color: {color}", ttl_ms=900)

    def activate_eyedropper(self):
        """Switch to the eyedropper tool."""
        self.tool_manager.set_active_tool('eyedropper')

    def pick_color_at_pos(self, pos):
        """Sample a color from the active canvas at the given screen position."""
        if self.edit_mode in ['monster', 'tile']:
            sprite_editor = self._get_sprite_editor_at_pos(pos)
            if sprite_editor:
                grid_pos = sprite_editor.get_grid_position(pos)
                if grid_pos:
                    color = sprite_editor.get_pixel_color(grid_pos)
                    if color and color[3] > 0:
                        self.select_color((color[0], color[1], color[2], 255))
                        return True
                    ref_color = self._sample_reference_color_at_pos(pos, sprite_editor)
                    if ref_color:
                        self.select_color(ref_color)
                        return True
        elif self.edit_mode == 'background' and self.canvas_rect and self.current_background:
            if self.canvas_rect.collidepoint(pos):
                screen_x_rel = pos[0] - self.canvas_rect.x
                screen_y_rel = pos[1] - self.canvas_rect.y
                original_x = int((screen_x_rel + self.view_offset_x) / self.editor_zoom)
                original_y = int((screen_y_rel + self.view_offset_y) / self.editor_zoom)
                bg_width, bg_height = self.current_background.get_size()
                if 0 <= original_x < bg_width and 0 <= original_y < bg_height:
                    color = self.current_background.get_at((original_x, original_y))
                    self.select_color((color[0], color[1], color[2], 255))
                    return True
        return False

    def _sample_reference_color_at_pos(self, pos, sprite_editor):
        """Sample a color from the reference image under the given screen position."""
        if not self.scaled_reference_image or not sprite_editor:
            return None
        local_x = pos[0] - sprite_editor.position[0]
        local_y = pos[1] - sprite_editor.position[1]
        if local_x < 0 or local_y < 0:
            return None
        if local_x >= self.scaled_reference_image.get_width() or local_y >= self.scaled_reference_image.get_height():
            return None
        color = self.scaled_reference_image.get_at((int(local_x), int(local_y)))
        if color[3] == 0:
            return None
        return (color[0], color[1], color[2], 255)

    def load_backgrounds(self):
        """
        Load available background images from the 'backgrounds' directory.

        This method scans the 'backgrounds' directory for PNG files and attempts
        to load them as background images. It returns a list of tuples, where each
        tuple contains the filename and the corresponding Pygame Surface.

        Returns:
            list: A list of tuples, each containing a filename and a Pygame Surface.
        """
        return self.file_io.load_backgrounds()

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
        self.dialog_manager.choose_background_action()

    def _handle_background_action_choice(self, action):
        """Callback after choosing background action."""
        self.dialog_manager._handle_background_action_choice(action)

    def create_new_background(self):
        """
        Create a new background image.
        """
        self.dialog_manager.create_new_background()

    def _create_new_background_callback(self, filename):
        """Callback after getting filename for new background."""
        self.dialog_manager._create_new_background_callback(filename)

    def save_background(self, filename=None):
        """
        Save the current background image.
        Uses Pygame input dialog if no filename provided or saving new.
        """
        self.dialog_manager.save_background(filename=filename)

    def _save_background_callback(self, filename):
        """Callback after getting filename for saving background."""
        self.dialog_manager._save_background_callback(filename)

    def load_monster(self):
        """
        Load the current monster's sprites.

        This method loads the sprites for the currently selected monster. It updates
        the sprite frames and prints a status message.
        """
        try:
            # Ensure monsters list and index are valid
            if not isinstance(self.monsters, list) or not self.monsters:
                print("Error: Monster data not loaded or invalid.")
                return
            if not (0 <= self.current_monster_index < len(self.monsters)):
                print(f"Error: current_monster_index {self.current_monster_index} out of range.")
                return

            monster_name = self.monsters[self.current_monster_index]['name']
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
        if not isinstance(self.monsters, list) or not self.monsters:
            print("Error: Monster data not loaded or invalid. Cannot switch.")
            return

        if self.current_monster_index > 0:
            self.current_monster_index -= 1
            self.load_monster()
            print(f"Switched to previous monster: {self.monsters[self.current_monster_index]['name']}")
        else:
            print("Already at the first monster.")

    def next_monster(self):
        """
        Switch to the next monster in the list.

        This method increments the current monster index and loads the next
        monster's sprites. It prints a status message.
        """
        # Ensure monsters list is loaded and valid
        if not isinstance(self.monsters, list) or not self.monsters:
            print("Error: Monster data not loaded or invalid. Cannot switch.")
            return
        
        if self.current_monster_index < len(self.monsters) - 1:
            self.current_monster_index += 1
            self.load_monster()
            print(f"Switched to next monster: {self.monsters[self.current_monster_index].get('name', 'Unknown')}")
        else:
            print("Already at the last monster.")

    def _get_background_files(self):
        """Helper to get list of .png files in background directory."""
        return self.dialog_manager._get_background_files()

    def _get_reference_files(self, directory):
        """Helper to get image files from a directory."""
        return self.dialog_manager._get_reference_files(directory)

    def _set_dialog_directory(self, directory):
        """Update dialog list to show images from the given directory."""
        self.dialog_manager._set_dialog_directory(directory)

    def _update_scrollbar_from_offset(self):
        self.dialog_manager._update_scrollbar_from_offset()

    def _set_scroll_offset_from_thumb(self, thumb_center_y):
        self.dialog_manager._set_scroll_offset_from_thumb(thumb_center_y)

    def _ensure_dialog_scroll(self):
        """Keep selected file in view when using file list dialogs."""
        self.dialog_manager._ensure_dialog_scroll()

    def _make_tray_scrollbar(self, tray_rect, content_top, total, visible, scroll_offset):
        """Return scrollbar and thumb rects for a tray if overflow exists."""
        if total <= visible or visible <= 0:
            return None, None
        scrollbar_width = 8
        scrollbar_rect = pygame.Rect(
            tray_rect.right - scrollbar_width - 2,
            content_top,
            scrollbar_width,
            max(1, tray_rect.bottom - content_top - 2),
        )
        ratio = visible / total
        thumb_height = max(16, int(scrollbar_rect.height * ratio))
        max_offset = max(1, total - visible)
        top = scrollbar_rect.y + int((scroll_offset / max_offset) * (scrollbar_rect.height - thumb_height))
        thumb_rect = pygame.Rect(scrollbar_rect.x, top, scrollbar_rect.width, thumb_height)
        return scrollbar_rect, thumb_rect

    def _set_tray_scroll_from_thumb(self, thumb_center_y, total, visible, scrollbar_rect, thumb_height):
        """Compute scroll offset based on thumb position within tray scrollbar."""
        if not scrollbar_rect or total <= visible or visible <= 0:
            return 0
        max_offset = total - visible
        usable = max(1, scrollbar_rect.height - thumb_height)
        relative = thumb_center_y - scrollbar_rect.y - (thumb_height // 2)
        relative = max(0, min(relative, usable))
        return int(round((relative / usable) * max_offset))

    def trigger_load_tileset_dialog(self):
        """Initiates the dialog for loading a tileset file."""
        self.dialog_manager.trigger_load_tileset_dialog()

    def trigger_load_background_dialog(self):
        """Initiates the dialog for loading a background file."""
        self.dialog_manager.trigger_load_background_dialog()

    def trigger_load_reference_dialog(self):
        """Initiates the dialog for loading a reference image."""
        self.dialog_manager.trigger_load_reference_dialog()

    def _load_selected_reference_callback(self, file_path):
        """Callback after selecting a reference file to load."""
        self.dialog_manager._load_selected_reference_callback(file_path)

    def _load_selected_tileset_callback(self, filename_or_path):
        """Callback after selecting a tileset file to load."""
        self.dialog_manager._load_selected_tileset_callback(filename_or_path)

    def _load_selected_background_callback(self, filename):
        """Callback after selecting a background file to load."""
        self.dialog_manager._load_selected_background_callback(filename)

    def save_state(self):
        """Save the current state of the active canvas to the undo stack."""
        self.undo_redo.save_state()

    def undo(self):
        """Revert to the previous state from the undo stack."""
        self.undo_redo.undo()

    def redo(self):
        """Reapply the last undone action from the redo stack."""
        self.undo_redo.redo()

    def get_active_canvas(self):
        """Return the active sprite-like editor for the current mode."""
        if self.edit_mode == 'monster':
            return self.sprites.get(self.current_sprite)
        if self.edit_mode == 'tile':
            return self.tile_canvas
        return None

    def _get_sprite_editor_at_pos(self, pos):
        """Return the SpriteEditor instance at the given screen position, or None."""
        if self.edit_mode == 'monster':
            for name, sprite_editor in self.sprites.items():
                editor_rect = pygame.Rect(sprite_editor.position, (sprite_editor.display_width, sprite_editor.display_height))
                if editor_rect.collidepoint(pos):
                    return sprite_editor
        elif self.edit_mode == 'tile':
            editor_rect = pygame.Rect(self.tile_canvas.position, (self.tile_canvas.display_width, self.tile_canvas.display_height))
            if editor_rect.collidepoint(pos):
                return self.tile_canvas
        return None

    def handle_event(self, event):
        """Process a single Pygame event by delegating to the EventHandler."""
        return self.event_handler.process_event(event)

    def load_reference_image(self):
        """Opens a dialog to select a reference image, loads and scales it."""
        self.trigger_load_reference_dialog()

    def import_reference_to_canvas(self):
        """Import the reference image behind the canvas using nearest-neighbor sampling."""
        sprite_editor = self.get_active_canvas()
        if not sprite_editor:
            print("Import failed: No active canvas.")
            return
        if not self.reference_image:
            print("Import failed: No reference image loaded.")
            return
        if not self.scaled_reference_image:
            self._scale_reference_image()
        if not self.scaled_reference_image:
            print("Import failed: Reference image not available for sampling.")
            return

        self.save_state()

        src_w, src_h = self.scaled_reference_image.get_size()
        dst_w, dst_h = sprite_editor.frame.get_size()
        scale_x = src_w / dst_w if dst_w else 1
        scale_y = src_h / dst_h if dst_h else 1

        for y in range(dst_h):
            sample_y = min(src_h - 1, max(0, int((y + 0.5) * scale_y)))
            for x in range(dst_w):
                sample_x = min(src_w - 1, max(0, int((x + 0.5) * scale_x)))
                color = self.scaled_reference_image.get_at((sample_x, sample_y))
                if color.a == 0:
                    continue
                sprite_editor.frame.set_at((x, y), (color.r, color.g, color.b, 255))
        print("Imported reference image into canvas.")

    def _scale_reference_image(self):
        """Scales the loaded reference image using Aspect Fit, then applies
           user-defined scale and offset, preparing it for display behind the active editor.
        """
        if not self.reference_image:
            self.scaled_reference_image = None
            return

        # Target dimensions are the display size of the active editor grid
        sprite_editor = self.get_active_canvas()
        if not sprite_editor:
            print("Error: Cannot scale reference image, active editor not found.")
            self.scaled_reference_image = None
            return

        canvas_w = sprite_editor.display_width
        canvas_h = sprite_editor.display_height
        orig_w, orig_h = self.reference_image.get_size()

        if orig_w == 0 or orig_h == 0:
             print("Warning: Reference image has zero dimension. Cannot scale.")
             self.scaled_reference_image = None
             return

        # 1. Calculate initial aspect fit scale
        scale_w_ratio = canvas_w / orig_w
        scale_h_ratio = canvas_h / orig_h
        aspect_scale = min(scale_w_ratio, scale_h_ratio)
        initial_scaled_w = int(orig_w * aspect_scale)
        initial_scaled_h = int(orig_h * aspect_scale)

        # 2. Apply user scale on top of aspect fit
        current_scaled_w = int(initial_scaled_w * self.ref_img_scale)
        current_scaled_h = int(initial_scaled_h * self.ref_img_scale)

        # Prevent scaling to zero size
        if current_scaled_w <= 0 or current_scaled_h <= 0:
             print("Warning: Calculated final scaled size is zero or negative. Cannot scale.")
             self.scaled_reference_image = None
             return

        try:
            # 3. Scale the ORIGINAL image to the final calculated size
            user_scaled_surf = pygame.transform.smoothscale(self.reference_image, (current_scaled_w, current_scaled_h))

            # 4. Create the final surface matching canvas size, transparent background
            final_display_surf = pygame.Surface((canvas_w, canvas_h), pygame.SRCALPHA)
            final_display_surf.fill((0, 0, 0, 0)) # Fully transparent

            # 5. Calculate centering position AND apply user offset
            center_x = (canvas_w - current_scaled_w) // 2
            center_y = (canvas_h - current_scaled_h) // 2
            blit_x = center_x + int(self.ref_img_offset.x)
            blit_y = center_y + int(self.ref_img_offset.y)

            # 6. Blit the user-scaled image onto the transparent canvas at the final position
            final_display_surf.blit(user_scaled_surf, (blit_x, blit_y))

            # Store this surface before applying alpha
            self.scaled_reference_image = final_display_surf

            # Apply the current alpha value
            self.apply_reference_alpha()

        except pygame.error as e:
            print(f"Error during reference image scaling: {e}")
            self.scaled_reference_image = None
        except ValueError as e: # Catch potential issues with smoothscale
            print(f"Error during reference image scaling (ValueError): {e}")
            self.scaled_reference_image = None


    def clear_reference_image(self):
        """Removes the current reference image."""
        self.reference_image_path = None
        self.reference_image = None
        self.scaled_reference_image = None
        # Reset panning and scaling
        self.ref_img_offset.update(0, 0)
        self.ref_img_scale = 1.0
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
            
    def _draw_loading_state(self, surface):
        loading_font = pygame.font.Font(config.DEFAULT_FONT, 30)
        loading_surf = loading_font.render("Waiting for mode selection...", True, config.BLACK)
        loading_rect = loading_surf.get_rect(center=surface.get_rect().center)
        surface.blit(loading_surf, loading_rect)

    def _draw_paste_preview(self, surface, sprite_editor):
        if not sprite_editor:
            return
        if self.tool_manager.active_tool_name != 'paste' or not self.copy_buffer:
            return
        mouse_pos = pygame.mouse.get_pos()
        grid_pos = sprite_editor.get_grid_position(mouse_pos)
        if not grid_pos:
            return

        min_rel_x = 0
        min_rel_y = 0
        max_rel_x = 0
        max_rel_y = 0
        for rel_x, rel_y in self.copy_buffer:
            min_rel_x = min(min_rel_x, rel_x)
            min_rel_y = min(min_rel_y, rel_y)
            max_rel_x = max(max_rel_x, rel_x)
            max_rel_y = max(max_rel_y, rel_y)

        for (rel_x, rel_y), color in self.copy_buffer.items():
            if len(color) < 4 or color[3] <= 0:
                continue
            abs_x = grid_pos[0] + rel_x
            abs_y = grid_pos[1] + rel_y
            if not (0 <= abs_x < config.NATIVE_SPRITE_RESOLUTION[0] and 0 <= abs_y < config.NATIVE_SPRITE_RESOLUTION[1]):
                continue
            preview_color = (color[0], color[1], color[2], min(170, max(60, color[3])))
            pixel_rect = pygame.Rect(
                sprite_editor.position[0] + abs_x * config.EDITOR_PIXEL_SIZE,
                sprite_editor.position[1] + abs_y * config.EDITOR_PIXEL_SIZE,
                config.EDITOR_PIXEL_SIZE,
                config.EDITOR_PIXEL_SIZE,
            )
            pygame.draw.rect(surface, preview_color, pixel_rect)

        outline_rect = pygame.Rect(
            sprite_editor.position[0] + (grid_pos[0] + min_rel_x) * config.EDITOR_PIXEL_SIZE,
            sprite_editor.position[1] + (grid_pos[1] + min_rel_y) * config.EDITOR_PIXEL_SIZE,
            (max_rel_x - min_rel_x + 1) * config.EDITOR_PIXEL_SIZE,
            (max_rel_y - min_rel_y + 1) * config.EDITOR_PIXEL_SIZE,
        )
        pygame.draw.rect(surface, config.BLUE, outline_rect, 2)
        hint_surf = self.font_small.render("Paste preview (Esc to cancel)", True, config.BLACK)
        surface.blit(hint_surf, (outline_rect.x, max(0, outline_rect.y - 18)))

    def _draw_monster_ui(self, surface):
        for sprite_editor in self.sprites.values():
            sprite_editor.draw_background(surface)
        if self.scaled_reference_image:
            active_sprite_editor = self.sprites.get(self.current_sprite)
            if active_sprite_editor:
                surface.blit(self.scaled_reference_image, active_sprite_editor.position)
        for sprite_editor in self.sprites.values():
            display_surface = sprite_editor.frame.copy()
            scaled_display_frame = pygame.transform.scale(
                display_surface,
                (sprite_editor.display_width, sprite_editor.display_height),
            )
            scaled_display_frame.set_alpha(self.subject_alpha)
            surface.blit(scaled_display_frame, sprite_editor.position)
        active_sprite_editor = self.sprites.get(self.current_sprite)
        if active_sprite_editor:
            active_sprite_editor.draw_highlight(surface, self.current_sprite)
            self._draw_paste_preview(surface, active_sprite_editor)
        monster_name = "Unknown"
        if isinstance(self.monsters, list) and 0 <= self.current_monster_index < len(self.monsters):
            monster_name = self.monsters[self.current_monster_index].get('name', 'Unknown')
        info_text = f"Editing: {monster_name} ({self.current_sprite})"
        info_surf = self.font.render(info_text, True, config.BLACK)
        surface.blit(info_surf, (50, 50))
        if self.mode == 'select':
            active_sprite_editor = self.sprites.get(self.current_sprite)
            if active_sprite_editor:
                self.selection.draw(surface, active_sprite_editor.position)

    def _draw_background_ui(self, surface):
        if self.current_background and self.canvas_rect:
            scaled_width = int(self.current_background.get_width() * self.editor_zoom)
            scaled_height = int(self.current_background.get_height() * self.editor_zoom)
            if scaled_width > 0 and scaled_height > 0:
                zoomed_bg = pygame.transform.scale(
                    self.current_background,
                    (scaled_width, scaled_height),
                )
                max_offset_x = max(0, scaled_width - self.canvas_rect.width)
                max_offset_y = max(0, scaled_height - self.canvas_rect.height)
                clamped_offset_x = max(0, min(self.view_offset_x, max_offset_x))
                clamped_offset_y = max(0, min(self.view_offset_y, max_offset_y))
                source_rect = pygame.Rect(
                    clamped_offset_x,
                    clamped_offset_y,
                    self.canvas_rect.width,
                    self.canvas_rect.height,
                )
                surface.blit(zoomed_bg, self.canvas_rect.topleft, source_rect)
            pygame.draw.rect(surface, config.BLACK, self.canvas_rect, 1)
        bg_name = (
            self.backgrounds[self.current_background_index][0]
            if self.current_background_index != -1
            else "New BG"
        )
        info_text = f"Editing BG: {bg_name} | Brush: {self.brush_size} | Zoom: {self.editor_zoom:.2f}x"
        info_surf = self.font.render(info_text, True, config.BLACK)
        surface.blit(info_surf, (50, 50))

    def _draw_tile_ui(self, surface):
        self.tile_canvas.draw_background(surface)
        if self.scaled_reference_image:
            surface.blit(self.scaled_reference_image, self.tile_canvas.position)
        display_surface = self.tile_canvas.frame.copy()
        scaled_display = pygame.transform.scale(
            display_surface,
            (self.tile_canvas.display_width, self.tile_canvas.display_height),
        )
        scaled_display.set_alpha(self.subject_alpha)
        surface.blit(scaled_display, self.tile_canvas.position)
        self._draw_paste_preview(surface, self.tile_canvas)
        pygame.draw.rect(
            surface,
            config.SELECTION_HIGHLIGHT_COLOR,
            pygame.Rect(
                self.tile_canvas.position,
                (self.tile_canvas.display_width, self.tile_canvas.display_height),
            ),
            3,
        )
        tileset_name = self.tile_set.name if self.tile_set else "Tiles"
        if self.asset_edit_target == 'tile':
            tile = self.current_tile()
            walkable_state = tile.properties.get("walkable", True) if tile else True
            tile_label = f"{tile.id} ({tile.name})" if tile else "No Tile"
            walkable_text = "Walkable" if walkable_state else "Blocked"
            frame_info = ""
            if tile and tile.frames:
                frame_info = (
                    f" | Frame {self.current_tile_frame_index + 1}/{len(tile.frames)}"
                    f" @ {tile.frame_duration_ms}ms"
                )
            info_text = f"Tileset: {tileset_name} | Tile: {tile_label} | {walkable_text}{frame_info}"
            info_surf = self.font.render(info_text, True, config.BLACK)
            surface.blit(info_surf, (50, 50))
            if self.mode == 'select':
                self.selection.draw(surface, self.tile_canvas.position)
            self.draw_tile_panel(surface)
        else:
            npc = self.current_npc()
            npc_label = npc.id if npc else "No NPC"
            frame_info = ""
            if npc:
                frames = npc.states.get(self.current_npc_state, {}).get(self.current_npc_angle, [])
                frame_info = (
                    f" | Frame {self.current_npc_frame_index + 1}/{len(frames) if frames else 1}"
                    f" @ {npc.frame_duration_ms}ms"
                )
            info_text = (
                f"Tileset: {tileset_name} | NPC: {npc_label} | State: {self.current_npc_state}"
                f" | Angle: {self.current_npc_angle}{frame_info}"
            )
            info_surf = self.font.render(info_text, True, config.BLACK)
            surface.blit(info_surf, (50, 50))
            if self.mode == 'select':
                self.selection.draw(surface, self.tile_canvas.position)
            self.draw_npc_panel(surface)

    def _draw_common_ui(self, surface):
        self.palette.draw(surface, self.current_color)
        if hasattr(self, 'buttons') and self.buttons:
            self._draw_button_panel(surface)
        pygame.draw.rect(surface, config.GRAY_LIGHT, self.brush_slider)
        pygame.draw.rect(surface, config.BLACK, self.brush_slider, 1)
        brush_text = f"Brush: {self.brush_size}"
        brush_surf = self.font.render(brush_text, True, config.BLACK)
        brush_rect = brush_surf.get_rect(midleft=(self.brush_slider.right + 10, self.brush_slider.centery))
        surface.blit(brush_surf, brush_rect)
        pygame.draw.rect(surface, config.GRAY_LIGHT, self.ref_alpha_slider_rect)
        pygame.draw.rect(surface, config.BLACK, self.ref_alpha_slider_rect, 1)
        pygame.draw.rect(surface, config.BLUE, self.ref_alpha_knob_rect)
        alpha_text = f"Ref Alpha: {self.reference_alpha}"
        alpha_surf = self.font.render(alpha_text, True, config.BLACK)
        alpha_rect = alpha_surf.get_rect(
            midleft=(self.ref_alpha_slider_rect.right + 10, self.ref_alpha_slider_rect.centery),
        )
        surface.blit(alpha_surf, alpha_rect)
        if self.edit_mode in ['monster', 'tile']:
            pygame.draw.rect(surface, config.GRAY_LIGHT, self.subj_alpha_slider_rect)
            pygame.draw.rect(surface, config.BLACK, self.subj_alpha_slider_rect, 1)
            pygame.draw.rect(surface, config.RED, self.subj_alpha_knob_rect)
            subj_alpha_text = f"Subj Alpha: {self.subject_alpha}"
            subj_alpha_surf = self.font.render(subj_alpha_text, True, config.BLACK)
            subj_alpha_rect = subj_alpha_surf.get_rect(
                midleft=(self.subj_alpha_slider_rect.right + 10, self.subj_alpha_slider_rect.centery),
            )
            surface.blit(subj_alpha_surf, subj_alpha_rect)

        if self.status_message and pygame.time.get_ticks() <= self.status_message_expire_tick:
            status_bg = pygame.Rect(20, config.EDITOR_HEIGHT - 34, config.EDITOR_WIDTH - 40, 24)
            pygame.draw.rect(surface, config.WHITE, status_bg)
            pygame.draw.rect(surface, config.BLACK, status_bg, 1)
            status_surf = self.font_small.render(self.status_message, True, config.BLACK)
            surface.blit(status_surf, (status_bg.x + 8, status_bg.y + 5))

    def draw_ui(self):
        """Draw the entire editor UI onto the screen."""
        screen.fill(config.EDITOR_BG_COLOR)

        if self.dialog_mode:
            self.draw_dialog(screen)
            return

        if self.edit_mode is None:
            self._draw_loading_state(screen)
            return

        if self.edit_mode == 'monster':
            self._draw_monster_ui(screen)
        elif self.edit_mode == 'background':
            self._draw_background_ui(screen)
        elif self.edit_mode == 'tile':
            self._draw_tile_ui(screen)

        self._draw_common_ui(screen)

    def draw_dialog(self, surface):
        """Draws the current dialog box overlay."""
        self.dialog_manager.draw_dialog(surface)
    # <<< End Restore draw_dialog >>>

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

def main(argv=None):
    global monsters

    # Set up necessary directories if they don't exist.
    if not os.path.exists(config.SPRITE_DIR):
        os.makedirs(config.SPRITE_DIR)
        print(f"Created missing directory: {config.SPRITE_DIR}")
    if not os.path.exists(config.BACKGROUND_DIR):
        os.makedirs(config.BACKGROUND_DIR)
        print(f"Created missing directory: {config.BACKGROUND_DIR}")
    if not os.path.exists(config.DATA_DIR):
        os.makedirs(config.DATA_DIR)
        print(f"Created missing directory: {config.DATA_DIR}")

    # Ensure monster data is loaded globally for the editor.
    if not monsters:
        print("Reloading monster data for main execution...")
        monsters = load_monsters()
        if not monsters:
            print("Fatal: Could not load monster data. Exiting.")
            return 1

    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["monster", "background", "tile"], help="Start editor in a specific mode.")
    parser.add_argument("--asset", choices=["tile", "npc"], help="When in tile mode, select asset type.")
    parser.add_argument("--npc", dest="npc_id", help="When in tile mode, preselect NPC id.")
    args = parser.parse_args(argv)

    env_mode = os.environ.get("POKECLONE_EDITOR_MODE")
    env_asset = os.environ.get("POKECLONE_EDITOR_ASSET")
    env_npc = os.environ.get("POKECLONE_EDITOR_NPC")

    mode = args.mode or env_mode
    asset = args.asset or env_asset
    npc_id = args.npc_id or env_npc

    editor = Editor(monsters=monsters, skip_initial_dialog=bool(mode))
    if mode:
        editor.dialog_manager.state.reset()
        editor._set_edit_mode_and_continue(mode)
        editor.dialog_manager.state.reset()
        if mode == "tile":
            if npc_id:
                editor.selected_npc_id = npc_id
            if asset:
                editor.set_asset_edit_target(asset)
            elif npc_id:
                editor.set_asset_edit_target("npc")
            if npc_id:
                editor._load_current_npc_frame()
    editor.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
