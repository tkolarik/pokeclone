import json
import os
import sys
from typing import List, Optional, Tuple

import pygame

from src.core import config


def load_monsters():
    """Load monster data from disk.

    Returns a list of monster dicts or exits on fatal error to preserve existing behavior.
    """
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


class FileIOManager:
    def __init__(self, editor):
        self.editor = editor

    def load_backgrounds(self) -> List[Tuple[str, pygame.Surface]]:
        """Load available background images from the backgrounds directory."""
        backgrounds: List[Tuple[str, pygame.Surface]] = []
        for filename in os.listdir(config.BACKGROUND_DIR):
            if filename.endswith(".png"):
                path = os.path.join(config.BACKGROUND_DIR, filename)
                try:
                    bg = pygame.image.load(path).convert_alpha()
                    backgrounds.append((filename, bg))
                except pygame.error as e:
                    print(f"Failed to load background {filename}: {e}")
        return backgrounds

    def save_background(self, surface: pygame.Surface, filename: str) -> Optional[str]:
        """Save a background surface to disk. Returns full path on success."""
        if not filename:
            return None
        if not filename.endswith(".png"):
            filename += ".png"
        base_filename = os.path.basename(filename)
        full_path = os.path.join(config.BACKGROUND_DIR, base_filename)
        try:
            pygame.image.save(surface, full_path)
        except pygame.error as e:
            print(f"Error saving background {full_path}: {e}")
            return None
        return full_path

    def load_background(self, filename_or_path: str) -> Optional[pygame.Surface]:
        """Load a background surface from disk using a filename or full path."""
        if not filename_or_path:
            return None
        path = filename_or_path
        if not os.path.isabs(path):
            path = os.path.join(config.BACKGROUND_DIR, filename_or_path)
        try:
            return pygame.image.load(path).convert_alpha()
        except (pygame.error, FileNotFoundError) as e:
            print(f"Error loading background {path}: {e}")
            return None

    def load_reference_image(self, file_path: str) -> Optional[pygame.Surface]:
        """Load a reference image surface from disk."""
        if not file_path:
            return None
        try:
            return pygame.image.load(file_path).convert_alpha()
        except (pygame.error, FileNotFoundError) as e:
            print(f"Error loading reference image {file_path}: {e}")
            return None
