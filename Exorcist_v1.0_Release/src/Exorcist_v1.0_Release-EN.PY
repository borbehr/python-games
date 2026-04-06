#!/usr/bin/env python3

import pygame
import sys
import random
import math
from enum import Enum

pygame.init()
pygame.mixer.init()
pygame.font.init()

info = pygame.display.Info()
SCREEN_WIDTH = info.current_w
SCREEN_HEIGHT = info.current_h
FPS = 60

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
ORANGE = (255, 165, 0)
PURPLE = (128, 0, 128)
BROWN = (139, 69, 19)
DARK_GREEN = (0, 100, 0)
GRAY = (100, 100, 100)

PLAYER_RADIUS = 20
PLAYER_SPEED = 5
PLAYER_HEALTH = 100
PLAYER_MAX_HEALTH = 100

ENEMY_BASE_RADIUS = 15
BULLET_RADIUS = 4

ENEMY_SPAWN_DELAY = 1000
BOSS_SPAWN_SCORE = 500
UPGRADE_SPAWN_CHANCE = 0.1

DIFFICULTY_MULTIPLIERS = {
    "easy": 0.7,
    "normal": 1.0,
    "hard": 1.5,
    "nightmare": 2.5
}

def distance(x1, y1, x2, y2):
    return math.hypot(x1 - x2, y1 - y2)

def angle_to_direction(angle):
    return math.cos(angle), math.sin(angle)

def point_in_rect(px, py, rect):
    return rect.collidepoint(px, py)

def clamp(value, min_val, max_val):
    return max(min_val, min(value, max_val))

class Button:
    def __init__(self, x, y, width, height, text, color=GRAY, hover_color=WHITE, text_color=BLACK, font_size=32):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.text_color = text_color
        self.font = pygame.font.Font(None, font_size)
        self.hovered = False

    def draw(self, screen):
        color = self.hover_color if self.hovered else self.color
        pygame.draw.rect(screen, color, self.rect, border_radius=10)
        pygame.draw.rect(screen, BLACK, self.rect, 3, border_radius=10)
        text_surf = self.font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def update(self, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)

    def is_clicked(self, mouse_pos, mouse_click):
        return mouse_click and self.rect.collidepoint(mouse_pos)

class Particle:
    def __init__(self, x, y, vx, vy, color, lifetime=30, radius=3):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.radius = radius

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.lifetime -= 1
        self.vx *= 0.98
        self.vy *= 0.98

    def draw(self, screen):
        alpha = int(255 * (self.lifetime / self.max_lifetime))
        color = self.color
        if alpha < 255:
            color = tuple(int(c * (self.lifetime / self.max_lifetime)) for c in self.color)
        pygame.draw.circle(screen, color, (int(self.x), int(self.y)), self.radius)

    def is_alive(self):
        return self.lifetime > 0

class UpgradeType(Enum):
    HEALTH = "health"
    SPEED = "speed"
    DAMAGE = "damage"
    FIRERATE = "firerate"
    SCORE_BONUS = "score_bonus"

class Upgrade:
    def __init__(self, x, y, upgrade_type):
        self.x = x
        self.y = y
        self.radius = 12
        self.type = upgrade_type
        self.lifetime = 10000
        self.spawn_time = pygame.time.get_ticks()
        self.color = self._get_color()

    def _get_color(self):
        colors = {
            UpgradeType.HEALTH: RED,
            UpgradeType.SPEED: CYAN,
            UpgradeType.DAMAGE: ORANGE,
            UpgradeType.FIRERATE: YELLOW,
            UpgradeType.SCORE_BONUS: GREEN
        }
        return colors.get(self.type, WHITE)

    def draw(self, screen):
        pulse = abs(math.sin(pygame.time.get_ticks() * 0.005)) * 3
        radius = self.radius + int(pulse)
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), radius)
        pygame.draw.circle(screen, WHITE, (int(self.x), int(self.y)), radius-2, 2)

    def is_expired(self):
        return pygame.time.get_ticks() - self.spawn_time > self.lifetime

    def apply(self, player):
        if self.type == UpgradeType.HEALTH:
            player.health = min(player.max_health, player.health + 25)
        elif self.type == UpgradeType.SPEED:
            player.speed += 1
            player.speed = min(player.speed, 10)
        elif self.type == UpgradeType.DAMAGE:
            player.damage += 5
        elif self.type == UpgradeType.FIRERATE:
            player.fire_rate = max(50, player.fire_rate - 20)
        elif self.type == UpgradeType.SCORE_BONUS:
            return 100
        return 0

