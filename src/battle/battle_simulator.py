import pygame
import sys
import random
import os
import json
import copy

# Import the centralized config
# from ..core import config # Relative import
from src.core import config # Absolute import from src

# Initialize Pygame
pygame.init()
pygame.mixer.init()

# Screen dimensions from config
# WIDTH, HEIGHT = 1200, 600
SCREEN = pygame.display.set_mode((config.BATTLE_WIDTH, config.BATTLE_HEIGHT))
pygame.display.set_caption("Battle Simulator")

# Font from config
FONT = pygame.font.Font(config.DEFAULT_FONT, config.BATTLE_FONT_SIZE)

# Constants from config
# STAT_CHANGE_MULTIPLIER = 0.66 # Defined constant for stat changes
# NATIVE_SPRITE_RESOLUTION = (32, 32)

class Move:
    def __init__(self, name, type_, power, effect=None):
        self.name = name
        self.type = type_
        self.power = power
        self.effect = effect

class Creature:
    def __init__(self, name, type_, max_hp, attack, defense, moves, sprite,
                 level=1, base_stats=None, move_pool=None, learnset=None):
        self.name = name
        self.type = type_
        self.level = level
        self.base_stats = base_stats or {
            "max_hp": max_hp,
            "attack": attack,
            "defense": defense,
        }
        self.max_hp = max_hp
        self.current_hp = max_hp
        self.attack = attack
        self.defense = defense
        self.moves = moves
        self.move_pool = move_pool or []
        self.learnset = learnset or []
        # Sprite is expected to be native resolution here
        # Scaling happens in draw_battle
        self.sprite = sprite

    def is_alive(self):
        return self.current_hp > 0

# Load type effectiveness chart
# Use path from config
with open(os.path.join(config.DATA_DIR, 'type_chart.json'), 'r') as f:
    type_chart = json.load(f)

def clamp_level(level):
    try:
        level_value = int(level)
    except (TypeError, ValueError):
        level_value = config.DEFAULT_MONSTER_LEVEL
    return max(config.MIN_MONSTER_LEVEL, min(config.MAX_MONSTER_LEVEL, level_value))

def level_modifier(level):
    return 1 + (clamp_level(level) - 1) * config.LEVEL_STAT_GROWTH

def scale_stat(base_stat, level):
    return max(1, int(round(base_stat * level_modifier(level))))

def scale_stats(base_stats, level):
    return {
        "max_hp": scale_stat(base_stats.get("max_hp", 1), level),
        "attack": scale_stat(base_stats.get("attack", 1), level),
        "defense": scale_stat(base_stats.get("defense", 1), level),
    }

def normalize_base_stats(monster):
    base_stats = monster.get("base_stats")
    if not base_stats:
        base_stats = {
            "max_hp": monster.get("max_hp", 1),
            "attack": monster.get("attack", 1),
            "defense": monster.get("defense", 1),
        }
    return {
        "max_hp": int(base_stats.get("max_hp", 1)),
        "attack": int(base_stats.get("attack", 1)),
        "defense": int(base_stats.get("defense", 1)),
    }

def normalize_move_pool(monster):
    move_pool = monster.get("move_pool")
    if not move_pool:
        move_pool = monster.get("moves", [])
    return list(move_pool)

def normalize_learnset(monster, move_pool):
    learnset = monster.get("learnset")
    if learnset:
        return learnset
    return [{"level": 1, "move": move} for move in move_pool]

def flatten_learnset(learnset):
    flattened = []
    for entry in learnset:
        level = entry.get("level", 1)
        try:
            level = int(level)
        except (TypeError, ValueError):
            level = 1
        if "move" in entry:
            flattened.append((level, entry["move"]))
        elif "moves" in entry:
            for move_name in entry["moves"]:
                flattened.append((level, move_name))
    return flattened

def build_moves_for_level(learnset, level, moves_dict):
    flattened = flatten_learnset(learnset)
    available = [move_name for lvl, move_name in flattened if lvl <= level]
    if not available:
        available = [move_name for _, move_name in flattened]
    seen = set()
    ordered = []
    for move_name in available:
        if move_name not in seen:
            seen.add(move_name)
            ordered.append(move_name)
    if len(ordered) > config.MAX_BATTLE_MOVES:
        ordered = ordered[-config.MAX_BATTLE_MOVES:]
    return [moves_dict.get(move_name, Move(move_name, 'Normal', 50)) for move_name in ordered]

