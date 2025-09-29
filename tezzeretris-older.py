from copy import deepcopy
from typing import no_type_check

import pygame
import sys
import random
import math

pygame.init()

try:
    pygame.mixer.init()
except Exception as e:
    print("Seems you don't have mixer. Oh well..")

# ============= SOUND SETUP ================
try:
    sound_lineclear = pygame.mixer.Sound("assets/new_linescore.wav")
    sound_levelup = pygame.mixer.Sound("assets/levelup.wav")
    sound_gameover = pygame.mixer.Sound("assets/gameover.wav")
    sound_startgame = pygame.mixer.Sound("assets/start.wav")
    pygame.mixer.music.load("assets/background_ambient.wav")
    pygame.mixer.music.play(loops=100)
except OSError as e:
    sound_startgame = sound_lineclear = sound_levelup = sound_gameover = None
    print(f"[WARNING] {e}")
# ==========================================

# Screen setup
WIDTH, HEIGHT = 720, 1280
BLOCK_SIZE = 32
COLS = WIDTH // BLOCK_SIZE
ROWS = HEIGHT // BLOCK_SIZE

screen = pygame.display.set_mode((WIDTH, HEIGHT))
board_surface = pygame.Surface.convert_alpha(screen)
pygame.display.set_caption("Tezzeretris")

# Shapes and colors
SHAPES = {
    "I": [[1, 1, 1, 1]],
    "O": [[1, 1], [1, 1]],
    "T": [[0, 1, 0], [1, 1, 1]],
    "S": [[0, 1, 1], [1, 1, 0]],
    "Z": [[1, 1, 0], [0, 1, 1]],
    "J": [[1, 0, 0], [1, 1, 1]],
    "L": [[0, 0, 1], [1, 1, 1]],
}

COLORS = {
    "I": (0, 255, 255),
    "O": (255, 255, 0),
    "T": (128, 0, 128),
    "S": (0, 255, 0),
    "Z": (255, 0, 0),
    "J": (0, 0, 255),
    "L": (255, 165, 0),
}

# Game board
board = [[(0, 0, 0) for _ in range(COLS)] for _ in range(ROWS)]

# Scoring & level system
started = False
score = 0
level = 1
lines_cleared = 0
fall_speed = 400  # milliseconds, will go down with levels

# Font for UI
font = pygame.font.SysFont("Arial", 24)


