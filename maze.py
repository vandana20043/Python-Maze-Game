# ======================================================================
#  MAZE RUNNER - a complete maze game made with Python and Pygame
# ======================================================================

import array
import math
import random
import sys

import pygame

# ----------------------------------------------------------------------
#  SETTINGS (numbers you can change to customize the game)
# ----------------------------------------------------------------------
WIDTH, HEIGHT = 960, 720          # window size in pixels
FPS = 60                          # frames per second
HUD_H = 70                        # height of the top information bar
FOOTER_H = 36                     # height of the bottom controls bar
MAZE_AREA_H = HEIGHT - HUD_H - FOOTER_H   # vertical space for the maze

COIN_POINTS = 100                 # points for each coin
CLEAR_BONUS = 200                 # points for finishing a level
TIME_BONUS_PER_SECOND = 10        # points for every second under "par" time

# Each level: size in tiles (must be ODD numbers), a seed (a fixed number that
# makes the maze the same every time), how many coins, and the par time.
LEVELS = [
    {"name": "Easy",   "cols": 19, "rows": 13, "seed": 7,  "coins": 5,  "par": 60},
    {"name": "Medium", "cols": 25, "rows": 17, "seed": 21, "coins": 8,  "par": 100},
    {"name": "Hard",   "cols": 31, "rows": 21, "seed": 42, "coins": 12, "par": 150},
]

# Colors are (Red, Green, Blue), each from 0 to 255
WHITE = (255, 255, 255)
GOLD = (255, 215, 0)
LIGHT = (225, 220, 255)
WALL_BASE = (70, 40, 140)
WALL_TOP = (105, 70, 195)
FLOOR_A = (245, 238, 255)
FLOOR_B = (234, 226, 250)
START_TILE = (190, 225, 255)
PLAYER_COLOR = (255, 140, 0)
EXIT_GREEN = (40, 200, 110)
EXIT_DARK = (20, 120, 70)
BUTTON = (40, 170, 110)
BUTTON_HOVER = (70, 210, 140)

