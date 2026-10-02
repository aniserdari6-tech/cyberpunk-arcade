import pygame
import random
import sys
import math
import json
import os

pygame.init()

# Audio completely disabled to prevent background sound issues when switching apps
AUDIO_ENABLED = False

WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Cyberpunk Arcade Cabinet - Ultimate Edition v6")

# --- BULLETPROOF PERSISTENT HIGH SCORE MANAGEMENT ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else os.getcwd()
HIGH_SCORE_FILE = os.path.join(SCRIPT_DIR, "high_score.json")

def load_high_score():
    if os.path.exists(HIGH_SCORE_FILE):
        try:
            with open(HIGH_SCORE_FILE, 'r') as f:
                return json.load(f).get("high_score", 0)
        except Exception:
            return 0
    return 0

def save_high_score(hs):
    try:
        with open(HIGH_SCORE_FILE, 'w') as f:
            json.dump({"high_score": hs}, f)
    except Exception:
        pass

# --- 2D PHYSICS ENGINE ---
class Vec2:
    def __init__(self, x=0.0, y=0.0):
        self.x = float(x)
        self.y = float(y)

    def __add__(self, other):
        return Vec2(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Vec2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar):
        return Vec2(self.x * scalar, self.y * scalar)

    def magnitude(self):
        return math.sqrt(self.x**2 + self.y**2)


class PhysicsBody:
    def __init__(self, x, y, width, height, mass=1.0, is_static=False):
        self.pos = Vec2(x, y)
        self.vel = Vec2(0.0, 0.0)
        self.acc = Vec2(0.0, 0.0)
        self.forces = Vec2(0.0, 0.0)
        
        self.width = width
        self.height = height
        self.mass = float(max(0.1, mass))
        self.is_static = is_static
        self.drag = 0.82

    def update(self, dt):
        if self.is_static:
            return
        dt = min(dt, 0.05)
        self.acc.x = self.forces.x / self.mass
        self.acc.y = self.forces.y / self.mass
        self.vel.x += self.acc.x * dt
        self.vel.y += self.acc.y * dt
        
        max_vel = 1500.0
        self.vel.x = max(-max_vel, min(max_vel, self.vel.x))
        self.vel.y = max(-max_vel, min(max_vel, self.vel.y))
        
        self.vel.x *= self.drag
        self.vel.y *= self.drag
        self.pos.x += self.vel.x * dt
        self.pos.y += self.vel.y * dt

        if math.isnan(self.pos.x) or math.isinf(self.pos.x):
            self.pos.x = 0.0
            self.vel.x = 0.0
        if math.isnan(self.pos.y) or math.isinf(self.pos.y):
            self.pos.y = 0.0
            self.vel.y = 0.0

        self.forces = Vec2(0.0, 0.0)

    def get_rect(self):
        return pygame.Rect(int(self.pos.x), int(self.pos.y), self.width, self.height)

    def collides_with(self, other):
        return self.get_rect().colliderect(other.get_rect())
# -----------------------------------

# Theme Palettes
THEMES = [
    {"bg": (15, 17, 23), "road": (25, 30, 42), "line": (155, 89, 182), "player": (0, 255, 255)},
    {"bg": (20, 10, 30), "road": (35, 15, 45), "line": (231, 76, 60), "player": (241, 196, 15)},
    {"bg": (10, 25, 15), "road": (15, 35, 20), "line": (46, 204, 113), "player": (46, 204, 113)},
]

WHITE = (255, 255, 255)
RED = (231, 76, 60)
BLUE = (52, 152, 219)
YELLOW = (241, 196, 15)
GREEN = (46, 204, 113)
MAGENTA = (255, 0, 127)
CYAN = (0, 255, 255)
ORANGE = (243, 156, 18)
GRAY = (70, 80, 95)
PANEL_BG = (22, 26, 35)

clock = pygame.time.Clock()
FPS = 60

ROAD_X = 240
ROAD_WIDTH = 320
LANES = [ROAD_X + 35, ROAD_X + 135, ROAD_X + 235]
current_lane = 1