def play_level_up_effect(
    screen: pygame.Surface, level: int, board_surface: pygame.Surface = None
):
    """Play a quick celebratory effect when leveling up."""
    clock2 = pygame.time.Clock()
    font2 = pygame.font.SysFont("System", 60, bold=True)

    surf = font2.render(f"LEVEL {level}", True, (255, 40, 0))
    rect = surf.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))

    particles = []
    for _ in range(400):
        particles.append(
            [
                rect.centerx,
                rect.centery,  # x, y
                random.uniform(-15, 15),
                random.uniform(-15, 15),  # vx, vy
                random.randint(20, 60),  # life frames
            ]
        )

    for frame in range(100):
        if board_surface:
            screen.blit(board_surface, (0, 0))
        else:
            screen.fill((0, 0, 0))

        # pulsating text
        scale = 200 + int(20 * (1 + math.sin(frame / 8)))
        scaled = pygame.transform.scale(
            surf, (surf.get_width() * scale // 100, surf.get_height() * scale // 100)
        )
        srect = scaled.get_rect(center=rect.center)
        screen.blit(scaled, srect)

        # update/draw particles
        for p in particles:
            if p[4] > 0:
                p[0] += p[2]
                p[1] += p[3]
                p[3] += 0.05  # gravity
                p[4] -= 1
                pygame.draw.circle(
                    screen,
                    (
                        random.randint(100, 255),
                        random.randint(100, 255),
                        random.randint(100, 255),
                        random.randint(1, 10) / 10,
                    ),
                    (int(p[0]), int(p[1])),
                    3,
                )

        pygame.display.flip()
        clock2.tick(60)


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
                    board[self.y + y][self.x + x] = (150,self.color[1],self.color[2])
                    pygame.draw.rect(board_surface, (150,self.color[1],self.color[2]), (BLOCK_SIZE, BLOCK_SIZE, x * BLOCK_SIZE, y * BLOCK_SIZE), 1)
                    screen.blit(board_surface, (0, 0))
                    pygame.display.flip()
                    return clear_lines()


def clear_lines():
    global board, score, lines_cleared, level, fall_speed
    new_board = [row for row in board if any(c == (0, 0, 0) for c in row)]
    cleared = ROWS - len(new_board)
    if cleared > 0:
        for _ in range(cleared):
            new_board.insert(0, [(0, 0, 0)] * COLS)
        board = new_board

        # Scoring
        score += (cleared**2) * 100
        lines_cleared += cleared

        if sound_lineclear:
            sound_lineclear.play()

        # Level increase depending on level
        if lines_cleared >= level * 5:
            level_up(pygame.Surface.convert_alpha(board_surface))

    return cleared


def level_up(smuggled_board):
    global level, fall_speed, started
    level += 1
    fall_speed = max(100, fall_speed - 50)  # speed up

    if sound_levelup:
        sound_levelup.play()

    redrum_flash()
    pygame.time.wait(1000)
    play_level_up_effect(screen, level, smuggled_board)
    started = False


def redrum_flash():
    eastern_roulette = [0, 255]
    for color in range(255, 0, -1):
        screen.fill(
            (
                abs(random.choice(eastern_roulette) - color),
                abs(random.choice(eastern_roulette) - color),
                abs(random.choice(eastern_roulette) - color),
            )
        )
        pygame.display.flip()
        pygame.time.delay(1)


def lotto_for_colors():
    return random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)


def prep_board(somesurface: pygame.Surface, colors: tuple):
    b_cols = [[(0, 0, 0) for _ in range(COLS)] for _ in range(ROWS)]
    color_r, color_g, color_b = colors
    alpha = 0.2
    winner = max([color_r, color_g, color_b])
    b_finished = pygame.Surface(somesurface.get_size())

    for row in range(ROWS):
        for col in range(COLS):
            match int(winner):
                case int(color_r):
                    color_r = 255 - ((random.randint(0, 255) * 2) - 255)
                    alpha = random.randint(0, 100) / 1000
                case int(color_g):
                    color_g = 255 - ((random.randint(0, 255) * 2) - 255)
                    alpha = random.randint(0, 100) / 1000
                case int(color_b):
                    color_b = 255 - ((random.randint(0, 255) * 2) - 255)
                    alpha = random.randint(0, 100) / 1000
                case _:
                    color_r = random.randint(150, 255)
                    color_g = random.randint(150, 255)
                    color_b = random.randint(150, 255)
                    alpha = random.randint(0, 100) / 1000

            b_cols[row][col] = (color_r, color_g, color_b)

    for y in range(ROWS):
        for x in range(COLS):
            r = b_cols[y][x][0]
            g = b_cols[y][x][1]
            b = b_cols[y][x][2]

            if r>255:
                r=255
            elif g>255:
                g=255
            elif b>255:
                b=255

            pygame.draw.rect(b_finished, (random.randint(0, 20), random.randint(0, 20), \
                                          random.randint(0, 20)), (x * BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE), 3)
            pygame.draw.rect(b_finished, (255, 130, 100),(x * BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE),2)

    return b_finished


def draw_board(board_surf: pygame.Surface):
    screen.blit(board_surf, (0, 0))


def draw_piece(bsurf: pygame.Surface, piece):
    for y, row in enumerate(piece.shape):
        for x, cell in enumerate(row):
            if cell:
                nx = (piece.x + x) * BLOCK_SIZE
                ny = (piece.y + y) * BLOCK_SIZE
                pygame.draw.rect(
                    bsurf, piece.color, (nx, ny, BLOCK_SIZE, BLOCK_SIZE), 5
                )
                pygame.draw.rect(
                    bsurf, (200, 200, 200), (nx, ny, BLOCK_SIZE, BLOCK_SIZE), 1
                )