def apply_stat_change(creature, stat, change):
    """Applies a stat change multiplier to a creature's specified stat."""
    if hasattr(creature, stat):
        current_stat_value = getattr(creature, stat)
        if change > 0:
            # Formula for increasing stat stage
            multiplier = 1 + config.STAT_CHANGE_MULTIPLIER / (2 ** (change - 1))
            new_stat_value = int(current_stat_value * multiplier)
        elif change < 0: # Check for negative change explicitly
            # Formula for decreasing stat stage
            # Use abs(change) for the exponent
            divider = 1 + config.STAT_CHANGE_MULTIPLIER / (2 ** (abs(change) - 1))
            # Avoid division by zero if divider somehow becomes 0 (unlikely with current formula)
            if divider == 0:
                print(f"Warning: Stat change divider became zero for stat {stat}, change {change}. Stat unchanged.")
                new_stat_value = current_stat_value
            else:
                 new_stat_value = int(current_stat_value / divider)
        else: # change == 0
            # No change if change is zero
            new_stat_value = current_stat_value

        setattr(creature, stat, new_stat_value)
        # print(f"Debug: Applied change {change} to {stat}. Old: {current_stat_value}, New: {new_stat_value}") # Optional debug print
    else:
        print(f"Warning: Stat '{stat}' not found on creature {creature.name}.")

def calculate_damage(attacker, defender, move):
    if move.power == 0:  # Stat-changing move
        if move.effect['target'] == 'self':
            apply_stat_change(attacker, move.effect['stat'], move.effect['change'])
        else:  # 'opponent'
            apply_stat_change(defender, move.effect['stat'], -move.effect['change'])
        return 0, 1  # No damage, normal effectiveness

    effectiveness = type_chart.get(move.type, {}).get(defender.type, 1)
    base_damage = (10 * attacker.attack * move.power) / (30 * defender.defense)
    damage = int((base_damage + 2) * effectiveness * random.uniform(0.85, 1.0))
    
    
    return damage, effectiveness

def create_default_sprite():
    """Creates a default sprite at native resolution."""
    sprite = pygame.Surface(config.NATIVE_SPRITE_RESOLUTION, pygame.SRCALPHA)
    # Simple placeholder: gray square with border
    sprite.fill(config.GRAY_LIGHT)
    pygame.draw.rect(sprite, config.GRAY_DARK, sprite.get_rect(), 2)
    # Draw a simple question mark or symbol if desired
    # font = pygame.font.Font(config.DEFAULT_FONT, config.NATIVE_SPRITE_RESOLUTION[1] // 2)
    # text = font.render("?", True, config.BLACK)
    # text_rect = text.get_rect(center=sprite.get_rect().center)
    # sprite.blit(text, text_rect)
    return sprite

def create_sprite_from_file(filename):
    """Loads sprite at native resolution, scales down if necessary."""
    try:
        sprite = pygame.image.load(filename).convert_alpha()
        # Check if loaded image matches native resolution
        if sprite.get_size() != config.NATIVE_SPRITE_RESOLUTION:
            print(f"Warning: Loaded sprite {filename} size {sprite.get_size()} does not match native {config.NATIVE_SPRITE_RESOLUTION}. Scaling down.")
            sprite = pygame.transform.smoothscale(sprite, config.NATIVE_SPRITE_RESOLUTION)
        return sprite
    except pygame.error:
        print(f"Sprite file not found: {filename}")
        # Return a default native size sprite if file not found
        return create_default_sprite() 
    
def load_moves():
    moves_file = os.path.join(config.DATA_DIR, 'moves.json')
    try:
        with open(moves_file, 'r') as f:
            moves_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading {moves_file}: {e}")
        return {}
    return {
        move['name']: Move(move['name'], move['type'], move['power'], move.get('effect'))
        for move in moves_data
    }

