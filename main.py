"""
Khala Joybug - a Kivy arcade game for phones.

Khala the ladybug eats falling leaves, dodges spiders, grabs golden clovers
to go invincible, and at 100 points faces the Queen Bee.

HOW THIS FILE IS ORGANISED
    1. Tuning numbers  - every "magic number" in one place.
    2. GameScreen      - the play field: state, rules, drawing.
    3. MobileGameApp   - the window around it: score header + D-pad buttons.

COORDINATES
    Kivy puts (0, 0) at the BOTTOM-left, so "up" is +y and falling things
    have their y reduced. An object's (x, y) is its bottom-left corner,
    measured from the bottom-left corner of the play field.
"""

import os
import random

from kivy.app import App
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.stencilview import StencilView

# --------------------------------------------------------------------------
# 1. TUNING NUMBERS
#
#    Sizes go through dp() ("density-independent pixels") when used, so the
#    bug is the same physical size on every phone. On a desktop 1 dp = 1 px,
#    so these are exactly your original pixel values.
#
#    Speeds are per SECOND instead of per frame. Your originals are shown
#    alongside (original x 60 frames = per second).
# --------------------------------------------------------------------------
PLAYER_SIZE = 60
PLAYER_SPEED = 420                  # was 7 per frame
STAR_SPEED_BOOST = 1.6              # 60% faster while golden
STAR_DURATION = 5.0                 # was 300 frames
STAR_FLASHES_PER_SECOND = 6         # was a 10-frame gold/pink cycle

SPIDER_SIZE = (40, 70)
SPIDER_SPEED = (180, 480)           # was 3-8 per frame
SPIDERS_PER_SECOND = 1.2            # was a 0.02 chance per frame
LEAF_SIZE = 40
LEAF_SPEED = (120, 240)             # was 2-4 per frame
LEAVES_PER_SECOND = 0.6             # was 0.01 per frame
CLOVER_SIZE = 45
CLOVER_SPEED = 240                  # was 4 per frame
CLOVERS_PER_SECOND = 0.12           # was 0.002 per frame

LEAF_POINTS = 15
SPIDER_SMASH_POINTS = 25
SURVIVAL_POINTS = 1                 # every second you stay alive
SURVIVAL_POINTS_GOLDEN = 5
BOSS_TRIGGER_SCORE = 100

BOSS_SIZE = 120
BOSS_HEALTH = 3
BOSS_HOVER_SPEED = 240              # was 4 per frame
BOSS_CHARGE_DELAY = 2.0             # was 120 frames
BOSS_CHARGE_SPEED = 900             # was 15 per frame
BOSS_RETREAT_SPEED = 480            # was 8 per frame
BOSS_TOP_GAP = 20
THORNS_HEIGHT = 24

# The pictures have empty corners, so a full-square hitbox would hurt Khala
# when nothing visibly touched her. Hazards get their box shrunk this much
# on every side. Set to 0 for your original, stricter behaviour.
HAZARD_HITBOX_INSET = 0.15

MAX_FRAME_TIME = 0.05               # never simulate more than 1/20 s at once

BACKGROUND_COLOR = (0.1, 0.2, 0.1, 1)       # the leaf bed
THORN_STRIP_COLOR = (0.4, 0.1, 0.1, 1)
BUTTON_GREEN = (0.2, 0.4, 0.2, 1)
WHITE = (1, 1, 1, 1)
BOSS_CHARGE_TINT = (1, 0.3, 0.3, 1)         # red: she is diving
BOSS_RETREAT_TINT = (0.6, 0.6, 1, 1)        # blue: she is cooling off
STAR_FLASH_TINT = (1, 0.4, 1, 1)            # pink half of the golden flash

KEY_DIRECTIONS = {273: "up", 274: "down", 275: "right", 276: "left"}

APP_DIR = os.path.dirname(os.path.abspath(__file__))


def asset(filename):
    """Full path to a picture or sound that sits next to this file."""
    return os.path.join(APP_DIR, filename)


def load_sound(filename):
    """Load a sound, or return None (and say so) when the file is missing."""
    path = asset(filename)
    sound = SoundLoader.load(path) if os.path.exists(path) else None
    if not sound:
        print("WARNING: '%s' not found. Carrying on without it." % filename)
    return sound


