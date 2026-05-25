import pygame
import sys
import random
import os

pygame.init()

WIDTH, HEIGHT = 900, 580
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("WW1 Turn-Based")

# ── Colors ─────────────────────────────────────────────────
WHITE      = (255, 255, 255)
BLACK      = (0,   0,   0  )
DARK_BG    = (22,  26,  34 )
PANEL_BG   = (14,  18,  26 )
GOLD       = (210, 175, 55 )
LIGHT_BLUE = (90,  155, 230)
RED_COL    = (220, 70,  70 )
GRAY       = (155, 155, 155)
HP_GREEN   = (55,  185, 75 )
HP_YELLOW  = (215, 185, 45 )
HP_RED     = (205, 55,  55 )
COVER_COL  = (70,  150, 215)
MENU_DARK  = (16,  20,  28 )
HIGHLIGHT  = (255, 215, 0  )
DIM        = (80,  80,  100)

# ── Fonts ──────────────────────────────────────────────────
font_title = pygame.font.SysFont('Arial', 52, bold=True)
font_sub   = pygame.font.SysFont('Arial', 24)
font_large = pygame.font.SysFont('Arial', 28, bold=True)
font_med   = pygame.font.SysFont('Arial', 21)
font_small = pygame.font.SysFont('Arial', 17)
font_tiny  = pygame.font.SysFont('Arial', 14)

clock = pygame.time.Clock()

# ── Sprites ────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def load_sprite(filename, target_h):
    raw   = pygame.image.load(os.path.join(BASE_DIR, 'assets', filename)).convert_alpha()
    scale = target_h / raw.get_height()
    w     = int(raw.get_width() * scale)
    right = pygame.transform.smoothscale(raw, (w, target_h))
    left  = pygame.transform.flip(right, True, False)
    return right, left, w

TARGET_H        = 190
ATTACK_FLASH_MS = 100
DEAD_FRAME_MS   = 180   # ms per death animation frame

# ── Layout ─────────────────────────────────────────────────
GROUND_Y     = 420
TRENCH_W     = 150
TRENCH_DEPTH = 55
COVER_SINK   = 48    # px soldier sinks when in cover
P1_X         = 130
P2_X         = 770

idle_right,   idle_left,   UNIT_W   = load_sprite('sprite_idle.png',   TARGET_H)
attack_right, attack_left, ATTACK_W = load_sprite('sprite_attack.png', TARGET_H)

# Death frames — scaled to same height as idle
dead_frames = []   # list of (right_surf, left_surf, width)
for i in range(1, 5):
    dead_frames.append(load_sprite(f'sprite_dead_{i}.png', TARGET_H))