# Button positions (rectangles: x, y, width, height)
START_BUTTON = pygame.Rect(WIDTH // 2 - 150, 380, 300, 70)
NEXT_BUTTON = pygame.Rect(WIDTH // 2 - 140, 510, 280, 64)
AGAIN_BUTTON = pygame.Rect(WIDTH // 2 - 140, 510, 280, 64)
RESUME_BUTTON = pygame.Rect(WIDTH // 2 - 130, 310, 260, 60)
RESTART_BUTTON = pygame.Rect(WIDTH // 2 - 130, 390, 260, 60)


# ----------------------------------------------------------------------
#  HELPER FUNCTIONS
# ----------------------------------------------------------------------
def generate_maze(cols, rows, seed):
    """Build a maze. Returns a grid where 1 = wall and 0 = floor.

    It starts with all walls and digs tunnels (a method called the
    'recursive backtracker'). Every floor tile is connected to every other
    floor tile, so the exit can always be reached.
    """
    rng = random.Random(seed)
    grid = [[1] * cols for _ in range(rows)]      # grid[row][column]
    grid[1][1] = 0                                # the start tile is open
    stack = [(1, 1)]                              # tiles we can step back to

    while stack:
        cx, cy = stack[-1]                        # current tile
        options = []
        for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
            nx, ny = cx + dx, cy + dy
            # stay inside the border and only visit untouched tiles
            if 1 <= nx < cols - 1 and 1 <= ny < rows - 1 and grid[ny][nx] == 1:
                options.append((dx, dy))
        if options:
            dx, dy = rng.choice(options)
            grid[cy + dy // 2][cx + dx // 2] = 0  # open the wall in between
            grid[cy + dy][cx + dx] = 0            # open the new tile
            stack.append((cx + dx, cy + dy))
        else:
            stack.pop()                           # dead end: step back
    return grid


def make_tone(frequencies, duration):
    """Create a short beep from code. Returns None if sound is unavailable."""
    if pygame.mixer.get_init() is None:
        return None
    try:
        sample_rate, sound_format, channels = pygame.mixer.get_init()
        if sound_format != -16:
            return None
        count = int(sample_rate * duration)
        samples = array.array("h")                # "h" = 16-bit numbers
        for i in range(count):
            part = min(int(i / count * len(frequencies)), len(frequencies) - 1)
            freq = frequencies[part]
            fade = 1 - i / count                  # the beep gets quieter
            value = int(9000 * fade * math.sin(2 * math.pi * freq * i / sample_rate))
            for _ in range(channels):
                samples.append(value)
        return pygame.mixer.Sound(buffer=samples.tobytes())
    except Exception:
        return None


def make_background():
    """Create a colorful gradient picture with soft circles, drawn once."""
    surface = pygame.Surface((WIDTH, HEIGHT))
    top, bottom = (45, 20, 100), (15, 120, 165)
    for y in range(HEIGHT):
        t = y / HEIGHT
        color = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        pygame.draw.line(surface, color, (0, y), (WIDTH, y))
    circles = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    rng = random.Random(3)
    for _ in range(16):
        color = (rng.randint(150, 255), rng.randint(80, 255), rng.randint(150, 255), 35)
        pygame.draw.circle(circles, color,
                           (rng.randint(0, WIDTH), rng.randint(0, HEIGHT)),
                           rng.randint(40, 140))
    surface.blit(circles, (0, 0))
    return surface


def format_time(seconds):
    """Turn 75.3 seconds into the text '01:15'."""
    return f"{int(seconds) // 60:02d}:{int(seconds) % 60:02d}"


# ----------------------------------------------------------------------
#  THE GAME CLASS (holds everything the game needs)
# ----------------------------------------------------------------------
class Game:
    def __init__(self):
        # Prepare sound first (this must happen before pygame.init)
        pygame.mixer.pre_init(22050, -16, 1, 512)
        pygame.init()
        if pygame.mixer.get_init() is None:
            try:
                pygame.mixer.init(22050, -16, 1, 512)
            except pygame.error:
                pass                              # no sound card: that is OK

        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Maze Runner")
        self.clock = pygame.time.Clock()

        self.font_title = pygame.font.SysFont("arial", 84, bold=True)
        self.font_big = pygame.font.SysFont("arial", 52, bold=True)
        self.font_med = pygame.font.SysFont("arial", 28, bold=True)
        self.font_small = pygame.font.SysFont("arial", 22)

        self.background = make_background()
        self.dim = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        self.dim.fill((0, 0, 25, 170))            # dark see-through layer

        self.coin_sound = make_tone([880, 1320], 0.12)
        self.win_sound = make_tone([523, 659, 784, 1047], 0.6)
        self.muted = False

        self.running = True
        self.state = "start"   # start, playing, paused, level_complete, game_over
        self.result = {}
        self.new_game()

    # ------------------------------------------------------------------
    #  Setting up a game and a level
    # ------------------------------------------------------------------
    def new_game(self):
        """Reset everything for a brand-new game."""
        self.level_index = 0
        self.total_score = 0
        self.total_time = 0.0
        self.total_coins = 0
        self.load_level()

    def load_level(self):
        """Build the current level. Also used to restart the level."""
        cfg = LEVELS[self.level_index]
        cols, rows = cfg["cols"], cfg["rows"]
        self.grid = generate_maze(cols, rows, cfg["seed"])

        # Tile size is chosen so the maze always fits in the window
        self.tile = min(WIDTH // cols, MAZE_AREA_H // rows)
        maze_w, maze_h = cols * self.tile, rows * self.tile
        self.maze_rect = pygame.Rect((WIDTH - maze_w) // 2,
                                     HUD_H + (MAZE_AREA_H - maze_h) // 2,
                                     maze_w, maze_h)

        # One rectangle per wall tile (used for collisions)
        self.walls = []
        for y in range(rows):
            for x in range(cols):
                if self.grid[y][x] == 1:
                    self.walls.append(self.cell_rect(x, y))

        self.maze_surface = self.build_maze_surface(cols, rows)

        # Player: a small square in the centre of the start tile (1, 1)
        size = int(self.tile * 0.6)
        self.player = pygame.Rect(0, 0, size, size)
        self.player.center = self.cell_rect(1, 1).center
        self.speed = max(3, self.tile // 9)       # pixels per frame

        # Exit: the bottom-right open tile
        self.exit_rect = self.cell_rect(cols - 2, rows - 2)

        # Coins: placed on random floor tiles (same places every time)
        floor_tiles = [(x, y) for y in range(rows) for x in range(cols)
                       if self.grid[y][x] == 0
                       and (x, y) != (1, 1) and (x, y) != (cols - 2, rows - 2)]
        rng = random.Random(cfg["seed"] + 1000)
        chosen = rng.sample(floor_tiles, cfg["coins"])
        self.coin_radius = max(5, self.tile // 5)
        self.coin_rects = []
        for x, y in chosen:
            rect = pygame.Rect(0, 0, self.coin_radius * 2, self.coin_radius * 2)
            rect.center = self.cell_rect(x, y).center
            self.coin_rects.append(rect)

        self.coins_collected = 0
        self.elapsed = 0.0

    def cell_rect(self, x, y):
        """Screen rectangle of the tile in column x, row y."""
        return pygame.Rect(self.maze_rect.x + x * self.tile,
                           self.maze_rect.y + y * self.tile,
                           self.tile, self.tile)

    def build_maze_surface(self, cols, rows):
        """Draw the walls and floor once onto a picture (faster than redrawing)."""
        surface = pygame.Surface((cols * self.tile, rows * self.tile))
        for y in range(rows):
            for x in range(cols):
                rect = pygame.Rect(x * self.tile, y * self.tile, self.tile, self.tile)
                if self.grid[y][x] == 1:
                    pygame.draw.rect(surface, WALL_BASE, rect)
                    pygame.draw.rect(surface, WALL_TOP, rect.inflate(-6, -6),
                                     border_radius=5)
                elif (x, y) == (1, 1):
                    pygame.draw.rect(surface, START_TILE, rect)
                else:
                    pygame.draw.rect(surface, FLOOR_A if (x + y) % 2 == 0 else FLOOR_B, rect)
        return surface

    # ------------------------------------------------------------------
    #  Sound helper
    # ------------------------------------------------------------------
    def play(self, sound):
        if sound is not None and not self.muted:
            sound.play()

    # ------------------------------------------------------------------
    #  Handling keyboard and mouse
    # ------------------------------------------------------------------
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:         # the X button
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self.on_key(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.on_click(event.pos)

    def on_key(self, key):
        confirm = key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)
        if key == pygame.K_m:
            self.muted = not self.muted
        if self.state == "start":
            if confirm:
                self.start_game()
        elif self.state == "playing":
            if key in (pygame.K_p, pygame.K_ESCAPE):
                self.state = "paused"
            elif key == pygame.K_r:
                self.load_level()
        elif self.state == "paused":
            if key in (pygame.K_p, pygame.K_ESCAPE, pygame.K_RETURN):
                self.state = "playing"
            elif key == pygame.K_r:
                self.load_level()
                self.state = "playing"
        elif self.state == "level_complete":
            if confirm:
                self.next_level()
        elif self.state == "game_over":
            if confirm:
                self.start_game()

    def on_click(self, pos):
        if self.state == "start" and START_BUTTON.collidepoint(pos):
            self.start_game()
        elif self.state == "paused":
            if RESUME_BUTTON.collidepoint(pos):
                self.state = "playing"
            elif RESTART_BUTTON.collidepoint(pos):
                self.load_level()
                self.state = "playing"
        elif self.state == "level_complete" and NEXT_BUTTON.collidepoint(pos):
            self.next_level()
        elif self.state == "game_over" and AGAIN_BUTTON.collidepoint(pos):
            self.start_game()

    def start_game(self):
        self.new_game()
        self.state = "playing"

    def next_level(self):
        self.level_index += 1
        if self.level_index >= len(LEVELS):
            self.level_index = len(LEVELS) - 1    # keep the last maze on screen
            self.state = "game_over"
        else:
            self.load_level()
            self.state = "playing"

    # ------------------------------------------------------------------
    #  Updating the game (movement, collisions, coins, winning)
    # ------------------------------------------------------------------
    def move_player(self, dx, dy):
        """Move the player and stop at walls. X and Y are handled separately."""
        self.player.x += dx
        for i in self.player.collidelistall(self.walls):
            wall = self.walls[i]
            if self.player.colliderect(wall):
                if dx > 0:
                    self.player.right = wall.left
                elif dx < 0:
                    self.player.left = wall.right

        self.player.y += dy
        for i in self.player.collidelistall(self.walls):
            wall = self.walls[i]
            if self.player.colliderect(wall):
                if dy > 0:
                    self.player.bottom = wall.top
                elif dy < 0:
                    self.player.top = wall.bottom

    def update(self, dt):
        if self.state != "playing":
            return
        self.elapsed += dt

        keys = pygame.key.get_pressed()
        dx = dy = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= self.speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += self.speed
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy -= self.speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy += self.speed
        self.move_player(dx, dy)
        self.player.clamp_ip(self.maze_rect)      # never leave the maze

        # Collect coins
        for coin in list(self.coin_rects):
            if self.player.colliderect(coin):
                self.coin_rects.remove(coin)
                self.coins_collected += 1
                self.play(self.coin_sound)

        # Reached the exit?
        if self.exit_rect.collidepoint(self.player.center):
            self.finish_level()

    def finish_level(self):
        cfg = LEVELS[self.level_index]
        coin_points = self.coins_collected * COIN_POINTS
        seconds_saved = max(0, cfg["par"] - int(self.elapsed))
        time_bonus = seconds_saved * TIME_BONUS_PER_SECOND
        self.total_score += coin_points + time_bonus + CLEAR_BONUS
        self.total_time += self.elapsed
        self.total_coins += self.coins_collected
        self.result = {"time": self.elapsed, "coins": self.coins_collected,
                       "coin_total": cfg["coins"], "coin_points": coin_points,
                       "time_bonus": time_bonus}
        self.play(self.win_sound)
        self.state = "level_complete"

    # ------------------------------------------------------------------
    #  Drawing helpers
    # ------------------------------------------------------------------
    def draw_text(self, text, font, color, center=None, topleft=None,
                  midright=None, shadow=False):
        image = font.render(text, True, color)
        rect = image.get_rect()
        if center:
            rect.center = center
        elif topleft:
            rect.topleft = topleft
        elif midright:
            rect.midright = midright
        if shadow:
            self.screen.blit(font.render(text, True, (0, 0, 0)), (rect.x + 3, rect.y + 3))
        self.screen.blit(image, rect)

    def draw_button(self, rect, text):
        hovered = rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(self.screen, BUTTON_HOVER if hovered else BUTTON,
                         rect, border_radius=16)
        pygame.draw.rect(self.screen, WHITE, rect, 3, border_radius=16)
        self.draw_text(text, self.font_med, WHITE, center=rect.center)

    def draw_panel(self, rect):
        pygame.draw.rect(self.screen, (30, 25, 70), rect, border_radius=24)
        pygame.draw.rect(self.screen, WHITE, rect, 3, border_radius=24)

    # ------------------------------------------------------------------
    #  Drawing each screen
    # ------------------------------------------------------------------
    def draw_start(self):
        self.draw_text("MAZE RUNNER", self.font_title, GOLD,
                       center=(WIDTH // 2, 160), shadow=True)
        self.draw_text("Find the exit, grab the coins, beat the clock!",
                       self.font_med, WHITE, center=(WIDTH // 2, 250), shadow=True)
        self.draw_text("3 levels: Easy, Medium and Hard", self.font_small, LIGHT,
                       center=(WIDTH // 2, 300))
        self.draw_button(START_BUTTON, "START GAME")

        panel = pygame.Rect(WIDTH // 2 - 300, 490, 600, 180)
        self.draw_panel(panel)
        controls = ["Arrow keys or W A S D  -  Move",
                    "P or Esc  -  Pause / Resume",
                    "R  -  Restart the level",
                    "M  -  Sound on / off",
                    "Enter or Space  -  Start"]
        for i, line in enumerate(controls):
            self.draw_text(line, self.font_small, WHITE,
                           center=(WIDTH // 2, 515 + i * 30))

    def draw_game(self):
        cfg = LEVELS[self.level_index]

        # Top information bar
        pygame.draw.rect(self.screen, (25, 18, 60), (0, 0, WIDTH, HUD_H))
        pygame.draw.line(self.screen, GOLD, (0, HUD_H), (WIDTH, HUD_H), 3)
        live_score = self.total_score + self.coins_collected * COIN_POINTS
        mid = HUD_H // 2
        self.draw_text(f"Level {self.level_index + 1}/{len(LEVELS)} ({cfg['name']})",
                       self.font_med, WHITE, center=(150, mid))
        self.draw_text(f"Time {format_time(self.elapsed)}", self.font_med, WHITE,
                       center=(390, mid))
        self.draw_text(f"Score {live_score}", self.font_med, GOLD, center=(620, mid))
        self.draw_text(f"Coins {self.coins_collected}/{cfg['coins']}", self.font_med,
                       GOLD, center=(830, mid))

        # Maze
        self.screen.blit(self.maze_surface, self.maze_rect.topleft)

        # Exit (pulsing green target)
        ticks = pygame.time.get_ticks()
        pulse = (math.sin(ticks / 250) + 1) / 2
        pygame.draw.rect(self.screen, EXIT_GREEN, self.exit_rect.inflate(-4, -4),
                         border_radius=8)
        pygame.draw.circle(self.screen, WHITE, self.exit_rect.center,
                           int(self.exit_rect.width * (0.22 + 0.06 * pulse)))
        pygame.draw.circle(self.screen, EXIT_DARK, self.exit_rect.center,
                           max(2, int(self.exit_rect.width * 0.1)))

        # Coins (they gently bob in size)
        for coin in self.coin_rects:
            r = self.coin_radius + int(math.sin(ticks / 180) * 2)
            pygame.draw.circle(self.screen, GOLD, coin.center, r)
            pygame.draw.circle(self.screen, (200, 150, 0), coin.center, r, 2)
            pygame.draw.circle(self.screen, (255, 245, 150), coin.center, max(2, r // 3))

        # Player: an orange square with eyes
        pygame.draw.rect(self.screen, PLAYER_COLOR, self.player, border_radius=6)
        size = self.player.width
        eye = max(2, size // 6)
        for fraction in (0.3, 0.7):
            eye_pos = (self.player.x + int(size * fraction), self.player.y + int(size * 0.4))
            pygame.draw.circle(self.screen, WHITE, eye_pos, eye)
            pygame.draw.circle(self.screen, (0, 0, 0), eye_pos, max(1, eye // 2))

        # Bottom controls bar
        sound_text = "OFF" if self.muted else "ON"
        self.draw_text(f"Move: Arrows / WASD    P: Pause    R: Restart level    M: Sound ({sound_text})",
                       self.font_small, LIGHT, center=(WIDTH // 2, HEIGHT - FOOTER_H // 2))

    def draw_paused(self):
        self.screen.blit(self.dim, (0, 0))
        self.draw_panel(pygame.Rect(WIDTH // 2 - 230, 190, 460, 340))
        self.draw_text("PAUSED", self.font_big, GOLD, center=(WIDTH // 2, 245))
        self.draw_button(RESUME_BUTTON, "Resume")
        self.draw_button(RESTART_BUTTON, "Restart Level")
        self.draw_text("Press P to resume, R to restart", self.font_small, LIGHT,
                       center=(WIDTH // 2, 490))

    def draw_level_complete(self):
        self.screen.blit(self.dim, (0, 0))
        self.draw_panel(pygame.Rect(WIDTH // 2 - 300, 110, 600, 500))
        self.draw_text(f"Level {self.level_index + 1} Complete!", self.font_big, GOLD,
                       center=(WIDTH // 2, 165))
        res = self.result
        lines = [("Time", format_time(res["time"])),
                 ("Coins collected", f"{res['coins']} / {res['coin_total']}"),
                 ("Coin points", f"+{res['coin_points']}"),
                 ("Time bonus", f"+{res['time_bonus']}"),
                 ("Level clear bonus", f"+{CLEAR_BONUS}"),
                 ("Total score", str(self.total_score))]
        for i, (label, value) in enumerate(lines):
            y = 225 + i * 42
            color = GOLD if label == "Total score" else WHITE
            self.draw_text(label, self.font_med, color, topleft=(WIDTH // 2 - 240, y))
            self.draw_text(value, self.font_med, color, midright=(WIDTH // 2 + 240, y + 15))
        last = self.level_index == len(LEVELS) - 1
        self.draw_button(NEXT_BUTTON, "See Final Score" if last else "Next Level")

    def draw_game_over(self):
        self.screen.blit(self.dim, (0, 0))
        self.draw_panel(pygame.Rect(WIDTH // 2 - 300, 110, 600, 500))
        self.draw_text("GAME OVER", self.font_big, GOLD, center=(WIDTH // 2, 165))
        self.draw_text("You escaped all 3 mazes!", self.font_med, WHITE,
                       center=(WIDTH // 2, 220))
        self.draw_text("FINAL SCORE", self.font_small, LIGHT, center=(WIDTH // 2, 285))
        self.draw_text(str(self.total_score), self.font_title, GOLD,
                       center=(WIDTH // 2, 345))
        possible = sum(level["coins"] for level in LEVELS)
        self.draw_text(f"Total time: {format_time(self.total_time)}", self.font_med,
                       WHITE, center=(WIDTH // 2, 430))
        self.draw_text(f"Coins collected: {self.total_coins} / {possible}", self.font_med,
                       WHITE, center=(WIDTH // 2, 470))
        self.draw_button(AGAIN_BUTTON, "Play Again")

    def draw(self):
        self.screen.blit(self.background, (0, 0))
        if self.state == "start":
            self.draw_start()
        else:
            self.draw_game()
            if self.state == "paused":
                self.draw_paused()
            elif self.state == "level_complete":
                self.draw_level_complete()
            elif self.state == "game_over":
                self.draw_game_over()
        pygame.display.flip()

    # ------------------------------------------------------------------
    #  The main game loop
    # ------------------------------------------------------------------
    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000      # seconds since the last frame
            dt = min(dt, 0.1)                     # avoid big jumps in the timer
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Game().run()