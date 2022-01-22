import random
import katagames_sdk as katasdk

kataen = katasdk.engine
pygame = kataen.pygame
"""
  testing the two possibilities to draw rect on screen...
"""

print('pygame version is= ', end='')
print(pygame.ver)

fg_elements = list()
game_over = None
surf, screen = None, pygame.Surface((0, 0))
offset = 0

@katasdk.web_entry_point
def init_game():
    global game_over, fg_elements, surf, screen

    game_over = False

    # screen = pygame.display.set_mode((640,480))
    kataen.init(kataen.HD_MODE)
    screen = kataen.get_screen()

    # let's create 20 rect objects...
    for rank in range(10):
        fg_elements.append(pygame.rect.Rect(16 + rank * 55, 33, 25, 40))
    for rank in range(10):
        fg_elements.append(pygame.rect.Rect(16 + rank * 50, 93, 33, 12))

    surf = pygame.Surface((random.randint(60, 93), 88 + random.randint(88, 133)))
    surf.fill((255, 0, 255))  # rose super flashy,  ça aurait pu etre pygame.Color('orange'))


@katasdk.web_animate
def update_game(infot=None):
    global game_over, screen, fg_elements, surf, offset
    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            game_over = True
        elif ev.type == pygame.KEYDOWN:
            if ev.key==pygame.K_DOWN:
                offset+=16
            elif ev.key == pygame.K_UP:
                offset-=16
    
    screen.fill(pygame.color.Color('antiquewhite2'))
    # it can be drawn
    for elt in fg_elements:
        pygame.draw.rect(screen, pygame.color.Color('aquamarine4'), elt)
    screen.blit(surf, (640 // 3, offset+109))

    # pygame.display.flip()
    kataen.display_update()


if __name__ == '__main__':
    init_game()
    while not game_over:
        update_game()
    kataen.cleanup()
    print('bye!')