class Bullet:
    def __init__(self, x, y, angle, speed=12, damage=20, radius=5, color=YELLOW):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = speed
        self.damage = damage
        self.radius = radius
        self.color = color
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed

    def update(self):
        self.x += self.vx
        self.y += self.vy

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)
        trail_x = self.x - self.vx * 1.5
        trail_y = self.y - self.vy * 1.5
        pygame.draw.circle(screen, self.color, (int(trail_x), int(trail_y)), self.radius//2)

    def is_off_screen(self):
        return (self.x < -50 or self.x > SCREEN_WIDTH + 50 or
                self.y < -50 or self.y > SCREEN_HEIGHT + 50)

class Enemy:
    def __init__(self, x, y, radius, health, speed, color, damage, score_reward, enemy_type="normal"):
        self.x = x
        self.y = y
        self.radius = radius
        self.health = health
        self.max_health = health
        self.speed = speed
        self.color = color
        self.damage = damage
        self.score_reward = score_reward
        self.type = enemy_type
        self.shoot_cooldown = 0
        self.shoot_delay = 1000

    def update(self, player_x, player_y, dt):
        dx = player_x - self.x
        dy = player_y - self.y
        dist = math.hypot(dx, dy)
        if dist > 0:
            self.x += (dx / dist) * self.speed * dt * 60
            self.y += (dy / dist) * self.speed * dt * 60
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= dt * 1000

    def draw(self, screen):
        pygame.draw.circle(screen, self.color, (int(self.x), int(self.y)), self.radius)
        health_ratio = self.health / self.max_health
        bar_width = self.radius * 2
        bar_height = 5
        bar_x = self.x - self.radius
        bar_y = self.y - self.radius - 10
        pygame.draw.rect(screen, RED, (bar_x, bar_y, bar_width, bar_height))
        pygame.draw.rect(screen, GREEN, (bar_x, bar_y, bar_width * health_ratio, bar_height))
        eye_radius = self.radius // 3
        pygame.draw.circle(screen, BLACK, (int(self.x - self.radius*0.4), int(self.y - self.radius*0.2)), eye_radius)
        pygame.draw.circle(screen, BLACK, (int(self.x + self.radius*0.4), int(self.y - self.radius*0.2)), eye_radius)

    def take_damage(self, amount):
        self.health -= amount
        return self.health <= 0

    def can_shoot(self):
        return self.shoot_cooldown <= 0

    def shoot(self, target_x, target_y):
        angle = math.atan2(target_y - self.y, target_x - self.x)
        self.shoot_cooldown = self.shoot_delay
        return Bullet(self.x, self.y, angle, speed=8, damage=15, radius=4, color=MAGENTA)

class Goblin(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, radius=18, health=40, speed=2.5, color=DARK_GREEN,
                         damage=15, score_reward=50, enemy_type="goblin")

class Shooter(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, radius=16, health=30, speed=1.8, color=PURPLE,
                         damage=10, score_reward=70, enemy_type="shooter")
        self.shoot_delay = 1500

class Tank(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, radius=28, health=150, speed=1.2, color=BROWN,
                         damage=25, score_reward=150, enemy_type="tank")

class FastEnemy(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, radius=12, health=20, speed=4.2, color=CYAN,
                         damage=8, score_reward=40, enemy_type="fast")

class Boss(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, radius=50, health=500, speed=1.0, color=RED,
                         damage=40, score_reward=1000, enemy_type="boss")
        self.shoot_delay = 800
        self.phase = 0

    def draw(self, screen):
        super().draw(screen)
        horn_length = self.radius // 2
        left_horn = (self.x - self.radius*0.6, self.y - self.radius*0.8)
        right_horn = (self.x + self.radius*0.6, self.y - self.radius*0.8)
        pygame.draw.line(screen, BLACK, (self.x, self.y - self.radius), left_horn, 5)
        pygame.draw.line(screen, BLACK, (self.x, self.y - self.radius), right_horn, 5)
        pygame.draw.circle(screen, RED, (int(self.x), int(self.y - self.radius*0.5)), self.radius//3)

    def shoot(self, target_x, target_y):
        bullets = []
        base_angle = math.atan2(target_y - self.y, target_x - self.x)
        for offset in (-0.3, 0, 0.3):
            angle = base_angle + offset
            bullets.append(Bullet(self.x, self.y, angle, speed=10, damage=20, radius=6, color=ORANGE))
        self.shoot_cooldown = self.shoot_delay
        return bullets

class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = PLAYER_RADIUS
        self.health = PLAYER_HEALTH
        self.max_health = PLAYER_MAX_HEALTH
        self.speed = PLAYER_SPEED
        self.damage = 20
        self.fire_rate = 200
        self.last_shot = 0
        self.score = 0
        self.kills = 0
        self.invincible_frames = 0
        self.invincible_duration = 1000
        self.last_hit_time = 0
        self.weapon_type = "pistol"

    def update(self, keys, dt):
        dx = dy = 0
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx += 1
        if dx != 0 or dy != 0:
            length = math.hypot(dx, dy)
            dx /= length
            dy /= length
        self.x += dx * self.speed * dt * 60
        self.y += dy * self.speed * dt * 60
        self.x = clamp(self.x, self.radius, SCREEN_WIDTH - self.radius)
        self.y = clamp(self.y, self.radius, SCREEN_HEIGHT - self.radius)

        if self.invincible_frames > 0:
            self.invincible_frames -= dt * 1000

    def draw(self, screen):
        pygame.draw.circle(screen, BLUE, (int(self.x), int(self.y)), self.radius)
        pygame.draw.circle(screen, BLACK, (int(self.x), int(self.y)), self.radius, 2)
        eye_radius = self.radius // 4
        pygame.draw.circle(screen, WHITE, (int(self.x - self.radius*0.4), int(self.y - self.radius*0.2)), eye_radius)
        pygame.draw.circle(screen, WHITE, (int(self.x + self.radius*0.4), int(self.y - self.radius*0.2)), eye_radius)
        pygame.draw.circle(screen, BLACK, (int(self.x - self.radius*0.4), int(self.y - self.radius*0.2)), eye_radius//2)
        pygame.draw.circle(screen, BLACK, (int(self.x + self.radius*0.4), int(self.y - self.radius*0.2)), eye_radius//2)
        pygame.draw.line(screen, BLACK, (self.x - self.radius*0.3, self.y + self.radius*0.2),
                         (self.x, self.y + self.radius*0.4), 3)
        pygame.draw.line(screen, BLACK, (self.x + self.radius*0.3, self.y + self.radius*0.2),
                         (self.x, self.y + self.radius*0.4), 3)
        hat_rect = pygame.Rect(self.x - self.radius, self.y - self.radius*1.2, self.radius*2, self.radius)
        pygame.draw.ellipse(screen, BROWN, hat_rect)
        health_ratio = self.health / self.max_health
        bar_width = self.radius * 2
        bar_height = 6
        bar_x = self.x - self.radius
        bar_y = self.y - self.radius - 15
        pygame.draw.rect(screen, RED, (bar_x, bar_y, bar_width, bar_height))
        pygame.draw.rect(screen, GREEN, (bar_x, bar_y, bar_width * health_ratio, bar_height))

    def shoot(self, target_x, target_y, current_time):
        if current_time - self.last_shot < self.fire_rate:
            return None
        self.last_shot = current_time
        angle = math.atan2(target_y - self.y, target_x - self.x)
        bullets = []
        if self.weapon_type == "pistol":
            bullets.append(Bullet(self.x, self.y, angle, speed=14, damage=self.damage, radius=5, color=YELLOW))
        elif self.weapon_type == "auto":
            bullets.append(Bullet(self.x, self.y, angle, speed=16, damage=self.damage-5, radius=4, color=WHITE))
        elif self.weapon_type == "shotgun":
            for offset in (-0.2, 0, 0.2):
                bullets.append(Bullet(self.x, self.y, angle+offset, speed=12, damage=self.damage-2, radius=4, color=ORANGE))
        elif self.weapon_type == "laser":
            bullets.append(Bullet(self.x, self.y, angle, speed=22, damage=self.damage+10, radius=6, color=CYAN))
        return bullets

    def take_damage(self, amount):
        if self.invincible_frames <= 0:
            self.health -= amount
            self.invincible_frames = self.invincible_duration
            self.last_hit_time = pygame.time.get_ticks()
            return True
        return False

    def add_score(self, points):
        self.score += points

    def heal(self, amount):
        self.health = min(self.max_health, self.health + amount)

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
        pygame.display.set_caption("Exorcist: Battle with Evil")
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = "menu"
        self.difficulty = "normal"
        self.font = pygame.font.Font(None, 36)
        self.big_font = pygame.font.Font(None, 72)
        self.small_font = pygame.font.Font(None, 24)

        self.player = None
        self.enemies = []
        self.bullets = []
        self.particles = []
        self.upgrades = []
        self.enemy_bullets = []

        self.last_enemy_spawn = 0
        self.enemy_spawn_delay = ENEMY_SPAWN_DELAY
        self.boss_spawned = False
        self.boss_score_threshold = BOSS_SPAWN_SCORE
        self.wave = 1

        self.buttons = []
        self.setup_menu()

    def setup_menu(self):
        center_x = SCREEN_WIDTH // 2
        start_y = SCREEN_HEIGHT // 2 - 100
        btn_width = 250
        btn_height = 60
        self.buttons = [
            Button(center_x - btn_width//2, start_y, btn_width, btn_height, "Start Game", GREEN, YELLOW),
            Button(center_x - btn_width//2, start_y + 80, btn_width, btn_height, "Difficulty: Normal", GRAY, WHITE),
            Button(center_x - btn_width//2, start_y + 160, btn_width, btn_height, "Exit", RED, ORANGE),
        ]

    def start_game(self):
        self.player = Player(SCREEN_WIDTH//2, SCREEN_HEIGHT//2)
        self.enemies.clear()
        self.bullets.clear()
        self.particles.clear()
        self.upgrades.clear()
        self.enemy_bullets.clear()
        self.last_enemy_spawn = pygame.time.get_ticks()
        self.boss_spawned = False
        self.wave = 1
        mult = DIFFICULTY_MULTIPLIERS.get(self.difficulty, 1.0)
        self.enemy_spawn_delay = int(ENEMY_SPAWN_DELAY / mult)
        self.state = "playing"

    def handle_events(self):
        mouse_pos = pygame.mouse.get_pos()
        mouse_click = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    mouse_click = True
            if event.type == pygame.KEYDOWN:
                if self.state == "playing" and event.key == pygame.K_ESCAPE:
                    self.state = "paused"
                elif self.state == "paused" and event.key == pygame.K_ESCAPE:
                    self.state = "playing"
                elif self.state == "game_over" and event.key == pygame.K_RETURN:
                    self.state = "menu"
                elif event.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()

        if self.state == "menu":
            for btn in self.buttons:
                btn.update(mouse_pos)
                if btn.is_clicked(mouse_pos, mouse_click):
                    if btn.text == "Start Game":
                        self.start_game()
                    elif "Difficulty" in btn.text:
                        difficulties = list(DIFFICULTY_MULTIPLIERS.keys())
                        current_idx = difficulties.index(self.difficulty)
                        next_idx = (current_idx + 1) % len(difficulties)
                        self.difficulty = difficulties[next_idx]
                        btn.text = f"Difficulty: {self.difficulty.capitalize()}"
                        if self.difficulty == "nightmare":
                            btn.color = RED
                        else:
                            btn.color = GRAY
                    elif btn.text == "Exit":
                        self.running = False

        elif self.state == "playing":
            keys = pygame.key.get_pressed()
            self.player.update(keys, self.clock.get_time())
            if pygame.mouse.get_pressed()[0]:
                mx, my = pygame.mouse.get_pos()
                bullets = self.player.shoot(mx, my, pygame.time.get_ticks())
                if bullets:
                    self.bullets.extend(bullets)
            if keys[pygame.K_1]:
                self.player.weapon_type = "pistol"
            elif keys[pygame.K_2]:
                self.player.weapon_type = "auto"
            elif keys[pygame.K_3]:
                self.player.weapon_type = "shotgun"
            elif keys[pygame.K_4]:
                self.player.weapon_type = "laser"

    def spawn_enemy(self):
        side = random.choice(['top', 'bottom', 'left', 'right'])
        if side == 'top':
            x = random.randint(0, SCREEN_WIDTH)
            y = -ENEMY_BASE_RADIUS
        elif side == 'bottom':
            x = random.randint(0, SCREEN_WIDTH)
            y = SCREEN_HEIGHT + ENEMY_BASE_RADIUS
        elif side == 'left':
            x = -ENEMY_BASE_RADIUS
            y = random.randint(0, SCREEN_HEIGHT)
        else:
            x = SCREEN_WIDTH + ENEMY_BASE_RADIUS
            y = random.randint(0, SCREEN_HEIGHT)

        rand = random.random()
        mult = DIFFICULTY_MULTIPLIERS[self.difficulty]
        if self.wave >= 5 and rand < 0.1 * mult:
            enemy = Tank(x, y)
        elif rand < 0.3 * mult:
            enemy = Shooter(x, y)
        elif rand < 0.6 * mult:
            enemy = FastEnemy(x, y)
        else:
            enemy = Goblin(x, y)

        enemy.health = int(enemy.health * (1 + self.wave * 0.1) * mult)
        enemy.max_health = enemy.health
        self.enemies.append(enemy)

    def update(self):
        if self.state != "playing":
            return

        dt = self.clock.get_time() / 1000.0

        now = pygame.time.get_ticks()
        if now - self.last_enemy_spawn > self.enemy_spawn_delay:
            self.spawn_enemy()
            self.last_enemy_spawn = now

        for enemy in self.enemies[:]:
            enemy.update(self.player.x, self.player.y, dt)
            if hasattr(enemy, 'can_shoot') and enemy.can_shoot() and enemy.type in ('shooter', 'boss'):
                if enemy.type == 'boss':
                    bullets = enemy.shoot(self.player.x, self.player.y)
                    self.enemy_bullets.extend(bullets)
                else:
                    bullet = enemy.shoot(self.player.x, self.player.y)
                    if bullet:
                        self.enemy_bullets.append(bullet)
            if distance(self.player.x, self.player.y, enemy.x, enemy.y) < self.player.radius + enemy.radius:
                if self.player.take_damage(enemy.damage):
                    self.create_particle_burst(self.player.x, self.player.y, RED, 20)
                    if self.player.health <= 0:
                        self.state = "game_over"

        for bullet in self.bullets[:]:
            bullet.update()
            if bullet.is_off_screen():
                self.bullets.remove(bullet)
                continue
            for enemy in self.enemies[:]:
                if distance(bullet.x, bullet.y, enemy.x, enemy.y) < bullet.radius + enemy.radius:
                    if enemy.take_damage(bullet.damage):
                        self.player.add_score(enemy.score_reward)
                        self.player.kills += 1
                        self.enemies.remove(enemy)
                        self.create_particle_burst(enemy.x, enemy.y, enemy.color, 30)
                        if random.random() < UPGRADE_SPAWN_CHANCE:
                            upgrade_type = random.choice(list(UpgradeType))
                            self.upgrades.append(Upgrade(enemy.x, enemy.y, upgrade_type))
                        if enemy.type == "boss":
                            self.boss_spawned = False
                    if bullet in self.bullets:
                        self.bullets.remove(bullet)
                    break

        for bullet in self.enemy_bullets[:]:
            bullet.update()
            if bullet.is_off_screen():
                self.enemy_bullets.remove(bullet)
            elif distance(self.player.x, self.player.y, bullet.x, bullet.y) < self.player.radius + bullet.radius:
                self.player.take_damage(bullet.damage)
                self.create_particle_burst(self.player.x, self.player.y, RED, 15)
                self.enemy_bullets.remove(bullet)
                if self.player.health <= 0:
                    self.state = "game_over"

        for upgrade in self.upgrades[:]:
            if upgrade.is_expired():
                self.upgrades.remove(upgrade)
            elif distance(self.player.x, self.player.y, upgrade.x, upgrade.y) < self.player.radius + upgrade.radius:
                bonus = upgrade.apply(self.player)
                if bonus > 0:
                    self.player.add_score(bonus)
                self.upgrades.remove(upgrade)
                self.create_particle_burst(upgrade.x, upgrade.y, upgrade.color, 10)

        for particle in self.particles[:]:
            particle.update()
            if not particle.is_alive():
                self.particles.remove(particle)

        if self.player.kills >= self.wave * 10:
            self.wave += 1

        if not self.boss_spawned and self.player.score >= self.boss_score_threshold:
            self.boss_score_threshold += BOSS_SPAWN_SCORE
            self.boss_spawned = True
            side = random.choice(['top', 'bottom', 'left', 'right'])
            if side == 'top':
                x = random.randint(100, SCREEN_WIDTH-100)
                y = -50
            elif side == 'bottom':
                x = random.randint(100, SCREEN_WIDTH-100)
                y = SCREEN_HEIGHT + 50
            elif side == 'left':
                x = -50
                y = random.randint(100, SCREEN_HEIGHT-100)
            else:
                x = SCREEN_WIDTH + 50
                y = random.randint(100, SCREEN_HEIGHT-100)
            self.enemies.append(Boss(x, y))

        if self.player.health <= 0:
            self.state = "game_over"

    def create_particle_burst(self, x, y, color, count=20):
        for _ in range(count):
            angle = random.uniform(0, 2*math.pi)
            speed = random.uniform(1, 5)
            vx = math.cos(angle) * speed
            vy = math.sin(angle) * speed
            lifetime = random.randint(20, 50)
            radius = random.randint(2, 6)
            self.particles.append(Particle(x, y, vx, vy, color, lifetime, radius))

    def draw(self):
        self.screen.fill(BLACK)
        if self.state == "menu":
            self.draw_menu()
        elif self.state == "playing":
            self.draw_game()
        elif self.state == "paused":
            self.draw_game()
            s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            s.fill((0, 0, 0, 128))
            self.screen.blit(s, (0, 0))
            pause_text = self.big_font.render("PAUSED", True, WHITE)
            self.screen.blit(pause_text, (SCREEN_WIDTH//2 - pause_text.get_width()//2, SCREEN_HEIGHT//2))
            cont_text = self.small_font.render("Press ESC to continue", True, WHITE)
            self.screen.blit(cont_text, (SCREEN_WIDTH//2 - cont_text.get_width()//2, SCREEN_HEIGHT//2 + 50))
        elif self.state == "game_over":
            self.draw_game_over()

        pygame.display.flip()

    def draw_menu(self):
        title = self.big_font.render("EXORCIST: BATTLE WITH EVIL", True, RED)
        subtitle = self.font.render("Fight the hordes of darkness", True, WHITE)
        self.screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 100))
        self.screen.blit(subtitle, (SCREEN_WIDTH//2 - subtitle.get_width()//2, 180))
        for btn in self.buttons:
            btn.draw(self.screen)
        tip = self.small_font.render("Controls: WASD / arrows - move, mouse - aim and shoot, 1-4 - switch weapon", True, GRAY)
        self.screen.blit(tip, (10, SCREEN_HEIGHT - 30))

    def draw_game(self):
        for enemy in self.enemies:
            enemy.draw(self.screen)
        for bullet in self.bullets:
            bullet.draw(self.screen)
        for bullet in self.enemy_bullets:
            bullet.draw(self.screen)
        for upgrade in self.upgrades:
            upgrade.draw(self.screen)
        for particle in self.particles:
            particle.draw(self.screen)
        self.player.draw(self.screen)

        score_text = self.font.render(f"Score: {self.player.score}", True, WHITE)
        health_text = self.font.render(f"Health: {self.player.health}", True, RED)
        kills_text = self.font.render(f"Kills: {self.player.kills}", True, WHITE)
        wave_text = self.font.render(f"Wave: {self.wave}", True, CYAN)
        weapon_text = self.font.render(f"Weapon: {self.player.weapon_type.upper()}", True, YELLOW)
        self.screen.blit(score_text, (10, 10))
        self.screen.blit(health_text, (10, 50))
        self.screen.blit(kills_text, (10, 90))
        self.screen.blit(wave_text, (10, 130))
        self.screen.blit(weapon_text, (SCREEN_WIDTH - weapon_text.get_width() - 10, 10))

        if self.player.invincible_frames > 0 and (pygame.time.get_ticks() // 100) % 2 == 0:
            s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            s.fill((255, 255, 255, 30))
            self.screen.blit(s, (0, 0))

    def draw_game_over(self):
        self.draw_game()
        s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        s.fill((0, 0, 0, 180))
        self.screen.blit(s, (0, 0))
        go_text = self.big_font.render("GAME OVER", True, RED)
        score_text = self.font.render(f"Final Score: {self.player.score}", True, WHITE)
        kills_text = self.font.render(f"Enemies destroyed: {self.player.kills}", True, WHITE)
        wave_text = self.font.render(f"Wave reached: {self.wave}", True, CYAN)
        restart_text = self.small_font.render("Press ENTER to return to menu", True, WHITE)
        self.screen.blit(go_text, (SCREEN_WIDTH//2 - go_text.get_width()//2, SCREEN_HEIGHT//2 - 100))
        self.screen.blit(score_text, (SCREEN_WIDTH//2 - score_text.get_width()//2, SCREEN_HEIGHT//2 - 20))
        self.screen.blit(kills_text, (SCREEN_WIDTH//2 - kills_text.get_width()//2, SCREEN_HEIGHT//2 + 20))
        self.screen.blit(wave_text, (SCREEN_WIDTH//2 - wave_text.get_width()//2, SCREEN_HEIGHT//2 + 60))
        self.screen.blit(restart_text, (SCREEN_WIDTH//2 - restart_text.get_width()//2, SCREEN_HEIGHT//2 + 150))

    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = Game()
    game.run()