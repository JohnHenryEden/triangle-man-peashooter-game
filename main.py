try:
    import sys
    import random
    import math
    import os
    import pygame
    from socket import *
    from pygame.locals import *
except ImportError as err:
    print(f"couldn't load module. {err}")
    sys.exit(2)

def load_png(name):
    """ Load image and return image object"""
    fullname = os.path.join("data", name)
    try:
        image = pygame.image.load(fullname)
        if image.get_alpha() is None:
            image = image.convert()
        else:
            image = image.convert_alpha()
    except FileNotFoundError:
        print(f"Cannot load image: {fullname}")
        raise SystemExit
    return image, image.get_rect()

def calculate_new_xy(speed, angle_in_degrees):
    move_vec = pygame.math.Vector2()
    move_vec.from_polar((speed, angle_in_degrees))
    return move_vec

mc_image = None
projectile_friend_image = None
projectile_foe_image = None
enemy_image = None

# Main character class
class MainCharacter(pygame.sprite.Sprite):
    """ Main character class
    Returns: Main character object
    Functions: update, move_up, move_down, move_left, move_right
    Attributes: area, vector"""
    def __init__(self, mc_image, mc_dmg_image):
        pygame.sprite.Sprite.__init__(self)
        self.image, self.rect = mc_image    
        self.dmg_image, self.dmg_rect = mc_dmg_image    
        self.orig_image = self.image.copy()    
        screen = pygame.display.get_surface()
        self.area = screen.get_rect()
        self.speed = 5
        self.hp = 5
        self.state = "still"
        self.direction = "left"
        self.reload = 500
        self.is_hit = False
        self.invincible_time = 500
        self.last = pygame.time.get_ticks()
        self.last_dmg = pygame.time.get_ticks()
        self.reinit()
        
    def reinit(self):
        self.state = "still"
        screen = pygame.display.get_surface()
        self.movepos = [screen.get_rect().centerx,screen.get_rect().centery]
            
    def update(self):
        newpos = self.rect.move(self.movepos)
        if self.area.contains(newpos):
            self.rect = newpos
        if self.is_hit:
            self.image = self.dmg_image
            now = pygame.time.get_ticks()
            if (now - self.last_dmg) % 10 == 0:
                self.image = self.orig_image
            if now - self.last_dmg > self.invincible_time:
                self.is_hit = False
                self.last_dmg = now
        else:
            self.image = self.orig_image
        pygame.event.pump()
        
    def face_left(self):
        if self.direction != "left":
            self.image = pygame.transform.flip(self.image, True, False)
            self.orig_image = pygame.transform.flip(self.orig_image, True, False)
            self.dmg_image = pygame.transform.flip(self.dmg_image, True, False)
        self.direction = "left"
        
    def face_right(self):
        if self.direction != "right":
            self.image = pygame.transform.flip(self.image, True, False)
            self.orig_image = pygame.transform.flip(self.orig_image, True, False)
            self.dmg_image = pygame.transform.flip(self.dmg_image, True, False)
        self.direction = "right"

    def move_up(self):
        self.movepos[1] =  -(self.speed)
        self.state = "moveup"

    def move_down(self):
        self.movepos[1] = (self.speed)
        self.state = "movedown"
        
    def move_left(self):
        self.movepos[0] = - (self.speed)
        self.face_left()
        self.state = "moveleft"
        
    def move_right(self):
        self.movepos[0] = (self.speed)
        self.face_right()
        self.state = "moveright"
    
    def on_hit(self):
        if self.is_hit == False:
            if self.hp > 0:
                self.hp -= 1
                self.is_hit = True
                self.last_dmg = pygame.time.get_ticks()
            else:
                self.kill()
            
        
class Projectile(pygame.sprite.Sprite):
    """ Projectile class, launched by both friend and foe, cause damage upon hit
    Returns: projectile object
    Functions: update, calc_new_pos
    Attributes: area, vector"""
    def __init__(self, side, launching_rect, direction, projectile_friend_image, projectile_foe_image):
        pygame.sprite.Sprite.__init__(self)
        self.side = side
        if self.side == "friend":
            self.image, self.rect = projectile_friend_image  
        elif self.side == "foe":
            self.image, self.rect = projectile_foe_image
        screen = pygame.display.get_surface()
        self.area = screen.get_rect()
        self.speed = 10
        self.dmg = 1
        self.state = "still"
        self.launching_rect = launching_rect
        self.direction = direction
        self.reinit()
    
    def reinit(self):
        self.state = "still"
        self.movepos = [self.launching_rect.centerx, self.launching_rect.centery]
        
    def update(self):
        newpos = self.rect.move(self.movepos)
        self.movepos = [0, 0]
        if self.area.contains(newpos):
            self.rect = newpos
        else:
            self.kill()
        pygame.event.pump()
    
    def move(self):
        self.state = "moving"
        if self.direction == "up":
            self.movepos[1] = self.movepos[1] - (self.speed)
        if self.direction == "down":
            self.movepos[1] = self.movepos[1] + (self.speed)
        if self.direction == "left":
            self.movepos[0] = self.movepos[0] - (self.speed)
        if self.direction == "right":
            self.movepos[0] = self.movepos[0] + (self.speed)
    def moveToTarget(self):
        self.state = "moving"
        dx, dy = self.direction.centerx - self.launching_rect.centerx, self.direction.centery - self.launching_rect.centery
        angle = math.atan2(dy, dx)  # 计算角度
        velocity = (math.cos(angle) * self.speed, math.sin(angle) * self.speed)
        self.movepos[0] = self.movepos[0] + velocity[0]
        self.movepos[1] = self.movepos[1] + velocity[1]

