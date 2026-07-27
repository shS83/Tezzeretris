#!/usr/bin/env python3
"""
PSYTRIS
A psychedelic falling-block game in one file.

Controls:
	Left / A	Move left
	Right / D	Move right
	Down / S	Soft drop
	Up / W / X	Rotate clockwise
	Z		Rotate counter-clockwise
	Space		Hard drop
	C / Left Shift	Hold piece
	P / Escape	Pause
	R		Restart after game over
	F11		Toggle fullscreen
"""

from __future__ import annotations

import colorsys
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path

import pygame as pg


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WINDOW_WIDTH = 960
WINDOW_HEIGHT = 900
FPS = 120

BOARD_COLS = 10
BOARD_ROWS = 22
HIDDEN_ROWS = 2
VISIBLE_ROWS = BOARD_ROWS - HIDDEN_ROWS
CELL_SIZE = 36

BOARD_WIDTH = BOARD_COLS * CELL_SIZE
BOARD_HEIGHT = VISIBLE_ROWS * CELL_SIZE
BOARD_X = (WINDOW_WIDTH - BOARD_WIDTH) // 2
BOARD_Y = (WINDOW_HEIGHT - BOARD_HEIGHT) // 2

LOCK_DELAY = 450
CLEAR_DELAY = 520
DAS_DELAY = 145
ARR_DELAY = 42
SOFT_DROP_DELAY = 35

BACKGROUND_SIZE = (240, 225)

EMPTY = None

SHAPES = {
	"I": (
		("....", "IIII", "....", "...."),
		("..I.", "..I.", "..I.", "..I."),
		("....", "....", "IIII", "...."),
		(".I..", ".I..", ".I..", ".I.."),
	),
	"O": (
		(".OO.", ".OO.", "....", "...."),
		(".OO.", ".OO.", "....", "...."),
		(".OO.", ".OO.", "....", "...."),
		(".OO.", ".OO.", "....", "...."),
	),
	"T": (
		(".T..", "TTT.", "....", "...."),
		(".T..", ".TT.", ".T..", "...."),
		("....", "TTT.", ".T..", "...."),
		(".T..", "TT..", ".T..", "...."),
	),
	"S": (
		(".SS.", "SS..", "....", "...."),
		(".S..", ".SS.", "..S.", "...."),
		("....", ".SS.", "SS..", "...."),
		("S...", "SS..", ".S..", "...."),
	),
	"Z": (
		("ZZ..", ".ZZ.", "....", "...."),
		("..Z.", ".ZZ.", ".Z..", "...."),
		("....", "ZZ..", ".ZZ.", "...."),
		(".Z..", "ZZ..", "Z...", "...."),
	),
	"J": (
		("J...", "JJJ.", "....", "...."),
		(".JJ.", ".J..", ".J..", "...."),
		("....", "JJJ.", "..J.", "...."),
		(".J..", ".J..", "JJ..", "...."),
	),
	"L": (
		("..L.", "LLL.", "....", "...."),
		(".L..", ".L..", ".LL.", "...."),
		("....", "LLL.", "L...", "...."),
		("LL..", ".L..", ".L..", "...."),
	),
}

PIECE_HUES = {
	"I": 0.50,
	"O": 0.15,
	"T": 0.79,
	"S": 0.34,
	"Z": 0.98,
	"J": 0.62,
	"L": 0.08,
}

