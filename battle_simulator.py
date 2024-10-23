import pygame
import sys
import random
import os
import json

# Initialize Pygame
pygame.init()
pygame.mixer.init()

# Screen dimensions
WIDTH, HEIGHT = 1200, 600
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Battle Simulator")

# Font
FONT = pygame.font.Font(None, 30)

class Move:
    def __init__(self, name, type_, power, effect=None):
        self.name = name
        self.type = type_
        self.power = power
        self.effect = effect

class Creature:
    def __init__(self, name, type_, max_hp, attack, defense, moves, sprite):
        self.name = name
        self.type = type_
        self.max_hp = max_hp
        self.current_hp = max_hp
        self.attack = attack
        self.defense = defense
        self.moves = moves
        self.sprite = pygame.transform.scale(sprite, (int(64 * 3), int(64 * 3)))

    def is_alive(self):
        return self.current_hp > 0

# Load type effectiveness chart
with open('data/type_chart.json', 'r') as f:
    type_chart = json.load(f)

def apply_stat_change(creature, stat, change):
    if stat == "attack":
        if change > 0:
            creature.attack = int(creature.attack * (1 + 0.66 / (2 ** (change - 1))))
        else:
            creature.attack = int(creature.attack / (1 + 0.66 / (2 ** (abs(change) - 1))))
    elif stat == "defense":
        if change > 0:
            creature.defense = int(creature.defense * (1 + 0.66 / (2 ** (change - 1))))
        else:
            creature.defense = int(creature.defense / (1 + 0.66 / (2 ** (abs(change) - 1))))

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
    sprite = pygame.Surface((64, 64), pygame.SRCALPHA)
    sprite.fill((200, 200, 200))  # Light gray background
    pygame.draw.rect(sprite, (100, 100, 100), (10, 10, 44, 44))  # Dark gray rectangle
    pygame.draw.circle(sprite, (255, 255, 255), (32, 32), 10)  # White circle
    return sprite

def create_sprite_from_file(filename):
    try:
        sprite = pygame.image.load(filename).convert_alpha()
        return pygame.transform.scale(sprite, (64, 64))
    except pygame.error:
        print(f"Sprite file not found: {filename}")
        return create_default_sprite()
    
def load_creatures():
    creatures = []
    with open('data/monsters.json', 'r') as f:
        monsters_data = json.load(f)
    
    with open('data/moves.json', 'r') as f:
        moves_data = json.load(f)
    
    moves_dict = {move['name']: Move(move['name'], move['type'], move['power'], move.get('effect')) for move in moves_data}
    
    for monster in monsters_data:
        sprite = create_sprite_from_file(f"sprites/{monster['name']}_front.png")
        moves = [moves_dict.get(move_name, Move(move_name, 'Normal', 50)) for move_name in monster['moves']]
        creature = Creature(monster['name'], monster['type'], monster['max_hp'], 
                            monster['attack'], monster['defense'], moves, sprite)
        creatures.append(creature)
    
    return creatures