def draw_single(bsurf: pygame.Surface, shape: tuple, color: tuple, px: int, py: int):
    global BLOCK_SIZE
    for y, row in enumerate(shape):
        for x, cell in enumerate(row):
            if cell:
                nx = (px * BLOCK_SIZE)
                ny = (py * BLOCK_SIZE)
                pygame.draw.rect(bsurf, color, (nx, ny, BLOCK_SIZE, BLOCK_SIZE), 5)
                pygame.draw.rect(bsurf, (200, 200, 200), (nx, ny, BLOCK_SIZE, BLOCK_SIZE), 2)



def draw_ui():
    global started
    score_text = font.render(f"Score: {score}", True, (255, 255, 255))
    level_text = font.render(f"Level: {level}", True, (255, 255, 255))
    y_text = font.render(f"current piece y: {current_piece.y}", True, (255, 255, 0))
    screen.blit(score_text, (10, 10))
    screen.blit(level_text, (10, 40))
    screen.blit(y_text, (10, 70))
    if sound_startgame and not started:
        sound_startgame.set_volume(0.4)
        sound_startgame.play()
        started = True


# Main Game loop
clock = pygame.time.Clock()
current_piece = Piece(random.choice(list(SHAPES.keys())))
fall_time = 0
level_r, level_g, level_b = (
    random.randint(1, 100),
    random.randint(1, 100),
    random.randint(1, 100),
)

while True:
    dt = clock.tick(120)
    fall_time += dt
    old_pieces = []

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

                    if current_piece.valid(dy=1):
                        current_piece.y += 1
                    else:
                        current_piece.place()
                        old_pieces.append(current_piece)

            elif event.key == pygame.K_KP_PLUS:
                level_up(board_surface)


    if fall_time > fall_speed or current_piece.y > 30:
        if current_piece.valid(dy=1):
            current_piece.y += 1
        else:
            cleared = current_piece.place()
            old_pieces.append(cleared)
            current_piece = Piece(random.choice(list(SHAPES.keys())))
            if not current_piece.valid():

                if sound_gameover:
                    sound_gameover.play()
                    pygame.time.delay(4000)  # wait so player hears it

                print("GAME OVER! Final Score:", score)
                pygame.quit()
                sys.exit()
        fall_time = 0


    proper_board = prep_board(screen, (240, random.randint(10, 100), 58))
    screen.fill((0, 0, 0))
    proper_board.set_colorkey((255, 149, 100))
    proper_board.set_alpha(100)
    draw_board(proper_board)
    if len(old_pieces) > 0:
        for obj in old_pieces:
            try:
                shape = tuple(obj.shape)
                print(shape)
                color = obj.color
                print(color)
                x = obj.y
                y = obj.y
                print(x, y)
                draw_single(screen, shape, color, x, y)
                pygame.display.update()
            except AttributeError:
                continue



    # for rivi in range(ROWS-1, 0, -1):
    #     for sarake in range(COLS-1, 0, -1):
    draw_piece(screen, current_piece)


            #if board[rivi][sarake] != (0, 0, 0):
                #pygame.draw.rect(screen, board[rivi][sarake], (BLOCK_SIZE * rivi, BLOCK_SIZE * sarake, BLOCK_SIZE, BLOCK_SIZE),5, 5)
                # draw_piece(screen, piece=board[rivi][sarake])
                # print(lines_cleared.__dir__)

                # print(board.__dir__)




    # new_stage = pygame.Surface(proper_board.convert_alpha().get_size())
    # new_stage.fill((0, 0, 0))
    # screen.blit(new_stage, (0, 0))
    # draw_piece(new_stage, current_piece)
    draw_ui()
    pygame.display.flip()