class GameScreen(StencilView):
    """The play field. A StencilView is a Widget that never draws outside
    its own rectangle, so a spider entering from above cannot cover the
    score header."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # --- Player (Khala Joybug) ---
        self.player_size = dp(PLAYER_SIZE)
        self.player_normal_speed = dp(PLAYER_SPEED)
        self.boss_size = dp(BOSS_SIZE)

        # --- Falling things: each is {"x", "y", "size", "speed"} ---
        self.enemies = []        # spiders
        self.collectibles = []   # leaves
        self.clovers = []        # golden clovers

        # --- Sound ---
        self.crunch_sound = load_sound("crunch.wav")
        self.bg_music = load_sound("metal_music.mp3")
        if self.bg_music:
            self.bg_music.loop = True
            self.bg_music.volume = 0.6

        # reset_game() is the one place that defines a fresh round, so the
        # starting values are written once instead of here AND there.
        self.reset_game()

        # --- Clocks ---
        Clock.schedule_interval(self.update, 1.0 / 60.0)
        Clock.schedule_interval(self.increase_score, 1.0)

    # ------------------------------------------------------------------
    # ROUND SETUP
    # ------------------------------------------------------------------
    def reset_game(self):
        """Put every piece of game state back to its starting value."""
        self.score = 0
        self.enemies.clear()
        self.collectibles.clear()
        self.clovers.clear()

        self.player_x = (self.width - self.player_size) / 2
        self.player_y = self.height * 0.25
        self.player_speed = self.player_normal_speed
        self.current_direction = None

        self.game_over = False
        self.star_mode = False
        self.star_timer = 0.0

        self.boss_mode = False
        self.boss_defeated = False
        self.boss_state = "hover"        # "hover", "charging" or "retreating"
        self.boss_health = BOSS_HEALTH
        self.boss_x = (self.width - self.boss_size) / 2
        self.boss_y = self.boss_hover_y()
        self.boss_direction = 1          # +1 = flying right, -1 = flying left
        self.boss_charge_timer = 0.0
        self.boss_color = WHITE

        if self.bg_music:
            self.bg_music.play()

    def trigger_game_over(self):
        self.game_over = True
        self.current_direction = None
        self.star_mode = False
        if self.bg_music:
            self.bg_music.stop()

    def on_size(self, *args):
        """The layout just gave us our real size (or the phone rotated)."""
        if not hasattr(self, "boss_color"):
            return                       # fires once before __init__ is done
        if self.score == 0 and not self.boss_mode and not self.enemies:
            # Nothing has happened yet: re-centre for the real screen size.
            self.player_x = (self.width - self.player_size) / 2
            self.player_y = self.height * 0.25
        self.keep_player_on_screen()
        self.boss_x = max(0, min(self.boss_x, self.width - self.boss_size))

    # ------------------------------------------------------------------
    # SCORE OVER TIME
    # ------------------------------------------------------------------
    def increase_score(self, dt):
        """Once a second: points just for staying alive, 5x while golden."""
        if self.game_over or self.boss_defeated:
            return
        self.score += SURVIVAL_POINTS_GOLDEN if self.star_mode else SURVIVAL_POINTS

    # ------------------------------------------------------------------
    # SPAWNING
    # ------------------------------------------------------------------
    def new_falling_item(self, size, speed):
        size = dp(size)
        return {
            "x": random.uniform(0, max(0, self.width - size)),
            "y": self.height,            # starts just above the play field
            "size": size,
            "speed": dp(speed),
        }

    def spawn_enemy(self):
        self.enemies.append(self.new_falling_item(
            random.uniform(*SPIDER_SIZE), random.uniform(*SPIDER_SPEED)))

    def spawn_collectible(self):
        self.collectibles.append(self.new_falling_item(
            LEAF_SIZE, random.uniform(*LEAF_SPEED)))

    def spawn_clover(self):
        if not self.boss_mode:
            self.clovers.append(self.new_falling_item(CLOVER_SIZE, CLOVER_SPEED))

    # ------------------------------------------------------------------
    # COLLISIONS
    # ------------------------------------------------------------------
    def check_collision(self, x1, y1, size1, x2, y2, size2):
        """True when two squares overlap (axis-aligned bounding boxes).

        They overlap only if they overlap on BOTH axes: each one's left edge
        is left of the other's right edge, and the same from bottom to top.
        """
        return (x1 < x2 + size2 and x1 + size1 > x2 and
                y1 < y2 + size2 and y1 + size1 > y2)

    def player_touches(self, x, y, size, inset=0.0):
        """Does Khala overlap this square? `inset` shrinks the square first."""
        pad = size * inset
        return self.check_collision(
            self.player_x, self.player_y, self.player_size,
            x + pad, y + pad, size - 2 * pad)

    # ------------------------------------------------------------------
    # THE FRAME TICK
    # ------------------------------------------------------------------
    def update(self, dt):
        """Runs every frame. `dt` = seconds since the previous frame."""
        dt = min(dt, MAX_FRAME_TIME)     # a lag spike must not teleport things
        if not (self.game_over or self.boss_defeated):
            self.step(dt)
        self.draw()

    def step(self, dt):
        """Move the game forward by `dt` seconds."""
        # 1. Reached the boss score? Clear the board, bring in the Queen.
        if self.score >= BOSS_TRIGGER_SCORE and not self.boss_mode:
            self.start_boss_fight()

        # 2. Count down the golden-clover power.
        if self.star_mode:
            self.star_timer -= dt
            if self.star_timer <= 0:
                self.end_star_mode()

        # 3 + 4. Move Khala, then keep her inside the play field.
        self.move_player(dt)

        # 5 / 6. Either the falling-things phase or the boss phase.
        if self.boss_mode:
            self.update_boss(dt)
        else:
            self.update_falling_phase(dt)

    # ---- Khala ---------------------------------------------------------
    def move_player(self, dt):
        distance = self.player_speed * dt
        if self.current_direction == "up":
            self.player_y += distance
        elif self.current_direction == "down":
            self.player_y -= distance
        elif self.current_direction == "left":
            self.player_x -= distance
        elif self.current_direction == "right":
            self.player_x += distance
        self.keep_player_on_screen()

    def keep_player_on_screen(self):
        self.player_x = max(0, min(self.player_x, self.width - self.player_size))
        self.player_y = max(0, min(self.player_y, self.height - self.player_size))

    # ---- golden clover power -------------------------------------------
    def start_star_mode(self):
        self.star_mode = True
        self.star_timer = STAR_DURATION
        self.player_speed = self.player_normal_speed * STAR_SPEED_BOOST

    def end_star_mode(self):
        self.star_mode = False
        self.star_timer = 0.0
        self.player_speed = self.player_normal_speed

    # ---- falling things ------------------------------------------------
    def update_falling_phase(self, dt):
        # "Chance per second" x "seconds this frame" = chance this frame.
        if random.random() < SPIDERS_PER_SECOND * dt:
            self.spawn_enemy()
        if random.random() < LEAVES_PER_SECOND * dt:
            self.spawn_collectible()
        if random.random() < CLOVERS_PER_SECOND * dt:
            self.spawn_clover()

        # Clovers go first, so grabbing one saves you from a spider that
        # lands in the very same frame.
        self.clovers = self.fall(self.clovers, dt, self.on_clover)
        self.enemies = self.fall(self.enemies, dt, self.on_spider,
                                 inset=HAZARD_HITBOX_INSET)
        self.collectibles = self.fall(self.collectibles, dt, self.on_leaf)

    def fall(self, items, dt, on_touch, inset=0.0):
        """Move falling things down; return the ones still in play.

        This replaces three copies of the same loop (clovers, spiders,
        leaves). The only part that differed was what happens when Khala
        touches one, so that part is handed in as `on_touch`.
        """
        still_falling = []
        for item in items:
            item["y"] -= item["speed"] * dt
            if self.player_touches(item["x"], item["y"], item["size"], inset):
                on_touch()
                continue                       # touched things disappear
            if item["y"] > -item["size"]:      # fell off the bottom: drop it
                still_falling.append(item)
        return still_falling

    def on_clover(self):
        self.start_star_mode()
        self.play_crunch()

    def on_leaf(self):
        self.score += LEAF_POINTS
        self.play_crunch()

    def on_spider(self):
        if self.star_mode:
            self.score += SPIDER_SMASH_POINTS  # smashing spiders while golden
            self.play_crunch()
        elif not self.game_over:
            self.trigger_game_over()

    def play_crunch(self):
        if self.crunch_sound:
            self.crunch_sound.play()

    # ---- the Queen Bee -------------------------------------------------
    def boss_hover_y(self):
        return self.height - self.boss_size - dp(BOSS_TOP_GAP)

    def start_boss_fight(self):
        self.boss_mode = True
        self.enemies.clear()
        self.collectibles.clear()
        self.clovers.clear()
        self.end_star_mode()
        self.boss_state = "hover"
        self.boss_charge_timer = 0.0
        self.boss_color = WHITE
        self.boss_x = (self.width - self.boss_size) / 2
        self.boss_y = self.boss_hover_y()

    def update_boss(self, dt):
        """A three-state machine: hover -> charging -> retreating -> hover."""
        if self.boss_state == "hover":
            self.boss_color = WHITE
            self.boss_y = self.boss_hover_y()
            self.boss_x += self.boss_direction * dp(BOSS_HOVER_SPEED) * dt
            # Clamp to the wall AND point back inward. Flipping the speed
            # with "*= -1" can flip-flop forever if she is ever past the wall.
            right_wall = self.width - self.boss_size
            if self.boss_x <= 0:
                self.boss_x, self.boss_direction = 0, 1
            elif self.boss_x >= right_wall:
                self.boss_x, self.boss_direction = right_wall, -1

            self.boss_charge_timer += dt
            if self.boss_charge_timer > BOSS_CHARGE_DELAY:
                self.boss_state = "charging"
                self.boss_charge_timer = 0.0

        elif self.boss_state == "charging":
            self.boss_color = BOSS_CHARGE_TINT
            self.boss_y -= dp(BOSS_CHARGE_SPEED) * dt

            # Did the Queen hit Khala? (She is only dangerous while diving.)
            if self.player_touches(self.boss_x, self.boss_y, self.boss_size,
                                   HAZARD_HITBOX_INSET):
                self.trigger_game_over()
                return

            # Did she slam into the rose thorns on the floor?
            if self.boss_y <= 0:
                self.boss_y = 0
                self.boss_state = "retreating"
                self.boss_health -= 1
                self.play_crunch()
                if self.boss_health <= 0:
                    self.boss_defeated = True
                    self.current_direction = None

        elif self.boss_state == "retreating":
            self.boss_color = BOSS_RETREAT_TINT
            self.boss_y += dp(BOSS_RETREAT_SPEED) * dt
            if self.boss_y >= self.boss_hover_y():
                self.boss_y = self.boss_hover_y()
                self.boss_state = "hover"

    # ------------------------------------------------------------------
    # DRAWING
    # ------------------------------------------------------------------
    def draw(self):
        """Wipe the play field and repaint it from the current state."""
        self.canvas.clear()
        with self.canvas:
            Color(*BACKGROUND_COLOR)
            Rectangle(pos=self.pos, size=self.size)

            if self.boss_mode:
                self.draw_thorns()

            for leaf in self.collectibles:
                self.draw_sprite("leaf.png", leaf["x"], leaf["y"], leaf["size"])
            for clover in self.clovers:
                self.draw_sprite("clover.png", clover["x"], clover["y"], clover["size"])
            for enemy in self.enemies:
                self.draw_sprite("spider.png", enemy["x"], enemy["y"], enemy["size"])

            if self.boss_mode and not self.boss_defeated:
                self.draw_sprite("bee.png", self.boss_x, self.boss_y,
                                 self.boss_size, self.boss_color)

            # While golden, flash between the gold picture and a pink tint.
            if self.star_mode:
                gold_half = int(self.star_timer * STAR_FLASHES_PER_SECOND * 2) % 2 == 0
                if gold_half:
                    self.draw_sprite("ladybug_gold.png", self.player_x,
                                     self.player_y, self.player_size)
                else:
                    self.draw_sprite("ladybug.png", self.player_x,
                                     self.player_y, self.player_size, STAR_FLASH_TINT)
            else:
                self.draw_sprite("ladybug.png", self.player_x, self.player_y,
                                 self.player_size)

    def draw_sprite(self, filename, x, y, size, tint=WHITE):
        """Draw one picture at play-field position (x, y).

        self.x / self.y is where the play field sits inside the window. It
        is NOT (0, 0) because the D-pad sits underneath, so every picture
        has to be shifted by it or it lands behind the buttons.
        """
        Color(*tint)
        Rectangle(source=asset(filename), pos=(self.x + x, self.y + y),
                  size=(size, size))

    def draw_thorns(self):
        """The floor of rose thorns that hurts the Queen when she dives."""
        Color(*THORN_STRIP_COLOR)
        Rectangle(pos=self.pos, size=(self.width, dp(THORNS_HEIGHT) * 0.4))
        Color(*WHITE)
        tile_width, tile_height = dp(THORNS_HEIGHT) * 128 / 48, dp(THORNS_HEIGHT)
        x = 0
        while x < self.width:
            Rectangle(source=asset("thorns.png"), pos=(self.x + x, self.y),
                      size=(tile_width, tile_height))
            x += tile_width


class MobileGameApp(App):
    title = "Khala Joybug"

    def build(self):
        self.main_layout = BoxLayout(orientation="vertical")

        # Score / status header
        self.score_label = Label(text="KHALA JOYBUG: 0", font_size="20sp",
                                 bold=True, size_hint_y=0.1,
                                 halign="center", valign="middle")
        # Wrap long messages onto a second line instead of running off the
        # sides of a narrow phone screen.
        self.score_label.bind(size=lambda label, size: setattr(label, "text_size", size))
        self.main_layout.add_widget(self.score_label)

        # The play field
        self.game_world = GameScreen()
        self.main_layout.add_widget(self.game_world)

        # D-pad (swapped for a restart button when the round ends)
        self.controls_layout = BoxLayout(orientation="horizontal", size_hint_y=0.2)
        self.showing_dpad = False
        self.setup_dpad()
        self.main_layout.add_widget(self.controls_layout)

        Window.bind(on_key_down=self.on_key_down, on_key_up=self.on_key_up)
        Clock.schedule_interval(self.update_ui, 1.0 / 30.0)
        return self.main_layout

    # ---- controls ------------------------------------------------------
    def make_direction_button(self, text, direction):
        button = Button(text=text, bold=True, background_color=BUTTON_GREEN)
        button.bind(on_press=lambda *_: self.set_move(direction),
                    on_release=lambda *_: self.stop_move(direction))
        return button

    def setup_dpad(self):
        self.controls_layout.clear_widgets()
        up_down = BoxLayout(orientation="vertical")
        up_down.add_widget(self.make_direction_button("UP", "up"))
        up_down.add_widget(self.make_direction_button("DOWN", "down"))
        self.controls_layout.add_widget(self.make_direction_button("LEFT", "left"))
        self.controls_layout.add_widget(up_down)
        self.controls_layout.add_widget(self.make_direction_button("RIGHT", "right"))
        self.showing_dpad = True

    def setup_end_button(self, message, color):
        self.controls_layout.clear_widgets()
        restart = Button(text=message, font_size="18sp", bold=True,
                         background_color=color)
        restart.bind(on_press=lambda *_: self.handle_restart())
        self.controls_layout.add_widget(restart)
        self.showing_dpad = False

    def handle_restart(self):
        self.game_world.reset_game()
        self.setup_dpad()

    def set_move(self, direction):
        game = self.game_world
        if not game.game_over and not game.boss_defeated:
            game.current_direction = direction

    def stop_move(self, direction=None):
        """Stop only if the released button is the one currently steering.

        Without this check, pressing RIGHT with one thumb and then lifting
        the other thumb off LEFT would stop Khala even though RIGHT is still
        held down.
        """
        game = self.game_world
        if direction is None or game.current_direction == direction:
            game.current_direction = None

    def on_key_down(self, window, key, *args):
        """Arrow keys, so you can test on a computer."""
        if key in KEY_DIRECTIONS:
            self.set_move(KEY_DIRECTIONS[key])

    def on_key_up(self, window, key, *args):
        if key in KEY_DIRECTIONS:
            self.stop_move(KEY_DIRECTIONS[key])

    # ---- header text -----------------------------------------------------
    def update_ui(self, dt):
        """Copy the game's state into the header and the bottom bar."""
        game = self.game_world
        if game.game_over:
            self.score_label.text = "KHALA JOYBUG CRUSHED! RE-ROCK!"
            if self.showing_dpad:
                self.setup_end_button("RESPAWN KHALA JOYBUG", (0.8, 0.2, 0.2, 1))
        elif game.boss_defeated:
            self.score_label.text = "VICTORY! KHALA JOYBUG SAVED THE GARDEN!"
            if self.showing_dpad:
                self.setup_end_button("PLAY AGAIN", (0.2, 0.8, 0.2, 1))
        elif game.boss_mode:
            self.score_label.text = "BEE HEALTH: " + "I " * game.boss_health
        elif game.star_mode:
            self.score_label.text = "INVINCIBLE METAL MODE: %ds" % (int(game.star_timer) + 1)
        else:
            self.score_label.text = "JOY SCORE: %d / %d" % (game.score, BOSS_TRIGGER_SCORE)


if __name__ == "__main__":
    MobileGameApp().run()
