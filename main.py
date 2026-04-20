import pygame
import sys
import os
from constants import SCREEN_W, SCREEN_H, ROOM_W, ROOM_H, STEP_X, STEP_Y, \
                      WALL_T, DOOR_SIZE, BG_COLOR, FPS
from map_generator import generate_map
from room import FLOOR_COLOR, WALL_COLOR
from player import Player
from world import finalize_map, get_camera, current_room, resolve_walls
import minimap
import damage_number
from shop import Shop
from save import SAVE_PATH, save_exists, write_save, load_game
from ui import Button, make_menu_buttons

pygame.init()
screen  = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Blade Echo")
clock   = pygame.time.Clock()
font_sm = pygame.font.SysFont(None, 20)
font_md = pygame.font.SysFont(None, 24)
font_lg = pygame.font.SysFont(None, 52)
font_xl = pygame.font.SysFont(None, 96)

# ── Game state ────────────────────────────────────────────────────────────────
rooms = start_room = grid = None
hallway_floors = hall_walls = all_walls = None
player    = None
state     = 'menu'
floor_num = 1
sublevel  = 1
show_map  = False


def level_number():
    return (floor_num - 1) * 3 + sublevel


def _build_level():
    global rooms, start_room, grid, hallway_floors, hall_walls, all_walls
    is_boss_sl = (sublevel == 3)
    rooms, start_room, grid = generate_map(is_boss_sublevel=is_boss_sl)
    for room in rooms:
        wx = room.grid_x * STEP_X
        wy = room.grid_y * STEP_Y
        room.setup_geometry(wx, wy, ROOM_W, ROOM_H, WALL_T, DOOR_SIZE)
        if room.event_type in ('monster', 'boss'):
            room.spawn_event(wx, wy, ROOM_W, ROOM_H, floor_number=level_number())
        elif room.event_type == 'exit':
            room.place_gate()
        elif room.event_type == 'shop':
            room.shop = Shop(floor_num)
    hallway_floors, hall_walls, all_walls = finalize_map(rooms)