class Enemy(pygame.sprite.Sprite):
    """ Enemy class, Randomly generate up to 5 enemies, shoot projectile towards player and move at a random direction
    Returns: projectile object
    Functions: update, calc_new_pos
    Attributes: area, vector"""
    def __init__(self, enemy_image, hit_image):
        pygame.sprite.Sprite.__init__(self)
        self.image, self.rect = enemy_image
        self.orig_image = self.image.copy()
        self.bright_image, self.hit_rect = hit_image
        
        screen = pygame.display.get_surface()
        self.area = screen.get_rect()
        self.xspeed = random.randint(-4, 4)
        self.yspeed = random.randint(-4, 4)
        self.state = "still"
        self.hp = 2
        belt_left = [random.randint(self.rect.width, self.rect.width * 2), random.randint(self.rect.width, self.area.height - self.rect.width)]
        belt_right = [random.randint(self.area.width - self.rect.width * 2, self.area.width - self.rect.width), random.randint(self.rect.width, self.area.height - self.rect.width)]
        
        pos_seed = random.randint(0, 1)
        if pos_seed == 0:
            self.pos = belt_left
        if pos_seed == 1:
            self.pos = belt_right
        self.dir = random.randint(0, 359)
        self.reload = random.randint(3000, 5000)
        self.last = pygame.time.get_ticks()
        self.last_dmg = pygame.time.get_ticks()
        self.is_hit = False
        self.reinit()
        
    def reinit(self):
        self.state = "still"
        self.movepos = [self.pos[0], self.pos[1]]
        
    def update(self):
        newpos = self.rect.move(self.movepos)
        self.movepos = [0, 0]
        self.rect = newpos
        if self.is_hit:
            self.image = self.bright_image
            now = pygame.time.get_ticks()
            if (now - self.last_dmg) % 10 == 0:
                self.image = self.orig_image
            if now - self.last_dmg > 500:
                self.is_hit = False
                self.last_dmg = now
        else:
            self.image = self.orig_image
        if self.rect.top <= self.area.top or self.rect.bottom >= self.area.bottom:
            self.yspeed = -self.yspeed
        if self.rect.left <= self.area.left or self.rect.right >= self.area.right:
            self.xspeed = -self.xspeed
            
        pygame.event.pump()
    
    def fire(self, projectile, target_rect):
        projectile.moveTo(target_rect)
    
    def move(self):
        self.state = "moving"
        self.movepos[0] = self.movepos[0] + self.xspeed
        self.movepos[1] = self.movepos[1] + self.yspeed
        
    def on_hit(self, game):
        if self.hp > 0:
            self.hp -= 1
            self.is_hit = True
            self.last_dmg = pygame.time.get_ticks()
        else:
            self.kill()
            game.score += 1
            print(game.score)

