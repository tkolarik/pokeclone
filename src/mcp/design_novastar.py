#!/usr/bin/env python3
"""
Script to design Novastar sprites using the EditorApiController.
Implements the MCP monster drawing workflow programmatically.
"""
import sys
import os
import math

# Ensure we can import from src
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

try:
    from src.editor.api_control import EditorApiController
except ImportError:
    print("Error: Could not import EditorApiController. Run this from the project root.")
    sys.exit(1)

def get_star_points(cx, cy, outer_radius, inner_radius, num_points=5):
    points = []
    angle = -math.pi / 2  # Start at top
    step = math.pi / num_points
    
    for _ in range(num_points * 2):
        r = outer_radius if _ % 2 == 0 else inner_radius
        points.append((
            cx + int(math.cos(angle) * r),
            cy + int(math.sin(angle) * r)
        ))
        angle += step
    return points

def is_point_in_polygon(x, y, polygon):
    n = len(polygon)
    inside = False
    p1x, p1y = polygon[0]
    for i in range(n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x, p2y
    return inside

def rasterize_polygon(polygon, width=32, height=32):
    pixels = []
    for y in range(height):
        for x in range(width):
            if is_point_in_polygon(x, y, polygon):
                pixels.append({"x": x, "y": y})
    return pixels

def main():
    controller = EditorApiController()
    
    print("Starting session...")
    controller.start_session({})
    
    monster_name = "Novastar"
    print(f"Selecting {monster_name}...")
    try:
        controller.execute_action({"action": "select_monster", "monsterName": monster_name})
    except Exception:
        print("Novastar does not exist in monsters.json.")
        return

    # Palette
    COLOR_FILL = [255, 215, 0, 255]      # Gold
    COLOR_SHADE = [218, 165, 32, 255]    # Goldenrod
    COLOR_EYE = [0, 0, 0, 255]           # Black
    COLOR_HIGHLIGHT = [255, 255, 255, 255] # White
    
    # Generate Star Shape (Center 16,16; Outer 14, Inner 6)
    star_poly = get_star_points(16, 16, 14, 6)
    star_pixels = rasterize_polygon(star_poly)
    
    # --- FRONT SPRITE ---
    print("Drawing Front Sprite...")
    controller.execute_action({"action": "set_sprite", "sprite": "front"})
    
    # Draw Star Body
    controller.execute_action({"action": "set_color", "color": COLOR_FILL})
    controller.execute_action({"action": "draw_pixels", "points": star_pixels})
    
    # Face details
    eyes = [
        {"x": 13, "y": 14}, {"x": 13, "y": 15}, # Left Eye
        {"x": 19, "y": 14}, {"x": 19, "y": 15}, # Right Eye
    ]
    controller.execute_action({"action": "set_color", "color": COLOR_EYE})
    controller.execute_action({"action": "draw_pixels", "points": eyes})
    
    smile = [
        {"x": 15, "y": 18}, {"x": 16, "y": 18}, {"x": 17, "y": 18},
        {"x": 14, "y": 17}, {"x": 18, "y": 17}
    ]
    controller.execute_action({"action": "set_color", "color": COLOR_EYE})
    controller.execute_action({"action": "draw_pixels", "points": smile})
    
    highlights = [
        {"x": 12, "y": 13}, {"x": 18, "y": 13}
    ]
    controller.execute_action({"action": "set_color", "color": COLOR_HIGHLIGHT})
    controller.execute_action({"action": "draw_pixels", "points": highlights})

    # Checkpoint
    print("Checkpoint: Verifying Front Sprite...")
    controller.get_state()
    pixel_check = controller.execute_action({"action": "read_pixel", "x": 16, "y": 16})
    print(f"Center pixel check: {pixel_check}")

    # --- BACK SPRITE ---
    print("Drawing Back Sprite...")
    controller.execute_action({"action": "set_sprite", "sprite": "back"})
    
    # Draw Star Body
    controller.execute_action({"action": "set_color", "color": COLOR_FILL})
    controller.execute_action({"action": "draw_pixels", "points": star_pixels})
    
    # Shading (Center)
    shade_pixels = []
    for p in star_pixels:
        dx = p["x"] - 16
        dy = p["y"] - 16
        if dx*dx + dy*dy < 16: # Radius 4 circle in center
            shade_pixels.append(p)
            
    controller.execute_action({"action": "set_color", "color": COLOR_SHADE})
    controller.execute_action({"action": "draw_pixels", "points": shade_pixels})

    # Save
    print("Saving sprites...")
    res = controller.execute_action({"action": "save_monster_sprites"})
    print(f"Saved: {res}")

if __name__ == "__main__":
    main()
