import pygame as pg
import sys
import random
import math
from pygame.locals import *
from config import *

pg.init()

try:
    pg.mixer.init()
except Exception as e:
    print("Seems you don't have mixer. Oh well..")

try:
    sound_lineclear = pg.mixer.Sound("assets/new_linescore.wav")
    sound_levelup = pg.mixer.Sound("assets/levelup.wav")
    sound_gameover = pg.mixer.Sound("assets/gameover.wav")
    sound_startgame = pg.mixer.Sound("assets/start.wav")
    pg.mixer.music.load("assets/background_ambient.wav")
    pg.mixer.music.play(loops=100)
except OSError as e:
    sound_startgame = sound_lineclear = sound_levelup = sound_gameover = None
    print(f"[WARNING] {e}")

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
board = [[(0, 0, 0, 0.0) for _ in range(COLS)] for _ in range(ROWS)]

# Scoring & level system
started = False
score = 0
level = 1
lines_cleared = 0
fall_speed = 500  # milliseconds, will go down with levels

# Font for UI
font = pg.font.SysFont("Fira Code", 24)


def play_level_up_effect(level: int, surface : pg.Surface = None):
    """Play a quick celebratory effect when leveling up."""
    global lines_cleared, board_surface
    clock2 = pg.time.Clock()
    font2 = pg.font.SysFont("Newsreader", 60, bold=True)

    surf = font2.render(f"LEVEL {level}", True, (255, 40, 0))
    rect = surf.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))

    particles = []
    for _ in range(400):
        particles.append([
            rect.centerx, rect.centery,  # x, y
            random.uniform(-15, 15), random.uniform(-15, 15),  # vx, vy
            random.randint(20, 60)  # life frames
        ])

    for frame in range(100):
        if board_surface:
            screen.blit(board_surface, (0, 0))
        else:
            screen.fill((0, 0, 0, 0.0))

        # pulsating text
        scale = 200 + int(20 * (1 + math.sin(frame / 8)))
        scaled = pg.transform.scale(
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
                pg.draw.circle(screen,
                                   (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255),
                                    random.randint(1, 10) / 10), (int(p[0]), int(p[1])), 3)

        pg.display.flip()
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
                    board[self.y + y][self.x + x] = self.color
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
        score += (cleared ** 2) * 100
        lines_cleared += cleared

        if sound_lineclear:
            sound_lineclear.play()

        # Level increase depending on level
        if lines_cleared >= level * 5:
            level_up()

    return cleared


def level_up():
    global level, fall_speed, started, board_surf
    level += 1
    fall_speed = max(100, fall_speed - 50)  # speed up

    if sound_levelup:
        sound_levelup.play()

    redrum_flash()
    pg.time.wait(1000)
    play_level_up_effect(level, board_surf)
    started = False


def redrum_flash():
    colrs = [255, 200, 150, 0.3]

    dictresult = {"color": random.randint(0, 255), "alpha": random.randint(0, 255)}
    alpha = dictresult.get("alpha")
    colorresult = dictresult.get("color")

    match colorresult:
        case "yellow":
            colrs = [255, 255, 0, float(alpha)]
        case "red":
            colrs = [255, 0, 0, float(alpha)]
        case "green":
            colrs = [0, 255, 0, float(alpha)]
        case "blue":
            colrs = [0, 0, 255, float(alpha)]
        case "gray":
            colrs = [128, 128, 255, float(alpha)]
        case "cyan":
            colrs = [100, 255, 255, float(alpha)]
        case _:
            colrs = [0, 255, 128, float(alpha)]

    fadestart = 255

    if coord := colrs.index(255):
        replaced = True
    for colr in range(fadestart, 0, -1):
        colrs[coord] = colr
        board_surf.fill(colrs)
        screen.blit(board_surf, (0, 0))
        pg.display.update()
        pg.time.delay(1)

def lotto_for_colors():
    return [random.randint(100,255), random.randint(100,255), random.randint(100,255), random.randint(1,100) / 100]

def prep_board(randomsurface: pg.Surface, colors: tuple):
    b_cols = [[(0, 0, 0) for _ in range(COLS)] for _ in range(ROWS)]
    b_finished = pg.Surface(randomsurface.get_size())

    for r in range(ROWS):
        for c in range(COLS):
            b_cols[r][c] = (colors[0], colors[1], colors[2])

        # color_r, color_g, color_b = colors
        # winner = max([color_r, color_g, color_b])


        # for rivi in range(ROWS):
        #     for sarake in range(COLS):
        #         match int(winner):
        #             case int(color_r):
        #                 color_r = 255 - (random.randint(0, 255))
        #                 alpha = random.randint(0, 100) / 1000
        #             case int(color_g):
        #                 color_g = 255 - (random.randint(0, 255))
        #                 alpha = random.randint(0, 100) / 1000
        #             case int(color_b):
        #                 color_b = 255 - (random.randint(0, 255))
        #                 alpha = random.randint(0, 100) / 1000
        #             case _:
        #                 color_r = random.randint(150, 255)
        #                 color_g = random.randint(150, 255)
        #                 color_b = random.randint(150, 255)
        #                 alpha = random.randint(0, 100) / 1000

                # b_cols[rivi][sarake] = (color_r, color_g, color_b, alpha)

        strange = b_cols.pop()
        print(strange)

        for y in range(ROWS):
            for x in range(COLS):
                rand_r = random.randint(20, 100)
                rand_g = random.randint(30, 70)
                rand_b = random.randint(46, 120)
                alpha = random.randint(1, 10) / 10

                pg.draw.rect(b_finished, (rand_r, rand_g, rand_b, alpha), (x * BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE), 1)
                r = b_cols[y][x][0]
                g = b_cols[y][x][1]
                b = b_cols[y][x][2]
                print(f"r {r}, g {g}, b {b}")
                pg.draw.rect(b_finished, (r, g, b),(x * BLOCK_SIZE, y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE), 2)

    return b_finished

