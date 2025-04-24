#!/usr/bin/env python
import pygame
import os
import shutil

# --- Configuration ---
SPRITES_DIR = "sprites"
BACKUP_DIR = "sprites_backup"
NATIVE_SPRITE_RESOLUTION = (32, 32)
# --- End Configuration ---

def convert_sprites():
    """ 
    Converts sprites in SPRITES_DIR to NATIVE_SPRITE_RESOLUTION,
    backing up originals to BACKUP_DIR first.
    """
    pygame.init() # Need Pygame for loading and scaling
    print("Starting sprite conversion...")
    
    if not os.path.isdir(SPRITES_DIR):
        print(f"Error: Sprites directory '{SPRITES_DIR}' not found. Aborting.")
        return
        
    # Create backup directory if it doesn't exist
    if not os.path.exists(BACKUP_DIR):
        try:
            os.makedirs(BACKUP_DIR)
            print(f"Created backup directory: {BACKUP_DIR}")
        except OSError as e:
            print(f"Error creating backup directory '{BACKUP_DIR}': {e}. Aborting.")
            return
    else:
         print(f"Backup directory '{BACKUP_DIR}' already exists.")

    converted_count = 0
    skipped_count = 0
    backup_count = 0
    error_count = 0

    # Iterate through files in the sprites directory
    print(f"Scanning directory: {SPRITES_DIR}")
    for filename in os.listdir(SPRITES_DIR):
        if filename.lower().endswith('.png'):
            original_path = os.path.join(SPRITES_DIR, filename)
            backup_path = os.path.join(BACKUP_DIR, filename)
            
            # 1. Backup the original file
            try:
                if not os.path.exists(backup_path):
                     shutil.copy2(original_path, backup_path) # copy2 preserves metadata
                     print(f"  Backed up: {filename} -> {BACKUP_DIR}/")
                     backup_count += 1
                # else: Skip backup if already exists in backup folder
                     
            except Exception as e:
                print(f"  Error backing up {filename}: {e}")
                error_count += 1
                continue # Skip processing this file if backup failed

            # 2. Load, Check Size, Scale if needed, and Overwrite
            try:
                img = pygame.image.load(original_path).convert_alpha()
                
                if img.get_size() != NATIVE_SPRITE_RESOLUTION:
                    print(f"  Converting: {filename} from {img.get_size()} to {NATIVE_SPRITE_RESOLUTION}")
                    scaled_img = pygame.transform.scale(img, NATIVE_SPRITE_RESOLUTION)
                    
                    # Create a new surface and blit the scaled image onto it
                    final_surface = pygame.Surface(NATIVE_SPRITE_RESOLUTION, pygame.SRCALPHA)
                    final_surface.fill((0,0,0,0)) # Ensure transparent background
                    final_surface.blit(scaled_img, (0,0))
                    
                    # Overwrite the original file with the new surface
                    pygame.image.save(final_surface, original_path)
                    converted_count += 1
                else:
                    # If already correct size, no need to re-save
                    skipped_count += 1
                    
            except pygame.error as e:
                print(f"  Error processing {filename}: {e}")
                error_count += 1
            except Exception as e:
                 print(f"  Unexpected error processing {filename}: {e}")
                 error_count += 1
                 
    print("\nConversion Summary:")
    print(f"  Files backed up: {backup_count}")
    print(f"  Files converted (resized): {converted_count}")
    print(f"  Files skipped (already correct size): {skipped_count}")
    print(f"  Errors encountered: {error_count}")
    print("Sprite conversion process complete.")
    pygame.quit()

if __name__ == "__main__":
    convert_sprites() 