class Button:
    def __init__(self, rect, text, action=None):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.action = action
        self.color = (200, 200, 200)
        self.hover_color = (150, 150, 150)
        self.font = pygame.font.Font(None, 24)

    def draw(self, surface):
        mouse_pos = pygame.mouse.get_pos()
        is_hover = self.rect.collidepoint(mouse_pos)
        color = self.hover_color if is_hover else self.color
        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, (0, 0, 0), self.rect, 2)
        text_surf = self.font.render(self.text, True, (0, 0, 0))
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def is_clicked(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                return True
        return False

def draw_battle(creature1, creature2, buttons, background):
    SCREEN.blit(background, (0, 0))

    # Draw creatures higher up
    SCREEN.blit(creature1.sprite, (100, HEIGHT - creature1.sprite.get_height() - 200))
    SCREEN.blit(creature2.sprite, (WIDTH - creature2.sprite.get_width() - 100, HEIGHT - creature2.sprite.get_height() - 200))

    # Draw HP bars
    pygame.draw.rect(SCREEN, (0, 0, 0), (100, 100, 200, 20))
    pygame.draw.rect(SCREEN, (0, 255, 0), (100, 100, 200 * (creature1.current_hp / creature1.max_hp), 20))
    pygame.draw.rect(SCREEN, (0, 0, 0), (WIDTH - 300, 100, 200, 20))
    pygame.draw.rect(SCREEN, (0, 255, 0), (WIDTH - 300, 100, 200 * (creature2.current_hp / creature2.max_hp), 20))

    # Draw names and HP
    name1 = FONT.render(f"{creature1.name} HP: {creature1.current_hp}/{creature1.max_hp}", True, (0, 0, 0))
    name2 = FONT.render(f"{creature2.name} HP: {creature2.current_hp}/{creature2.max_hp}", True, (0, 0, 0))
    SCREEN.blit(name1, (100, 80))
    SCREEN.blit(name2, (WIDTH - 300, 80))

    # Draw attack and defense stats
    attack1 = FONT.render(f"ATK: {creature1.attack}", True, (0, 0, 0))
    defense1 = FONT.render(f"DEF: {creature1.defense}", True, (0, 0, 0))
    attack2 = FONT.render(f"ATK: {creature2.attack}", True, (0, 0, 0))
    defense2 = FONT.render(f"DEF: {creature2.defense}", True, (0, 0, 0))
    
    SCREEN.blit(attack1, (100, 130))
    SCREEN.blit(defense1, (100, 160))
    SCREEN.blit(attack2, (WIDTH - 300, 130))
    SCREEN.blit(defense2, (WIDTH - 300, 160))

    # Draw move buttons (smaller and at the bottom)
    button_width = 150
    button_height = 40
    button_spacing = 10
    total_width = len(buttons) * (button_width + button_spacing) - button_spacing
    start_x = (WIDTH - total_width) // 2
    start_y = HEIGHT - button_height - 20

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
    songs_dir = '/Users/thomaskolarik/scratchdir/pokeclone/songs'
    songs = [f for f in os.listdir(songs_dir) if f.endswith('.mp3') or f.endswith('.wav')]
    if songs:
        random_song = random.choice(songs)
        pygame.mixer.music.load(os.path.join(songs_dir, random_song))
        pygame.mixer.music.play(-1)  # -1 means loop indefinitely

def stop_music():
    pygame.mixer.music.stop()

def load_random_background():
    backgrounds = [f for f in os.listdir('backgrounds') if f.endswith('.png')]
    if backgrounds:
        background_path = os.path.join('backgrounds', random.choice(backgrounds))
        background = pygame.image.load(background_path).convert_alpha()
        return pygame.transform.scale(background, (WIDTH, HEIGHT))
    else:
        default_bg = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        default_bg.fill((255, 255, 255, 255))  # White background with full opacity
        return default_bg

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
    start_x = (WIDTH - total_width) // 2
    start_y = HEIGHT - button_height - 20
    for i, move in enumerate(creature1.moves):
        rect = (start_x + i * (button_width + button_spacing), start_y, button_width, button_height)
        button = Button(rect, move.name, action=move)
        buttons.append(button)

    background = load_random_background()

    while running:
        # Clear the screen with a white color instead of black
        SCREEN.fill((255, 255, 255))  # Fill with white

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
            message = FONT.render(f"{winner} wins!", True, (0, 0, 0))
            SCREEN.blit(message, (WIDTH // 2 - message.get_width() // 2, HEIGHT // 2 - message.get_height() // 2))
            pygame.display.flip()
            pygame.time.delay(3000)
            stop_music()
            return show_end_options()

        clock.tick(30)

def show_end_options():
    new_battle_button = Button((WIDTH // 2 - 150, HEIGHT // 2 - 60, 300, 50), "New Battle")
    quit_button = Button((WIDTH // 2 - 150, HEIGHT // 2 + 10, 300, 50), "Quit")

    while True:
        SCREEN.fill((255, 255, 255))
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
    creatures = load_creatures()
    if len(creatures) < 2:
        print("Not enough creatures to battle. Please add more creature data.")
        return

    while True:
        # Constants for grid layout
        GRID_COLS = 3
        GRID_ROWS = 2
        CREATURES_PER_PAGE = GRID_COLS * GRID_ROWS
        BUTTON_WIDTH = 350
        BUTTON_HEIGHT = 80
        BUTTON_SPACING = 20
        
        # Calculate grid positions
        start_x = (WIDTH - (BUTTON_WIDTH * GRID_COLS + BUTTON_SPACING * (GRID_COLS - 1))) // 2
        start_y = (HEIGHT - (BUTTON_HEIGHT * GRID_ROWS + BUTTON_SPACING * (GRID_ROWS - 1))) // 2

        # Pagination variables
        current_page = 0
        total_pages = (len(creatures) + CREATURES_PER_PAGE - 1) // CREATURES_PER_PAGE

        player_creature = None
        selected_index = 0

        while player_creature is None:
            SCREEN.fill((255, 255, 255))
            title = FONT.render("Choose your monster:", True, (0, 0, 0))
            SCREEN.blit(title, (WIDTH // 2 - title.get_width() // 2, 20))

            # Display page number
            page_info = FONT.render(f"Page {current_page + 1}/{total_pages}", True, (0, 0, 0))
            SCREEN.blit(page_info, (WIDTH // 2 - page_info.get_width() // 2, HEIGHT - 30))

            # Create and draw buttons for the current page
            buttons = []
            for i in range(CREATURES_PER_PAGE):
                creature_index = current_page * CREATURES_PER_PAGE + i
                if creature_index >= len(creatures):
                    break

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
                    pygame.draw.rect(SCREEN, (0, 255, 0), button.rect, 3)  # Green border

                # Display the creature's sprite next to the button
                creature_sprite = pygame.transform.scale(creature.sprite, (64, 64))
                SCREEN.blit(creature_sprite, (x + 5 , y + (BUTTON_HEIGHT - 64) // 2))

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RIGHT:
                        if current_page < total_pages - 1:
                            current_page += 1
                            selected_index = 0
                    elif event.key == pygame.K_LEFT:
                        if current_page > 0:
                            current_page -= 1
                            selected_index = 0
                    elif event.key == pygame.K_DOWN:
                        selected_index = (selected_index + GRID_COLS) % len(buttons)
                    elif event.key == pygame.K_UP:
                        selected_index = (selected_index - GRID_COLS) % len(buttons)
                    elif event.key == pygame.K_RIGHT and selected_index % GRID_COLS < GRID_COLS - 1:
                        selected_index = min(selected_index + 1, len(buttons) - 1)
                    elif event.key == pygame.K_LEFT and selected_index % GRID_COLS > 0:
                        selected_index = max(selected_index - 1, 0)
                    elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                        player_creature = buttons[selected_index].action

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left mouse button
                        for i, button in enumerate(buttons):
                            if button.rect.collidepoint(event.pos):
                                player_creature = button.action
                                break

            pygame.display.flip()

        # Choose a random opponent that isn't the player's creature
        opponent_creature = random.choice([c for c in creatures if c != player_creature])
        
        # Reset HP for both creatures before the battle
        player_creature.current_hp = player_creature.max_hp
        opponent_creature.current_hp = opponent_creature.max_hp
        
        continue_game = battle(player_creature, opponent_creature)
        
        if not continue_game:
            break

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()