player_width = 45
player_height = 45
player_y = HEIGHT - 100

player_body = PhysicsBody(LANES[current_lane], player_y, player_width, player_height, mass=1.0)

entities = []
particles = []
float_texts = []
player_trails = []
spawn_timer = 0
road_scroll_offset = 0.0

score = 0
high_score = load_high_score()
lives = 3
shield_timer = 0
slow_timer = 0
rush_timer = 0
magnet_timer = 0
overdrive_charge = 0.0
overdrive_timer = 0
coin_streak = 0
stage = 1
is_paused = False
shake_timer = 0

touch_start_x = 0
touch_start_y = 0

font = pygame.font.SysFont(None, 28)
large_font = pygame.font.SysFont(None, 36)
small_font = pygame.font.SysFont(None, 20)
title_font = pygame.font.SysFont(None, 44)

# Game States: "MENU", "TUTORIAL", "PLAYING", "GAME_OVER"
game_state = "MENU"

def quit_game():
    pygame.quit()
    sys.exit()

def spawn_particles(x, y, color, count=6):
    for _ in range(count):
        if len(particles) > 60:
            particles.pop(0)
        particles.append({
            'x': x + player_width // 2,
            'y': y + player_height // 2,
            'vx': random.uniform(-3.5, 3.5),
            'vy': random.uniform(-3.5, 3.5),
            'color': color,
            'life': 25
        })

def add_floating_text(text, x, y, color):
    if len(float_texts) > 10:
        float_texts.pop(0)
    float_texts.append({
        'text': text,
        'x': x,
        'y': y,
        'color': color,
        'life': 30
    })

