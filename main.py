import pygame
import random
from enum import Enum
import math
import asyncio
import json
import os

# Initialize Pygame
pygame.init()

# Constants
GRID_SIZE = 20
CELL_SIZE = 20
WINDOW_WIDTH = GRID_SIZE * CELL_SIZE
HEADER_HEIGHT = 60
CONTROLLER_HEIGHT = 120
FOOTER_HEIGHT = 30
PLAY_ZONE_HEIGHT = GRID_SIZE * CELL_SIZE
WINDOW_HEIGHT = PLAY_ZONE_HEIGHT + HEADER_HEIGHT + CONTROLLER_HEIGHT + FOOTER_HEIGHT
INITIAL_FPS = 5
MAX_FPS = 15

# Colors
WHITE = (255, 255, 255)
GREEN = (0, 128, 0)
LIGHT_GREEN = (100, 200, 100)
DARK_GREEN = (0, 80, 0)
RED = (255, 0, 0)
BLACK = (0, 0, 0)
YELLOW = (255, 255, 0)
BLUE = (0, 100, 255)

# UI Theme Colors
DARK_BG = (30, 30, 30)
GRID_COLOR = (42, 42, 42)
BAR_BG = (20, 20, 20)
TEXT_LIGHT = (240, 240, 240)
BORDER_COLOR = (70, 70, 70)
GOLD = (255, 215, 0)

# Direction enum
class Direction(Enum):
    RIGHT = 0
    DOWN = 1
    LEFT = 2
    UP = 3


