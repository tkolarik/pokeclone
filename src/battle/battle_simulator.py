import pygame
import sys
import random
import os
import json

# Import the centralized config
# from ..core import config # Relative import
from src.core import config # Absolute import from src
from src.battle.engine import (
    BattleEngine,
    Creature,
    Move,
    NO_MOVE_FALLBACK_NAME as ENGINE_NO_MOVE_FALLBACK_NAME,
    apply_stat_change as engine_apply_stat_change,
    build_moves_for_level as engine_build_moves_for_level,
    calculate_damage as engine_calculate_damage,
    clamp_level as engine_clamp_level,
    flatten_learnset as engine_flatten_learnset,
    level_modifier as engine_level_modifier,
    opponent_choose_move as engine_opponent_choose_move,
    scale_stat as engine_scale_stat,
    scale_stats as engine_scale_stats,
)
from src.core.monster_schema import derive_move_pool_from_learnset, normalize_monster

AUDIO_ENABLED = False
_AUDIO_INIT_ATTEMPTED = False
SCREEN = None
FONT = None

_SFX_CACHE = {}

# Load type effectiveness chart
type_chart = {}
type_chart_path = os.path.join(config.DATA_DIR, 'type_chart.json')
try:
    with open(type_chart_path, 'r') as f:
        type_chart = json.load(f)
except (FileNotFoundError, json.JSONDecodeError, OSError) as e:
    print(f"Warning: failed to load type chart '{type_chart_path}': {e}")


def initialize_battle_runtime():
    global SCREEN
    if not pygame.get_init():
        pygame.init()
    if SCREEN is None:
        SCREEN = pygame.display.set_mode((config.BATTLE_WIDTH, config.BATTLE_HEIGHT))
        pygame.display.set_caption("Battle Simulator")
    _get_font()
    _initialize_audio()


def _initialize_audio():
    global AUDIO_ENABLED, _AUDIO_INIT_ATTEMPTED
    if _AUDIO_INIT_ATTEMPTED:
        return AUDIO_ENABLED
    _AUDIO_INIT_ATTEMPTED = True
    try:
        pygame.mixer.init()
        AUDIO_ENABLED = True
    except pygame.error as e:
        AUDIO_ENABLED = False
        print(f"Warning: Audio mixer unavailable: {e}")
    return AUDIO_ENABLED


def _get_screen():
    if SCREEN is None:
        initialize_battle_runtime()
    return SCREEN


def _get_font():
    global FONT
    if FONT is None:
        FONT = pygame.font.Font(config.DEFAULT_FONT, config.BATTLE_FONT_SIZE)
    return FONT


def _is_audio_ready():
    return AUDIO_ENABLED and pygame.mixer.get_init() is not None


def _resolve_sfx_path(event_key, move=None):
    if move is not None and getattr(move, "name", None):
        move_name = move.name
        move_candidates = [
            os.path.join(config.SOUNDS_DIR, "moves", f"{move_name}.wav"),
            os.path.join(config.SOUNDS_DIR, "moves", f"{move_name}.mp3"),
        ]
        for path in move_candidates:
            if os.path.exists(path):
                return path

    relative = config.BATTLE_SFX_EVENT_FILES.get(event_key)
    if not relative:
        return None
    absolute = os.path.join(config.SOUNDS_DIR, relative)
    return absolute if os.path.exists(absolute) else None


def _load_sfx(path):
    if path in _SFX_CACHE:
        return _SFX_CACHE[path]
    try:
        sound = pygame.mixer.Sound(path)
        _SFX_CACHE[path] = sound
        return sound
    except pygame.error as e:
        print(f"Failed to load SFX '{path}': {e}")
        return None


def play_battle_sfx(event_key, move=None):
    if not _is_audio_ready():
        return
    path = _resolve_sfx_path(event_key, move=move)
    if not path:
        return
    sound = _load_sfx(path)
    if sound is None:
        return
    try:
        sound.play()
    except pygame.error as e:
        print(f"Failed to play SFX '{path}': {e}")

def clamp_level(level):
    return engine_clamp_level(level)