def trigger_overdrive():
    global overdrive_timer, overdrive_charge, shake_timer, score
    overdrive_timer = 300  # 5 seconds of absolute power
    overdrive_charge = 0.0
    shake_timer = 25
    add_floating_text("NEON SURGE!", WIDTH // 2 - 50, HEIGHT // 2, MAGENTA)
    
    for ent in entities[:]:
        if ent['type'] == 'obstacle':
            spawn_particles(ent['body'].pos.x, ent['body'].pos.y, MAGENTA, count=10)
            score += 10
            entities.remove(ent)

def reset_game():
    global score, high_score, lives, entities, particles, float_texts, player_trails, game_state, current_lane, shield_timer, slow_timer, rush_timer, magnet_timer, overdrive_charge, overdrive_timer, coin_streak, stage, shake_timer, is_paused
    if score > high_score:
        high_score = score
        save_high_score(high_score)
    score = 0
    lives = 3
    shield_timer = 0
    slow_timer = 0
    rush_timer = 0
    magnet_timer = 0
    overdrive_charge = 0.0
    overdrive_timer = 0
    coin_streak = 0
    stage = 1
    shake_timer = 0
    is_paused = False
    entities.clear()
    particles.clear()
    float_texts.clear()
    player_trails.clear()
    current_lane = 1
    player_body.pos.x = LANES[current_lane]
    player_body.vel = Vec2(0, 0)
    game_state = "PLAYING"

# --- INSTANT TOUCH / CLICK HANDLER (TRIGGERED ON DOWN PRESS) ---
def handle_instant_press(x, y):
    global game_state, is_paused, current_lane
    
    if game_state == "MENU":
        play_rect = pygame.Rect(WIDTH // 2 - 130, 260, 260, 50)
        tut_rect = pygame.Rect(WIDTH // 2 - 130, 330, 260, 50)
        if play_rect.collidepoint(x, y):
            reset_game()
        elif tut_rect.collidepoint(x, y):
            game_state = "TUTORIAL"
            
    elif game_state == "TUTORIAL":
        back_rect = pygame.Rect(WIDTH // 2 - 130, 525, 260, 40)
        if back_rect.collidepoint(x, y):
            game_state = "MENU"
            
    elif game_state == "PLAYING":
        if is_paused:
            resume_rect = pygame.Rect(WIDTH // 2 - 130, HEIGHT // 2 - 35, 260, 45)
            menu_rect = pygame.Rect(WIDTH // 2 - 130, HEIGHT // 2 + 20, 260, 45)
            if resume_rect.collidepoint(x, y):
                is_paused = False
            elif menu_rect.collidepoint(x, y):
                is_paused = False
                game_state = "MENU"
        else:
            pause_btn_rect = pygame.Rect(630, 535, 140, 40)
            if pause_btn_rect.collidepoint(x, y):
                is_paused = True
            else:
                # Instant road lane selection on touch down
                road_third = ROAD_WIDTH / 3.0
                if x >= ROAD_X and x <= ROAD_X + ROAD_WIDTH:
                    if x < ROAD_X + road_third:
                        current_lane = 0
                    elif x < ROAD_X + road_third * 2:
                        current_lane = 1
                    else:
                        current_lane = 2
                        
    elif game_state == "GAME_OVER":
        restart_rect = pygame.Rect(WIDTH // 2 - 130, HEIGHT // 2 + 35, 260, 45)
        menu_rect = pygame.Rect(WIDTH // 2 - 130, HEIGHT // 2 + 90, 260, 45)
        if restart_rect.collidepoint(x, y):
            reset_game()
        elif menu_rect.collidepoint(x, y):
            game_state = "MENU"

while True:
    dt = clock.tick(FPS) / 1000.0
    if dt > 0.1:
        dt = 0.1

    render_offset_x = 0
    render_offset_y = 0
    if shake_timer > 0:
        shake_timer -= 1
        render_offset_x = random.randint(-5, 5)
        render_offset_y = random.randint(-5, 5)

    stage = 1 + (score // 50)
    theme_idx = (stage - 1) % len(THEMES)
    current_theme = THEMES[theme_idx]

    canvas = pygame.Surface((WIDTH, HEIGHT))
    canvas.fill(current_theme["bg"])

    base_speed = 220.0 + (stage * 18.0)
    if slow_timer > 0:
        base_speed *= 0.5
    if rush_timer > 0 or overdrive_timer > 0:
        base_speed *= 1.4

    road_scroll_offset = (road_scroll_offset + base_speed * dt) % 40

    # --- EVENT HANDLING ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            quit_game()

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if game_state in ["TUTORIAL", "GAME_OVER"]:
                    game_state = "MENU"
                elif game_state == "PLAYING":
                    is_paused = not is_paused
                else:
                    quit_game()
            
            if game_state == "MENU":
                if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    reset_game()
                elif event.key == pygame.K_t:
                    game_state = "TUTORIAL"
            elif game_state == "TUTORIAL":
                if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE or event.key == pygame.K_BACKSPACE:
                    game_state = "MENU"
            elif game_state == "GAME_OVER":
                if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    reset_game()
                elif event.key == pygame.K_m:
                    game_state = "MENU"
            elif game_state == "PLAYING":
                if event.key == pygame.K_p:
                    is_paused = not is_paused
                elif not is_paused:
                    if event.key == pygame.K_LEFT and current_lane > 0:
                        current_lane -= 1
                    elif event.key == pygame.K_RIGHT and current_lane < 2:
                        current_lane += 1
                    elif (event.key == pygame.K_UP or event.key == pygame.K_w):
                        if overdrive_charge >= 100.0 and overdrive_timer == 0:
                            trigger_overdrive()

        elif event.type == getattr(pygame, 'FINGERDOWN', None):
            touch_start_x = event.x * WIDTH
            touch_start_y = event.y * HEIGHT
            # Trigger instant response on touch down for zero input lag
            handle_instant_press(touch_start_x, touch_start_y)

        elif event.type == getattr(pygame, 'FINGERUP', None):
            touch_end_x = event.x * WIDTH
            touch_end_y = event.y * HEIGHT
            dy = touch_end_y - touch_start_y

            # Swipe up for Overdrive Surge
            if game_state == "PLAYING" and not is_paused and dy < -40:
                if overdrive_charge >= 100.0 and overdrive_timer == 0:
                    trigger_overdrive()

        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            handle_instant_press(mx, my)

    # --- UPDATE LOGIC FOR PLAYING STATE ---
    if game_state == "PLAYING" and not is_paused:
        if shield_timer > 0:
            shield_timer -= 1
        if slow_timer > 0:
            slow_timer -= 1
        if rush_timer > 0:
            rush_timer -= 1
        if magnet_timer > 0:
            magnet_timer -= 1
        if overdrive_timer > 0:
            overdrive_timer -= 1

        target_x = LANES[current_lane]
        diff_x = target_x - player_body.pos.x

        if abs(diff_x) < 0.2:
            player_body.pos.x = target_x
            player_body.vel.x = 0.0
        else:
            player_body.pos.x += diff_x * min(1.0, 25.0 * dt)
            player_body.vel.x = 0.0

        player_body.update(dt)

        if len(player_trails) > 5:
            player_trails.pop(0)
        player_trails.append((player_body.pos.x, player_body.pos.y))

        spawn_timer += 1
        spawn_threshold = max(22, 48 - (stage * 2))
        if rush_timer > 0 or overdrive_timer > 0:
            spawn_threshold = 12

        if spawn_timer > spawn_threshold:
            spawn_timer = 0
            
            if rush_timer > 0 or overdrive_timer > 0:
                ent_type = 'coin'
                lane = random.choice([0, 1, 2])
            else:
                rand_val = random.random()
                if rand_val < 0.25:
                    ent_type = 'coin'
                elif rand_val < 0.31:
                    ent_type = 'shield'
                elif rand_val < 0.37:
                    ent_type = 'slow'
                elif rand_val < 0.43:
                    ent_type = 'rush'
                elif rand_val < 0.49:
                    ent_type = 'magnet'
                elif rand_val < 0.68 and stage >= 2:
                    blocked_lanes = random.sample([0, 1, 2], 2)
                    for l in blocked_lanes:
                        body = PhysicsBody(LANES[l], -60, player_width, player_height, is_static=True)
                        entities.append({
                            'type': 'obstacle',
                            'body': body,
                            'speed': base_speed
                        })
                    continue
                else:
                    ent_type = 'obstacle'
                lane = random.choice([0, 1, 2])

            body = PhysicsBody(LANES[lane], -60, player_width, player_height, is_static=True)
            entities.append({
                'type': ent_type,
                'body': body,
                'speed': base_speed
            })

        for ent in entities[:]:
            if magnet_timer > 0 and ent['type'] == 'coin':
                target_coin_x = LANES[current_lane]
                if ent['body'].pos.x < target_coin_x:
                    ent['body'].pos.x += min(3.5, target_coin_x - ent['body'].pos.x)
                elif ent['body'].pos.x > target_coin_x:
                    ent['body'].pos.x -= min(3.5, ent['body'].pos.x - target_coin_x)

            ent['body'].pos.y += ent['speed'] * dt
            
            if ent['body'].pos.y > HEIGHT:
                entities.remove(ent)
                if ent['type'] == 'obstacle':
                    score += 2
                    coin_streak = 0

            if player_body.collides_with(ent['body']):
                px, py = ent['body'].pos.x, ent['body'].pos.y
                multiplier = 3 if overdrive_timer > 0 else 1

                if ent['type'] == 'coin':
                    coin_streak += 1
                    bonus = min(coin_streak, 4)
                    gained = ((5 if rush_timer > 0 else 3) * bonus) * multiplier
                    score += gained
                    overdrive_charge = min(100.0, overdrive_charge + 3.5)
                    spawn_particles(px, py, YELLOW)
                    add_floating_text(f"+{gained}", px + 5, py, YELLOW)
                    entities.remove(ent)
                elif ent['type'] == 'shield':
                    shield_timer = 240
                    overdrive_charge = min(100.0, overdrive_charge + 10.0)
                    spawn_particles(px, py, GREEN)
                    add_floating_text("SHIELD", px - 5, py, GREEN)
                    entities.remove(ent)
                elif ent['type'] == 'slow':
                    slow_timer = 200
                    overdrive_charge = min(100.0, overdrive_charge + 10.0)
                    spawn_particles(px, py, BLUE)
                    add_floating_text("SLOW-MO", px - 5, py, BLUE)
                    entities.remove(ent)
                elif ent['type'] == 'rush':
                    rush_timer = 250
                    overdrive_charge = min(100.0, overdrive_charge + 12.0)
                    spawn_particles(px, py, MAGENTA)
                    add_floating_text("RUSH!", px - 5, py, MAGENTA)
                    entities.remove(ent)
                elif ent['type'] == 'magnet':
                    magnet_timer = 300
                    overdrive_charge = min(100.0, overdrive_charge + 10.0)
                    spawn_particles(px, py, ORANGE)
                    add_floating_text("MAGNET!", px - 5, py, ORANGE)
                    entities.remove(ent)
                elif ent['type'] == 'obstacle':
                    if overdrive_timer > 0:
                        spawn_particles(px, py, MAGENTA, count=8)
                        score += 5
                        entities.remove(ent)
                    elif shield_timer > 0:
                        spawn_particles(px, py, CYAN)
                        add_floating_text("BLOCKED", px - 5, py, CYAN)
                        entities.remove(ent)
                    else:
                        lives -= 1
                        coin_streak = 0
                        shake_timer = 15
                        spawn_particles(px, py, RED)
                        add_floating_text("-1 LIFE", px - 5, py, RED)
                        entities.remove(ent)
                        if lives <= 0:
                            game_state = "GAME_OVER"
                            if score > high_score:
                                high_score = score
                                save_high_score(high_score)

        for p in particles[:]:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['life'] -= 1
            if p['life'] <= 0:
                particles.remove(p)

        for ft in float_texts[:]:
            ft['y'] -= 1.5
            ft['life'] -= 1
            if ft['life'] <= 0:
                float_texts.remove(ft)

    # --- DRAWING ROUTINES ---
    if game_state in ["PLAYING", "GAME_OVER"]:
        pygame.draw.rect(canvas, PANEL_BG, (0, 0, ROAD_X, HEIGHT))
        pygame.draw.rect(canvas, PANEL_BG, (ROAD_X + ROAD_WIDTH, 0, WIDTH - (ROAD_X + ROAD_WIDTH), HEIGHT))
        pygame.draw.line(canvas, GRAY, (ROAD_X, 0), (ROAD_X, HEIGHT), 3)
        pygame.draw.line(canvas, GRAY, (ROAD_X + ROAD_WIDTH, 0), (ROAD_X + ROAD_WIDTH, HEIGHT), 3)

        road_bg = current_theme["road"]
        if overdrive_timer > 0:
            road_bg = (random.randint(30, 60), 10, random.randint(40, 70))
        pygame.draw.rect(canvas, road_bg, (ROAD_X, 0, ROAD_WIDTH, HEIGHT))

        line_color = MAGENTA if overdrive_timer > 0 else current_theme["line"]
        for lx in [ROAD_X + 106, ROAD_X + 213]:
            for y_pos in range(int(-40 + road_scroll_offset), HEIGHT, 40):
                pygame.draw.line(canvas, line_color, (lx, y_pos), (lx, y_pos + 20), 2)

        for p in particles:
            pygame.draw.circle(canvas, p['color'], (int(p['x']), int(p['y'])), 3)

        for ft in float_texts:
            txt_surface = small_font.render(ft['text'], True, ft['color'])
            canvas.blit(txt_surface, (ft['x'], ft['y']))

        if overdrive_timer > 0:
            player_color = MAGENTA
        elif shield_timer > 0:
            player_color = GREEN
        elif slow_timer > 0:
            player_color = BLUE
        elif rush_timer > 0:
            player_color = MAGENTA
        elif magnet_timer > 0:
            player_color = ORANGE
        else:
            player_color = current_theme["player"]

        for idx, (tx, ty) in enumerate(player_trails):
            alpha_color = (player_color[0]//2, player_color[1]//2, player_color[2]//2)
            trail_rect = pygame.Rect(int(tx), int(ty), player_width, player_height)
            pygame.draw.rect(canvas, alpha_color, trail_rect, border_radius=8)

        squish_factor = int(abs(LANES[current_lane] - player_body.pos.x) * 0.15)
        render_w = max(30, player_width - squish_factor)
        render_h = min(55, player_height + squish_factor)
        player_render_rect = pygame.Rect(
            int(player_body.pos.x + (player_width - render_w) // 2),
            int(player_body.pos.y + (player_height - render_h) // 2),
            render_w,
            render_h
        )
        pygame.draw.rect(canvas, player_color, player_render_rect, border_radius=8)

        for ent in entities:
            if ent['type'] == 'coin':
                color = YELLOW
            elif ent['type'] == 'shield':
                color = GREEN
            elif ent['type'] == 'slow':
                color = BLUE
            elif ent['type'] == 'rush':
                color = MAGENTA
            elif ent['type'] == 'magnet':
                color = ORANGE
            else:
                color = RED
            pygame.draw.rect(canvas, color, ent['body'].get_rect(), border_radius=8)

        # --- LEFT SIDE PANEL HUD ---
        canvas.blit(large_font.render("NEON RUN", True, CYAN), (25, 25))
        canvas.blit(font.render(f"Score: {score}", True, WHITE), (25, 90))
        canvas.blit(font.render(f"High: {high_score}", True, YELLOW), (25, 130))
        canvas.blit(font.render(f"Lives: {lives}", True, RED), (25, 180))
        canvas.blit(font.render(f"Stage: {stage}", True, current_theme["line"]), (25, 230))
        
        if coin_streak > 1:
            canvas.blit(small_font.render(f"Streak x{coin_streak}", True, YELLOW), (25, 280))

        canvas.blit(small_font.render("SURGE METER", True, WHITE), (25, 330))
        bar_w, bar_h = 180, 14
        fill_w = int(bar_w * (overdrive_charge / 100.0))
        pygame.draw.rect(canvas, GRAY, (25, 355, bar_w, bar_h), border_radius=4)
        if fill_w > 0:
            bar_color = MAGENTA if overdrive_charge >= 100 else CYAN
            pygame.draw.rect(canvas, bar_color, (25, 355, fill_w, bar_h), border_radius=4)
        pygame.draw.rect(canvas, WHITE, (25, 355, bar_w, bar_h), 1, border_radius=4)

        if overdrive_charge >= 100 and overdrive_timer == 0:
            pulse_text = small_font.render("SWIPE UP TO SURGE!", True, MAGENTA)
            canvas.blit(pulse_text, (25, 375))

        # --- RIGHT SIDE PANEL HUD ---
        canvas.blit(font.render("STATUS", True, WHITE), (630, 25))
        y_offset = 65
        if overdrive_timer > 0:
            canvas.blit(small_font.render(f"OVERDRIVE: {overdrive_timer//60}s", True, MAGENTA), (630, y_offset))
            y_offset += 25
        if shield_timer > 0:
            canvas.blit(small_font.render(f"Shield: {shield_timer//60}s", True, GREEN), (630, y_offset))
            y_offset += 25
        if slow_timer > 0:
            canvas.blit(small_font.render(f"Slow-Mo: {slow_timer//60}s", True, BLUE), (630, y_offset))
            y_offset += 25
        if rush_timer > 0:
            canvas.blit(small_font.render("COIN RUSH!", True, MAGENTA), (630, y_offset))
            y_offset += 25
        if magnet_timer > 0:
            canvas.blit(small_font.render(f"Magnet: {magnet_timer//60}s", True, ORANGE), (630, y_offset))

        pause_btn_rect = pygame.Rect(630, 535, 140, 40)
        pygame.draw.rect(canvas, PANEL_BG, pause_btn_rect, border_radius=6)
        pygame.draw.rect(canvas, CYAN, pause_btn_rect, 2, border_radius=6)
        pause_txt = font.render("PAUSE", True, CYAN)
        canvas.blit(pause_txt, (pause_btn_rect.centerx - pause_txt.get_width() // 2, pause_btn_rect.centery - pause_txt.get_height() // 2))

        if is_paused:
            pause_overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pause_overlay.fill((0, 0, 0, 200))
            canvas.blit(pause_overlay, (0, 0))
            
            paused_text = large_font.render("GAME PAUSED", True, YELLOW)
            canvas.blit(paused_text, (WIDTH // 2 - paused_text.get_width() // 2, HEIGHT // 2 - 90))

            resume_rect = pygame.Rect(WIDTH // 2 - 130, HEIGHT // 2 - 35, 260, 45)
            pygame.draw.rect(canvas, CYAN, resume_rect, border_radius=8)
            pygame.draw.rect(canvas, WHITE, resume_rect, 2, border_radius=8)
            res_txt = font.render("RESUME GAME", True, (15, 17, 23))
            canvas.blit(res_txt, (resume_rect.centerx - res_txt.get_width() // 2, resume_rect.centery - res_txt.get_height() // 2))

            menu_rect = pygame.Rect(WIDTH // 2 - 130, HEIGHT // 2 + 20, 260, 45)
            pygame.draw.rect(canvas, PANEL_BG, menu_rect, border_radius=8)
            pygame.draw.rect(canvas, RED, menu_rect, 2, border_radius=8)
            menu_txt = font.render("MAIN MENU", True, WHITE)
            canvas.blit(menu_txt, (menu_rect.centerx - menu_txt.get_width() // 2, menu_rect.centery - menu_txt.get_height() // 2))

        if game_state == "GAME_OVER":
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 220))
            canvas.blit(overlay, (0, 0))
            
            go_text = large_font.render("GAME OVER", True, RED)
            final_score = font.render(f"Final Score: {score}", True, WHITE)
            hi_score_text = font.render(f"High Score: {high_score}", True, YELLOW)
            
            canvas.blit(go_text, (WIDTH // 2 - go_text.get_width() // 2, HEIGHT // 2 - 95))
            canvas.blit(final_score, (WIDTH // 2 - final_score.get_width() // 2, HEIGHT // 2 - 50))
            canvas.blit(hi_score_text, (WIDTH // 2 - hi_score_text.get_width() // 2, HEIGHT // 2 - 15))

            restart_rect = pygame.Rect(WIDTH // 2 - 130, HEIGHT // 2 + 35, 260, 45)
            pygame.draw.rect(canvas, CYAN, restart_rect, border_radius=8)
            pygame.draw.rect(canvas, WHITE, restart_rect, 2, border_radius=8)
            restart_txt = font.render("PLAY AGAIN", True, (15, 17, 23))
            canvas.blit(restart_txt, (restart_rect.centerx - restart_txt.get_width() // 2, restart_rect.centery - restart_txt.get_height() // 2))

            go_menu_rect = pygame.Rect(WIDTH // 2 - 130, HEIGHT // 2 + 90, 260, 45)
            pygame.draw.rect(canvas, PANEL_BG, go_menu_rect, border_radius=8)
            pygame.draw.rect(canvas, MAGENTA, go_menu_rect, 2, border_radius=8)
            go_menu_txt = font.render("MAIN MENU", True, WHITE)
            canvas.blit(go_menu_txt, (go_menu_rect.centerx - go_menu_txt.get_width() // 2, go_menu_rect.centery - go_menu_txt.get_height() // 2))

    elif game_state == "MENU":
        canvas.fill((15, 17, 23))
        
        for x in range(0, WIDTH, 40):
            pygame.draw.line(canvas, (25, 30, 45), (x, 0), (x, HEIGHT), 1)
        for y in range(0, HEIGHT, 40):
            pygame.draw.line(canvas, (25, 30, 45), (0, y), (WIDTH, y), 1)

        title_surf = title_font.render("CYBERPUNK ARCADE", True, CYAN)
        sub_surf = font.render("ULTIMATE EDITION", True, MAGENTA)
        
        canvas.blit(title_surf, (WIDTH // 2 - title_surf.get_width() // 2, 120))
        canvas.blit(sub_surf, (WIDTH // 2 - sub_surf.get_width() // 2, 165))

        btn_w, btn_h = 260, 50
        
        play_rect = pygame.Rect(WIDTH // 2 - btn_w // 2, 260, btn_w, btn_h)
        pygame.draw.rect(canvas, CYAN, play_rect, border_radius=8)
        pygame.draw.rect(canvas, WHITE, play_rect, 2, border_radius=8)
        play_txt = font.render("START GAME", True, (15, 17, 23))
        canvas.blit(play_txt, (play_rect.centerx - play_txt.get_width() // 2, play_rect.centery - play_txt.get_height() // 2))

        tut_rect = pygame.Rect(WIDTH // 2 - btn_w // 2, 330, btn_w, btn_h)
        pygame.draw.rect(canvas, PANEL_BG, tut_rect, border_radius=8)
        pygame.draw.rect(canvas, MAGENTA, tut_rect, 2, border_radius=8)
        tut_txt = font.render("HOW TO PLAY / INFO", True, WHITE)
        canvas.blit(tut_txt, (tut_rect.centerx - tut_txt.get_width() // 2, tut_rect.centery - tut_txt.get_height() // 2))

        hs_txt = font.render(f"All-Time High Score: {high_score}", True, YELLOW)
        canvas.blit(hs_txt, (WIDTH // 2 - hs_txt.get_width() // 2, 450))

        foot_txt = small_font.render("Tap buttons or press Enter / T", True, GRAY)
        canvas.blit(foot_txt, (WIDTH // 2 - foot_txt.get_width() // 2, 520))

    elif game_state == "TUTORIAL":
        canvas.fill((15, 17, 23))

        head_surf = large_font.render("FIELD MANUAL & CODEX", True, CYAN)
        canvas.blit(head_surf, (WIDTH // 2 - head_surf.get_width() // 2, 30))

        y_pos = 85
        sections = [
            ("CONTROLS:", [
                "• Tap Left, Middle, or Right road zones to shift lanes instantly.",
                "• On-screen Pause button & Menu buttons for easy navigation.",
                "• Swipe Up when Surge Meter is full to trigger Overdrive!"
            ]),
            ("OBSTACLES & STAGES:", [
                "• Red Blocks: Avoid them! In Stage 2+, they spawn across lanes",
                "  with guaranteed open paths to slip through safely.",
                "• Stages increase progressively every 50 points, boosting speed."
            ]),
            ("POWER-UPS:", [
                "• Yellow Coins: Increase score and charge your Overdrive Surge.",
                "• Shield (Green): Temporary invulnerability against red blocks.",
                "• Slow-Mo (Blue): Cuts game speed in half for precision dodging.",
                "• Rush (Magenta): Accelerates speed and multiplies coin rewards.",
                "• Magnet (Orange): Automatically pulls nearby coins toward you."
            ])
        ]

        for title, bullets in sections:
            t_surf = font.render(title, True, YELLOW)
            canvas.blit(t_surf, (50, y_pos))
            y_pos += 26
            for b in bullets:
                b_surf = small_font.render(b, True, WHITE)
                canvas.blit(b_surf, (70, y_pos))
                y_pos += 20
            y_pos += 10

        back_rect = pygame.Rect(WIDTH // 2 - 130, 525, 260, 40)
        pygame.draw.rect(canvas, CYAN, back_rect, border_radius=6)
        back_txt = font.render("BACK TO MENU", True, (15, 17, 23))
        canvas.blit(back_txt, (back_rect.centerx - back_txt.get_width() // 2, back_rect.centery - back_txt.get_height() // 2))

    screen.fill(current_theme["bg"])
    screen.blit(canvas, (render_offset_x, render_offset_y))

    pygame.display.flip()