class SnakeGame:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
        self.virtual_screen = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Snake Game - Realistic Snake")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        self.footer_font = pygame.font.Font(None, 20)

        self.snake = [pygame.math.Vector2(5, 5)]
        self.food = pygame.math.Vector2(0, 0)
        self.direction = Direction.RIGHT
        self.score = 0
        self.current_fps = INITIAL_FPS

        self.highscore_file = "highscore.json"
        self.leaderboard = self.load_leaderboard()
        self.high_score = self.leaderboard[0]["score"] if self.leaderboard else 0
        self.paused = False
        self.is_game_over = False
        self.inputting_name = False
        self.input_name = ""

        # Golden Apple state
        self.golden_food = None
        self.golden_food_timer = 0

        # Swipe and touch controls
        self.swipe_start_pos = None
        self.min_swipe_distance = 25
        self.name_input_index = 0

        # Movement and rendering states
        self.input_queue = []
        self.prev_snake = list(self.snake)
        self.last_update_time = pygame.time.get_ticks()

        self.spawn_food()
        self.running = True

    def load_leaderboard(self):
        """Load leaderboard from JSON file."""
        default_leaderboard = [
            {"name": "BOT", "score": 40},
            {"name": "VIP", "score": 30},
            {"name": "SNA", "score": 20},
            {"name": "NEW", "score": 10},
            {"name": "BEG", "score": 5}
        ]
        if os.path.exists(self.highscore_file):
            try:
                with open(self.highscore_file, "r") as f:
                    data = json.load(f)
                    if "leaderboard" in data:
                        return data["leaderboard"]
                    elif "high_score" in data:
                        # Convert old format
                        high_score = data["high_score"]
                        default_leaderboard[0] = {"name": "AAA", "score": high_score}
                        default_leaderboard.sort(key=lambda x: x["score"], reverse=True)
                        return default_leaderboard
            except Exception as e:
                print(f"Error loading leaderboard: {e}")
        return default_leaderboard

    def save_leaderboard(self):
        """Save leaderboard to JSON file."""
        try:
            with open(self.highscore_file, "w") as f:
                json.dump({"leaderboard": self.leaderboard}, f)
            # Update high score cache
            if self.leaderboard:
                self.high_score = self.leaderboard[0]["score"]
        except Exception as e:
            print(f"Error saving leaderboard: {e}")

    def spawn_food(self):
        """Spawn food at a random location not occupied by snake."""
        while True:
            x = random.randint(0, GRID_SIZE - 1)
            y = random.randint(0, GRID_SIZE - 1)
            food_pos = pygame.math.Vector2(x, y)

            if food_pos not in self.snake:
                self.food = food_pos
                break

    def get_clicked_button(self, vx, vy):
        cx = 120
        cy = HEADER_HEIGHT + PLAY_ZONE_HEIGHT + CONTROLLER_HEIGHT // 2  # 520
        
        # Check DPAD buttons
        if pygame.Rect(cx - 20, cy - 45, 40, 25).collidepoint(vx, vy):
            return "UP"
        if pygame.Rect(cx - 20, cy + 20, 40, 25).collidepoint(vx, vy):
            return "DOWN"
        if pygame.Rect(cx - 45, cy - 20, 25, 40).collidepoint(vx, vy):
            return "LEFT"
        if pygame.Rect(cx + 20, cy - 20, 25, 40).collidepoint(vx, vy):
            return "RIGHT"
            
        # Check Pause button
        px = 280
        py = cy
        if pygame.Rect(px - 35, py - 20, 70, 40).collidepoint(vx, vy):
            return "PAUSE"
            
        return None

    def change_input_letter(self, amount):
        if len(self.input_name) < 3:
            self.input_name = (self.input_name + "AAA")[:3]
        char_list = list(self.input_name)
        curr_char = char_list[self.name_input_index]
        new_ord = ord(curr_char) + amount
        if new_ord < ord('A'):
            new_ord = ord('Z')
        elif new_ord > ord('Z'):
            new_ord = ord('A')
        char_list[self.name_input_index] = chr(new_ord)
        self.input_name = "".join(char_list)

    def submit_name(self):
        if len(self.input_name) == 3:
            self.leaderboard.append({"name": self.input_name, "score": self.score})
            self.leaderboard.sort(key=lambda x: x["score"], reverse=True)
            self.leaderboard = self.leaderboard[:5]
            self.save_leaderboard()
            self.inputting_name = False

    def handle_direction_change(self, new_dir):
        if self.paused or self.is_game_over or self.inputting_name:
            return
        ref_dir = self.input_queue[-1] if self.input_queue else self.direction
        is_opposite = (
            (new_dir == Direction.RIGHT and ref_dir == Direction.LEFT) or
            (new_dir == Direction.LEFT and ref_dir == Direction.RIGHT) or
            (new_dir == Direction.UP and ref_dir == Direction.DOWN) or
            (new_dir == Direction.DOWN and ref_dir == Direction.UP)
        )
        if not is_opposite and len(self.input_queue) < 2:
            self.input_queue.append(new_dir)

    def handle_events(self):
        """Handle keyboard/mouse/touch input and window close."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.VIDEORESIZE:
                self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.swipe_start_pos = event.pos
                
                # Check for click on virtual buttons
                screen_w, screen_h = self.screen.get_size()
                scale = min(screen_w / WINDOW_WIDTH, screen_h / WINDOW_HEIGHT)
                offset_x = (screen_w - WINDOW_WIDTH * scale) // 2
                offset_y = (screen_h - WINDOW_HEIGHT * scale) // 2
                
                vx = (event.pos[0] - offset_x) / scale
                vy = (event.pos[1] - offset_y) / scale
                
                if self.is_game_over:
                    self.reset_game()
                    return
                    
                button = self.get_clicked_button(vx, vy)
                if button:
                    if self.inputting_name:
                        if button == "UP":
                            self.change_input_letter(1)
                        elif button == "DOWN":
                            self.change_input_letter(-1)
                        elif button == "LEFT":
                            self.name_input_index = (self.name_input_index - 1) % 3
                        elif button == "RIGHT":
                            self.name_input_index = (self.name_input_index + 1) % 3
                        elif button == "PAUSE":
                            self.submit_name()
                    else:
                        if button == "PAUSE":
                            self.paused = not self.paused
                            if not self.paused:
                                self.last_update_time = pygame.time.get_ticks()
                        elif not self.paused:
                            if button == "UP":
                                self.handle_direction_change(Direction.UP)
                            elif button == "DOWN":
                                self.handle_direction_change(Direction.DOWN)
                            elif button == "LEFT":
                                self.handle_direction_change(Direction.LEFT)
                            elif button == "RIGHT":
                                self.handle_direction_change(Direction.RIGHT)
            elif event.type == pygame.MOUSEBUTTONUP:
                if self.swipe_start_pos:
                    end_pos = event.pos
                    dx = end_pos[0] - self.swipe_start_pos[0]
                    dy = end_pos[1] - self.swipe_start_pos[1]
                    dist = math.hypot(dx, dy)
                    
                    if dist > self.min_swipe_distance:
                        # Swipe detected!
                        if abs(dx) > abs(dy):
                            new_dir = Direction.RIGHT if dx > 0 else Direction.LEFT
                        else:
                            new_dir = Direction.DOWN if dy > 0 else Direction.UP
                        self.handle_direction_change(new_dir)
                    self.swipe_start_pos = None
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_f, pygame.K_F11):
                    pygame.display.toggle_fullscreen()
                    return
 
                if self.inputting_name:
                    if event.key == pygame.K_BACKSPACE:
                        self.input_name = self.input_name[:-1]
                    elif event.key == pygame.K_RETURN:
                        self.submit_name()
                    elif event.key == pygame.K_LEFT:
                        self.name_input_index = (self.name_input_index - 1) % 3
                    elif event.key == pygame.K_RIGHT:
                        self.name_input_index = (self.name_input_index + 1) % 3
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        self.change_input_letter(1)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        self.change_input_letter(-1)
                    else:
                        char = event.unicode
                        if char.isalnum() and len(self.input_name) < 3:
                            char_list = list(self.input_name + "   ")[:3]
                            char_list[self.name_input_index] = char.upper()
                            self.input_name = "".join(char_list).strip()
                            self.name_input_index = (self.name_input_index + 1) % 3
                    return
 
                if self.is_game_over:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.reset_game()
                    return
 
                if event.key in (pygame.K_p, pygame.K_ESCAPE):
                    self.paused = not self.paused
                    if not self.paused:
                        self.last_update_time = pygame.time.get_ticks()
                    return
 
                if self.paused:
                    return
 
                new_dir = None
                if event.key in (pygame.K_RIGHT, pygame.K_d):
                    new_dir = Direction.RIGHT
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    new_dir = Direction.DOWN
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    new_dir = Direction.LEFT
                elif event.key in (pygame.K_UP, pygame.K_w):
                    new_dir = Direction.UP
 
                if new_dir is not None:
                    self.handle_direction_change(new_dir)

    def update_speed(self):
        """Update game speed based on score."""
        speed_increase = self.score // 50
        new_fps = INITIAL_FPS + speed_increase
        self.current_fps = min(new_fps, MAX_FPS)

    def move_snake(self):
        """Move the snake in the current direction."""
        # Store current positions for rendering interpolation
        self.prev_snake = [pos.copy() for pos in self.snake]

        # Dequeue direction from input queue
        if self.input_queue:
            self.direction = self.input_queue.pop(0)

        head = self.snake[0]
        new_head = head.copy()

        if self.direction == Direction.RIGHT:
            new_head.x += 1
        elif self.direction == Direction.DOWN:
            new_head.y += 1
        elif self.direction == Direction.LEFT:
            new_head.x -= 1
        elif self.direction == Direction.UP:
            new_head.y -= 1

        # Check if snake hit the wall
        wall_hit = False
        if (
            new_head.x < 0
            or new_head.x >= GRID_SIZE
            or new_head.y < 0
            or new_head.y >= GRID_SIZE
        ):
            wall_hit = True
            self.score -= 1

            # Wrap around to the other side
            new_head.x = new_head.x % GRID_SIZE
            new_head.y = new_head.y % GRID_SIZE

        # Check collision with itself
        if new_head in self.snake:
            self.game_over()
            return

        self.snake.insert(0, new_head)

        # Check if snake ate food
        if new_head == self.food:
            self.score += 10
            self.spawn_food()
            self.update_speed()
            if self.score > self.high_score:
                self.high_score = self.score
            # Spawn golden apple with 15% chance
            if random.random() < 0.15 and self.golden_food is None:
                self.spawn_golden_apple()
        elif self.golden_food and new_head == self.golden_food:
            self.score += 30
            self.golden_food = None
            self.golden_food_timer = 0
            self.update_speed()
            if self.score > self.high_score:
                self.high_score = self.score
            # Pop 3 segments to shrink the snake by 2 net segments (since new_head was inserted)
            for _ in range(3):
                if len(self.snake) > 2:
                    self.snake.pop()
        else:
            self.snake.pop()

        if wall_hit:
            print(f"Hit wall! Score: {self.score}, Speed: {self.current_fps}")

    def spawn_golden_apple(self):
        """Spawn a golden apple at a random unoccupied cell."""
        while True:
            x = random.randint(0, GRID_SIZE - 1)
            y = random.randint(0, GRID_SIZE - 1)
            pos = pygame.math.Vector2(x, y)
            if pos not in self.snake and pos != self.food:
                self.golden_food = pos
                self.golden_food_timer = 60  # 60 frames countdown
                break

    def game_over(self):
        """Handle game over."""
        print(f"Game Over! Final Score: {self.score}")
        print(f"Final Speed: {self.current_fps} FPS")
        # Check if score qualifies for Top 5 leaderboard
        if len(self.leaderboard) < 5 or self.score > self.leaderboard[-1]["score"]:
            self.inputting_name = True
            self.input_name = "AAA"
            self.name_input_index = 0
        self.is_game_over = True

    def reset_game(self):
        """Reset the game."""
        self.snake = [pygame.math.Vector2(5, 5)]
        self.prev_snake = list(self.snake)
        self.direction = Direction.RIGHT
        self.input_queue.clear()
        self.score = 0
        self.current_fps = INITIAL_FPS
        self.spawn_food()
        self.golden_food = None
        self.golden_food_timer = 0
        self.is_game_over = False
        self.paused = False
        self.inputting_name = False
        self.last_update_time = pygame.time.get_ticks()

    def draw_snake_head(self, g, x, y):
        """Draw the snake's head with eyes and tongue."""
        center_x = x + CELL_SIZE // 2
        center_y = y + CELL_SIZE // 2

        # Draw red forked tongue sticking out
        tongue_color = RED
        if self.direction == Direction.RIGHT:
            start = (center_x + CELL_SIZE // 2 - 2, center_y)
            mid = (center_x + CELL_SIZE // 2 + 5, center_y)
            end1 = (center_x + CELL_SIZE // 2 + 8, center_y - 3)
            end2 = (center_x + CELL_SIZE // 2 + 8, center_y + 3)
        elif self.direction == Direction.LEFT:
            start = (center_x - CELL_SIZE // 2 + 2, center_y)
            mid = (center_x - CELL_SIZE // 2 - 5, center_y)
            end1 = (center_x - CELL_SIZE // 2 - 8, center_y - 3)
            end2 = (center_x - CELL_SIZE // 2 - 8, center_y + 3)
        elif self.direction == Direction.DOWN:
            start = (center_x, center_y + CELL_SIZE // 2 - 2)
            mid = (center_x, center_y + CELL_SIZE // 2 + 5)
            end1 = (center_x - 3, center_y + CELL_SIZE // 2 + 8)
            end2 = (center_x + 3, center_y + CELL_SIZE // 2 + 8)
        elif self.direction == Direction.UP:
            start = (center_x, center_y - CELL_SIZE // 2 + 2)
            mid = (center_x, center_y - CELL_SIZE // 2 - 5)
            end1 = (center_x - 3, center_y - CELL_SIZE // 2 - 8)
            end2 = (center_x + 3, center_y - CELL_SIZE // 2 - 8)

        pygame.draw.line(g, tongue_color, start, mid, 2)
        pygame.draw.line(g, tongue_color, mid, end1, 2)
        pygame.draw.line(g, tongue_color, mid, end2, 2)

        # Draw main head body
        pygame.draw.circle(
            g, DARK_GREEN, (center_x, center_y), CELL_SIZE // 2 - 2
        )
        pygame.draw.circle(
            g, BLACK, (center_x, center_y), CELL_SIZE // 2 - 2, 2
        )

        # Draw eyes (white sclera and black pupil)
        def draw_eye(gx, gy):
            pygame.draw.circle(g, WHITE, (int(gx), int(gy)), 3)
            pygame.draw.circle(g, BLACK, (int(gx), int(gy)), 1)

        if self.direction == Direction.RIGHT:
            draw_eye(center_x + 4, center_y - 4)
            draw_eye(center_x + 4, center_y + 4)
        elif self.direction == Direction.LEFT:
            draw_eye(center_x - 4, center_y - 4)
            draw_eye(center_x - 4, center_y + 4)
        elif self.direction == Direction.DOWN:
            draw_eye(center_x - 4, center_y + 4)
            draw_eye(center_x + 4, center_y + 4)
        elif self.direction == Direction.UP:
            draw_eye(center_x - 4, center_y - 4)
            draw_eye(center_x + 4, center_y - 4)

    def draw_snake_body(self, g, x, y, is_last=False, factor=1.0):
        """Draw a body segment of the snake with scale texture."""
        center_x = x + CELL_SIZE // 2
        center_y = y + CELL_SIZE // 2
        radius = int((CELL_SIZE // 2 - 1) * factor)

        # Draw main segment circle
        color = LIGHT_GREEN if is_last else GREEN
        pygame.draw.circle(g, color, (center_x, center_y), radius)

        # Draw outer darker green scale border
        pygame.draw.circle(g, DARK_GREEN, (center_x, center_y), radius, 1)

        # Draw a tiny inner scale highlighting circle for texture
        if radius > 4:
            pygame.draw.circle(g, LIGHT_GREEN if not is_last else WHITE, (center_x - 1, center_y - 1), radius - 3, 1)

    def draw(self):
        """Draw the game."""
        # 1. Fill base virtual window background
        self.virtual_screen.fill(BAR_BG)

        # Draw Play Zone Background
        pygame.draw.rect(self.virtual_screen, DARK_BG, (0, HEADER_HEIGHT, WINDOW_WIDTH, PLAY_ZONE_HEIGHT))

        # Draw play zone grid lines
        for x in range(GRID_SIZE):
            pygame.draw.line(self.virtual_screen, GRID_COLOR, (x * CELL_SIZE, HEADER_HEIGHT), (x * CELL_SIZE, HEADER_HEIGHT + PLAY_ZONE_HEIGHT))
        for y in range(GRID_SIZE):
            pygame.draw.line(self.virtual_screen, GRID_COLOR, (0, HEADER_HEIGHT + y * CELL_SIZE), (WINDOW_WIDTH, HEADER_HEIGHT + y * CELL_SIZE))

        # Calculate interpolation factor
        if self.paused or self.is_game_over:
            t = 1.0
        else:
            update_interval = 1000.0 / self.current_fps
            t = (pygame.time.get_ticks() - self.last_update_time) / update_interval
            t = max(0.0, min(1.0, t))

        # Draw snake with interpolation (shifted down by HEADER_HEIGHT)
        for i, segment in enumerate(self.snake):
            curr_pos = segment
            prev_pos = self.prev_snake[i] if i < len(self.prev_snake) else curr_pos

            # Interpolate coordinates with wrap-around check
            diff = curr_pos - prev_pos
            if diff.x > 1:
                diff.x -= GRID_SIZE
            elif diff.x < -1:
                diff.x += GRID_SIZE

            if diff.y > 1:
                diff.y -= GRID_SIZE
            elif diff.y < -1:
                diff.y += GRID_SIZE

            draw_pos = prev_pos + diff * t
            x = (draw_pos.x % GRID_SIZE) * CELL_SIZE
            y = (draw_pos.y % GRID_SIZE) * CELL_SIZE + HEADER_HEIGHT

            if i == 0:
                self.draw_snake_head(self.virtual_screen, x, y)
            else:
                is_last = i == len(self.snake) - 1
                factor = 1.0 - (i / len(self.snake)) * 0.4
                self.draw_snake_body(self.virtual_screen, x, y, is_last, factor)

        # Draw normal apple (shifted down by HEADER_HEIGHT)
        food_x = self.food.x * CELL_SIZE
        food_y = self.food.y * CELL_SIZE + HEADER_HEIGHT
        center_x = food_x + CELL_SIZE // 2
        center_y = food_y + CELL_SIZE // 2

        pygame.draw.circle(
            self.virtual_screen, RED, (center_x, center_y), CELL_SIZE // 2 - 2
        )
        pygame.draw.circle(
            self.virtual_screen, (200, 0, 0),
            (center_x, center_y), CELL_SIZE // 2 - 2, 2
        )

        # Draw stem
        pygame.draw.line(
            self.virtual_screen,
            (100, 150, 50),
            (center_x, center_y - CELL_SIZE // 2),
            (center_x, center_y - CELL_SIZE // 2 - 3),
            2,
        )

        # Draw golden apple if active (shifted down by HEADER_HEIGHT)
        if self.golden_food is not None:
            g_food_x = self.golden_food.x * CELL_SIZE
            g_food_y = self.golden_food.y * CELL_SIZE + HEADER_HEIGHT
            g_center_x = g_food_x + CELL_SIZE // 2
            g_center_y = g_food_y + CELL_SIZE // 2

            # Golden apple blinking when expiring
            draw_golden = True
            if self.golden_food_timer < 20 and (self.golden_food_timer // 2) % 2 == 0:
                draw_golden = False

            if draw_golden:
                # Gold apple body
                pygame.draw.circle(self.virtual_screen, (255, 215, 0), (g_center_x, g_center_y), CELL_SIZE // 2 - 2)
                # Outer gold border
                pygame.draw.circle(self.virtual_screen, (218, 165, 32), (g_center_x, g_center_y), CELL_SIZE // 2 - 2, 2)
                # Shine point
                pygame.draw.circle(self.virtual_screen, WHITE, (g_center_x - 3, g_center_y - 3), 2)
                # Stem
                pygame.draw.line(self.virtual_screen, (100, 150, 50), (g_center_x, g_center_y - CELL_SIZE // 2 + 1), (g_center_x + 2, g_center_y - CELL_SIZE // 2 - 2), 2)
                # Leaf
                pygame.draw.circle(self.virtual_screen, GREEN, (g_center_x + 3, g_center_y - CELL_SIZE // 2 - 1), 2)

        # Draw play zone boundary border
        pygame.draw.rect(self.virtual_screen, BORDER_COLOR, (0, HEADER_HEIGHT, WINDOW_WIDTH, PLAY_ZONE_HEIGHT), 1)

        # 2. Draw Top Header Bar Text
        score_text = self.font.render(f"Score: {self.score}", True, TEXT_LIGHT)
        self.virtual_screen.blit(score_text, (15, 12))

        highscore_text = self.font.render(f"High: {self.high_score}", True, GOLD)
        self.virtual_screen.blit(highscore_text, (WINDOW_WIDTH - highscore_text.get_width() - 15, 12))

        speed_text = self.small_font.render(f"Speed: {self.current_fps} FPS", True, TEXT_LIGHT)
        self.virtual_screen.blit(speed_text, (WINDOW_WIDTH // 2 - speed_text.get_width() // 2, 20))

        # 3. Draw Bottom Controller Area
        controller_y = HEADER_HEIGHT + PLAY_ZONE_HEIGHT
        pygame.draw.rect(self.virtual_screen, BAR_BG, (0, controller_y, WINDOW_WIDTH, CONTROLLER_HEIGHT))
        pygame.draw.line(self.virtual_screen, BORDER_COLOR, (0, controller_y), (WINDOW_WIDTH, controller_y), 1)

        # Draw D-PAD
        cx = 120
        cy = controller_y + CONTROLLER_HEIGHT // 2  # 520
        
        # Determine colors (highlight active direction if not paused/gameover/nameinput)
        up_color = GREEN if (self.direction == Direction.UP and not self.paused and not self.is_game_over and not self.inputting_name) else (50, 50, 50)
        down_color = GREEN if (self.direction == Direction.DOWN and not self.paused and not self.is_game_over and not self.inputting_name) else (50, 50, 50)
        left_color = GREEN if (self.direction == Direction.LEFT and not self.paused and not self.is_game_over and not self.inputting_name) else (50, 50, 50)
        right_color = GREEN if (self.direction == Direction.RIGHT and not self.paused and not self.is_game_over and not self.inputting_name) else (50, 50, 50)
        
        # Draw background cross
        pygame.draw.rect(self.virtual_screen, (30, 30, 30), (cx - 45, cy - 45, 90, 90), 0, 10)
        pygame.draw.circle(self.virtual_screen, (40, 40, 40), (cx, cy), 15)

        # Draw button shapes (rounded corners)
        pygame.draw.rect(self.virtual_screen, up_color, (cx - 20, cy - 45, 40, 25), 0, 4)
        pygame.draw.rect(self.virtual_screen, down_color, (cx - 20, cy + 20, 40, 25), 0, 4)
        pygame.draw.rect(self.virtual_screen, left_color, (cx - 45, cy - 20, 25, 40), 0, 4)
        pygame.draw.rect(self.virtual_screen, right_color, (cx + 20, cy - 20, 25, 40), 0, 4)
        
        # Draw button borders
        pygame.draw.rect(self.virtual_screen, BORDER_COLOR, (cx - 20, cy - 45, 40, 25), 1, 4)
        pygame.draw.rect(self.virtual_screen, BORDER_COLOR, (cx - 20, cy + 20, 40, 25), 1, 4)
        pygame.draw.rect(self.virtual_screen, BORDER_COLOR, (cx - 45, cy - 20, 25, 40), 1, 4)
        pygame.draw.rect(self.virtual_screen, BORDER_COLOR, (cx + 20, cy - 20, 25, 40), 1, 4)

        # Draw arrow indicators (polygons/triangles)
        # Up
        pygame.draw.polygon(self.virtual_screen, TEXT_LIGHT, [(cx, cy - 40), (cx - 8, cy - 26), (cx + 8, cy - 26)])
        # Down
        pygame.draw.polygon(self.virtual_screen, TEXT_LIGHT, [(cx, cy + 40), (cx - 8, cy + 26), (cx + 8, cy + 26)])
        # Left
        pygame.draw.polygon(self.virtual_screen, TEXT_LIGHT, [(cx - 40, cy), (cx - 26, cy - 8), (cx - 26, cy + 8)])
        # Right
        pygame.draw.polygon(self.virtual_screen, TEXT_LIGHT, [(cx + 40, cy), (cx + 26, cy - 8), (cx + 26, cy + 8)])

        # Draw Action/Pause button
        px = 280
        py = cy
        pause_button_rect = pygame.Rect(px - 35, py - 20, 70, 40)
        
        # Decide color and label for Pause/Action button
        if self.inputting_name:
            action_color = GOLD
            action_label = "OK"
        elif self.is_game_over:
            action_color = GREEN
            action_label = "PLAY"
        elif self.paused:
            action_color = GREEN
            action_label = "RESUME"
        else:
            action_color = RED
            action_label = "PAUSE"
            
        pygame.draw.rect(self.virtual_screen, action_color, pause_button_rect, 0, 8)
        pygame.draw.rect(self.virtual_screen, TEXT_LIGHT, pause_button_rect, 2, 8)
        
        action_text_surf = self.small_font.render(action_label, True, BLACK if action_color in (GOLD, GREEN) else TEXT_LIGHT)
        self.virtual_screen.blit(action_text_surf, (px - action_text_surf.get_width() // 2, py - action_text_surf.get_height() // 2))

        # 4. Draw Bottom Footer Bar Text
        instructions = self.footer_font.render(
            "Swipe/D-Pad/Keys: Move | Pause/Tap Screen to Control",
            True,
            TEXT_LIGHT,
        )
        self.virtual_screen.blit(
            instructions, (WINDOW_WIDTH // 2 - instructions.get_width() // 2, controller_y + CONTROLLER_HEIGHT + 7)
        )

        # 5. Draw Dialogue Card Overlays (Centered over Play Zone)
        
        # Draw Pause Card
        if self.paused:
            card_width = 260
            card_height = 100
            cx_card = WINDOW_WIDTH // 2 - card_width // 2
            cy_card = HEADER_HEIGHT + PLAY_ZONE_HEIGHT // 2 - card_height // 2

            card_surface = pygame.Surface((card_width, card_height))
            card_surface.fill((15, 15, 15))
            pygame.draw.rect(card_surface, GOLD, (0, 0, card_width, card_height), 2)

            pause_text = self.font.render("PAUSED", True, GOLD)
            resume_text = self.small_font.render("Tap RESUME or P to Play", True, TEXT_LIGHT)

            card_surface.blit(pause_text, (card_width // 2 - pause_text.get_width() // 2, 20))
            card_surface.blit(resume_text, (card_width // 2 - resume_text.get_width() // 2, 55))

            self.virtual_screen.blit(card_surface, (cx_card, cy_card))

        # Draw Name Input Card
        elif self.inputting_name:
            card_width = 280
            card_height = 180
            cx_card = WINDOW_WIDTH // 2 - card_width // 2
            cy_card = HEADER_HEIGHT + PLAY_ZONE_HEIGHT // 2 - card_height // 2

            card_surface = pygame.Surface((card_width, card_height))
            card_surface.fill((15, 15, 15))
            pygame.draw.rect(card_surface, GOLD, (0, 0, card_width, card_height), 2)

            title_text = self.font.render("NEW HIGH SCORE!", True, GOLD)
            prompt_text = self.small_font.render("D-Pad Up/Down to cycle, L/R to move:", True, TEXT_LIGHT)
            
            # Render individual characters with active indicator
            for idx in range(3):
                char = self.input_name[idx] if idx < len(self.input_name) else "_"
                char_color = GOLD if idx == self.name_input_index else GREEN
                char_surf = self.font.render(char, True, char_color)
                # Position them: centered around card_width // 2
                # Spacing of 30 pixels: index 0 at -30, index 1 at 0, index 2 at +30
                pos_x = card_width // 2 - char_surf.get_width() // 2 + (idx - 1) * 30
                pos_y = 90
                card_surface.blit(char_surf, (pos_x, pos_y))
                
                # Draw underline for active character
                if idx == self.name_input_index:
                    pygame.draw.line(card_surface, GOLD, (pos_x, pos_y + char_surf.get_height() + 2), (pos_x + char_surf.get_width(), pos_y + char_surf.get_height() + 2), 2)
                    
            submit_text = self.small_font.render("Click OK or Press ENTER", True, TEXT_LIGHT)

            card_surface.blit(title_text, (card_width // 2 - title_text.get_width() // 2, 15))
            card_surface.blit(prompt_text, (card_width // 2 - prompt_text.get_width() // 2, 50))
            card_surface.blit(submit_text, (card_width // 2 - submit_text.get_width() // 2, 140))

            self.virtual_screen.blit(card_surface, (cx_card, cy_card))

        # Draw Game Over Card
        elif self.is_game_over:
            card_width = 300
            card_height = 280
            cx_card = WINDOW_WIDTH // 2 - card_width // 2
            cy_card = HEADER_HEIGHT + PLAY_ZONE_HEIGHT // 2 - card_height // 2

            card_surface = pygame.Surface((card_width, card_height))
            card_surface.fill((15, 15, 15))
            pygame.draw.rect(card_surface, RED, (0, 0, card_width, card_height), 2)

            game_over_text = self.font.render("GAME OVER", True, RED)
            final_score_text = self.small_font.render(f"Final Score: {self.score}", True, TEXT_LIGHT)
            leaderboard_title = self.small_font.render("TOP 5 LEADERBOARD", True, GOLD)

            card_surface.blit(game_over_text, (card_width // 2 - game_over_text.get_width() // 2, 15))
            card_surface.blit(final_score_text, (card_width // 2 - final_score_text.get_width() // 2, 45))
            card_surface.blit(leaderboard_title, (card_width // 2 - leaderboard_title.get_width() // 2, 75))

            start_y = 105
            for index, entry in enumerate(self.leaderboard):
                rank = index + 1
                name = entry["name"]
                score = entry["score"]
                entry_color = GOLD if rank == 1 else TEXT_LIGHT

                entry_str = f"{rank}.  {name:<5}  {score:>5}"
                entry_text = self.small_font.render(entry_str, True, entry_color)
                card_surface.blit(entry_text, (card_width // 2 - 60, start_y + index * 22))

            restart_text = self.small_font.render("Tap screen or Press ENTER to play", True, TEXT_LIGHT)
            card_surface.blit(restart_text, (card_width // 2 - restart_text.get_width() // 2, 230))

            self.virtual_screen.blit(card_surface, (cx_card, cy_card))

        # 5. Aspect-ratio aware scaling to actual window size
        screen_w, screen_h = self.screen.get_size()
        scale = min(screen_w / WINDOW_WIDTH, screen_h / WINDOW_HEIGHT)
        new_w = int(WINDOW_WIDTH * scale)
        new_h = int(WINDOW_HEIGHT * scale)
        
        offset_x = (screen_w - new_w) // 2
        offset_y = (screen_h - new_h) // 2
        
        scaled_surface = pygame.transform.scale(self.virtual_screen, (new_w, new_h))
        
        self.screen.fill(BLACK)
        self.screen.blit(scaled_surface, (offset_x, offset_y))
        pygame.display.flip()

    async def run(self):
        """Main game loop compatible with Pygbag/web browsers."""
        self.last_update_time = pygame.time.get_ticks()

        while self.running:
            self.handle_events()
            if not self.paused and not self.is_game_over:
                current_time = pygame.time.get_ticks()
                update_interval = 1000.0 / self.current_fps
                if current_time - self.last_update_time >= update_interval:
                    self.move_snake()
                    self.last_update_time = current_time

                    # Decrement golden food timer
                    if self.golden_food is not None:
                        self.golden_food_timer -= 1
                        if self.golden_food_timer <= 0:
                            self.golden_food = None
            self.draw()
            self.clock.tick(60)

            # Give the browser's event loop time to run.
            await asyncio.sleep(0)

        pygame.quit()


if __name__ == "__main__":
    game = SnakeGame()
    asyncio.run(game.run())