def init_game():
    global player, floor_num, sublevel
    floor_num, sublevel = 1, 1
    _build_level()
    player = Player(start_room.wx + ROOM_W // 2 - 16,
                    start_room.wy + ROOM_H // 2 - 16, speed=300)


def advance_level():
    global floor_num, sublevel
    sublevel += 1
    if sublevel > 3:
        sublevel = 1
        floor_num += 1
    if floor_num > 3:
        floor_num, sublevel = 1, 1
    coins_kept = player.coins
    hp_kept    = player.hp
    _build_level()
    player.x = start_room.wx + ROOM_W // 2 - 16
    player.y = start_room.wy + ROOM_H // 2 - 16
    player.rect.topleft = (int(player.x), int(player.y))
    player.coins = coins_kept
    player.hp    = hp_kept


def _do_load_game():
    global rooms, start_room, grid, floor_num, sublevel, player, \
           hallway_floors, hall_walls, all_walls
    rooms, start_room, grid, floor_num, sublevel, player, \
        hallway_floors, hall_walls, all_walls = load_game()


# ── UI elements ───────────────────────────────────────────────────────────────
menu_buttons = make_menu_buttons(font_lg, save_exists)
menu_btn_ig  = Button((SCREEN_W - 110, 8, 100, 30), "Menu", font_sm,
                      color=(50, 50, 70), hover=(80, 80, 110))
gameover_btn = Button((SCREEN_W // 2 - 140, SCREEN_H // 2 + 40, 280, 55),
                      "Return to Menu", font_lg,
                      color=(80, 40, 40), hover=(120, 60, 60))

# ── Main loop ─────────────────────────────────────────────────────────────────
running  = True
cur_room = None
while running:
    dt     = clock.tick(FPS) / 1000
    events = pygame.event.get()

    for event in events:
        if event.type == pygame.QUIT:
            if state == 'playing':
                write_save(player, rooms, floor_num, sublevel)
            running = False

        if state == 'menu':
            if menu_buttons[0].is_clicked(event):
                init_game()
                state = 'playing'
            elif menu_buttons[1].is_clicked(event):
                _do_load_game()
                state = 'playing'
            elif menu_buttons[2].is_clicked(event):
                running = False

        elif state == 'gameover':
            if gameover_btn.is_clicked(event):
                state = 'menu'
                menu_buttons = make_menu_buttons(font_lg, save_exists)

        elif state == 'playing':
            shop = cur_room.shop if cur_room else None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if not (shop and shop.open):
                        player.perform_parry()
                elif event.key == pygame.K_m:
                    show_map = not show_map
                elif event.key == pygame.K_e and shop:
                    shop.toggle()
                elif event.key == pygame.K_F1:
                    advance_level()
                    break
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if menu_btn_ig.is_clicked(event):
                    write_save(player, rooms, floor_num, sublevel)
                    state = 'menu'
                    menu_buttons = make_menu_buttons(font_lg, save_exists)
                elif shop and shop.open:
                    shop.handle_click(event.pos, player)
                else:
                    player.swing_sword()

    # ── Menu ──────────────────────────────────────────────────────────────
    if state == 'menu':
        screen.fill((15, 15, 25))
        title = font_xl.render("Blade Echo", True, (180, 120, 255))
        screen.blit(title, title.get_rect(centerx=SCREEN_W // 2, y=SCREEN_H // 4))
        for btn in menu_buttons:
            btn.draw(screen)
        pygame.display.flip()
        continue

    # ── Game over ─────────────────────────────────────────────────────────
    if state == 'gameover':
        screen.fill((10, 5, 5))
        txt = font_xl.render("GAME OVER", True, (220, 50, 50))
        screen.blit(txt, txt.get_rect(centerx=SCREEN_W // 2, y=SCREEN_H // 2 - 80))
        gameover_btn.draw(screen)
        pygame.display.flip()
        continue

    # ── Playing update ────────────────────────────────────────────────────
    cam_x, cam_y = get_camera(player, SCREEN_W, SCREEN_H)
    player.handle_input(pygame.key.get_pressed(), dt, cam_x, cam_y)

    cur_room = current_room(player, rooms)
    if cur_room:
        cur_room.visited = True
        cur_room.try_lock(player.rect)

    lock_walls   = [w for r in rooms if r.is_locked for w in r.lock_walls]
    active_walls = all_walls + lock_walls

    resolve_walls(player, active_walls)
    player.update(dt)
    damage_number.update_all(dt)
    cam_x, cam_y = get_camera(player, SCREEN_W, SCREEN_H)

    if player.hp <= 0:
        if save_exists():
            os.remove(SAVE_PATH)
        state = 'gameover'
        continue

    if cur_room:
        cur_room.update(player, dt, active_walls)
        if cur_room.gate and cur_room.gate.rect.colliderect(player.rect):
            advance_level()
            continue

    # ── Playing draw ──────────────────────────────────────────────────────
    screen.fill(BG_COLOR)

    for f in hallway_floors:
        pygame.draw.rect(screen, FLOOR_COLOR,
                         (f.x - cam_x, f.y - cam_y, f.width, f.height))

    for room in rooms:
        room.draw(screen, cam_x, cam_y, font_sm)

    for w in hall_walls:
        pygame.draw.rect(screen, WALL_COLOR,
                         (w.x - cam_x, w.y - cam_y, w.width, w.height))

    for bullet in player.deflected_bullets:
        bullet.draw(screen, cam_x, cam_y)

    player.draw(screen, cam_x, cam_y)
    damage_number.draw_all(screen, font_sm, cam_x, cam_y)

    if cur_room:
        tag  = ' [START]' if cur_room.is_start else (' [BOSS]' if cur_room.is_boss else '')
        info = font_md.render(f"Room: {cur_room.event_type}{tag}", True, (220, 220, 220))
    else:
        info = font_md.render("Hallway", True, (160, 160, 160))
    screen.blit(info, (8, 8))
    screen.blit(font_md.render(f"HP: {player.hp}",       True, (220, 80, 80)),  (8, 28))
    screen.blit(font_md.render(f"Coins: {player.coins}", True, (255, 215, 0)),  (8, 48))
    screen.blit(font_md.render(f"Floor {floor_num}  –  Sub-level {sublevel}/3",
                               True, (180, 180, 220)), (8, 68))

    menu_btn_ig.draw(screen)

    if show_map:
        minimap.draw(screen, rooms, cur_room, font_md)

    if cur_room and cur_room.shop:
        cur_room.shop.draw(screen)
        cur_room.shop.draw_hint(screen, font_md)

    pygame.display.flip()

pygame.quit()
sys.exit()