def draw_board(actual_board: pg.Surface):
    screen.blit(actual_board, (0, 0))

def draw_piece(bsurf: pg.Surface, piece):
    for y, row in enumerate(piece.shape):
        for x, cell in enumerate(row):
            if cell:
                nx = (piece.x + x) * BLOCK_SIZE
                ny = (piece.y + y) * BLOCK_SIZE
                if ny > bsurf.get_height():
                    ny = piece.y * BLOCK_SIZE
                pg.draw.rect(bsurf, piece.color, (nx, ny, BLOCK_SIZE, BLOCK_SIZE), 2)
                pg.draw.rect(bsurf, (200, 200, 200), (nx, ny, BLOCK_SIZE, BLOCK_SIZE), 0)
                screen.blit(bsurf, (nx, ny))


def draw_ui():
    global started
    score_text = font.render(f"SCORE: {score}", True, (150, 255, 150))
    level_text = font.render(f"LEVEL: {level}", True, (255, 255, 150))
    screen.blit(score_text, (10, 10))
    screen.blit(level_text, (10, 60))
    if sound_startgame and not started:
            sound_startgame.set_volume(0.4)
            sound_startgame.play()
            started = True

# Main Game loop
clock = pg.time.Clock()
current_piece = Piece(random.choice(list(SHAPES.keys())))
fall_time = 0
# level_r, level_g, level_b = random.randint(1, 255), random.randint(1, 255), random.randint(1, 255)
# board_surf = prep_board(screen, (level_r, level_g, level_b, random.randint(1, 100) / 100))
board_surf = prep_board(screen, (random.randint(10,150), 120, random.randint(40,200), 0.8))
blank_board = board_surf.copy()
running = True

while running:
    dt = clock.tick(120)
    fall_time += dt

    for event in pg.event.get():
        if event.type == pg.QUIT:
            running = False
            pg.quit()
            sys.exit()

        elif event.type == pg.KEYDOWN:
            if event.key == pg.K_ESCAPE:
                running = False
                pg.quit()
                sys.exit()

            if event.key == pg.K_LEFT and current_piece.valid(dx=-1):
                current_piece.x -= 1
            elif event.key == pg.K_RIGHT and current_piece.valid(dx=1):
                current_piece.x += 1
            elif event.key == pg.K_DOWN and current_piece.valid(dy=1):
                current_piece.y += 1
            elif event.key == pg.K_UP:
                old_shape = current_piece.shape
                current_piece.rotate()
                if not current_piece.valid():
                    current_piece.shape = old_shape
            elif event.key == pg.K_SPACE:
                ghostpiece = Piece(random.choice(list(SHAPES.keys())))
                while current_piece.valid():
                    current_piece.y += 1
                    draw_piece(board_surf, current_piece)
                    screen.blit(board_surf, (0, 0))
                    color_for_piece = (0, 0, 0)
                    ghostpiece.color = color_for_piece
                    ghostpiece.y = current_piece.y - 1
                    draw_piece(screen, ghostpiece)
                    screen.blit(board_surface, (0, 0))

                board_surf = blank_board.copy()
                current_piece.y -= 1
                current_piece.color = (255, 200, 150, 1.0)
                draw_piece(board_surf, current_piece)
                board_surf.blit(screen, (0, 0))
                pg.display.update()

            elif event.key == pg.K_KP_PLUS:
                level_up()

    if fall_time > fall_speed:
        if current_piece.valid(dy=1):
            current_piece.y += 1
        else:
            cleared = current_piece.place()
            current_piece = Piece(random.choice(list(SHAPES.keys())))
            if not current_piece.valid():

                if sound_gameover:
                    sound_gameover.play()
                    pg.time.delay(4000)  # wait so player hears it

                print("GAME OVER! Final Score:", score)
                pg.quit()
                sys.exit()
        fall_time = 0

    screen.fill((0, 0, 0))
    todays_colors = []
    for row in range(ROWS):
        for col in range(COLS):
            todays_colors.append((random.randint(10, 255), (random.randint(10, 255), (random.randint(10, 255), random.randint(1, 10) / 20))))
    proper_board = prep_board(board_surf, todays_colors)
    draw_board(proper_board)
    draw_piece(proper_board, current_piece)
    screen.blit(proper_board, (0, 0))
    draw_ui()
    pg.display.update()



pg.quit()
sys.exit()