class Game():
    def __init__(self):
        self.score = 0
        self.size = (1280, 720)
        self.title = "Triangle_man_adventure"
        self.bg_color = (255, 208, 148)
        self.enemy_spawn_delay = 3000
        self.enemy_count = 3
        self.mc_sprite_img = "triangle_dude.png"
        self.mc_dmg_img = "triangle_dude_hit.png"
        self.fri_bullet_img = "projectile_friend.png"
        self.foe_bullet_img = "projectile_foe.png"
        self.enemy_img = "enemy.png"
        self.enemy_hit_img = "enemy_hit.png"
    
    def start(self):
        # Initialise screen
        pygame.init()
        pygame.key.stop_text_input()
        screen = pygame.display.set_mode(self.size)
        pygame.display.set_caption(self.title)
        
        mc_image = load_png(self.mc_sprite_img)  
        mc_dmg_image = load_png(self.mc_dmg_img)  
        projectile_friend_image = load_png(self.fri_bullet_img)  
        projectile_foe_image = load_png(self.foe_bullet_img)  
        enemy_image = load_png(self.enemy_img)  
        enemy_hit_image = load_png(self.enemy_hit_img)  

        # Fill background
        background = pygame.Surface(screen.get_size())
        background = background.convert()
        background.fill(self.bg_color)
        
        # clock
        clock = pygame.time.Clock()
        
        global mc
        mc = MainCharacter(mc_image, mc_dmg_image)
        
        mc_sprite = pygame.sprite.RenderPlain(mc)
        friend_proj_sprites = pygame.sprite.RenderPlain()
        foe_proj_sprites = pygame.sprite.RenderPlain()
        enemy_sprites = pygame.sprite.RenderPlain()
        
        # Blit everything to the screen
        screen.blit(background, (0, 0))
        pygame.display.flip()
        
        # Enemy spawn & fire delay
        last_enemy_spawn = pygame.time.get_ticks()
        
        # Display score
        myfont = pygame.font.SysFont("monospace", 25)

        
        # add projectile function
        def add_projectile(side, orig_rect, dir, shooter):
            now = pygame.time.get_ticks()
            if now - shooter.last >= shooter.reload:
                shooter.last = now
                proj = Projectile(side, orig_rect, dir, projectile_friend_image, projectile_foe_image)
                if side == "friend":
                    friend_proj_sprites.add(proj)
                if side == "foe":
                    foe_proj_sprites.add(proj)
                return proj
            return None
        
        def main_loop():
            # Event loop
            while True:
                        
                for event in pygame.event.get():
                    if event.type == QUIT:
                        pygame.quit()
                        sys.exit()
                    elif event.type == KEYUP:
                        if event.key == K_w or event.key == K_s or event.key == K_a or event.key == K_d:
                            mc.movepos = [0,0]
                            mc.state = "still"
                            
                # Hold to continuously shoot  
                keys = pygame.key.get_pressed()
                    
                if keys[pygame.K_w]:
                    mc.move_up()
                if keys[pygame.K_s]:
                    mc.move_down()
                if keys[pygame.K_a]:
                    mc.move_left()
                if keys[pygame.K_d]:
                    mc.move_right()
                if keys[pygame.K_r] and not mc.alive():
                    self.score = 0
                    self.start()
                    
                if keys[pygame.K_LEFT]:
                    add_projectile("friend", mc.rect, "left", mc)
                if keys[pygame.K_RIGHT]:
                    add_projectile("friend", mc.rect, "right", mc)
                if keys[pygame.K_UP]:
                    add_projectile("friend", mc.rect, "up", mc)
                if keys[pygame.K_DOWN]:
                    add_projectile("friend", mc.rect, "down", mc)
                    
                screen.blit(background, (0, 0))
                screen.blit(background, mc.rect, mc.rect)
                
                # Managing projectiles (friend)
                for proj_friend in friend_proj_sprites.sprites():
                    if screen.get_rect().contains(proj_friend.rect):
                        proj_friend.move()
                    else:
                        friend_proj_sprites.remove(proj_friend)
                    # hit detection(on enemy)
                    collide = proj_friend.rect.collideobjectsall(enemy_sprites.sprites())
                    if len(collide) > 0:
                        for item in collide:
                            item.on_hit(self)
                        proj_friend.kill()
                friend_proj_sprites.update()
                friend_proj_sprites.draw(screen)
                
                # Managing projectiles (foe)
                for proj_foe in foe_proj_sprites.sprites():
                    if screen.get_rect().contains(proj_foe.rect):
                        proj_foe.moveToTarget()
                    else:
                        foe_proj_sprites.remove(proj_foe)
                    # hit detection(on mc)
                    collide = proj_foe.rect.collideobjectsall(mc_sprite.sprites())
                    if len(collide) > 0:
                        for item in collide:
                            item.on_hit()
                        proj_foe.kill()
                        
                
                foe_proj_sprites.update()
                foe_proj_sprites.draw(screen)
                
                # Managing enemies
                if len(enemy_sprites.sprites()) < self.enemy_count:
                    now = pygame.time.get_ticks()
                    if len(enemy_sprites.sprites()) == 0 or now - last_enemy_spawn >= self.enemy_spawn_delay:
                        last_enemy_spawn = now
                        enemy = Enemy(enemy_image, enemy_hit_image)
                        enemy_sprites.add(enemy)
                        
                enemy_sprites.update()
                for enemy in enemy_sprites.sprites():
                    enemy.move()
                    add_projectile("foe", enemy.rect, mc.rect, enemy)
                    collide = enemy.rect.collideobjectsall(mc_sprite.sprites())
                    if len(collide) > 0:
                        for item in collide:
                            item.on_hit()
                        
                enemy_sprites.draw(screen)
                
                mc_sprite.update()
                mc_sprite.draw(screen)
                
                # render text
                label_score = myfont.render("Score: " + str(self.score), 1, (255,0,255))
                label_hp = myfont.render("HP: " + str(mc.hp), 1, (255,0,255))
                if not mc.alive():
                    label_restart = myfont.render("Press R to restart.", 1, (255,0,255))
                    screen.blit(label_restart, (10, 60))
                screen.blit(label_hp, (10, 10))
                screen.blit(label_score, (10, 30))
                pygame.display.flip()
                clock.tick(60)
        main_loop()

if __name__ == '__main__': 
    game = Game()
    game.start()