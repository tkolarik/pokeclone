from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class EditorState:
    """Container for editor state that changes during interaction."""

    # Core editing state
    current_color: Tuple[int, int, int, int] = (0, 0, 0, 255)
    current_monster_index: int = 0
    eraser_mode: bool = False
    fill_mode: bool = False
    paste_mode: bool = False
    current_sprite: str = "front"
    brush_size: int = 1
    adjusting_brush: bool = False
    copy_buffer: Optional[Dict[Tuple[int, int], Tuple[int, int, int, int]]] = None
    mode: str = "draw"
    edit_mode: Optional[str] = None

    # Background state
    backgrounds: List[Any] = field(default_factory=list)
    current_background_index: int = -1
    current_background: Optional[Any] = None

    # View state
    editor_zoom: float = 1.0
    view_offset_x: int = 0
    view_offset_y: int = 0
    panning: bool = False

    # Reference image state
    reference_image_path: Optional[str] = None
    reference_image: Optional[Any] = None
    scaled_reference_image: Optional[Any] = None
    reference_alpha: int = 128
    adjusting_alpha: bool = False
    subject_alpha: int = 255
    adjusting_subject_alpha: bool = False
    ref_img_offset: Optional[Any] = None
    ref_img_scale: float = 1.0

    # Tile editing state
    tile_set: Optional[Any] = None
    current_tile_index: int = -1
    selected_tile_id: Optional[str] = None
    tile_preview_cache: Dict[str, Any] = field(default_factory=dict)
    tile_list_scroll: int = 0
    tile_button_rects: List[Any] = field(default_factory=list)
    current_tile_frame_index: int = 0
    tile_frame_scroll: int = 0
    tile_frame_button_rects: List[Any] = field(default_factory=list)
    tile_frame_tray_rect: Optional[Any] = None
    tile_frame_scrollbar_rect: Optional[Any] = None
    tile_frame_scroll_thumb_rect: Optional[Any] = None
    tile_frame_dragging_scrollbar: bool = False
    tile_frame_visible: int = 0
    asset_edit_target: str = "tile"
    tile_anim_last_tick: int = 0

    # NPC editing state
    npc_list_scroll: int = 0
    npc_button_rects: List[Any] = field(default_factory=list)
    selected_npc_id: Optional[str] = None
    current_npc_state: str = "standing"
    current_npc_angle: str = "south"
    current_npc_frame_index: int = 0
    npc_state_scroll: int = 0
    npc_angle_scroll: int = 0
    npc_state_button_rects: List[Any] = field(default_factory=list)
    npc_angle_button_rects: List[Any] = field(default_factory=list)
    npc_state_tray_rect: Optional[Any] = None
    npc_angle_tray_rect: Optional[Any] = None
    npc_state_scrollbar_rect: Optional[Any] = None
    npc_state_scroll_thumb_rect: Optional[Any] = None
    npc_state_dragging_scrollbar: bool = False
    npc_state_visible: int = 0
    npc_angle_scrollbar_rect: Optional[Any] = None
    npc_angle_scroll_thumb_rect: Optional[Any] = None
    npc_angle_dragging_scrollbar: bool = False
    npc_angle_visible: int = 0

    # Undo/redo state
    undo_stack: List[Any] = field(default_factory=list)
    redo_stack: List[Any] = field(default_factory=list)

    def set_color(self, color: Tuple[int, int, int, int]) -> None:
        self.current_color = color

    def set_mode(self, mode: str) -> None:
        self.mode = mode

    def set_edit_mode(self, edit_mode: Optional[str]) -> None:
        self.edit_mode = edit_mode

    def reset_view(self) -> None:
        self.editor_zoom = 1.0
        self.view_offset_x = 0
        self.view_offset_y = 0
        self.panning = False
