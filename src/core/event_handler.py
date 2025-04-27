#!/usr/bin/env python3
import pygame
from pygame.locals import MOUSEBUTTONDOWN, MOUSEMOTION, MOUSEBUTTONUP, KEYDOWN, QUIT, KMOD_META, KMOD_CTRL, K_z, K_y, K_c, K_v, K_RETURN, K_BACKSPACE, K_ESCAPE, K_UP, K_DOWN
from src.core import config
# Import the Button class from editor_ui
# from ..editor.editor_ui import Button, Palette # Relative import
from src.editor.editor_ui import Button, Palette # Absolute import

# <<< Import Editor for type hint if needed, or remove if mock is sufficient
# from ..editor.pixle_art_editor import Editor # Relative import (Commented out)
# from src.editor.pixle_art_editor import Editor # Absolute import (Commented out)

class EventHandler:
    def __init__(self, editor):
        """
        Initializes the event handler.

        Args:
            editor: The main editor instance, used to access state and call methods.
        """
        self.editor = editor
        self.left_mouse_button_down = False # <<< Add flag to track mouse state

    def process_event(self, event):
        """
        Process a single Pygame event.
        Delegates event handling to specific methods based on event type and editor state.

        Args:
            event: The Pygame event to process.

        Returns:
            bool: True if the event was handled, False otherwise. 
                  Returning False for QUIT allows the main loop to catch it.
        """
        # Handle dialog events first if a dialog is active
        if self.editor.dialog_mode:
            return self._handle_dialog_event(event)

        # --- Normal Event Handling (No Dialog Active) ---
        if event.type == QUIT:
             return False # Let main loop handle closing

        if event.type == MOUSEBUTTONDOWN:
            # Store the fact that the mouse button is down
            # Needed for handle_drag logic
            self.left_mouse_button_down = (event.button == 1) 
            return self._handle_mouse_button_down(event)
        elif event.type == MOUSEMOTION:
            return self._handle_mouse_motion(event)
        elif event.type == MOUSEBUTTONUP:
            if event.button == 1:
                self.left_mouse_button_down = False # Reset flag
            return self._handle_mouse_button_up(event)
        elif event.type == KEYDOWN:
            return self._handle_key_down(event)
        
        # --- Handle Mouse Wheel for Zoom/Scroll ---
        elif event.type == pygame.MOUSEWHEEL:
             # TODO: Implement zoom/scroll later (maybe part of UI/camera manager)
             # Example: zooming on background?
             # if self.editor.edit_mode == 'background':
             #     if event.y > 0: editor.zoom_in(pygame.mouse.get_pos()) # Zoom in towards mouse
             #     elif event.y < 0: editor.zoom_out(pygame.mouse.get_pos()) # Zoom out from mouse
             #     return True
             # Example: Scrolling palette?
             # palette_rect = ...
             # if palette_rect.collidepoint(pygame.mouse.get_pos()):
             #     if event.y > 0: editor.palette.scroll(-1) # Scroll up
             #     elif event.y < 0: editor.palette.scroll(1) # Scroll down
             #     return True
             pass


        return False # Event not handled by this function

    def _handle_dialog_event(self, event):
        """Handles events when a dialog is active."""
        editor = self.editor # Alias for convenience
        # print(f"DEBUG: Handling dialog event: {event.type}, Mode: {editor.dialog_mode}") # REMOVED

        # Handle clicks on dialog buttons
        if event.type == MOUSEBUTTONDOWN and event.button == 1:
             # print(f"DEBUG: Dialog MOUSEBUTTONDOWN at {event.pos}") # REMOVED
             # print(f"DEBUG: Checking editor.dialog_options (len={len(editor.dialog_options)}): {editor.dialog_options}") # REMOVED
             for i, option in enumerate(editor.dialog_options):
                  # Check if it's a button AND it was clicked
                  if isinstance(option, Button): # Use imported Button
                       # print(f"DEBUG: Checking Button {i}: '{option.text}' at {option.rect}") # REMOVED
                       if option.rect.collidepoint(event.pos): # Use imported Button
                           # print(f"DEBUG: Collision DETECTED with Button '{option.text}'!") # REMOVED
                           # Use button's stored value to call the dialog choice handler
                           if hasattr(option, 'value') and option.value is not None:
                                # print(f"DEBUG: Button has value '{option.value}', calling _handle_dialog_choice...") # REMOVED
                                editor._handle_dialog_choice(option.value)
                                return True # Handled by dialog button click
                           # Handle direct action buttons if necessary
                           elif hasattr(option, 'action') and callable(option.action):
                                # print(f"DEBUG: Button has action '{option.action.__name__}', calling action...") # REMOVED
                                option.action()
                                return True
             # TODO: Handle clicks/drags within specific dialog types (color picker, file list scroll)
            # e.g., if editor.dialog_mode == 'color_picker': handle_color_picker_click/drag
            # e.g., if editor.dialog_mode == 'load_bg': handle_file_list_click/scroll

        # Handle KEYDOWN specifically for dialogs that need it
        elif event.type == KEYDOWN:
             if editor.dialog_mode == 'input_text' and editor.dialog_input_active:
                  if event.key == K_RETURN:
                       # Find the 'Save' or confirm button's value/action if possible,
                       # otherwise assume current input text is the value
                       confirm_value = editor.dialog_input_text
                       for btn in editor.dialog_options:
                           if isinstance(btn, Button) and btn.text.lower() == "save": # Use imported Button
                               confirm_value = btn.value if hasattr(btn, 'value') else confirm_value
                               break
                       editor._handle_dialog_choice(confirm_value)
                  elif event.key == K_BACKSPACE:
                       editor.dialog_input_text = editor.dialog_input_text[:-1]
                  elif event.key == K_ESCAPE:
                       # Find the 'Cancel' button's value/action if possible
                       cancel_value = None
                       for btn in editor.dialog_options:
                           if isinstance(btn, Button) and btn.text.lower() == "cancel": # Use imported Button
                               cancel_value = btn.value if hasattr(btn, 'value') else None
                               break
                       editor._handle_dialog_choice(cancel_value)
                  elif len(editor.dialog_input_text) < editor.dialog_input_max_length:
                       # Filter unwanted characters? For now, allow most printable chars
                       if event.unicode.isprintable():
                            editor.dialog_input_text += event.unicode
                  return True # Consume key event for text input

             # Handle key navigation for file list dialog
             elif editor.dialog_mode == 'load_bg':
                  if event.key == K_UP:
                       if editor.dialog_selected_file_index > 0:
                            editor.dialog_selected_file_index -= 1
                       # TODO: Add scroll logic if file list exceeds display area
                       return True
                  elif event.key == K_DOWN:
                       if editor.dialog_selected_file_index < len(editor.dialog_file_list) - 1:
                            editor.dialog_selected_file_index += 1
                       # TODO: Add scroll logic
                       return True
                  elif event.key == K_RETURN:
                       if 0 <= editor.dialog_selected_file_index < len(editor.dialog_file_list):
                           # Find the 'Load' button's value/action if possible,
                           # otherwise assume selected file index implies load action
                           load_value = editor.dialog_file_list[editor.dialog_selected_file_index]
                           for btn in editor.dialog_options:
                               if isinstance(btn, Button) and btn.text.lower() == "load": # Use imported Button
                                    load_value = btn.value if hasattr(btn, 'value') else load_value
                                    break
                           editor._handle_dialog_choice(load_value)
                       return True
                  elif event.key == K_ESCAPE:
                       # Find the 'Cancel' button's value/action
                       cancel_value = None
                       for btn in editor.dialog_options:
                           if isinstance(btn, Button) and btn.text.lower() == "cancel": # Use imported Button
                               cancel_value = btn.value if hasattr(btn, 'value') else None
                               break
                       editor._handle_dialog_choice(cancel_value)
                       return True

             # Generic Escape to cancel other simple choice dialogs
             elif event.key == K_ESCAPE:
                 if editor.dialog_mode in ['choose_edit_mode', 'choose_bg_action']:
                      editor._handle_dialog_choice(None) # Assuming None means cancel
                 return True

        return True # Consume other unhandled events while dialog is open

    def _handle_mouse_button_down(self, event):
        """Handles mouse button down events when no dialog is active."""
        editor = self.editor

        if event.button == 1: # Left click
            # 0a. Check Subject Alpha Slider Click/Drag Start
            if self.editor.edit_mode == 'monster' and self.editor.subj_alpha_slider_rect.collidepoint(event.pos):
                self.editor.adjusting_subject_alpha = True
                self._update_subject_alpha_slider(event.pos) # Update alpha and knob position
                return True # Event handled
                
            # 0b. Check Reference Alpha Slider Click/Drag Start
            if self.editor.ref_alpha_slider_rect.collidepoint(event.pos):
                self.editor.adjusting_alpha = True
                self._update_alpha_slider(event.pos) # Update alpha and knob position
                return True # Event handled

            # 1. Check UI Buttons
            for button in editor.buttons:
                if button.is_clicked(event):
                    if button.action:
                        button.action() # Call the button's assigned method
                    return True # <<< CRITICAL: Ensure button click consumes the event

            # 2. Check Palette Click
            palette_rect = pygame.Rect(editor.palette.position[0], editor.palette.position[1],
                                     config.PALETTE_COLS * (editor.palette.block_size + editor.palette.padding),
                                     config.PALETTE_ROWS * (editor.palette.block_size + editor.palette.padding) + 40) # Include scroll area roughly
            if palette_rect.collidepoint(event.pos):
                editor.palette.handle_click(event.pos, editor) # <<< Pass editor instance
                return True # <<< CRITICAL: Ensure palette click consumes the event

            # 3. Check Canvas Click (Sprite or Background)
            clicked_sprite_editor = editor._get_sprite_editor_at_pos(event.pos)
            is_bg_click = editor.edit_mode == 'background' and editor.canvas_rect.collidepoint(event.pos)

            if clicked_sprite_editor or is_bg_click:
                # Save state BEFORE the action starts (important for undo)
                # Only save state if not already dragging a selection
                if not (editor.mode == 'select' and editor.selection.selecting):
                     editor.save_state()

                if editor.mode == 'select':
                    if clicked_sprite_editor:
                         # If in select mode, a click on a sprite canvas ALWAYS starts the process.
                         # The SelectionTool.start method should handle the state.
                         editor.selection.start(event.pos, clicked_sprite_editor)
                         # Set selecting flag AFTER calling start
                         editor.selection.selecting = True 
                else: # Draw, erase, fill, paste modes
                    editor.tool_manager.handle_click(event.pos) # <<< Use ToolManager
                return True # Event handled by canvas click
            else:
                 # Click outside canvas areas
                 if editor.mode == 'select' and editor.selection.selecting:
                      # If currently selecting, clicking outside cancels it
                      print("Selection cancelled (clicked outside grid).")
                      editor.selection.selecting = False
                      editor.selection.active = False
                 # Reset drawing flag if click was outside canvas
                 # editor.drawing = False # REMOVED
                 return True # Consume click outside relevant areas

        elif event.button == 4: # Mouse wheel up
             # Handle palette scroll if mouse is over it
             palette_rect = pygame.Rect(editor.palette.position[0], editor.palette.position[1],
                                         config.PALETTE_COLS * (editor.palette.block_size + editor.palette.padding) + 30, # Rough width including scroll
                                         config.PALETTE_ROWS * (editor.palette.block_size + editor.palette.padding))
             if palette_rect.collidepoint(event.pos):
                 editor.palette.scroll_offset = max(0, editor.palette.scroll_offset - 1)
                 return True
             # TODO: Add zoom or other scroll behavior here if needed

        elif event.button == 5: # Mouse wheel down
              # Handle palette scroll if mouse is over it
             palette_rect = pygame.Rect(editor.palette.position[0], editor.palette.position[1],
                                         config.PALETTE_COLS * (editor.palette.block_size + editor.palette.padding) + 30, # Rough width
                                         config.PALETTE_ROWS * (editor.palette.block_size + editor.palette.padding))
             if palette_rect.collidepoint(event.pos):
                 editor.palette.scroll_offset = min(editor.palette.total_pages - 1, editor.palette.scroll_offset + 1)
                 return True
             # TODO: Add zoom or other scroll behavior here if needed

        # Handle Middle Mouse Button for Panning Start
        elif event.button == 2: # Middle mouse button
            if self.editor.edit_mode == 'background' and self.editor.canvas_rect and self.editor.canvas_rect.collidepoint(event.pos):
                self.editor.panning = True
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND) # Change cursor to hand
                return True # Panning started
                
        # Handle Right-click, Middle-click, etc. if needed
        # elif event.button == 3: # Right click
        #     # Example: Eyedropper tool?
        #     sprite_at_pos = editor._get_sprite_editor_at_pos(event.pos)
        #     if sprite_at_pos:
        #         grid_pos = sprite_at_pos.get_grid_position(event.pos)
        #         if grid_pos:
        #             color = sprite_at_pos.get_pixel_color(grid_pos)
        #             if color: editor.select_color(color)
        #             return True
        #     pass

        return False # Event not handled

    def _handle_mouse_motion(self, event):
        """Handles mouse motion events when no dialog is active."""
        editor = self.editor

        # Handle Subject Alpha Slider Drag
        if editor.adjusting_subject_alpha and (event.buttons[0] == 1):
            self._update_subject_alpha_slider(event.pos)
            return True

        # Handle Panning Drag
        if editor.panning and (event.buttons[1] == 1): # Check if middle button is held
            dx, dy = event.rel # Get relative motion
            editor.view_offset_x -= dx # Adjust view offset (inverse of mouse motion)
            editor.view_offset_y -= dy
            
            # Clamp view offset (ensure this logic matches draw_ui clamping)
            if editor.current_background:
                scaled_width = int(editor.current_background.get_width() * editor.editor_zoom)
                scaled_height = int(editor.current_background.get_height() * editor.editor_zoom)
                max_offset_x = max(0, scaled_width - editor.canvas_rect.width)
                max_offset_y = max(0, scaled_height - editor.canvas_rect.height)
                editor.view_offset_x = max(0, min(editor.view_offset_x, max_offset_x))
                editor.view_offset_y = max(0, min(editor.view_offset_y, max_offset_y))
            return True # Panning motion handled

        # Handle Reference alpha slider drag
        if editor.adjusting_alpha and (event.buttons[0] == 1): # Check if left button is held
            self._update_alpha_slider(event.pos) # Update alpha and knob position
            return True # Event handled

        # Handle drawing/erase/tool drag via ToolManager
        # Check if left button is down (using our flag) AND not in select mode
        if self.left_mouse_button_down and editor.mode != 'select':
             editor.tool_manager.handle_drag(event.pos) # <<< Use ToolManager
             return True

        # Handle selection drag
        elif editor.mode == 'select' and editor.selection.selecting and (event.buttons[0] == 1):
             clicked_sprite_editor = editor._get_sprite_editor_at_pos(event.pos)
             # Update selection only if dragging over the *same* editor? Or any? For now, any.
             if clicked_sprite_editor:
                  editor.selection.update(event.pos, clicked_sprite_editor) # Pass sprite editor
             # Allow drag outside the initial sprite editor? Yes for now.
             # Might need refinement if dragging over the *other* sprite editor.
             return True
        
        # TODO: Handle panning drag (e.g., middle mouse button held)

        return False # Event not handled

    def _handle_mouse_button_up(self, event):
        """Handles mouse button up events when no dialog is active."""
        editor = self.editor

        if event.button == 1: # Left button release
             # Stop adjusting subject alpha slider
            if editor.adjusting_subject_alpha:
                editor.adjusting_subject_alpha = False
                return True # Event handled
                
             # Stop adjusting reference alpha slider
            if editor.adjusting_alpha:
                editor.adjusting_alpha = False
                return True # Event handled

            # Handle drawing end - NO LONGER NEEDED HERE
            # if editor.drawing:
            #     editor.drawing = False
            #     return True

            # Handle selection end
            elif editor.mode == 'select' and editor.selection.selecting:
                # End selection regardless of where mouse is released? Or only if over canvas?
                # Current logic uses position from event. Let's assume release anywhere ends it.
                clicked_sprite_editor = editor._get_sprite_editor_at_pos(event.pos)
                # Need the sprite editor instance where selection *started* potentially,
                # but for now, just use the current one if available. If released outside,
                # end_selection might use the last known end_pos. This needs selection_manager logic check.
                # For now, assume end_selection handles release position correctly.
                # We might need to store which editor the selection started on if it matters.
                editor.selection.end_selection(event.pos, clicked_sprite_editor if clicked_sprite_editor else editor.sprites[editor.current_sprite]) # Pass editor instance, fallback to current if released outside
                editor.selection.selecting = False # Turn off selecting flag
                # Keep editor.selection.active True
                return True

        elif event.button == 2: # Middle button release
            if editor.panning:
                editor.panning = False
                pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW) # Change cursor back
                return True # Panning stopped

        return False # Event not handled

    def _handle_key_down(self, event):
        """Handles key down events when no dialog is active."""
        editor = self.editor

        # Modifier keys (Ctrl/Cmd) for shortcuts
        modifier_pressed = event.mod & KMOD_META or event.mod & KMOD_CTRL

        if modifier_pressed:
            if event.key == K_z:
                editor.undo()
                return True
            if event.key == K_y:
                editor.redo()
                return True
            if event.key == K_c and editor.mode == 'select':
                 editor.copy_selection()
                 return True
            if event.key == K_v:
                 editor.paste_selection()
                 return True
            # Add other Ctrl/Cmd shortcuts (e.g., Save - K_s?)
            # if event.key == K_s:
            #     editor.save_current() # Assuming a generic save method exists
            #     return True

        # Non-modifier key actions
        else:
            # --- Background Panning with Arrow Keys --- 
            if editor.edit_mode == 'background':
                panned = False
                if event.key == pygame.K_LEFT:
                    editor.view_offset_x -= config.PAN_SPEED_PIXELS
                    panned = True
                elif event.key == pygame.K_RIGHT:
                    editor.view_offset_x += config.PAN_SPEED_PIXELS
                    panned = True
                elif event.key == pygame.K_UP:
                    editor.view_offset_y -= config.PAN_SPEED_PIXELS
                    panned = True
                elif event.key == pygame.K_DOWN:
                    editor.view_offset_y += config.PAN_SPEED_PIXELS
                    panned = True
                
                if panned:
                    # Clamp view offset after panning
                    if editor.current_background:
                        scaled_width = int(editor.current_background.get_width() * editor.editor_zoom)
                        scaled_height = int(editor.current_background.get_height() * editor.editor_zoom)
                        max_offset_x = max(0, scaled_width - editor.canvas_rect.width)
                        max_offset_y = max(0, scaled_height - editor.canvas_rect.height)
                        editor.view_offset_x = max(0, min(editor.view_offset_x, max_offset_x))
                        editor.view_offset_y = max(0, min(editor.view_offset_y, max_offset_y))
                    return True # Arrow key handled for panning
            # --- End Background Panning ---
            
            # Add other non-modifier key actions here (e.g., tool switching)
            # if event.key == K_d: editor.set_tool('draw')
            # ...
            pass

        return False # Event not handled

    def _update_alpha_slider(self, mouse_pos):
        """Helper to update REFERENCE alpha value and knob position based on mouse click/drag."""
        editor = self.editor
        # Calculate relative x position within the slider track
        click_x_relative = mouse_pos[0] - editor.ref_alpha_slider_rect.x
        # Clamp relative position to bounds [0, slider_width]
        click_x_relative = max(0, min(editor.ref_alpha_slider_rect.width, click_x_relative))

        # Calculate effective width for ratio (slider width minus knob width for better feel?)
        # Or just use full slider width? Let's try full width first.
        slider_width_effective = editor.ref_alpha_slider_rect.width
        if slider_width_effective <= 0: slider_width_effective = 1 # Avoid division by zero

        # Calculate new alpha value (0-255)
        new_alpha = (click_x_relative / slider_width_effective) * 255
        editor.set_reference_alpha(new_alpha) # This clamps and applies alpha

        # Update knob position visually based on the relative click/drag position
        # Adjust the knob's center based on the relative click pos within the slider track
        # Ensure knob stays within bounds
        knob_center_x = editor.ref_alpha_slider_rect.x + click_x_relative
        editor.ref_alpha_knob_rect.centerx = knob_center_x
        # Clamp knob position fully within slider track bounds
        editor.ref_alpha_knob_rect.left = max(editor.ref_alpha_slider_rect.left, editor.ref_alpha_knob_rect.left)
        editor.ref_alpha_knob_rect.right = min(editor.ref_alpha_slider_rect.right, editor.ref_alpha_knob_rect.right)

    def _update_subject_alpha_slider(self, mouse_pos):
        """Helper to update SUBJECT alpha value and knob position based on mouse click/drag."""
        editor = self.editor
        # Calculate relative x position within the subject slider track
        click_x_relative = mouse_pos[0] - editor.subj_alpha_slider_rect.x
        click_x_relative = max(0, min(editor.subj_alpha_slider_rect.width, click_x_relative))

        slider_width_effective = editor.subj_alpha_slider_rect.width
        if slider_width_effective <= 0: slider_width_effective = 1

        # Calculate new alpha value (0-255)
        new_alpha = (click_x_relative / slider_width_effective) * 255
        editor.set_subject_alpha(new_alpha) # This clamps, updates alpha, and moves knob

# Note: This EventHandler assumes it receives the main Editor instance.
# Dependencies like editor.Button need to be handled (either import Button here or access via editor.Button).
# Methods like editor._handle_canvas_click, editor._get_sprite_editor_at_pos, editor.save_state, etc.,
# are called directly on the editor instance for now. These might be further refactored later.
