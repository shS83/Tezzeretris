import pygame
import sys
import random
import math

from pygame.examples.music_drop_fade import music_file_types

pygame.init()
pygame.mixer.init()

# ============= SOUND SETUP ================
try:
    sound_lineclear = pygame.mixer.Sound("assets/linescore.wav")
    sound_levelup = pygame.mixer.Sound("assets/levelup.wav")
    sound_gameover = pygame.mixer.Sound("assets/gameover.wav")
    sound_startgame = pygame.mixer.Sound("assets/start.wav")
    pygame.mixer.music.load("assets/background_ambient.wav")
    pygame.mixer.music.play()
except OSError as e:
    # Graceful fallback if sounds missing
    sound_lineclear = sound_levelup = sound_gameover = None
# ==========================================

# Screen setup
WIDTH, HEIGHT = 768, 1280
BLOCK_SIZE = 40
COLS = WIDTH // BLOCK_SIZE
ROWS = HEIGHT // BLOCK_SIZE

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Tezzertits")

# Shapes and colors
SHAPES = {
    "I": [[1, 1, 1, 1]],
    "O": [[1, 1],
          [1, 1]],
    "T": [[0, 1, 0],
          [1, 1, 1]],
    "S": [[0, 1, 1],
          [1, 1, 0]],
    "Z": [[1, 1, 0],
          [0, 1, 1]],
    "J": [[1, 0, 0],
          [1, 1, 1]],
    "L": [[0, 0, 1],
          [1, 1, 1]]
}

COLORS = {
    "I": (0, 255, 255),
    "O": (255, 255, 0),
    "T": (128, 0, 128),
    "S": (0, 255, 0),
    "Z": (255, 0, 0),
    "J": (0, 0, 255),
    "L": (255, 165, 0)
}

# Game board
board = [[(0, 0, 0) for _ in range(COLS)] for _ in range(ROWS)]

# Scoring & level system
started = False
score = 0
level = 1
lines_cleared = 0
fall_speed = 700  # milliseconds, will go down with levels

# Font for UI
font = pygame.font.SysFont("Fira Code", 24)