def level_modifier(level):
    return engine_level_modifier(level)

def scale_stat(base_stat, level):
    return engine_scale_stat(base_stat, level)

def scale_stats(base_stats, level):
    return engine_scale_stats(base_stats, level)

def normalize_base_stats(monster):
    normalized, _warnings = normalize_monster(monster, strict_conflicts=False)
    return dict(normalized["base_stats"])

def normalize_move_pool(monster):
    normalized, _warnings = normalize_monster(monster, strict_conflicts=False)
    return derive_move_pool_from_learnset(normalized["learnset"])

def normalize_learnset(monster, move_pool):
    normalized, _warnings = normalize_monster(monster, strict_conflicts=False)
    return list(normalized["learnset"])

def flatten_learnset(learnset):
    return engine_flatten_learnset(learnset)

def build_moves_for_level(learnset, level, moves_dict):
    return engine_build_moves_for_level(learnset, level, moves_dict)

def apply_stat_change(creature, stat, change):
    engine_apply_stat_change(creature, stat, change)

def calculate_damage(attacker, defender, move):
    return engine_calculate_damage(
        attacker,
        defender,
        move,
        type_chart=type_chart,
        rng_uniform=random.uniform,
        stat_change_fn=engine_apply_stat_change,
    )

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
        normalized_monster, schema_warnings = normalize_monster(monster, strict_conflicts=False)
        for warning in schema_warnings:
            print(f"Monster schema warning: {warning}")

        sprite_path = os.path.join(config.SPRITE_DIR, f"{normalized_monster['name']}_front.png")
        sprite = create_sprite_from_file(sprite_path)
        base_stats = normalized_monster["base_stats"]
        learnset = normalized_monster["learnset"]
        move_pool = derive_move_pool_from_learnset(learnset)
        level = config.MIN_MONSTER_LEVEL
        scaled_stats = scale_stats(base_stats, level)
        moves = build_moves_for_level(learnset, level, moves_dict)
        creature = Creature(normalized_monster['name'], normalized_monster['type'], scaled_stats['max_hp'], 
                            scaled_stats['attack'], scaled_stats['defense'], moves, sprite,
                            level=level, base_stats=base_stats, move_pool=move_pool, learnset=learnset)
        creatures.append(creature)
    
    return creatures

def parse_team_env(var_name):
    raw = os.environ.get(var_name)
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        return [parsed]
    return None

def build_team_entries(creatures, entries, size, default_level, fill_random=True):
    by_name = {c.name: c for c in creatures}
    team = []
    for entry in entries or []:
        name = None
        level = default_level
        if isinstance(entry, str):
            name = entry
        elif isinstance(entry, dict):
            name = entry.get("name") or entry.get("id")
            level = clamp_level(entry.get("level", default_level))
        if name and name in by_name:
            team.append((by_name[name], level))
    if fill_random:
        used = {t[0].name for t in team}
        pool = [c for c in creatures if c.name not in used]
        while len(team) < size and pool:
            pick = random.choice(pool)
            pool.remove(pick)
            team.append((pick, default_level))
        while len(team) < size:
            team.append((random.choice(creatures), default_level))
    if len(team) > size:
        team = team[:size]
    return team

def build_random_team(creatures, size, level):
    if len(creatures) >= size:
        picks = random.sample(creatures, size)
    else:
        picks = [random.choice(creatures) for _ in range(size)]
    return [(creature, level) for creature in picks]

def build_battle_team(team_entries, moves_dict):
    battle_team = []
    for template, level in team_entries:
        sprite_path = os.path.join(config.SPRITE_DIR, f"{template.name}_front.png")
        sprite = create_sprite_from_file(sprite_path)
        battle_team.append(
            create_battle_creature(
                template=template,
                level=level,
                moves_dict=moves_dict,
                sprite=sprite
            )
        )
    return battle_team

