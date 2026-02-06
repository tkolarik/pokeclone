import json
import os
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


Pixel = Tuple[int, int, int, int]
PixelBuffer = Dict[Tuple[int, int], Pixel]


@dataclass
class ClipboardEntry:
    entry_id: str
    pixels: PixelBuffer
    favorite: bool = False


class ClipboardManager:
    """Tracks clipboard history and persisted favorites for the editor."""

    def __init__(self, history_limit: int, favorites_path: str):
        self.history_limit = max(1, int(history_limit))
        self.favorites_path = favorites_path
        self.history: List[ClipboardEntry] = []
        self.active_index: int = -1

    def push(self, pixels: PixelBuffer, favorite: bool = False, entry_id: Optional[str] = None) -> Optional[ClipboardEntry]:
        normalized = self.normalize_pixels(pixels)
        if not normalized:
            return None

        signature = self._signature(normalized)
        existing_index = self._find_by_signature(signature)
        if existing_index is not None:
            existing = self.history.pop(existing_index)
            favorite = favorite or existing.favorite
            entry_id = entry_id or existing.entry_id

        new_entry = ClipboardEntry(entry_id=entry_id or str(uuid.uuid4()), pixels=normalized, favorite=favorite)
        self.history.insert(0, new_entry)
        self.history = self.history[: self.history_limit]
        self.active_index = 0
        return new_entry

    def get_active_entry(self) -> Optional[ClipboardEntry]:
        if not self.history:
            self.active_index = -1
            return None
        if self.active_index < 0 or self.active_index >= len(self.history):
            self.active_index = 0
        return self.history[self.active_index]

    def get_active_pixels(self) -> Optional[PixelBuffer]:
        active = self.get_active_entry()
        return self.clone_pixels(active.pixels) if active else None

    def cycle(self, direction: int) -> Optional[ClipboardEntry]:
        if not self.history:
            self.active_index = -1
            return None
        step = -1 if direction < 0 else 1
        if self.active_index < 0:
            self.active_index = 0
        else:
            self.active_index = (self.active_index + step) % len(self.history)
        return self.history[self.active_index]

    def set_active_favorite(self, favorite: bool) -> Optional[ClipboardEntry]:
        entry = self.get_active_entry()
        if not entry:
            return None
        entry.favorite = bool(favorite)
        return entry

    def toggle_active_favorite(self) -> Optional[ClipboardEntry]:
        entry = self.get_active_entry()
        if not entry:
            return None
        entry.favorite = not entry.favorite
        return entry

    def load_favorites(self) -> int:
        if not self.favorites_path or not os.path.exists(self.favorites_path):
            return 0
        try:
            with open(self.favorites_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return 0

        if not isinstance(data, list):
            return 0

        loaded = 0
        for record in reversed(data):
            if not isinstance(record, dict):
                continue
            pixels = self.deserialize_pixels(record.get("pixels"))
            if not pixels:
                continue
            self.push(
                pixels=pixels,
                favorite=True,
                entry_id=str(record.get("id") or uuid.uuid4()),
            )
            loaded += 1
        return loaded

    def save_favorites(self) -> bool:
        favorites = []
        for entry in self.history:
            if entry.favorite:
                favorites.append(
                    {
                        "id": entry.entry_id,
                        "pixels": self.serialize_pixels(entry.pixels),
                    }
                )

        directory = os.path.dirname(self.favorites_path)
        try:
            if directory and not os.path.isdir(directory):
                os.makedirs(directory, exist_ok=True)
            with open(self.favorites_path, "w", encoding="utf-8") as f:
                json.dump(favorites, f, indent=2)
        except OSError:
            return False
        return True

    def _find_by_signature(self, signature: Tuple[Tuple[int, int, int, int, int, int], ...]) -> Optional[int]:
        for idx, entry in enumerate(self.history):
            if self._signature(entry.pixels) == signature:
                return idx
        return None

    @staticmethod
    def _signature(pixels: PixelBuffer) -> Tuple[Tuple[int, int, int, int, int, int], ...]:
        rows = []
        for (x, y), (r, g, b, a) in pixels.items():
            rows.append((int(x), int(y), int(r), int(g), int(b), int(a)))
        rows.sort()
        return tuple(rows)

    @staticmethod
    def normalize_pixels(pixels: Optional[PixelBuffer]) -> PixelBuffer:
        if not isinstance(pixels, dict):
            return {}
        normalized: PixelBuffer = {}
        for key, value in pixels.items():
            if not isinstance(key, tuple) or len(key) != 2:
                continue
            try:
                if len(value) < 4:
                    continue
                x, y = int(key[0]), int(key[1])
                r, g, b, a = (int(value[0]), int(value[1]), int(value[2]), int(value[3]))
            except (TypeError, ValueError, IndexError):
                continue
            normalized[(x, y)] = (r, g, b, a)
        return normalized

    @staticmethod
    def clone_pixels(pixels: PixelBuffer) -> PixelBuffer:
        return {(x, y): (r, g, b, a) for (x, y), (r, g, b, a) in pixels.items()}

    @staticmethod
    def serialize_pixels(pixels: PixelBuffer) -> List[List[int]]:
        rows: List[List[int]] = []
        for (x, y), (r, g, b, a) in pixels.items():
            rows.append([int(x), int(y), int(r), int(g), int(b), int(a)])
        rows.sort(key=lambda row: (row[0], row[1], row[2], row[3], row[4], row[5]))
        return rows

    @staticmethod
    def deserialize_pixels(payload: Optional[List[List[int]]]) -> PixelBuffer:
        if not isinstance(payload, list):
            return {}
        pixels: PixelBuffer = {}
        for row in payload:
            if not isinstance(row, list) or len(row) != 6:
                continue
            x, y, r, g, b, a = [int(value) for value in row]
            pixels[(x, y)] = (r, g, b, a)
        return pixels
