import pygame
import os

# Initialize Pygame (required for surface creation)
pygame.init()

# Define image properties
width, height = 16, 16
filename = "test_ref_image.png"
assets_dir = os.path.join("tests", "assets")
filepath = os.path.join(assets_dir, filename)

# Create the surface
surface = pygame.Surface((width, height), pygame.SRCALPHA)

# Fill with distinct colors (e.g., quadrants)
red = (255, 0, 0, 255)
green = (0, 255, 0, 255)
blue = (0, 0, 255, 255)
yellow = (255, 255, 0, 255)
half_w, half_h = width // 2, height // 2

surface.fill(red, (0, 0, half_w, half_h))
surface.fill(green, (half_w, 0, width - half_w, half_h))
surface.fill(blue, (0, half_h, half_w, height - half_h))
surface.fill(yellow, (half_w, half_h, width - half_w, height - half_h))

# Save the image
try:
    pygame.image.save(surface, filepath)
    print(f"Successfully created test image: {filepath}")
except pygame.error as e:
    print(f"Error saving test image {filepath}: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
finally:
    # Quit Pygame
    pygame.quit() 