def load_creatures(moves_dict=None):
    creatures = []
    # Use paths from config
    monsters_file = os.path.join(config.DATA_DIR, 'monsters.json')
    
    try:
        with open(monsters_file, 'r') as f:
            monsters_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading {monsters_file}: {e}")
        return [] # Return empty list if core data fails

    if moves_dict is None:
        moves_dict = load_moves()
    if not moves_dict:
        return []
    
    for monster in monsters_data:
        # Use path from config
        sprite_path = os.path.join(config.SPRITE_DIR, f"{monster['name']}_front.png")
        sprite = create_sprite_from_file(sprite_path)
        base_stats = normalize_base_stats(monster)
        move_pool = normalize_move_pool(monster)
        learnset = normalize_learnset(monster, move_pool)
        level = config.MIN_MONSTER_LEVEL
        scaled_stats = scale_stats(base_stats, level)
        moves = build_moves_for_level(learnset, level, moves_dict)
        creature = Creature(monster['name'], monster['type'], scaled_stats['max_hp'], 
                            scaled_stats['attack'], scaled_stats['defense'], moves, sprite,
                            level=level, base_stats=base_stats, move_pool=move_pool, learnset=learnset)
        creatures.append(creature)
    
    return creatures

def create_battle_creature(template, level, moves_dict, sprite):
    base_stats = getattr(template, "base_stats", {
        "max_hp": template.max_hp,
        "attack": template.attack,
        "defense": template.defense,
    })
    move_pool = getattr(template, "move_pool", [move.name for move in template.moves])
    learnset = getattr(template, "learnset", [{"level": 1, "move": move} for move in move_pool])
    scaled_stats = scale_stats(base_stats, level)
    moves = build_moves_for_level(learnset, level, moves_dict)
    return Creature(
        name=template.name,
        type_=template.type,
        max_hp=scaled_stats['max_hp'],
        attack=scaled_stats['attack'],
        defense=scaled_stats['defense'],
        moves=moves,
        sprite=sprite,
        level=clamp_level(level),
        base_stats=base_stats,
        move_pool=move_pool,
        learnset=learnset,
    )