def create_battle_creature(template, level, moves_dict, sprite):
    base_stats = getattr(template, "base_stats", {
        "max_hp": template.max_hp,
        "attack": template.attack,
        "defense": template.defense,
    })
    learnset = getattr(template, "learnset", None)
    if not learnset:
        legacy_pool = getattr(template, "move_pool", [move.name for move in template.moves])
        learnset = [{"level": 1, "move": move} for move in legacy_pool]
    move_pool = derive_move_pool_from_learnset(learnset)
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
    screen = _get_screen()
    font = _get_font()
    screen.blit(background, (0, 0))

    display_size = config.BATTLE_SPRITE_DISPLAY_SIZE

    creature1_display_sprite = pygame.transform.scale(creature1.sprite, display_size)
    creature2_display_sprite = pygame.transform.scale(creature2.sprite, display_size)

    player_x = config.BATTLE_PLAYER_SPRITE_X
    player_y = config.BATTLE_PLAYER_SPRITE_BASELINE_Y - display_size[1]
    opponent_x = config.BATTLE_WIDTH - config.BATTLE_OPPONENT_SPRITE_X_MARGIN - display_size[0]
    opponent_y = config.BATTLE_OPPONENT_SPRITE_BASELINE_Y - display_size[1]

    screen.blit(creature1_display_sprite, (player_x, player_y))
    screen.blit(creature2_display_sprite, (opponent_x, opponent_y))

    # Draw HP bars
    hp_bar_width = config.BATTLE_HP_BAR_WIDTH
    hp_bar_height = config.BATTLE_HP_BAR_HEIGHT
    hp_left_x = config.BATTLE_HP_BAR_MARGIN_X
    hp_right_x = config.BATTLE_WIDTH - config.BATTLE_HP_BAR_MARGIN_X - hp_bar_width
    hp_y = config.BATTLE_HP_BAR_Y
    pygame.draw.rect(screen, config.BLACK, (hp_left_x, hp_y, hp_bar_width, hp_bar_height))
    pygame.draw.rect(
        screen,
        config.HP_BAR_COLOR,
        (hp_left_x, hp_y, hp_bar_width * (creature1.current_hp / creature1.max_hp), hp_bar_height),
    )
    pygame.draw.rect(screen, config.BLACK, (hp_right_x, hp_y, hp_bar_width, hp_bar_height))
    pygame.draw.rect(
        screen,
        config.HP_BAR_COLOR,
        (hp_right_x, hp_y, hp_bar_width * (creature2.current_hp / creature2.max_hp), hp_bar_height),
    )

    # Draw names and HP
    name1 = font.render(f"{creature1.name} Lv{creature1.level} HP: {creature1.current_hp}/{creature1.max_hp}", True, config.BLACK)
    name2 = font.render(f"{creature2.name} Lv{creature2.level} HP: {creature2.current_hp}/{creature2.max_hp}", True, config.BLACK)
    screen.blit(name1, (hp_left_x, config.BATTLE_NAME_Y))
    screen.blit(name2, (hp_right_x, config.BATTLE_NAME_Y))

    # Draw type labels under HP bars
    type_font_size = max(config.BATTLE_TYPE_FONT_MIN, config.BATTLE_FONT_SIZE - config.BATTLE_TYPE_FONT_OFFSET)
    type_font = pygame.font.Font(config.DEFAULT_FONT, type_font_size)
    type1 = type_font.render(f"Type: {creature1.type}", True, config.BLACK)
    type2 = type_font.render(f"Type: {creature2.type}", True, config.BLACK)
    type_y = config.BATTLE_TYPE_LABEL_Y
    screen.blit(type1, (hp_left_x, type_y))
    screen.blit(type2, (hp_right_x, type_y))

    # Draw attack and defense stats
    attack_y = type_y + type_font_size + config.BATTLE_TYPE_TO_STATS_GAP
    defense_y = attack_y + config.BATTLE_STATS_VERTICAL_GAP
    attack1 = font.render(f"ATK: {creature1.attack}", True, config.BLACK)
    defense1 = font.render(f"DEF: {creature1.defense}", True, config.BLACK)
    attack2 = font.render(f"ATK: {creature2.attack}", True, config.BLACK)
    defense2 = font.render(f"DEF: {creature2.defense}", True, config.BLACK)
    
    screen.blit(attack1, (hp_left_x, attack_y))
    screen.blit(defense1, (hp_left_x, defense_y))
    screen.blit(attack2, (hp_right_x, attack_y))
    screen.blit(defense2, (hp_right_x, defense_y))

    # Draw move buttons (smaller and at the bottom)
    button_width = config.BATTLE_MOVE_BUTTON_WIDTH
    button_height = config.BATTLE_MOVE_BUTTON_HEIGHT
    button_spacing = config.BATTLE_MOVE_BUTTON_SPACING
    total_width = len(buttons) * (button_width + button_spacing) - button_spacing
    start_x = (config.BATTLE_WIDTH - total_width) // 2
    start_y = config.BATTLE_HEIGHT - button_height - config.BATTLE_MOVE_BUTTON_BOTTOM_MARGIN

    for i, button in enumerate(buttons):
        button.rect.x = start_x + i * (button_width + button_spacing)
        button.rect.y = start_y
        button.rect.width = button_width
        button.rect.height = button_height
        button.draw(screen)
        move = getattr(button, "action", None)
        if move and getattr(move, "type", None):
            effectiveness = type_chart.get(move.type, {}).get(creature2.type, 1)
            if effectiveness > 1:
                pygame.draw.rect(screen, config.GREEN, button.rect, config.BATTLE_EFFECT_OUTLINE_WIDTH)
            elif effectiveness < 1:
                pygame.draw.rect(screen, config.RED, button.rect, config.BATTLE_EFFECT_OUTLINE_WIDTH)

    if not buttons:
        fallback_text = font.render(
            f"No moves available: {ENGINE_NO_MOVE_FALLBACK_NAME} is used automatically.",
            True,
            config.BLACK,
        )
        fallback_center = (
            config.BATTLE_WIDTH // 2,
            config.BATTLE_HEIGHT - config.BATTLE_MOVE_BUTTON_BOTTOM_MARGIN - 20,
        )
        if hasattr(fallback_text, "get_rect"):
            fallback_rect = fallback_text.get_rect(center=fallback_center)
            screen.blit(fallback_text, fallback_rect)
        else:
            screen.blit(fallback_text, fallback_center)

    try:
        pygame.display.flip()
    except pygame.error:
        pass