SCORE_TABLE = {
	1: 100,
	2: 300,
	3: 500,
	4: 800,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clamp(value: float, minimum: float, maximum: float) -> float:
	return max(minimum, min(maximum, value))


def ease_out_back(t: float) -> float:
	c1 = 1.70158
	c3 = c1 + 1.0
	return 1.0 + c3 * (t - 1.0) ** 3 + c1 * (t - 1.0) ** 2


def ease_out_cubic(t: float) -> float:
	return 1.0 - (1.0 - t) ** 3


def hsv_colour(hue: float, saturation: float = 1.0, value: float = 1.0) -> pg.Color:
	r, g, b = colorsys.hsv_to_rgb(hue % 1.0, saturation, value)
	return pg.Color(round(r * 255), round(g * 255), round(b * 255))


def load_font(size: int, bold: bool = False) -> pg.font.Font:
	for name in ("Fira Code", "DejaVu Sans", "Arial"):
		path = pg.font.match_font(name, bold=bold)
		if path:
			return pg.font.Font(path, size)
	return pg.font.Font(None, size)


def asset_path(filename: str) -> Path:
	return Path(__file__).resolve().parent / "assets" / filename


# ---------------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------------

class Audio:
	def __init__(self) -> None:
		self.available = False
		self.sounds: dict[str, pg.mixer.Sound | None] = {
			"clear": None,
			"level": None,
			"game_over": None,
			"start": None,
			"drop": None
		}

		try:
			if not pg.mixer.get_init():
				pg.mixer.init()
			self.available = True
		except pg.error as error:
			print(f"[AUDIO] Mixer unavailable: {error}")
			return

		files = {
			"clear": "new_linescore.wav",
			"level": "levelup.wav",
			"game_over": "gameover.wav",
			"start": "start.wav",
			"drop": "drop.wav"
		}

		for name, filename in files.items():
			try:
				self.sounds[name] = pg.mixer.Sound(asset_path(filename))
			except (FileNotFoundError, pg.error):
				self.sounds[name] = None

		music = asset_path("background_ambient.wav")
		try:
			pg.mixer.music.load(music)
			pg.mixer.music.set_volume(1.00)
			pg.mixer.music.play(-1)
		except (FileNotFoundError, pg.error):
			pass

	def play(self, name: str, volume: float = 1.0) -> None:
		sound = self.sounds.get(name)
		if sound:
			sound.set_volume(clamp(volume, 0.0, 1.0))
			sound.play()


# ---------------------------------------------------------------------------
# Piece and random bag
# ---------------------------------------------------------------------------

@dataclass
class Piece:
	kind: str
	x: int = BOARD_COLS // 2 - 2
	y: int = 0
	rotation: int = 0

	def cells(self, rotation: int | None = None) -> list[tuple[int, int]]:
		state = SHAPES[self.kind][self.rotation if rotation is None else rotation % 4]
		return [
			(x, y)
			for y, row in enumerate(state)
			for x, value in enumerate(row)
			if value != "."
		]


class SevenBag:
	def __init__(self) -> None:
		self.queue: list[str] = []
		self._fill()

	def _fill(self) -> None:
		bag = list(SHAPES)
		random.shuffle(bag)
		self.queue.extend(bag)

	def pop(self) -> str:
		if len(self.queue) < 7:
			self._fill()
		return self.queue.pop(0)

	def preview(self, amount: int = 5) -> list[str]:
		while len(self.queue) < amount:
			self._fill()
		return self.queue[:amount]


# ---------------------------------------------------------------------------
# Effects
# ---------------------------------------------------------------------------

@dataclass
class Particle:
	position: pg.Vector2
	velocity: pg.Vector2
	hue: float
	life: float
	max_life: float
	radius: float
	drag: float = 0.985
	gravity: float = 0.0

	def update(self, dt: float) -> bool:
		self.life -= dt
		self.velocity *= self.drag ** (dt * 60.0)
		self.velocity.y += self.gravity * dt
		self.position += self.velocity * dt
		return self.life > 0.0

	def draw(self, surface: pg.Surface) -> None:
		progress = clamp(self.life / self.max_life, 0.0, 1.0)
		alpha = round(255 * progress)
		radius = max(1, round(self.radius * (0.35 + progress)))

		glow = pg.Surface((radius * 8, radius * 8), pg.SRCALPHA)
		centre = glow.get_width() // 2
		colour = hsv_colour(self.hue + (1.0 - progress) * 0.18)

		for layer in range(4, 0, -1):
			layer_radius = radius * layer
			layer_alpha = round(alpha * 0.09 * (5 - layer))
			pg.draw.circle(
				glow,
				(*colour[:3], layer_alpha),
				(centre, centre),
				layer_radius,
			)

		pg.draw.circle(glow, (*colour[:3], alpha), (centre, centre), radius)
		surface.blit(glow, glow.get_rect(center=self.position), special_flags=pg.BLEND_RGBA_ADD)


class ScorePopup:
	def __init__(
		self,
		text: str,
		subtext: str,
		position: tuple[int, int],
		hue: float,
		duration: float = 1.35,
	) -> None:
		self.text = text
		self.subtext = subtext
		self.position = pg.Vector2(position)
		self.hue = hue
		self.age = 0.0
		self.duration = duration
		self.font = load_font(58, bold=True)
		self.small_font = load_font(23, bold=True)

	def update(self, dt: float) -> bool:
		self.age += dt
		return self.age < self.duration

	@staticmethod
	def outlined_text(
		font: pg.font.Font,
		text: str,
		colour: pg.Color | tuple[int, int, int] | str,
		outline_width: int = 2,
	) -> pg.Surface:
		"""
		Piirtää tekstin läpinäkyvälle pinnalle niin, että sen ympärillä
		on oikea musta reunus. Ei käytä maskeja tai additiivista blittausta.
		"""

		foreground = font.render(text, True, colour).convert_alpha()
		outline = font.render(text, True, (0, 0, 0)).convert_alpha()

		padding = outline_width + 2

		result = pg.Surface(
			(
				foreground.get_width() + padding * 2,
				foreground.get_height() + padding * 2,
			),
			pg.SRCALPHA,
		)

		centre_x = padding
		centre_y = padding

		for offset_y in range(-outline_width, outline_width + 1):
			for offset_x in range(-outline_width, outline_width + 1):
				if offset_x == 0 and offset_y == 0:
					continue

				# Jätetään aivan kauimmaiset kulmapikselit pois,
				# jolloin reunuksesta tulee pyöreämpi.
				if offset_x * offset_x + offset_y * offset_y > outline_width * outline_width + 1:
					continue

				result.blit(
					outline,
					(
						centre_x + offset_x,
						centre_y + offset_y,
					),
				)

		result.blit(
			foreground,
			(centre_x, centre_y),
		)

		return result

	def draw_rainbow_text(
		self,
		surface: pg.Surface,
		centre: pg.Vector2,
		angle: float,
		scale: float,
		alpha: int,
	) -> None:
		# Värilliset jälkikuvat piirretään ensin.
		for trail in range(4, 0, -1):
			trail_hue = (
				self.hue
				+ trail * 0.085
				+ self.age * 0.45
			)

			colour = hsv_colour(trail_hue)

			trail_text = self.outlined_text(
				self.font,
				self.text,
				colour,
				outline_width=2,
			)

			trail_text.set_alpha(
				max(
					0,
					round(alpha * (0.08 + trail * 0.025)),
				)
			)

			transformed = pg.transform.rotozoom(
				trail_text,
				angle - trail * 1.7,
				max(0.02, scale + trail * 0.035),
			)

			offset = pg.Vector2(
				-trail * 2.5,
				trail * 1.5,
			)

			# Tavallinen alpha-blittaus. Ei BLEND_RGBA_ADD-lippua.
			surface.blit(
				transformed,
				transformed.get_rect(center=centre + offset),
			)

		# Varsinainen valkoinen pisteteksti piirretään viimeisenä.
		main_text = self.outlined_text(
			self.font,
			self.text,
			(255, 255, 255),
			outline_width=2,
		)

		main_text = pg.transform.rotozoom(
			main_text,
			angle,
			max(0.02, scale),
		)

		main_text.set_alpha(alpha)

		surface.blit(
			main_text,
			main_text.get_rect(center=centre),
		)

	def draw(self, surface: pg.Surface) -> None:
		t = clamp(
			self.age / self.duration,
			0.0,
			1.0,
		)

		intro = clamp(
			t / 0.24,
			0.0,
			1.0,
		)

		outro = clamp(
			(1.0 - t) / 0.30,
			0.0,
			1.0,
		)

		alpha = round(
			255 * min(1.0, outro * 1.5)
		)

		scale = (
			0.18
			+ 1.18 * ease_out_back(intro)
		)

		scale *= (
			1.0
			+ math.sin(self.age * 16.0) * 0.045
		)

		angle = (
			math.sin(self.age * 11.0)
			* 13.0
			* (1.0 - t)
		)

		centre = (
			self.position
			+ pg.Vector2(
				0,
				-95.0 * ease_out_cubic(t),
			)
		)

		self.draw_rainbow_text(
			surface,
			centre,
			angle,
			scale,
			alpha,
		)

		if self.subtext:
			colour = hsv_colour(
				self.hue
				+ self.age * 0.25
			)

			subtext = self.outlined_text(
				self.small_font,
				self.subtext,
				colour,
				outline_width=2,
			)

			subtext.set_alpha(alpha)

			subtext_centre = (
				centre
				+ pg.Vector2(
					0,
					58 * scale,
				)
			)

			surface.blit(
				subtext,
				subtext.get_rect(center=subtext_centre),
			)


class LevelPopup:
	def __init__(self, level: int) -> None:
		self.level = level
		self.age = 0.0
		self.duration = 1.8
		self.font = load_font(72, bold=True)

	def update(self, dt: float) -> bool:
		self.age += dt
		return self.age < self.duration

	def draw(self, surface: pg.Surface) -> None:
		t = clamp(
			self.age / self.duration,
			0.0,
			1.0,
		)

		intro = clamp(
			t / 0.28,
			0.0,
			1.0,
		)

		outro = clamp(
			(1.0 - t) / 0.32,
			0.0,
			1.0,
		)

		alpha = round(
			255 * min(1.0, outro * 1.6)
		)

		scale = (
			0.25
			+ 1.4 * ease_out_back(intro)
		)

		scale *= (
			1.0
			+ math.sin(self.age * 13.0) * 0.055
		)

		angle = (
			math.sin(self.age * 8.0)
			* 7.0
		)

		centre = (
			WINDOW_WIDTH // 2,
			WINDOW_HEIGHT // 2,
		)

		text_value = f"LEVEL {self.level}"

		# Värilliset jälkikuvat piirretään ensin tavallisella
		# alpha-blittauksella. Ei BLEND_RGBA_ADD-lippua.
		for index in range(7, 0, -1):
			colour = hsv_colour(
				self.age * 0.45
				+ index / 7.0
			)

			trail = ScorePopup.outlined_text(
				self.font,
				text_value,
				colour,
				outline_width=2,
			)

			trail.set_alpha(
				round(
					alpha
					* (0.035 + index * 0.008)
				)
			)

			trail = pg.transform.rotozoom(
				trail,
				angle + index * 1.2,
				scale + index * 0.04,
			)

			offset = pg.Vector2(
				math.sin(index * 1.8) * index * 1.5,
				math.cos(index * 1.4) * index * 1.5,
			)

			surface.blit(
				trail,
				trail.get_rect(
					center=pg.Vector2(centre) + offset,
				),
			)

		# Varsinainen LEVEL-teksti piirretään viimeisenä kaikkien
		# värijälkien päälle.
		main = ScorePopup.outlined_text(
			self.font,
			text_value,
			(255, 255, 255),
			outline_width=2,
		)

		main = pg.transform.rotozoom(
			main,
			angle,
			scale,
		)

		main.set_alpha(alpha)

		surface.blit(
			main,
			main.get_rect(center=centre),
		)

class ScreenPulse:
	def __init__(self, hue: float, duration: float = 0.45, strength: int = 95) -> None:
		self.hue = hue
		self.age = 0.0
		self.duration = duration
		self.strength = strength

	def update(self, dt: float) -> bool:
		self.age += dt
		return self.age < self.duration

	def draw(self, surface: pg.Surface) -> None:
		t = clamp(self.age / self.duration, 0.0, 1.0)
		alpha = round(self.strength * (1.0 - t) ** 2)
		colour = hsv_colour(self.hue + self.age * 0.8)
		overlay = pg.Surface(surface.get_size(), pg.SRCALPHA)
		overlay.fill((*colour[:3], alpha))
		surface.blit(overlay, (0, 0), special_flags=pg.BLEND_RGBA_ADD)


class Effects:
	def __init__(self) -> None:
		self.particles: list[Particle] = []
		self.popups: list[ScorePopup] = []
		self.level_popups: list[LevelPopup] = []
		self.pulses: list[ScreenPulse] = []

	def line_burst(self, rows: list[int], strength: int) -> None:
		count_per_cell = 7 + strength * 2
		for row in rows:
			y = BOARD_Y + (row - HIDDEN_ROWS + 0.5) * CELL_SIZE
			for column in range(BOARD_COLS):
				x = BOARD_X + (column + 0.5) * CELL_SIZE
				for particle_index in range(count_per_cell):
					angle = random.uniform(-math.pi, math.pi)
					speed = random.uniform(70.0, 250.0 + strength * 65.0)
					velocity = pg.Vector2(math.cos(angle), math.sin(angle) * 0.66) * speed
					hue = column / BOARD_COLS + particle_index * 0.035 + random.random() * 0.08
					life = random.uniform(0.45, 1.05)
					self.particles.append(
						Particle(
							position=pg.Vector2(x, y),
							velocity=velocity,
							hue=hue,
							life=life,
							max_life=life,
							radius=random.uniform(1.4, 3.5 + strength * 0.35),
							gravity=random.uniform(20.0, 95.0),
						)
					)

	def score_popup(self, points: int, cleared: int, combo: int) -> None:
		names = {
			1: "SINGLE",
			2: "DOUBLE",
			3: "TRIPLE",
			4: "PSYTRIS!",
		}
		subtext = names.get(cleared, "")
		if combo > 1:
			subtext += f"  COMBO x{combo}"
		self.popups.append(
			ScorePopup(
				f"+{points:,}",
				subtext,
				(WINDOW_WIDTH // 2, BOARD_Y + BOARD_HEIGHT // 2),
				random.random(),
			)
		)

	def level_up(self, level: int) -> None:
		self.level_popups.append(LevelPopup(level))
		self.pulses.append(ScreenPulse(random.random(), duration=0.75, strength=125))

	def pulse(self, strength: int) -> None:
		self.pulses.append(ScreenPulse(random.random(), strength=strength))

	def update(self, dt: float) -> None:
		self.particles = [item for item in self.particles if item.update(dt)]
		self.popups = [item for item in self.popups if item.update(dt)]
		self.level_popups = [item for item in self.level_popups if item.update(dt)]
		self.pulses = [item for item in self.pulses if item.update(dt)]

	def draw_board_effects(self, surface: pg.Surface) -> None:
		for particle in self.particles:
			particle.draw(surface)

	def draw_foreground(self, surface: pg.Surface) -> None:
		for pulse in self.pulses:
			pulse.draw(surface)
		for popup in self.popups:
			popup.draw(surface)
		for popup in self.level_popups:
			popup.draw(surface)


# ---------------------------------------------------------------------------
# Psychedelic background
# ---------------------------------------------------------------------------

class PsyBackground:
	def __init__(self) -> None:
		self.time = 0.0
		self.surface = pg.Surface(BACKGROUND_SIZE)
		self.grid_x = [
			(x - BACKGROUND_SIZE[0] / 2.0) / BACKGROUND_SIZE[1]
			for x in range(BACKGROUND_SIZE[0])
		]
		self.grid_y = [
			(y - BACKGROUND_SIZE[1] / 2.0) / BACKGROUND_SIZE[1]
			for y in range(BACKGROUND_SIZE[1])
		]

	def update(self, dt: float) -> None:
		self.time += dt

	def draw(self, target: pg.Surface, intensity: float = 1.0) -> None:
		pixels = pg.PixelArray(self.surface)
		t = self.time

		for y, ny in enumerate(self.grid_y):
			for x, nx in enumerate(self.grid_x):
				radius = math.sqrt(nx * nx + ny * ny)
				angle = math.atan2(ny, nx)
				value = (
					math.sin(nx * 18.0 + t * 1.9)
					+ math.sin(ny * 21.0 - t * 1.45)
					+ math.sin((nx + ny) * 15.0 + t * 1.2)
					+ math.sin(radius * 47.0 - t * 4.2 + angle * 3.0)
				)
				hue = (value * 0.052 + radius * 0.35 + t * 0.035) % 1.0
				brightness = clamp(0.16 + (value + 4.0) * 0.055 * intensity, 0.08, 0.58)
				colour = hsv_colour(hue, 0.88, brightness)
				pixels[x, y] = colour

		del pixels
		scaled = pg.transform.smoothscale(self.surface, target.get_size())
		target.blit(scaled, (0, 0))

		# Slow transparent rotating rings over the plasma.
		# rings = pg.Surface(target.get_size(), pg.SRCALPHA)
		# centre = pg.Vector2(
		# 	target.get_width() / 2 + math.sin(t * 0.43) * 150,
		# 	target.get_height() / 2 + math.cos(t * 0.37) * 110,
		# )
		# for index in range(8):
		# 	radius = int(
		# 		(t * 75 + index * 115) % 920
		# 	)
		#
		# 	colour = hsv_colour(
		# 		t * 0.08 + index / 8
		# 	)
		#
		# 	alpha = int(
		# 		34 * (1.0 - radius / 920)
		# 	)
		#
		# 	pg.draw.circle(
		# 		rings,
		# 		(*colour[:3], alpha),
		# 		centre,
		# 		radius,
		# 		width=4,
		# 	)
		#
		# rings.set_alpha(128)
		#
		# target.blit(
		# 	rings,
		# 	(0, 0),
		# 	special_flags=pg.BLEND_RGBA_ADD,
		# )


# ---------------------------------------------------------------------------
# Game
# ---------------------------------------------------------------------------

class Psytris:
	def __init__(self) -> None:
		pg.init()
		pg.display.set_caption("PSYTRIS")
		self.fullscreen = False
		self.screen = pg.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
		self.clock = pg.time.Clock()

		self.audio = Audio()
		self.effects = Effects()
		self.background = PsyBackground()

		self.title_font = load_font(54, bold=True)
		self.ui_font = load_font(22, bold=True)
		self.small_font = load_font(17)
		self.score_font = load_font(28, bold=True)
		self.pause_font = load_font(62, bold=True)

		self.running = True
		self.paused = False
		self.game_over = False

		self.key_repeat_key: int | None = None
		self.key_repeat_elapsed = 0.0
		self.key_repeat_fired = False
		self.soft_drop_elapsed = 0.0

		self.reset()

	def reset(self) -> None:
		self.board: list[list[str | None]] = [
			[EMPTY for _ in range(BOARD_COLS)]
			for _ in range(BOARD_ROWS)
		]
		self.bag = SevenBag()
		self.current = Piece(self.bag.pop())
		self.hold_kind: str | None = None
		self.can_hold = True

		self.score = 0
		self.level = 1
		self.lines = 0
		self.combo = 0
		self.back_to_back = False

		self.drop_elapsed = 0.0
		self.lock_elapsed = 0.0
		self.clearing_rows: list[int] = []
		self.clear_elapsed = 0.0
		self.pending_points = 0

		self.paused = False
		self.game_over = False
		self.effects = Effects()
		self.audio.play("start", 0.55)

	def fall_interval(self) -> float:
		# Smoothly descends from 0.80 s toward 0.075 s.
		return max(0.075, 0.80 * (0.86 ** (self.level - 1)))

	def is_valid(
		self,
		piece: Piece,
		dx: int = 0,
		dy: int = 0,
		rotation: int | None = None,
	) -> bool:
		for cell_x, cell_y in piece.cells(rotation):
			x = piece.x + cell_x + dx
			y = piece.y + cell_y + dy

			if x < 0 or x >= BOARD_COLS or y >= BOARD_ROWS:
				return False
			if y >= 0 and self.board[y][x] is not EMPTY:
				return False

		return True

	def move(self, dx: int, dy: int) -> bool:
		if self.clearing_rows or self.game_over:
			return False
		if self.is_valid(self.current, dx=dx, dy=dy):
			self.current.x += dx
			self.current.y += dy
			if dx:
				self.lock_elapsed = 0.0
			return True
		return False

	def rotate(self, direction: int) -> None:
		if self.clearing_rows or self.game_over:
			return

		old_rotation = self.current.rotation
		new_rotation = (old_rotation + direction) % 4

		# A compact wall-kick list, sufficient for a responsive arcade feel.
		kicks = (
			(0, 0),
			(-1, 0),
			(1, 0),
			(-2, 0),
			(2, 0),
			(0, -1),
			(-1, -1),
			(1, -1),
		)

		for kick_x, kick_y in kicks:
			if self.is_valid(
				self.current,
				dx=kick_x,
				dy=kick_y,
				rotation=new_rotation,
			):
				self.current.rotation = new_rotation
				self.current.x += kick_x
				self.current.y += kick_y
				self.lock_elapsed = 0.0
				return

	def hard_drop(self) -> None:
		if self.clearing_rows or self.game_over:
			return

		distance = 0

		while self.is_valid(self.current, dy=1):
			self.current.y += 1
			distance += 1

		self.score += distance * 2

		if distance > 0:
			volume = clamp(
				0.35 + distance * 0.025,
				0.35,
				0.85,
			)

			self.audio.play(
				"drop",
				volume,
			)

		self.lock_piece()

	def hold(self) -> None:
		if not self.can_hold or self.clearing_rows or self.game_over:
			return

		old_kind = self.current.kind
		if self.hold_kind is None:
			self.hold_kind = old_kind
			self.current = Piece(self.bag.pop())
		else:
			self.current = Piece(self.hold_kind)
			self.hold_kind = old_kind

		self.can_hold = False
		self.drop_elapsed = 0.0
		self.lock_elapsed = 0.0

		if not self.is_valid(self.current):
			self.trigger_game_over()

	def lock_piece(self) -> None:
		for cell_x, cell_y in self.current.cells():
			x = self.current.x + cell_x
			y = self.current.y + cell_y
			if y < 0:
				self.trigger_game_over()
				return
			self.board[y][x] = self.current.kind

		full_rows = [
			row_index
			for row_index, row in enumerate(self.board)
			if all(cell is not EMPTY for cell in row)
		]

		if full_rows:
			self.begin_line_clear(full_rows)
		else:
			self.combo = 0
			self.spawn_piece()

	def begin_line_clear(self, rows: list[int]) -> None:
		self.clearing_rows = rows
		self.clear_elapsed = 0.0
		self.combo += 1

		cleared = len(rows)
		base_points = SCORE_TABLE[cleared] * self.level
		combo_bonus = max(0, self.combo - 1) * 50 * self.level
		tetris_bonus = 0

		if cleared == 4:
			if self.back_to_back:
				tetris_bonus = base_points // 2
			self.back_to_back = True
		else:
			self.back_to_back = False

		self.pending_points = base_points + combo_bonus + tetris_bonus
		self.score += self.pending_points
		self.lines += cleared

		old_level = self.level
		self.level = 1 + self.lines // 10

		self.effects.line_burst(rows, cleared)
		self.effects.score_popup(self.pending_points, cleared, self.combo)
		self.effects.pulse(60 + cleared * 18)
		self.audio.play("clear", min(1.0, 0.50 + cleared * 0.12))

		if self.level > old_level:
			self.effects.level_up(self.level)
			self.audio.play("level", 0.85)

	def finish_line_clear(self) -> None:
		rows = set(self.clearing_rows)
		remaining = [
			row
			for index, row in enumerate(self.board)
			if index not in rows
		]
		for _ in self.clearing_rows:
			remaining.insert(0, [EMPTY for _ in range(BOARD_COLS)])

		self.board = remaining
		self.clearing_rows = []
		self.clear_elapsed = 0.0
		self.spawn_piece()

	def spawn_piece(self) -> None:
		self.current = Piece(self.bag.pop())
		self.can_hold = True
		self.drop_elapsed = 0.0
		self.lock_elapsed = 0.0

		if not self.is_valid(self.current):
			self.trigger_game_over()

	def trigger_game_over(self) -> None:
		if self.game_over:
			return
		self.game_over = True
		self.audio.play("game_over", 0.9)
		self.effects.pulse(155)

	def ghost_y(self) -> int:
		test_y = self.current.y
		while self.is_valid(self.current, dy=test_y - self.current.y + 1):
			test_y += 1
		return test_y

	def toggle_fullscreen(self) -> None:
		self.fullscreen = not self.fullscreen
		flags = pg.FULLSCREEN if self.fullscreen else 0
		self.screen = pg.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), flags)

	def handle_keydown(self, key: int) -> None:
		if key == pg.K_F11:
			self.toggle_fullscreen()
			return

		if self.game_over:
			if key == pg.K_r:
				self.reset()
			elif key in (pg.K_ESCAPE, pg.K_q):
				self.running = False
			return

		if key in (pg.K_p, pg.K_ESCAPE):
			self.paused = not self.paused
			return

		if self.paused:
			return

		if key in (pg.K_LEFT, pg.K_a):
			self.move(-1, 0)
			self.start_horizontal_repeat(key)
		elif key in (pg.K_RIGHT, pg.K_d):
			self.move(1, 0)
			self.start_horizontal_repeat(key)
		elif key in (pg.K_DOWN, pg.K_s):
			if self.move(0, 1):
				self.score += 1
		elif key in (pg.K_UP, pg.K_w, pg.K_x):
			self.rotate(1)
		elif key == pg.K_z:
			self.rotate(-1)
		elif key == pg.K_SPACE:
			self.hard_drop()
		elif key in (pg.K_c, pg.K_LSHIFT, pg.K_RSHIFT):
			self.hold()

	def start_horizontal_repeat(self, key: int) -> None:
		self.key_repeat_key = key
		self.key_repeat_elapsed = 0.0
		self.key_repeat_fired = False

	def stop_horizontal_repeat(self, key: int) -> None:
		if self.key_repeat_key == key:
			self.key_repeat_key = None
			self.key_repeat_elapsed = 0.0
			self.key_repeat_fired = False

	def update_key_repeat(self, dt_ms: float) -> None:
		keys = pg.key.get_pressed()

		if self.key_repeat_key is not None:
			if not keys[self.key_repeat_key]:
				self.stop_horizontal_repeat(self.key_repeat_key)
			else:
				self.key_repeat_elapsed += dt_ms
				if not self.key_repeat_fired:
					if self.key_repeat_elapsed >= DAS_DELAY:
						self.key_repeat_fired = True
						self.key_repeat_elapsed -= DAS_DELAY
				elif self.key_repeat_elapsed >= ARR_DELAY:
					direction = -1 if self.key_repeat_key in (pg.K_LEFT, pg.K_a) else 1
					self.move(direction, 0)
					self.key_repeat_elapsed %= ARR_DELAY

		if keys[pg.K_DOWN] or keys[pg.K_s]:
			self.soft_drop_elapsed += dt_ms
			while self.soft_drop_elapsed >= SOFT_DROP_DELAY:
				if self.move(0, 1):
					self.score += 1
				self.soft_drop_elapsed -= SOFT_DROP_DELAY
		else:
			self.soft_drop_elapsed = 0.0

	def update(self, dt: float, dt_ms: float) -> None:
		self.background.update(dt)
		self.effects.update(dt)

		if self.paused or self.game_over:
			return

		self.update_key_repeat(dt_ms)

		if self.clearing_rows:
			self.clear_elapsed += dt_ms
			if self.clear_elapsed >= CLEAR_DELAY:
				self.finish_line_clear()
			return

		self.drop_elapsed += dt
		interval = self.fall_interval()

		while self.drop_elapsed >= interval:
			self.drop_elapsed -= interval
			if not self.move(0, 1):
				break

		if self.is_valid(self.current, dy=1):
			self.lock_elapsed = 0.0
		else:
			self.lock_elapsed += dt_ms
			if self.lock_elapsed >= LOCK_DELAY:
				self.audio.play(
					"drop",
					0.28,
				)

				self.lock_piece()

	def draw_block(
		self,
		surface: pg.Surface,
		grid_x: int,
		grid_y: int,
		kind: str,
		alpha: int = 255,
		ghost: bool = False,
		clear_progress: float | None = None,
	) -> None:
		if grid_y < HIDDEN_ROWS:
			return

		x = BOARD_X + grid_x * CELL_SIZE
		y = BOARD_Y + (grid_y - HIDDEN_ROWS) * CELL_SIZE
		centre = pg.Vector2(x + CELL_SIZE / 2, y + CELL_SIZE / 2)

		if ghost:
			colour = hsv_colour(PIECE_HUES[kind], 0.55, 0.75)
			pg.draw.rect(
				surface,
				(*colour[:3], 70),
				(x + 5, y + 5, CELL_SIZE - 10, CELL_SIZE - 10),
				width=2,
				border_radius=5,
			)
			return

		hue = PIECE_HUES[kind]
		scale = 1.0
		rotation = 0.0

		if clear_progress is not None:
			hue = (grid_x / BOARD_COLS + clear_progress * 1.8) % 1.0
			scale = 1.0 + math.sin(clear_progress * math.pi) * 0.38
			rotation = math.sin(clear_progress * math.pi * 5 + grid_x) * 12.0

		colour = hsv_colour(hue, 0.82, 1.0)
		dark = hsv_colour(hue, 0.95, 0.30)
		light = hsv_colour(hue + 0.025, 0.38, 1.0)

		size = max(3, int((CELL_SIZE - 4) * scale))
		block = pg.Surface((size + 18, size + 18), pg.SRCALPHA)
		rect = pg.Rect(9, 9, size, size)

		for glow_layer in range(4, 0, -1):
			grow = glow_layer * 3
			glow_rect = rect.inflate(grow * 2, grow * 2)
			pg.draw.rect(
				block,
				(*colour[:3], round(alpha * (0.035 + (4 - glow_layer) * 0.025))),
				glow_rect,
				border_radius=7 + grow,
			)

		pg.draw.rect(block, (*dark[:3], alpha), rect, border_radius=6)
		inner = rect.inflate(-5, -5)
		pg.draw.rect(block, (*colour[:3], alpha), inner, border_radius=5)

		highlight = pg.Rect(inner.x + 3, inner.y + 3, inner.width - 6, max(3, inner.height // 4))
		pg.draw.rect(block, (*light[:3], round(alpha * 0.85)), highlight, border_radius=4)
		pg.draw.rect(block, (255, 255, 255, round(alpha * 0.36)), inner, width=1, border_radius=5)

		if clear_progress is not None:
			white_alpha = round(255 * math.sin(clear_progress * math.pi))
			pg.draw.rect(block, (255, 255, 255, white_alpha), inner, border_radius=5)

		if rotation:
			block = pg.transform.rotozoom(block, rotation, 1.0)

		surface.blit(
			block,
			block.get_rect(center=centre),
			special_flags=pg.BLEND_RGBA_ADD if clear_progress is not None else 0,
		)

	def draw_board_frame(self, surface: pg.Surface) -> None:
		frame = pg.Surface((BOARD_WIDTH + 34, BOARD_HEIGHT + 34), pg.SRCALPHA)
		frame_rect = frame.get_rect()

		for layer in range(8, 0, -1):
			colour = hsv_colour(self.background.time * 0.05 + layer / 8.0)
			pg.draw.rect(
				frame,
				(*colour[:3], 8 + layer * 3),
				frame_rect.inflate(-layer * 2, -layer * 2),
				width=2,
				border_radius=18,
			)

		pg.draw.rect(
			frame,
			(2, 4, 12, 218),
			frame_rect.inflate(-15, -15),
			border_radius=10,
		)
		surface.blit(frame, frame.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)))

		grid = pg.Surface((BOARD_WIDTH, BOARD_HEIGHT), pg.SRCALPHA)
		for x in range(BOARD_COLS + 1):
			pg.draw.line(grid, (100, 150, 255, 22), (x * CELL_SIZE, 0), (x * CELL_SIZE, BOARD_HEIGHT))
		for y in range(VISIBLE_ROWS + 1):
			pg.draw.line(grid, (255, 100, 220, 18), (0, y * CELL_SIZE), (BOARD_WIDTH, y * CELL_SIZE))
		surface.blit(grid, (BOARD_X, BOARD_Y))

	def draw_piece_preview(
		self,
		surface: pg.Surface,
		kind: str | None,
		centre: tuple[int, int],
		cell: int = 20,
	) -> None:
		if kind is None:
			return

		cells = Piece(kind).cells(0)
		min_x = min(x for x, _ in cells)
		max_x = max(x for x, _ in cells)
		min_y = min(y for _, y in cells)
		max_y = max(y for _, y in cells)
		width = (max_x - min_x + 1) * cell
		height = (max_y - min_y + 1) * cell
		start_x = centre[0] - width // 2
		start_y = centre[1] - height // 2

		colour = hsv_colour(PIECE_HUES[kind], 0.78, 1.0)
		for x, y in cells:
			rect = pg.Rect(
				start_x + (x - min_x) * cell + 1,
				start_y + (y - min_y) * cell + 1,
				cell - 2,
				cell - 2,
			)
			pg.draw.rect(surface, colour, rect, border_radius=4)
			pg.draw.rect(surface, (255, 255, 255, 90), rect, width=1, border_radius=4)

	def draw_panel(
		self,
		surface: pg.Surface,
		rect: pg.Rect,
		title: str,
		hue: float,
	) -> None:
		panel = pg.Surface(rect.size, pg.SRCALPHA)
		colour = hsv_colour(hue)
		pg.draw.rect(panel, (2, 4, 14, 190), panel.get_rect(), border_radius=14)
		pg.draw.rect(panel, (*colour[:3], 105), panel.get_rect(), width=2, border_radius=14)
		title_surface = self.small_font.render(title, True, colour)
		panel.blit(title_surface, (12, 9))
		surface.blit(panel, rect)

	def draw_ui(self, surface: pg.Surface) -> None:
		title_hue = self.background.time * 0.06
		title = self.title_font.render("PSYTRIS", True, hsv_colour(title_hue))
		surface.blit(title, title.get_rect(midtop=(WINDOW_WIDTH // 2, 15)))

		left_x = 28
		right_x = WINDOW_WIDTH - 208

		score_rect = pg.Rect(left_x, 118, 180, 132)
		hold_rect = pg.Rect(left_x, 270, 180, 142)
		next_rect = pg.Rect(right_x, 118, 180, 385)
		stats_rect = pg.Rect(right_x, 523, 180, 172)

		self.draw_panel(surface, score_rect, "SCORE", title_hue + 0.10)
		self.draw_panel(surface, hold_rect, "HOLD", title_hue + 0.28)
		self.draw_panel(surface, next_rect, "NEXT", title_hue + 0.46)
		self.draw_panel(surface, stats_rect, "STATUS", title_hue + 0.64)

		score = self.score_font.render(f"{self.score:,}", True, "white")
		surface.blit(score, score.get_rect(center=(score_rect.centerx, score_rect.centery + 10)))

		self.draw_piece_preview(surface, self.hold_kind, (hold_rect.centerx, hold_rect.centery + 15), 25)

		for index, kind in enumerate(self.bag.preview(5)):
			self.draw_piece_preview(
				surface,
				kind,
				(next_rect.centerx, next_rect.y + 75 + index * 61),
				19,
			)

		status_lines = (
			f"LEVEL   {self.level}",
			f"LINES   {self.lines}",
			f"COMBO   {max(0, self.combo - 1)}",
			f"SPEED   {self.fall_interval():.3f}s",
		)
		for index, text in enumerate(status_lines):
			rendered = self.small_font.render(text, True, (225, 235, 255))
			surface.blit(rendered, (stats_rect.x + 15, stats_rect.y + 45 + index * 27))

		controls = (
			"← → / A D   MOVE",
			"↑ / W / X   ROTATE",
			"Z           REVERSE",
			"SPACE       DROP",
			"C / SHIFT   HOLD",
			"P / ESC     PAUSE",
		)
		for index, text in enumerate(controls):
			rendered = self.small_font.render(text, True, (180, 195, 225))
			surface.blit(rendered, (28, 470 + index * 28))

	def draw(self) -> None:
		self.background.draw(self.screen, intensity=1.0 + min(self.level, 15) * 0.025)
		self.draw_board_frame(self.screen)

		# Settled blocks.
		clear_progress = clamp(self.clear_elapsed / CLEAR_DELAY, 0.0, 1.0)
		for y, row in enumerate(self.board):
			for x, kind in enumerate(row):
				if kind is None:
					continue
				progress = clear_progress if y in self.clearing_rows else None
				self.draw_block(self.screen, x, y, kind, clear_progress=progress)

		# Ghost and active piece are hidden during line-clear animation.
		if not self.clearing_rows and not self.game_over:
			ghost_y = self.ghost_y()
			for cell_x, cell_y in self.current.cells():
				self.draw_block(
					self.screen,
					self.current.x + cell_x,
					ghost_y + cell_y,
					self.current.kind,
					ghost=True,
				)

			for cell_x, cell_y in self.current.cells():
				self.draw_block(
					self.screen,
					self.current.x + cell_x,
					self.current.y + cell_y,
					self.current.kind,
				)

		self.effects.draw_board_effects(self.screen)
		self.draw_ui(self.screen)
		self.effects.draw_foreground(self.screen)

		if self.paused:
			self.draw_overlay("PAUSED", "P or Esc to continue")
		elif self.game_over:
			self.draw_overlay("GAME OVER", f"Score {self.score:,} — press R to restart")

		pg.display.flip()

	def draw_overlay(
		self,
		heading: str,
		subheading: str,
	) -> None:
		overlay = pg.Surface(
			self.screen.get_size(),
			pg.SRCALPHA,
		)

		overlay.fill((0, 0, 8, 175))
		self.screen.blit(overlay, (0, 0))

		heading_centre = (
			WINDOW_WIDTH // 2,
			WINDOW_HEIGHT // 2 - 25,
		)

		hue = self.background.time * 0.12

		# Värilliset jälkikuvat piirretään ilman additiivista blittausta.
		for index in range(6, 0, -1):
			colour = hsv_colour(
				hue + index * 0.09
			)

			trail = ScorePopup.outlined_text(
				self.pause_font,
				heading,
				colour,
				outline_width=2,
			)

			trail.set_alpha(25)

			trail = pg.transform.rotozoom(
				trail,
				math.sin(
					self.background.time * 2.0
					+ index
				) * 2.0,
				1.0 + index * 0.025,
			)

			self.screen.blit(
				trail,
				trail.get_rect(
					center=heading_centre,
				),
			)

		# Varsinainen teksti piirretään aina päällimmäiseksi.
		main = ScorePopup.outlined_text(
			self.pause_font,
			heading,
			(255, 255, 255),
			outline_width=2,
		)

		self.screen.blit(
			main,
			main.get_rect(
				center=heading_centre,
			),
		)

		sub = ScorePopup.outlined_text(
			self.ui_font,
			subheading,
			(210, 220, 255),
			outline_width=2,
		)

		self.screen.blit(
			sub,
			sub.get_rect(
				center=(
					WINDOW_WIDTH // 2,
					WINDOW_HEIGHT // 2 + 55,
				),
			),
		)

	def run(self) -> None:
		while self.running:
			dt_ms = self.clock.tick(FPS)
			dt = min(dt_ms / 1000.0, 0.05)

			for event in pg.event.get():
				if event.type == pg.QUIT:
					self.running = False
				elif event.type == pg.KEYDOWN:
					self.handle_keydown(event.key)
				elif event.type == pg.KEYUP:
					self.stop_horizontal_repeat(event.key)

			self.update(dt, dt_ms)
			self.draw()

		pg.quit()


def main() -> None:
	try:
		Psytris().run()
	except KeyboardInterrupt:
		pg.quit()
		sys.exit(0)


if __name__ == "__main__":
	main()