class Button:
    def __init__(self, rect, text, action=None):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.action = action
        self.color = config.BUTTON_COLOR
        self.hover_color = config.BUTTON_HOVER_COLOR
        self.font = pygame.font.Font(config.DEFAULT_FONT, config.BUTTON_FONT_SIZE)

    def draw(self, surface):
        mouse_pos = pygame.mouse.get_pos()
        is_hover = self.rect.collidepoint(mouse_pos)
        color = self.hover_color if is_hover else self.color
        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, config.BLACK, self.rect, 2)
        text_surf = self.font.render(self.text, True, config.BLACK)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def is_clicked(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                return True
        return False

def draw_battle(creature1, creature2, buttons, background):
    SCREEN.blit(background, (0, 0))

    # Sprites are stored at native resolution in creature.sprite
    # Scale them ONCE here for display
    display_size = config.BATTLE_SPRITE_DISPLAY_SIZE
    
    # Use nearest-neighbor scaling (scale) for pixel art feel
    creature1_display_sprite = pygame.transform.scale(creature1.sprite, display_size)
    creature2_display_sprite = pygame.transform.scale(creature2.sprite, display_size)

    # Draw creatures higher up, adjusting position based on new display size
    SCREEN.blit(creature1_display_sprite, (100, config.BATTLE_HEIGHT - display_size[1] - 200))
    SCREEN.blit(creature2_display_sprite, (config.BATTLE_WIDTH - display_size[0] - 100, config.BATTLE_HEIGHT - display_size[1] - 200))

    # Draw HP bars
    hp_bar_width = 200
    hp_bar_height = 20
    pygame.draw.rect(SCREEN, config.BLACK, (100, 100, hp_bar_width, hp_bar_height))
    pygame.draw.rect(SCREEN, config.HP_BAR_COLOR, (100, 100, hp_bar_width * (creature1.current_hp / creature1.max_hp), hp_bar_height))
    pygame.draw.rect(SCREEN, config.BLACK, (config.BATTLE_WIDTH - 100 - hp_bar_width, 100, hp_bar_width, hp_bar_height))
    pygame.draw.rect(SCREEN, config.HP_BAR_COLOR, (config.BATTLE_WIDTH - 100 - hp_bar_width, 100, hp_bar_width * (creature2.current_hp / creature2.max_hp), hp_bar_height))

    # Draw names and HP
    name1 = FONT.render(f"{creature1.name} Lv{creature1.level} HP: {creature1.current_hp}/{creature1.max_hp}", True, config.BLACK)
    name2 = FONT.render(f"{creature2.name} Lv{creature2.level} HP: {creature2.current_hp}/{creature2.max_hp}", True, config.BLACK)
    SCREEN.blit(name1, (100, 80))
    SCREEN.blit(name2, (config.BATTLE_WIDTH - 100 - hp_bar_width, 80))

    # Draw attack and defense stats
    attack1 = FONT.render(f"ATK: {creature1.attack}", True, config.BLACK)
    defense1 = FONT.render(f"DEF: {creature1.defense}", True, config.BLACK)
    attack2 = FONT.render(f"ATK: {creature2.attack}", True, config.BLACK)
    defense2 = FONT.render(f"DEF: {creature2.defense}", True, config.BLACK)
    
    SCREEN.blit(attack1, (100, 130))
    SCREEN.blit(defense1, (100, 160))
    SCREEN.blit(attack2, (config.BATTLE_WIDTH - 100 - hp_bar_width, 130))
    SCREEN.blit(defense2, (config.BATTLE_WIDTH - 100 - hp_bar_width, 160))

    # Draw move buttons (smaller and at the bottom)
    button_width = 150
    button_height = 40
    button_spacing = 10
    total_width = len(buttons) * (button_width + button_spacing) - button_spacing
    start_x = (config.BATTLE_WIDTH - total_width) // 2
    start_y = config.BATTLE_HEIGHT - button_height - 20

    for i, button in enumerate(buttons):
        button.rect.x = start_x + i * (button_width + button_spacing)
        button.rect.y = start_y
        button.rect.width = button_width
        button.rect.height = button_height
        button.draw(SCREEN)

    pygame.display.flip()

def opponent_choose_move(creature):
    return random.choice(creature.moves)

def play_random_song():
    # Use path from config
    songs_dir = config.SONGS_DIR
    try:
        songs = [f for f in os.listdir(songs_dir) if f.endswith('.mp3') or f.endswith('.wav')]
        if songs:
            random_song = random.choice(songs)
            pygame.mixer.music.load(os.path.join(songs_dir, random_song))
            pygame.mixer.music.play(-1)  # -1 means loop indefinitely
        else:
             print(f"No songs found in {songs_dir}")
    except FileNotFoundError:
         print(f"Songs directory not found: {songs_dir}")
    except pygame.error as e:
         print(f"Error loading or playing song: {e}")

def stop_music():
    pygame.mixer.music.stop()

def load_random_background():
    # Use path from config
    backgrounds_dir = config.BACKGROUND_DIR
    try:
        backgrounds = [f for f in os.listdir(backgrounds_dir) if f.endswith('.png')]
        if backgrounds:
            background_path = os.path.join(backgrounds_dir, random.choice(backgrounds))
            background = pygame.image.load(background_path).convert_alpha()
            # Scale background to fit battle screen size
            return pygame.transform.scale(background, (config.BATTLE_WIDTH, config.BATTLE_HEIGHT))
        else:
             print(f"No backgrounds found in {backgrounds_dir}. Using default.")
    except FileNotFoundError:
         print(f"Backgrounds directory not found: {backgrounds_dir}. Using default.")
    except pygame.error as e:
         print(f"Error loading background: {e}. Using default.")
         
    # Default fallback background
    default_bg = pygame.Surface((config.BATTLE_WIDTH, config.BATTLE_HEIGHT), pygame.SRCALPHA)
    default_bg.fill((*config.BATTLE_BG_COLOR, 255))  # Ensure full opacity
    return default_bg

def prompt_for_level(prompt_text, default_level):
    input_text = ""
    hint_font = pygame.font.Font(config.DEFAULT_FONT, config.BATTLE_FONT_SIZE - 6)
    clock = pygame.time.Clock()

    while True:
        SCREEN.fill(config.BATTLE_BG_COLOR)
        prompt_surf = FONT.render(prompt_text, True, config.BLACK)
        prompt_rect = prompt_surf.get_rect(center=(config.BATTLE_WIDTH // 2, config.BATTLE_HEIGHT // 2 - 60))
        SCREEN.blit(prompt_surf, prompt_rect)

        value_text = input_text if input_text else str(default_level)
        value_surf = FONT.render(f"Level: {value_text}", True, config.BLACK)
        value_rect = value_surf.get_rect(center=(config.BATTLE_WIDTH // 2, config.BATTLE_HEIGHT // 2))
        SCREEN.blit(value_surf, value_rect)

        hint_surf = hint_font.render("Enter = confirm, Esc = default", True, config.GRAY_DARK)
        hint_rect = hint_surf.get_rect(center=(config.BATTLE_WIDTH // 2, config.BATTLE_HEIGHT // 2 + 50))
        SCREEN.blit(hint_surf, hint_rect)

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    level_value = int(input_text) if input_text else default_level
                    return clamp_level(level_value)
                if event.key == pygame.K_ESCAPE:
                    return clamp_level(default_level)
                if event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                elif event.unicode.isdigit() and len(input_text) < 3:
                    input_text += event.unicode

        clock.tick(config.FPS)

def battle(creature1, creature2):
    clock = pygame.time.Clock()
    running = True
    turn = 0  # 0 for player's turn, 1 for opponent's turn

    play_random_song()

    # Create buttons for player's moves
    buttons = []
    button_width = 150
    button_height = 40
    button_spacing = 10
    total_width = len(creature1.moves) * (button_width + button_spacing) - button_spacing
    start_x = (config.BATTLE_WIDTH - total_width) // 2
    start_y = config.BATTLE_HEIGHT - button_height - 20
    for i, move in enumerate(creature1.moves):
        rect = (start_x + i * (button_width + button_spacing), start_y, button_width, button_height)
        button = Button(rect, move.name, action=move)
        buttons.append(button)

    background = load_random_background()

    while running:
        # Clear the screen using config color
        SCREEN.fill(config.BATTLE_BG_COLOR)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                stop_music()
                pygame.quit()
                sys.exit()

            if turn == 0 and creature1.is_alive() and creature2.is_alive():
                for button in buttons:
                    if button.is_clicked(event):
                        move = button.action
                        damage, effectiveness = calculate_damage(creature1, creature2, move)
                        creature2.current_hp -= damage
                        if creature2.current_hp < 0:
                            creature2.current_hp = 0
                        if move.power == 0:
                            print(f"{creature1.name} used {move.name}!")
                            if move.effect['target'] == 'self':
                                print(f"{creature1.name}'s {move.effect['stat']} {'increased' if move.effect['change'] > 0 else 'decreased'}!")
                            else:
                                print(f"{creature2.name}'s {move.effect['stat']} {'decreased' if move.effect['change'] > 0 else 'increased'}!")
                        else:
                            print(f"{creature1.name} used {move.name}! It dealt {damage} damage.")
                        turn = 1  # Switch turn

        if turn == 1 and creature2.is_alive() and creature1.is_alive():
            pygame.time.delay(1000)  # Pause before opponent's move
            move = opponent_choose_move(creature2)
            damage, effectiveness = calculate_damage(creature2, creature1, move)
            creature1.current_hp -= damage
            if creature1.current_hp < 0:
                creature1.current_hp = 0
            if move.power == 0:
                print(f"{creature2.name} used {move.name}!")
                if move.effect['target'] == 'self':
                    print(f"{creature2.name}'s {move.effect['stat']} {'increased' if move.effect['change'] > 0 else 'decreased'}!")
                else:
                    print(f"{creature1.name}'s {move.effect['stat']} {'decreased' if move.effect['change'] > 0 else 'increased'}!")
            else:
                print(f"{creature2.name} used {move.name}! It dealt {damage} damage.")
            turn = 0  # Switch turn

        draw_battle(creature1, creature2, buttons, background)

        # Check for win condition
        if not creature1.is_alive() or not creature2.is_alive():
            winner = creature1.name if creature1.is_alive() else creature2.name
            message = FONT.render(f"{winner} wins!", True, config.BLACK)
            SCREEN.blit(message, (config.BATTLE_WIDTH // 2 - message.get_width() // 2, config.BATTLE_HEIGHT // 2 - message.get_height() // 2))
            pygame.display.flip()
            pygame.time.delay(3000)
            stop_music()
            return show_end_options()

        clock.tick(config.FPS) # Use FPS from config

def show_end_options():
    # Center buttons on battle screen dimensions
    new_battle_button = Button((config.BATTLE_WIDTH // 2 - 150, config.BATTLE_HEIGHT // 2 - 60, 300, 50), "New Battle")
    quit_button = Button((config.BATTLE_WIDTH // 2 - 150, config.BATTLE_HEIGHT // 2 + 10, 300, 50), "Quit")

    while True:
        SCREEN.fill(config.BATTLE_BG_COLOR)
        new_battle_button.draw(SCREEN)
        quit_button.draw(SCREEN)
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.MOUSEBUTTONDOWN:
                if new_battle_button.is_clicked(event):
                    return True
                if quit_button.is_clicked(event):
                    return False

def main():
    moves_dict = load_moves()
    creatures = load_creatures(moves_dict)
    if len(creatures) < 2:
        print("Not enough creatures to battle. Please add more creature data.")
        return

    # Font for hints (can reuse FONT or create a specific one)
    hint_font = pygame.font.Font(config.DEFAULT_FONT, config.BATTLE_FONT_SIZE - 2) # Slightly smaller

    while True:
        # Constants for grid layout
        GRID_COLS = 3
        GRID_ROWS = 2
        CREATURES_PER_PAGE = GRID_COLS * GRID_ROWS
        BUTTON_WIDTH = 350
        BUTTON_HEIGHT = 80
        BUTTON_SPACING = 20
        
        # Calculate grid positions based on battle screen size
        start_x = (config.BATTLE_WIDTH - (BUTTON_WIDTH * GRID_COLS + BUTTON_SPACING * (GRID_COLS - 1))) // 2
        start_y = (config.BATTLE_HEIGHT - (BUTTON_HEIGHT * GRID_ROWS + BUTTON_SPACING * (GRID_ROWS - 1))) // 2

        # Pagination variables
        current_page = 0
        total_pages = (len(creatures) + CREATURES_PER_PAGE - 1) // CREATURES_PER_PAGE

        player_creature = None
        selected_index = 0
        selected_player_creature = None

        # Hint variables
        nav_hint_text = ""
        hint_display_start_time = 0
        HINT_DURATION_MS = 1500 # Display hint for 1.5 seconds

        while selected_player_creature is None:
            current_time = pygame.time.get_ticks() # Get current time for hint timer
            SCREEN.fill(config.BATTLE_BG_COLOR)
            title = FONT.render("Choose your monster:", True, config.BLACK)
            SCREEN.blit(title, (config.BATTLE_WIDTH // 2 - title.get_width() // 2, 20))

            # Display page number
            page_info = FONT.render(f"Page {current_page + 1}/{total_pages}", True, config.BLACK)
            SCREEN.blit(page_info, (config.BATTLE_WIDTH // 2 - page_info.get_width() // 2, config.BATTLE_HEIGHT - 30))

            # Create and draw buttons for the current page
            buttons = []
            start_creature_index = current_page * CREATURES_PER_PAGE
            end_creature_index = min(start_creature_index + CREATURES_PER_PAGE, len(creatures))
            num_buttons_on_page = end_creature_index - start_creature_index

            for i in range(num_buttons_on_page):
                creature_index = start_creature_index + i
                creature = creatures[creature_index]
                row = i // GRID_COLS
                col = i % GRID_COLS
                x = start_x + col * (BUTTON_WIDTH + BUTTON_SPACING)
                y = start_y + row * (BUTTON_HEIGHT + BUTTON_SPACING)

                button = Button((x, y, BUTTON_WIDTH, BUTTON_HEIGHT), creature.name, action=creature)
                buttons.append(button)
                button.draw(SCREEN)

                # Highlight the selected button
                if i == selected_index:
                    pygame.draw.rect(SCREEN, config.GREEN, button.rect, 3)  # Green border

                # Display the creature's sprite next to the button
                creature_sprite = pygame.transform.scale(creature.sprite, (64, 64))
                SCREEN.blit(creature_sprite, (x + 5 , y + (BUTTON_HEIGHT - 64) // 2))

            # --- Display Navigation Hint ---
            if nav_hint_text and (current_time - hint_display_start_time < HINT_DURATION_MS):
                hint_surf = hint_font.render(nav_hint_text, True, config.RED) # Use a noticeable color
                # Position hint near the bottom page number
                hint_rect = hint_surf.get_rect(center=(config.BATTLE_WIDTH // 2, config.BATTLE_HEIGHT - 60))
                SCREEN.blit(hint_surf, hint_rect)
            else:
                nav_hint_text = "" # Clear hint if time expired
            # -------------------------------

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                # Check KEYDOWN first
                elif event.type == pygame.KEYDOWN:
                    # Clear previous hint on NEW key press
                    nav_hint_text = ""
                    # num_buttons_on_page calculated above
                    if num_buttons_on_page == 0: continue

                    # --- Intra-page Navigation --- 
                    if event.key == pygame.K_DOWN:
                        # Move down, wrapping around columns
                        if selected_index + GRID_COLS < num_buttons_on_page:
                            selected_index += GRID_COLS
                        else:
                            # Wrap to top row if possible, otherwise stay in last row
                            new_index = selected_index % GRID_COLS
                            if new_index < num_buttons_on_page:
                                selected_index = new_index
                            # else: stay at current index if wrapping leads nowhere valid
                    elif event.key == pygame.K_UP:
                        # Move up, wrapping around columns
                        if selected_index - GRID_COLS >= 0:
                            selected_index -= GRID_COLS
                        else:
                            # Wrap to bottom-most item in the same column
                            col = selected_index % GRID_COLS
                            last_row_items = num_buttons_on_page % GRID_COLS
                            last_full_row_index = num_buttons_on_page - last_row_items if last_row_items != 0 else num_buttons_on_page - GRID_COLS
                            target_index = last_full_row_index + col
                            if target_index >= num_buttons_on_page:
                                # If the target in the last row doesn't exist, go to the row above it
                                target_index -= GRID_COLS 
                            if target_index >= 0:
                                selected_index = target_index
                            # else: stay at current index if wrapping leads nowhere valid
                    elif event.key == pygame.K_RIGHT:
                        # Check if already at the last item on the page
                        if selected_index == num_buttons_on_page - 1:
                            if current_page < total_pages - 1:
                                nav_hint_text = "Press ] for Next Page"
                                hint_display_start_time = current_time
                            # Don't wrap around selection index if at edge and hint shown
                        elif selected_index + 1 < num_buttons_on_page:
                            selected_index += 1
                        # else: # Original wrap logic removed, hint handles the edge case
                        #     selected_index = 0 
                    elif event.key == pygame.K_LEFT:
                        # Check if already at the first item on the page
                        if selected_index == 0:
                            if current_page > 0:
                                nav_hint_text = "Press [ for Prev Page"
                                hint_display_start_time = current_time
                            # Don't wrap around selection index if at edge and hint shown
                        elif selected_index - 1 >= 0:
                            selected_index -= 1
                        # else: # Original wrap logic removed, hint handles the edge case
                        #      selected_index = num_buttons_on_page - 1
                    
                    # --- Page Navigation (Existing) --- 
                    elif event.key == pygame.K_RIGHTBRACKET: # Use ] for next page
                        if current_page < total_pages - 1:
                            current_page += 1
                            selected_index = 0 # Reset index on page change
                    elif event.key == pygame.K_LEFTBRACKET: # Use [ for previous page
                        if current_page > 0:
                            current_page -= 1
                            selected_index = 0 # Reset index on page change

                    # --- Selection (Existing) --- 
                    elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                        if 0 <= selected_index < num_buttons_on_page:
                            # Check if buttons list is valid for the index
                            if selected_index < len(buttons):
                                selected_player_creature = buttons[selected_index].action
                            else:
                                print(f"Error: selected_index {selected_index} out of range for buttons list (len {len(buttons)}).")

                # Check MOUSEBUTTONDOWN next
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    # Clear previous hint on mouse click
                    nav_hint_text = ""
                    if event.button == 1:  # Left mouse button
                        for i, button in enumerate(buttons):
                            if button.rect.collidepoint(event.pos):
                                selected_player_creature = button.action
                                break
                
                # Can add other elif event checks here if needed

            pygame.display.flip()

        # Create NEW instances for the battle to avoid deepcopy issues with Surface
        # and ensure stats/HP are reset.
        player_sprite_path = os.path.join(config.SPRITE_DIR, f"{selected_player_creature.name}_front.png")
        player_sprite = create_sprite_from_file(player_sprite_path)
        player_level = prompt_for_level("Choose your monster level", config.DEFAULT_MONSTER_LEVEL)
        player_for_battle = create_battle_creature(
            template=selected_player_creature,
            level=player_level,
            moves_dict=moves_dict,
            sprite=player_sprite
        )

        # Choose a random opponent that isn't the player's creature
        selected_opponent_creature = random.choice([c for c in creatures if c.name != selected_player_creature.name])
        opponent_sprite_path = os.path.join(config.SPRITE_DIR, f"{selected_opponent_creature.name}_front.png")
        opponent_sprite = create_sprite_from_file(opponent_sprite_path)
        opponent_for_battle = create_battle_creature(
            template=selected_opponent_creature,
            level=config.DEFAULT_MONSTER_LEVEL,
            moves_dict=moves_dict,
            sprite=opponent_sprite
        )
        
        # Pass the new instances to the battle function
        continue_game = battle(player_for_battle, opponent_for_battle)
        
        if not continue_game:
            break

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