def opponent_choose_move(attacker, defender):
    return engine_opponent_choose_move(
        attacker,
        defender,
        type_chart=type_chart,
        choice_fn=random.choice,
    )

def play_random_song():
    if not _is_audio_ready():
        return
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
    except OSError as e:
         print(f"Could not read songs directory '{songs_dir}': {e}")
    except pygame.error as e:
         print(f"Error loading or playing song: {e}")

def stop_music():
    if _is_audio_ready():
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
    except OSError as e:
         print(f"Could not read backgrounds directory '{backgrounds_dir}': {e}. Using default.")
    except pygame.error as e:
         print(f"Error loading background: {e}. Using default.")
         
    # Default fallback background
    default_bg = pygame.Surface((config.BATTLE_WIDTH, config.BATTLE_HEIGHT), pygame.SRCALPHA)
    default_bg.fill((*config.BATTLE_BG_COLOR, 255))  # Ensure full opacity
    return default_bg

def prompt_for_level(prompt_text, default_level):
    screen = _get_screen()
    font = _get_font()
    input_text = ""
    hint_font = pygame.font.Font(config.DEFAULT_FONT, config.BATTLE_FONT_SIZE - config.BATTLE_AUX_FONT_OFFSET)
    clock = pygame.time.Clock()

    while True:
        screen.fill(config.BATTLE_BG_COLOR)
        prompt_surf = font.render(prompt_text, True, config.BLACK)
        prompt_rect = prompt_surf.get_rect(center=(config.BATTLE_WIDTH // 2, config.BATTLE_HEIGHT // 2 - 60))
        screen.blit(prompt_surf, prompt_rect)

        value_text = input_text if input_text else str(default_level)
        value_surf = font.render(f"Level: {value_text}", True, config.BLACK)
        value_rect = value_surf.get_rect(center=(config.BATTLE_WIDTH // 2, config.BATTLE_HEIGHT // 2))
        screen.blit(value_surf, value_rect)

        hint_surf = hint_font.render("Enter = confirm, Esc = default", True, config.GRAY_DARK)
        hint_rect = hint_surf.get_rect(center=(config.BATTLE_WIDTH // 2, config.BATTLE_HEIGHT // 2 + 50))
        screen.blit(hint_surf, hint_rect)

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

def prompt_for_team_size(prompt_text, default_size, max_size):
    screen = _get_screen()
    font = _get_font()
    input_text = ""
    hint_font = pygame.font.Font(config.DEFAULT_FONT, config.BATTLE_FONT_SIZE - config.BATTLE_AUX_FONT_OFFSET)
    clock = pygame.time.Clock()

    while True:
        screen.fill(config.BATTLE_BG_COLOR)
        prompt_surf = font.render(prompt_text, True, config.BLACK)
        prompt_rect = prompt_surf.get_rect(center=(config.BATTLE_WIDTH // 2, config.BATTLE_HEIGHT // 2 - 60))
        screen.blit(prompt_surf, prompt_rect)

        value_text = input_text if input_text else str(default_size)
        value_surf = font.render(f"Team size: {value_text}", True, config.BLACK)
        value_rect = value_surf.get_rect(center=(config.BATTLE_WIDTH // 2, config.BATTLE_HEIGHT // 2))
        screen.blit(value_surf, value_rect)

        hint_surf = hint_font.render("Enter = confirm, Esc = default", True, config.GRAY_DARK)
        hint_rect = hint_surf.get_rect(center=(config.BATTLE_WIDTH // 2, config.BATTLE_HEIGHT // 2 + 50))
        screen.blit(hint_surf, hint_rect)

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    try:
                        size_value = int(input_text) if input_text else default_size
                    except ValueError:
                        size_value = default_size
                    size_value = max(1, min(max_size, size_value))
                    return size_value
                if event.key == pygame.K_ESCAPE:
                    return max(1, min(max_size, default_size))
                if event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                elif event.unicode.isdigit() and len(input_text) < 2:
                    input_text += event.unicode

        clock.tick(config.FPS)

def select_team(creatures, team_size):
    if not creatures:
        return []
    screen = _get_screen()
    font = _get_font()
    grid_cols = config.BATTLE_TEAM_GRID_COLS
    grid_rows = config.BATTLE_TEAM_GRID_ROWS
    per_page = grid_cols * grid_rows
    button_width = config.BATTLE_TEAM_BUTTON_WIDTH
    button_height = config.BATTLE_TEAM_BUTTON_HEIGHT
    button_spacing = config.BATTLE_TEAM_BUTTON_SPACING
    start_x = (config.BATTLE_WIDTH - (button_width * grid_cols + button_spacing * (grid_cols - 1))) // 2
    start_y = (config.BATTLE_HEIGHT - (button_height * grid_rows + button_spacing * (grid_rows - 1))) // 2

    current_page = 0
    total_pages = (len(creatures) + per_page - 1) // per_page
    selected_index = 0
    selected_names = []
    info_font = pygame.font.Font(config.DEFAULT_FONT, config.BATTLE_FONT_SIZE - config.BATTLE_AUX_FONT_OFFSET)

    done_button = Button(
        (
            config.BATTLE_WIDTH - config.BATTLE_TEAM_DONE_WIDTH - config.BATTLE_TEAM_SIDE_MARGIN,
            config.BATTLE_HEIGHT - config.BATTLE_TEAM_PANEL_BOTTOM_MARGIN,
            config.BATTLE_TEAM_DONE_WIDTH,
            config.BATTLE_TEAM_DONE_HEIGHT,
        ),
        "Done",
    )
    clear_button = Button(
        (
            config.BATTLE_TEAM_SIDE_MARGIN,
            config.BATTLE_HEIGHT - config.BATTLE_TEAM_PANEL_BOTTOM_MARGIN,
            config.BATTLE_TEAM_CLEAR_WIDTH,
            config.BATTLE_TEAM_CLEAR_HEIGHT,
        ),
        "Clear",
    )

    while True:
        screen.fill(config.BATTLE_BG_COLOR)
        title = font.render(f"Pick up to {team_size} monsters", True, config.BLACK)
        screen.blit(title, (config.BATTLE_WIDTH // 2 - title.get_width() // 2, config.BATTLE_TEAM_TITLE_Y))

        page_info = info_font.render(f"Page {current_page + 1}/{total_pages}", True, config.BLACK)
        screen.blit(
            page_info,
            (
                config.BATTLE_WIDTH // 2 - page_info.get_width() // 2,
                config.BATTLE_HEIGHT - config.BATTLE_TEAM_PAGE_INFO_BOTTOM_MARGIN,
            ),
        )

        selected_text = ", ".join(selected_names) if selected_names else "None"
        selected_label = info_font.render(f"Selected ({len(selected_names)}/{team_size}): {selected_text}", True, config.BLACK)
        screen.blit(selected_label, (config.BATTLE_TEAM_SELECTED_TEXT_X, config.BATTLE_TEAM_SELECTED_Y))

        buttons = []
        start_idx = current_page * per_page
        end_idx = min(start_idx + per_page, len(creatures))
        num_buttons = end_idx - start_idx

        for i in range(num_buttons):
            creature_index = start_idx + i
            creature = creatures[creature_index]
            row = i // grid_cols
            col = i % grid_cols
            x = start_x + col * (button_width + button_spacing)
            y = start_y + row * (button_height + button_spacing)
            button = Button((x, y, button_width, button_height), creature.name, action=creature)
            buttons.append(button)
            button.draw(screen)

            if creature.name in selected_names:
                pygame.draw.rect(
                    screen,
                    config.GREEN,
                    button.rect,
                    config.BATTLE_TEAM_SELECTED_BORDER_WIDTH,
                )
            elif i == selected_index:
                pygame.draw.rect(
                    screen,
                    config.RED,
                    button.rect,
                    config.BATTLE_TEAM_FOCUS_BORDER_WIDTH,
                )

            creature_sprite = pygame.transform.scale(creature.sprite, config.BATTLE_TEAM_SPRITE_SIZE)
            screen.blit(
                creature_sprite,
                (
                    x + config.BATTLE_TEAM_SPRITE_LEFT_PADDING,
                    y + (button_height - config.BATTLE_TEAM_SPRITE_SIZE[1]) // 2,
                ),
            )

        done_button.draw(screen)
        clear_button.draw(screen)
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if num_buttons == 0:
                    continue
                if event.key == pygame.K_DOWN:
                    if selected_index + grid_cols < num_buttons:
                        selected_index += grid_cols
                elif event.key == pygame.K_UP:
                    if selected_index - grid_cols >= 0:
                        selected_index -= grid_cols
                elif event.key == pygame.K_RIGHT:
                    if selected_index + 1 < num_buttons:
                        selected_index += 1
                elif event.key == pygame.K_LEFT:
                    if selected_index - 1 >= 0:
                        selected_index -= 1
                elif event.key == pygame.K_RIGHTBRACKET:
                    if current_page < total_pages - 1:
                        current_page += 1
                        selected_index = 0
                elif event.key == pygame.K_LEFTBRACKET:
                    if current_page > 0:
                        current_page -= 1
                        selected_index = 0
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if 0 <= selected_index < num_buttons:
                        creature = buttons[selected_index].action
                        if creature.name in selected_names:
                            selected_names.remove(creature.name)
                        elif len(selected_names) < team_size:
                            selected_names.append(creature.name)
                elif event.key == pygame.K_BACKSPACE and selected_names:
                    selected_names.pop()
                elif event.key == pygame.K_c:
                    selected_names = []
                elif event.key == pygame.K_d:
                    if selected_names:
                        return selected_names
                elif event.key == pygame.K_ESCAPE:
                    return None
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if done_button.is_clicked(event):
                    if selected_names:
                        return selected_names
                if clear_button.is_clicked(event):
                    selected_names = []
                for button in buttons:
                    if button.rect.collidepoint(event.pos):
                        creature = button.action
                        if creature.name in selected_names:
                            selected_names.remove(creature.name)
                        elif len(selected_names) < team_size:
                            selected_names.append(creature.name)
                        break
def _announce_turn(actor, defender, move, damage):
    if move is None:
        return
    if move.power == 0:
        print(f"{actor.name} used {move.name}!")
        effect = move.effect or {}
        target = effect.get("target")
        stat = effect.get("stat")
        change = effect.get("change", 0)
        if target == "self":
            direction = "increased" if change > 0 else "decreased"
            print(f"{actor.name}'s {stat} {direction}!")
        else:
            direction = "decreased" if change > 0 else "increased"
            print(f"{defender.name}'s {stat} {direction}!")
    else:
        print(f"{actor.name} used {move.name}! It dealt {damage} damage.")


def battle(creature1, creature2, show_end_menu=True):
    screen = _get_screen()
    font = _get_font()
    clock = pygame.time.Clock()
    engine = BattleEngine(creature1, creature2, type_chart=type_chart, rng=random)

    play_random_song()

    # Create buttons for player's moves
    buttons = []
    button_width = config.BATTLE_MOVE_BUTTON_WIDTH
    button_height = config.BATTLE_MOVE_BUTTON_HEIGHT
    button_spacing = config.BATTLE_MOVE_BUTTON_SPACING
    total_width = len(creature1.moves) * (button_width + button_spacing) - button_spacing
    start_x = (config.BATTLE_WIDTH - total_width) // 2
    start_y = config.BATTLE_HEIGHT - button_height - config.BATTLE_MOVE_BUTTON_BOTTOM_MARGIN
    for i, move in enumerate(creature1.moves):
        rect = (start_x + i * (button_width + button_spacing), start_y, button_width, button_height)
        button = Button(rect, move.name, action=move)
        buttons.append(button)

    background = load_random_background()

    while True:
        screen.fill(config.BATTLE_BG_COLOR)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                stop_music()
                pygame.quit()
                sys.exit()

            if engine.turn == "player" and creature1.is_alive() and creature2.is_alive():
                for button in buttons:
                    if button.is_clicked(event):
                        move = button.action
                        result = engine.resolve_player_turn(move)
                        play_battle_sfx("stat_change" if move.power == 0 else "attack", move=move)
                        if result.damage > 0:
                            play_battle_sfx("damage", move=move)
                        if result.defender_fainted:
                            play_battle_sfx("faint")
                        _announce_turn(creature1, creature2, move, result.damage)
                        break

        if engine.turn == "player" and creature1.is_alive() and creature2.is_alive() and not buttons:
            result = engine.resolve_player_turn(None)
            move = result.move
            if move is not None:
                print(f"{creature1.name} has no usable moves! {move.name} is used automatically.")
                play_battle_sfx("attack", move=move)
                if result.damage > 0:
                    play_battle_sfx("damage", move=move)
                if result.defender_fainted:
                    play_battle_sfx("faint")
                _announce_turn(creature1, creature2, move, result.damage)

        if engine.turn == "opponent" and creature2.is_alive() and creature1.is_alive() and engine.winner is None:
            pygame.time.delay(config.BATTLE_OPPONENT_MOVE_DELAY_MS)
            result = engine.resolve_opponent_turn()
            move = result.move
            if move is not None:
                play_battle_sfx("stat_change" if move.power == 0 else "attack", move=move)
                if result.damage > 0:
                    play_battle_sfx("damage", move=move)
                if result.defender_fainted:
                    play_battle_sfx("faint")
                _announce_turn(creature2, creature1, move, result.damage)

        draw_battle(creature1, creature2, buttons, background)

        if engine.winner is not None:
            winner = engine.winner
            winner_name = creature1.name if winner == "player" else creature2.name
            play_battle_sfx("victory" if winner == "player" else "defeat")
            message = font.render(f"{winner_name} wins!", True, config.BLACK)
            screen.blit(message, (config.BATTLE_WIDTH // 2 - message.get_width() // 2, config.BATTLE_HEIGHT // 2 - message.get_height() // 2))
            pygame.display.flip()
            pygame.time.delay(
                config.BATTLE_END_DELAY_NO_MENU_MS if not show_end_menu else config.BATTLE_END_DELAY_WITH_MENU_MS
            )
            stop_music()
            if show_end_menu:
                return show_end_options()
            return winner

        clock.tick(config.FPS)

def show_end_options():
    screen = _get_screen()
    # Center buttons on battle screen dimensions
    new_battle_button = Button((config.BATTLE_WIDTH // 2 - 150, config.BATTLE_HEIGHT // 2 - 60, 300, 50), "New Battle")
    quit_button = Button((config.BATTLE_WIDTH // 2 - 150, config.BATTLE_HEIGHT // 2 + 10, 300, 50), "Quit")

    while True:
        screen.fill(config.BATTLE_BG_COLOR)
        new_battle_button.draw(screen)
        quit_button.draw(screen)
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
    initialize_battle_runtime()
    font = _get_font()
    moves_dict = load_moves()
    creatures = load_creatures(moves_dict)
    if len(creatures) < 2:
        print("Not enough creatures to battle. Please add more creature data.")
        return
    while True:
        player_entries = parse_team_env("POKECLONE_PLAYER_TEAM")
        if player_entries:
            team_size = min(config.DEFAULT_TEAM_SIZE, max(1, len(player_entries)))
            player_team_entries = build_team_entries(
                creatures,
                player_entries,
                team_size,
                config.DEFAULT_TEAM_LEVEL,
                fill_random=True,
            )
        else:
            team_size = prompt_for_team_size("Choose team size (1-6)", config.DEFAULT_TEAM_SIZE, config.DEFAULT_TEAM_SIZE)
            selected_names = select_team(creatures, team_size)
            if selected_names:
                manual_entries = [{"name": name, "level": config.DEFAULT_TEAM_LEVEL} for name in selected_names]
                player_team_entries = build_team_entries(
                    creatures,
                    manual_entries,
                    team_size,
                    config.DEFAULT_TEAM_LEVEL,
                    fill_random=True,
                )
            else:
                player_team_entries = build_random_team(creatures, team_size, config.DEFAULT_TEAM_LEVEL)

        opponent_entries = parse_team_env("POKECLONE_OPPONENT_TEAM")
        if not opponent_entries and os.environ.get("POKECLONE_OPPONENT_ID"):
            opponent_entries = [{"name": os.environ.get("POKECLONE_OPPONENT_ID")}]
        if opponent_entries:
            opponent_team_entries = build_team_entries(
                creatures,
                opponent_entries,
                team_size,
                config.DEFAULT_TEAM_LEVEL,
                fill_random=True,
            )
        else:
            opponent_team_entries = build_random_team(creatures, team_size, config.DEFAULT_TEAM_LEVEL)

        player_team = build_battle_team(player_team_entries, moves_dict)
        opponent_team = build_battle_team(opponent_team_entries, moves_dict)

        player_index = 0
        opponent_index = 0
        while player_index < len(player_team) and opponent_index < len(opponent_team):
            result = battle(player_team[player_index], opponent_team[opponent_index], show_end_menu=False)
            if result == "player":
                opponent_index += 1
            else:
                player_index += 1

        final_winner = "player" if player_index < len(player_team) else "opponent"
        end_message = font.render(f"{final_winner.title()} team wins!", True, config.BLACK)
        screen = _get_screen()
        screen.fill(config.BATTLE_BG_COLOR)
        screen.blit(end_message, (config.BATTLE_WIDTH // 2 - end_message.get_width() // 2, config.BATTLE_HEIGHT // 2 - end_message.get_height() // 2))
        pygame.display.flip()
        pygame.time.delay(config.BATTLE_FINAL_MESSAGE_DELAY_MS)

        continue_game = show_end_options()
        if not continue_game:
            break

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