def play_level_up_effect(screen, level, board_surface=None):
    """Play a quick celebratory effect when leveling up."""
    clock2 = pygame.time.Clock()
    font2 = pygame.font.SysFont("Crimson Pro", 60, bold=True)

    surf = font2.render(f"LEVEL {level}", True, (255, 40, 0))
    rect = surf.get_rect(center=(screen.get_width()//2, screen.get_height()//2))

    particles = []
    for _ in range(400):
        particles.append([
            rect.centerx, rect.centery,               # x, y
            random.uniform(-15, 15), random.uniform(-15, 15),  # vx, vy
            random.randint(20, 60)                    # life frames
        ])

    for frame in range(200):
        if board_surface:
            screen.blit(board_surface, (0, 0))
        else:
            screen.fill((0, 0, 0))

        # pulsating text
        scale = 200 + int(20 * (1 + math.sin(frame/8)))
        scaled = pygame.transform.scale(
            surf, (surf.get_width()*scale//100, surf.get_height()*scale//100)
        )
        srect = scaled.get_rect(center=rect.center)
        screen.blit(scaled, srect)

        # update/draw particles
        for p in particles:
            if p[4] > 0:
                p[0] += p[2]
                p[1] += p[3]
                p[3] += 0.05              # gravity
                p[4] -= 1
                pygame.draw.circle(screen, (random.randint(100,255), random.randint(100,255), random.randint(100, 255), random.randint(1,10)/10), (int(p[0]), int(p[1])), 3)

        pygame.display.flip()
        clock2.tick(30)

class Piece:
    def __init__(self, shape):
        self.shape = SHAPES[shape]
        self.color = COLORS[shape]
        self.x = COLS // 2 - len(self.shape[0]) // 2
        self.y = 0

    def rotate(self):
        self.shape = [list(row) for row in zip(*self.shape[::-1])]

    def valid(self, dx=0, dy=0):
        for y, row in enumerate(self.shape):
            for x, cell in enumerate(row):
                if cell:
                    nx = self.x + x + dx
                    ny = self.y + y + dy
                    if nx < 0 or nx >= COLS or ny >= ROWS:
                        return False
                    if ny >= 0 and board[ny][nx] != (0, 0, 0):
                        return False
        return True

    def place(self):
        for y, row in enumerate(self.shape):
            for x, cell in enumerate(row):
                if cell:
                    board[self.y + y][self.x + x] = self.color
        return clear_lines()


def clear_lines():
    global board, score, lines_cleared, level, fall_speed
    new_board = [row for row in board if any(c == (0, 0, 0) for c in row)]
    cleared = ROWS - len(new_board)
    if cleared > 0:
        for _ in range(cleared):
            new_board.insert(0, [(0, 0, 0)] * COLS)
        backup_board = board.copy()
        board = new_board
        # Scoring
        score += (cleared ** 2) * 100
        lines_cleared += cleared

        # 🔊 Play line clear sound
        if sound_lineclear:
            sound_lineclear.play()

        # Level increase depending on level
        if lines_cleared >= level * 10:
            level_up(backup_board)

    return cleared


def level_up(smuggled_board):
    global level, fall_speed
    level += 1
    fall_speed = max(100, fall_speed - 50)  # speed up

    # Animation & sound
    # level_transition_effect()

    # board_surface = screen.copy()
    play_level_up_effect(screen, level, smuggled_board)

    if sound_levelup:
        sound_levelup.play()


def level_transition_effect():
    flash_colors = [(255, 255, 0), (255, 165, 0), (0, 255, 0), (0, 128, 255), (255, 0, 128)]
    for color in flash_colors:
        screen.fill(color)
        pygame.display.flip()
        pygame.time.delay(150)


def draw_board():
    for y in range(ROWS):
        for x in range(COLS):
            pygame.draw.rect(screen, board[y][x], (x * BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE), 0)
            pygame.draw.rect(screen, (10, 10, 30, 0.1), (x * BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE), 2)


def draw_piece(piece):
    for y, row in enumerate(piece.shape):
        for x, cell in enumerate(row):
            if cell:
                nx = (piece.x + x) * BLOCK_SIZE
                ny = (piece.y + y) * BLOCK_SIZE
                pygame.draw.rect(screen, piece.color, (nx, ny, BLOCK_SIZE, BLOCK_SIZE), 0)
                pygame.draw.rect(screen, (200, 200, 200), (nx, ny, BLOCK_SIZE, BLOCK_SIZE), 1)


def draw_ui():
    global started
    score_text = font.render(f"Score: {score}", True, (255, 255, 255))
    level_text = font.render(f"Level: {level}", True, (255, 255, 255))
    screen.blit(score_text, (10, 10))
    screen.blit(level_text, (10, 40))
    if sound_startgame and not started:
            sound_startgame.set_volume(0.4)
            sound_startgame.play()
            started = True

# Main Game loop
clock = pygame.time.Clock()
current_piece = Piece(random.choice(list(SHAPES.keys())))
fall_time = 0

while True:
    dt = clock.tick(60)
    fall_time += dt

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT and current_piece.valid(dx=-1):
                current_piece.x -= 1
            elif event.key == pygame.K_RIGHT and current_piece.valid(dx=1):
                current_piece.x += 1
            elif event.key == pygame.K_DOWN and current_piece.valid(dy=1):
                current_piece.y += 1
            elif event.key == pygame.K_UP:
                old_shape = current_piece.shape
                current_piece.rotate()
                if not current_piece.valid():
                    current_piece.shape = old_shape
            elif event.key == pygame.K_SPACE:
                while current_piece.valid():
                    current_piece.y += 1
                    draw_piece(current_piece)
                    pygame.display.flip()
                current_piece.y -= 1
            elif event.key == pygame.K_KP_PLUS:
                smugglers_surface = pygame.Surface.copy(screen)
                level_up(smugglers_surface)

    if fall_time > fall_speed:
        if current_piece.valid(dy=1):
            current_piece.y += 1
        else:
            cleared = current_piece.place()
            current_piece = Piece(random.choice(list(SHAPES.keys())))
            if not current_piece.valid():
                # 🔊 Game over sound
                if sound_gameover:
                    sound_gameover.play()
                    pygame.time.delay(4000)  # wait so player hears it
                print("GAME OVER! Final Score:", score)
                pygame.quit()
                sys.exit()
        fall_time = 0

    screen.fill((0, 0, 0))
    draw_board()
    draw_piece(current_piece)
    draw_ui()
    pygame.display.flip()
