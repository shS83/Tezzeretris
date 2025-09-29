import pygame as pg

pg.init()
# Screen setup
WIDTH, HEIGHT = 640, 800
BLOCK_SIZE = 40
COLS = WIDTH // BLOCK_SIZE
ROWS = HEIGHT // BLOCK_SIZE
screen = pg.display.set_mode((WIDTH, HEIGHT))
board_surface = pg.Surface((WIDTH, HEIGHT))
pg.display.set_caption("Tezzeretris")