# ==========================================================
#  Scene drawing
# ==========================================================
def draw_dead_tree(surface, x, h, seed):
    rng  = random.Random(seed)
    col  = (52, 42, 34)
    col2 = (44, 35, 28)
    tx   = x + rng.randint(-4, 4)
    base = GROUND_Y - 2
    pygame.draw.line(surface, col, (tx, base), (tx, base - h), 5)
    for _ in range(rng.randint(3, 5)):
        bh  = rng.randint(h // 4, h * 3 // 4)
        by  = base - bh
        dx  = rng.choice([-1, 1]) * rng.randint(22, 58)
        dy  = -rng.randint(5, 22)
        pygame.draw.line(surface, col, (tx, by), (tx + dx, by + dy), 3)
        for _ in range(rng.randint(1, 3)):
            sdx = rng.randint(-18, 18)
            sdy = -rng.randint(4, 18)
            pygame.draw.line(surface, col2, (tx + dx, by + dy),
                             (tx + dx + sdx, by + dy + sdy), 2)


def draw_trench_pit(surface, cx):
    pygame.draw.rect(surface, (24, 32, 18),
        (cx - TRENCH_W // 2, GROUND_Y - 6, TRENCH_W, TRENCH_DEPTH + 10),
        border_radius=6)
    # inner shadow
    pygame.draw.rect(surface, (18, 24, 14),
        (cx - TRENCH_W // 2 + 6, GROUND_Y + 10, TRENCH_W - 12, TRENCH_DEPTH - 5),
        border_radius=4)


def draw_sandbags(surface, cx):
    sb_y = GROUND_Y - 10
    # bottom row
    for i in range(5):
        sx = cx - TRENCH_W // 2 + 4 + i * 28
        pygame.draw.ellipse(surface, (108, 88, 62), (sx, sb_y, 30, 19))
        pygame.draw.ellipse(surface, (88, 70, 48), (sx, sb_y, 30, 19), 1)
    # top row (offset)
    for i in range(4):
        sx = cx - TRENCH_W // 2 + 18 + i * 28
        pygame.draw.ellipse(surface, (98, 80, 56), (sx, sb_y - 13, 30, 19))
        pygame.draw.ellipse(surface, (80, 62, 42), (sx, sb_y - 13, 30, 19), 1)


def draw_scene(surface):
    # Sky — dark overcast WWI palette
    surface.fill((36, 40, 52))
    pygame.draw.rect(surface, (44, 50, 42), (0, 280, WIDTH, 145))   # murky horizon band

    # Far ground mud
    pygame.draw.rect(surface, (36, 50, 28), (0, GROUND_Y, WIDTH, HEIGHT - GROUND_Y))
    # Subtle mud ruts
    for rx in range(0, WIDTH, 55):
        pygame.draw.line(surface, (30, 42, 22), (rx, GROUND_Y + 8), (rx + 30, GROUND_Y + 8), 1)

    # Dead trees (drawn before units so they stay behind)
    tree_specs = [(310, 105, 1), (390, 88, 2), (450, 118, 3), (530, 92, 4), (600, 108, 5)]
    for tx, th, seed in tree_specs:
        draw_dead_tree(surface, tx, th, seed)

    # Ground line
    pygame.draw.line(surface, (62, 88, 48), (0, GROUND_Y), (WIDTH, GROUND_Y), 2)

    # Trench pits (before soldiers so units appear IN FRONT and sinking into them)
    draw_trench_pit(surface, P1_X)
    draw_trench_pit(surface, P2_X)


# ==========================================================
#  Unit
# ==========================================================
class Unit:
    def __init__(self, name, unit_type, x, y, facing_left=False):
        self.name         = name
        self.unit_type    = unit_type
        self.x            = x
        self.y            = y
        self.facing_left  = facing_left
        self.max_hp       = 100
        self.hp           = 100.0
        self.base_def     = 10
        self.attack       = 25
        self.in_cover     = False
        self.attack_timer = 0    # ms remaining to show attack sprite
        # death animation
        self.is_dying     = False
        self.death_done   = False
        self.dead_frame   = 0    # 0-3
        self.dead_timer   = 0    # ms into current frame

    @property
    def defense(self):
        return self.base_def * 3 if self.in_cover else self.base_def

    def roll_damage(self):
        return self.attack * random.uniform(0.5, 1.5)

    def receive_hit(self, raw):
        dealt = max(1.0, raw - self.defense)
        self.hp = max(0.0, self.hp - dealt)
        return dealt

    def is_alive(self):
        return self.hp > 0

    def start_dying(self):
        self.is_dying   = True
        self.death_done = False
        self.dead_frame = 0
        self.dead_timer = 0

    # ── Actions ────────────────────────────────────────────
    def action_charge(self, target):
        self.attack   += 10
        self.base_def -= 10
        dealt = target.receive_hit(self.roll_damage())
        self.attack_timer = ATTACK_FLASH_MS
        return dealt, 'CHARGE ATTACK!  +10 ATK / -10 DEF  ->  ' + f'{dealt:.1f} dmg'

    def action_basic(self, target):
        was_cover = self.in_cover
        self.in_cover = False
        dealt = target.receive_hit(self.roll_damage())
        note  = ' (left cover)' if was_cover else ''
        self.attack_timer = ATTACK_FLASH_MS
        return dealt, 'BASIC ATTACK' + note + '  ->  ' + f'{dealt:.1f} dmg'

    def action_cover(self):
        self.in_cover = True
        self.attack   = max(1, self.attack - 5)
        return None, f'TAKE COVER!  DEF x3 = {self.defense}  /  -5 ATK'

    def action_retreat(self):
        self.base_def += 10
        self.attack    = max(1, self.attack - 10)
        return None, f'RETREAT!  +10 DEF  /  -10 ATK'

    # ── Update ─────────────────────────────────────────────
    def update(self, dt):
        if self.is_dying and not self.death_done:
            self.dead_timer += dt
            if self.dead_timer >= DEAD_FRAME_MS:
                self.dead_timer -= DEAD_FRAME_MS
                if self.dead_frame < len(dead_frames) - 1:
                    self.dead_frame += 1
                else:
                    self.death_done = True   # animation finished
        elif self.attack_timer > 0:
            self.attack_timer = max(0, self.attack_timer - dt)

    # ── Draw ───────────────────────────────────────────────
    def draw(self, surface):
        if self.is_dying:
            img, _, w = dead_frames[self.dead_frame]
            if self.facing_left:
                _, img, w = dead_frames[self.dead_frame]
        elif self.attack_timer > 0:
            img = attack_left if self.facing_left else attack_right
            w   = ATTACK_W
        else:
            img = idle_left if self.facing_left else idle_right
            w   = UNIT_W

        # Sink soldier into trench when in cover (not while dying)
        draw_y = self.y + (COVER_SINK if self.in_cover and not self.is_dying else 0)

        rect = img.get_rect(centerx=self.x, bottom=draw_y)
        surface.blit(img, rect)

        if not self.is_dying:
            ns = font_med.render(self.name, True, WHITE)
            ts = font_tiny.render(self.unit_type, True, GRAY)
            surface.blit(ns, (self.x - ns.get_width() // 2, draw_y + 4))
            surface.blit(ts, (self.x - ts.get_width() // 2, draw_y + 26))

    def draw_panel(self, surface, px, py, label, lc):
        W, H = 195, 132
        pygame.draw.rect(surface, PANEL_BG, (px, py, W, H), border_radius=8)
        pygame.draw.rect(surface, lc,       (px, py, W, H), 2, border_radius=8)

        lbl = font_large.render(label, True, lc)
        surface.blit(lbl, (px + 10, py + 6))

        bx, by, bw = px + 10, py + 38, W - 20
        pygame.draw.rect(surface, (70, 20, 20), (bx, by, bw, 10), border_radius=4)
        ratio = max(0, self.hp / self.max_hp)
        bcol  = HP_GREEN if ratio > 0.5 else (HP_YELLOW if ratio > 0.25 else HP_RED)
        pygame.draw.rect(surface, bcol, (bx, by, int(bw * ratio), 10), border_radius=4)

        rows = [
            (f'HP   {int(self.hp)}/{self.max_hp}',        bcol),
            (f'ATK  {self.attack}    DEF  {self.defense}', WHITE),
            ('Cover: ' + ('YES' if self.in_cover else 'no'), COVER_COL if self.in_cover else GRAY),
        ]
        for i, (txt, col) in enumerate(rows):
            s = font_small.render(txt, True, col)
            surface.blit(s, (px + 10, py + 54 + i * 24))


# ==========================================================
#  AI
# ==========================================================
def ai_choose(ai_unit, _enemy):
    ratio = ai_unit.hp / ai_unit.max_hp
    if ratio < 0.30:
        return random.choices([pygame.K_d, pygame.K_c], weights=[50, 50])[0]
    elif ratio < 0.60:
        return random.choices([pygame.K_c, pygame.K_b, pygame.K_a], weights=[30, 50, 20])[0]
    else:
        return random.choices([pygame.K_a, pygame.K_b, pygame.K_c], weights=[25, 55, 20])[0]


# ==========================================================
#  Menu
# ==========================================================
def draw_menu(selected):
    screen.fill(MENU_DARK)

    t1 = font_title.render('WW1', True, GOLD)
    t2 = font_title.render('TURN-BASED', True, WHITE)
    screen.blit(t1, (WIDTH // 2 - t1.get_width() // 2, 80))
    screen.blit(t2, (WIDTH // 2 - t2.get_width() // 2, 145))

    sub = font_sub.render('Select game mode', True, GRAY)
    screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 235))

    options = [
        ('SINGLE PLAYER', '1 player vs AI',          LIGHT_BLUE),
        ('MULTIPLAYER',   '2 players, same keyboard', RED_COL),
    ]
    box_w, box_h = 310, 90
    gap     = 30
    total_w = box_w * 2 + gap
    start_x = WIDTH // 2 - total_w // 2
    box_y   = 285

    for i, (title, desc, col) in enumerate(options):
        bx         = start_x + i * (box_w + gap)
        border_col = HIGHLIGHT if selected == i else DIM
        fill_col   = (30, 36, 50) if selected == i else PANEL_BG
        pygame.draw.rect(screen, fill_col,   (bx, box_y, box_w, box_h), border_radius=12)
        pygame.draw.rect(screen, border_col, (bx, box_y, box_w, box_h), 2, border_radius=12)
        ts = font_large.render(title, True, col if selected == i else GRAY)
        ds = font_small.render(desc,  True, WHITE if selected == i else DIM)
        screen.blit(ts, (bx + box_w // 2 - ts.get_width() // 2, box_y + 18))
        screen.blit(ds, (bx + box_w // 2 - ds.get_width() // 2, box_y + 58))

    hint = font_small.render('Arrow keys to choose   ENTER to confirm', True, GRAY)
    screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 415))
    pygame.display.flip()


def run_menu():
    selected = 0
    while True:
        draw_menu(selected)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    selected = 1 - selected
                if event.key == pygame.K_1:
                    return 'sp'
                if event.key == pygame.K_2:
                    return 'mp'
                if event.key == pygame.K_RETURN:
                    return 'sp' if selected == 0 else 'mp'
        clock.tick(60)


# ==========================================================
#  Game session
# ==========================================================
def make_units():
    p1 = Unit('Rifleman', 'Basic Infantry', P1_X, GROUND_Y, facing_left=False)
    p2 = Unit('Rifleman', 'Basic Infantry', P2_X, GROUND_Y, facing_left=True)
    return p1, p2


def run_game(mode):
    p1, p2          = make_units()
    turn            = 1
    game_over       = False
    death_pending   = False   # death animation playing, game_over not set yet
    pending_result  = ''      # result message shown after death animation
    log             = [
        'Your turn!' if mode == 'sp' else 'Player 1\'s turn!',
        '[A] Charge  [B] Attack  [C] Cover  [D] Retreat',
    ]
    ai_timer = 0

    def active_passive():
        return (p1, p2) if turn == 1 else (p2, p1)

    def apply_action(key):
        nonlocal turn, game_over, death_pending, pending_result, log
        attacker, defender = active_passive()

        if   key == pygame.K_a: _, msg = attacker.action_charge(defender)
        elif key == pygame.K_b: _, msg = attacker.action_basic(defender)
        elif key == pygame.K_c: _, msg = attacker.action_cover()
        elif key == pygame.K_d: _, msg = attacker.action_retreat()
        else: return

        who = 'You' if (mode == 'sp' and turn == 1) else f'P{turn}'
        log = [who + ': ' + msg]

        # Check for kill — start death animation instead of immediate game_over
        if not p1.is_alive():
            p1.start_dying()
            pending_result = 'AI wins!' if mode == 'sp' else 'Player 2 wins!'
            death_pending  = True
            log.append('...')
            return
        if not p2.is_alive():
            p2.start_dying()
            pending_result = 'You win!' if mode == 'sp' else 'Player 1 wins!'
            death_pending  = True
            log.append('...')
            return

        turn = 2 if turn == 1 else 1

        if mode == 'sp' and turn == 2:
            log.append('AI is thinking...')
        else:
            next_label = 'Your' if (mode == 'sp' and turn == 1) else f'Player {turn}\'s'
            log.append(next_label + ' turn — [A] Charge  [B] Attack  [C] Cover  [D] Retreat')

    running = True
    while running:
        dt = clock.tick(60)

        # Check if death animation just finished
        if death_pending:
            dead_unit = p1 if not p1.is_alive() else p2
            if dead_unit.death_done:
                death_pending = False
                game_over     = True
                log = [pending_result, '[R] restart   [M] menu']


        # AI turn - blocked while death is playing
        if mode == 'sp' and turn == 2 and not game_over and not death_pending:
            ai_timer += dt
            if ai_timer >= 900:
                ai_timer = 0
                apply_action(ai_choose(p2, p1))

        # Events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if not game_over and not death_pending:
                    is_player_turn = not (mode == 'sp' and turn == 2)
                    if is_player_turn and event.key in (pygame.K_a, pygame.K_b, pygame.K_c, pygame.K_d):
                        apply_action(event.key)
                elif game_over:
                    if event.key == pygame.K_r:
                        run_game(mode); return
                    if event.key == pygame.K_m:
                        return

        # Update unit timers
        p1.update(dt)
        p2.update(dt)

        # Draw background, trees, trench pits
        draw_scene(screen)

        # Draw units (sink into trench when in cover)
        p1.draw(screen)
        p2.draw(screen)

        # Sandbags on top of units for in-trench illusion
        draw_sandbags(screen, P1_X)
        draw_sandbags(screen, P2_X)

        # Stat panels
        p1_label = 'You'      if mode == 'sp' else 'Player 1'
        p2_label = 'AI'       if mode == 'sp' else 'Player 2'
        p1.draw_panel(screen, 10,          10, p1_label, LIGHT_BLUE)
        p2.draw_panel(screen, WIDTH - 205, 10, p2_label, RED_COL)

        # Mode badge
        badge = font_tiny.render('SINGLE PLAYER' if mode == 'sp' else 'MULTIPLAYER', True, GOLD)
        screen.blit(badge, (WIDTH // 2 - badge.get_width() // 2, 4))

        # Turn / status banner
        if game_over:
            b = font_large.render('GAME OVER', True, GOLD)
            screen.blit(b, (WIDTH // 2 - b.get_width() // 2, 18))
        elif death_pending:
            b = font_large.render('...', True, RED_COL)
            screen.blit(b, (WIDTH // 2 - b.get_width() // 2, 18))
        else:
            if mode == 'sp':
                btxt = '  YOUR TURN'     if turn == 1 else '  AI THINKING...'
                bcol = LIGHT_BLUE        if turn == 1 else RED_COL
            else:
                btxt = 'PLAYER ' + str(turn) + "'S TURN"
                bcol = LIGHT_BLUE if turn == 1 else RED_COL
            b = font_large.render(btxt, True, bcol)
            screen.blit(b, (WIDTH // 2 - b.get_width() // 2, 18))

        # Log panel
        log_y = HEIGHT - 92
        pygame.draw.rect(screen, PANEL_BG, (0, log_y, WIDTH, 92))
        pygame.draw.line(screen, GOLD, (0, log_y), (WIDTH, log_y), 1)
        for i, line in enumerate(log[-2:]):
            s = font_med.render(line, True, GOLD if i == 0 else WHITE)
            screen.blit(s, (18, log_y + 10 + i * 34))

        pygame.display.flip()


# Entry point
while True:
    mode = run_menu()
    run_game(mode)
