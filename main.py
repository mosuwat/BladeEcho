import pygame
import sys
import os
from constants import SCREEN_W, SCREEN_H, ROOM_W, ROOM_H, STEP_X, STEP_Y, \
                      WALL_T, DOOR_SIZE, HALLWAY_LEN, BG_COLOR, FPS
from map_generator import generate_map

from player import Player
from world import finalize_map, get_camera, current_room, resolve_walls
import tilemap as tilemap_mod
import sound
from shop import Shop
from save import SAVE_PATH, save_exists, write_save, load_game
from tutorial import build_tutorial, TutorialRoom
from ui import Button, make_menu_buttons, draw_hud, draw_boss_bar, \
               update_notifications, draw_notifications, \
               draw_minimap, update_all, draw_all, \
               SettingsOverlay, draw_buff_screen, draw_stats_screen
from console import DevConsole
import stats

pygame.init()
sound.load_settings()
screen  = pygame.display.set_mode((SCREEN_W, SCREEN_H))

_IMG_DIR      = os.path.join(os.path.dirname(__file__), 'images')
_hallway_h    = tilemap_mod.load(os.path.join(_IMG_DIR, 'hallway.tmx'))
_hallway_v    = tilemap_mod.load(os.path.join(_IMG_DIR, 'hallwayUp.tmx'))
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
state        = 'menu'
floor_num    = 1
sublevel     = 1
show_map     = False
_in_tutorial = False
show_buffs    = False
show_settings = False
chart_data    = None   # populated on entering 'stats' state


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
        if room.event_type in ('monster', 'boss', 'item'):
            room.spawn_event(wx, wy, ROOM_W, ROOM_H, floor_number=level_number())
        elif room.event_type == 'exit':
            room.place_gate()
        elif room.event_type == 'shop':
            room.shop = Shop(floor_num)
    hallway_floors, hall_walls, all_walls = finalize_map(rooms, _hallway_h, _hallway_v)


def init_tutorial():
    global rooms, start_room, grid, hallway_floors, hall_walls, all_walls, player, _in_tutorial
    tut_rooms, tut_start         = build_tutorial()
    rooms, start_room            = tut_rooms, tut_start
    grid                         = {}
    hallway_floors, hall_walls, all_walls = finalize_map(rooms, _hallway_h, _hallway_v)
    player = Player(start_room.wx + ROOM_W // 2 - 16,
                    start_room.wy + ROOM_H // 2 - 16, speed=300)
    _in_tutorial = True


def init_game():
    global player, floor_num, sublevel, _in_tutorial
    _in_tutorial = False
    floor_num, sublevel = 1, 1
    _build_level()
    player = Player(start_room.wx + ROOM_W // 2 - 16,
                    start_room.wy + ROOM_H // 2 - 16, speed=300)
    stats.recorder.start_run()


def advance_level():
    global floor_num, sublevel, state
    sublevel += 1
    if sublevel > 3:
        sublevel = 1
        floor_num += 1
    if floor_num > 3:
        stats.recorder.end_run(cleared=True)
        floor_num, sublevel = 1, 1
        if save_exists():
            os.remove(SAVE_PATH)
        state = 'victory'
        return
    stats.recorder.set_floor(floor_num)
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
        hallway_floors, hall_walls, all_walls = load_game(_hallway_h, _hallway_v)
    stats.recorder.start_run()


# ── UI elements ───────────────────────────────────────────────────────────────
menu_buttons    = make_menu_buttons(font_lg, save_exists)
menu_btn_ig     = Button((SCREEN_W - 110, 8, 100, 30), "Menu", font_sm,
                         color=(50, 50, 70), hover=(80, 80, 110))
gameover_btn    = Button((SCREEN_W // 2 - 140, SCREEN_H // 2 + 40, 280, 55),
                         "Return to Menu", font_lg,
                         color=(80, 40, 40), hover=(120, 60, 60))
gameover_stats_btn = Button((SCREEN_W // 2 - 140, SCREEN_H // 2 + 110, 280, 55),
                             "View Stats", font_lg,
                             color=(40, 40, 80), hover=(60, 60, 120))
victory_btn     = Button((SCREEN_W // 2 - 140, SCREEN_H // 2 + 40, 280, 55),
                          "Return to Menu", font_lg,
                          color=(40, 80, 40), hover=(60, 120, 60))
victory_stats_btn = Button((SCREEN_W // 2 - 140, SCREEN_H // 2 + 110, 280, 55),
                            "View Stats", font_lg,
                            color=(40, 40, 80), hover=(60, 60, 120))
settings_overlay = SettingsOverlay(font_md, font_lg)
dev_console      = DevConsole()

# ── Main loop ─────────────────────────────────────────────────────────────────
running  = True
cur_room = None
while running:
    dt     = clock.tick(FPS) / 1000
    events = pygame.event.get()

    for event in events:
        if event.type == pygame.QUIT:
            if state == 'playing' and not _in_tutorial:
                write_save(player, rooms, floor_num, sublevel)
            running = False

        if state == 'menu':
            if menu_buttons[0].is_clicked(event):
                init_game()
                show_settings = show_buffs = False
                state = 'playing'
            elif menu_buttons[1].is_clicked(event):
                _do_load_game()
                show_settings = show_buffs = False
                state = 'playing'
            elif menu_buttons[2].is_clicked(event):
                init_tutorial()
                show_settings = show_buffs = False
                state = 'playing'
            elif menu_buttons[3].is_clicked(event):
                chart_data = stats.recorder.get_chart_data()
                state = 'stats'
            elif menu_buttons[4].is_clicked(event):
                running = False

        elif state == 'gameover':
            if gameover_btn.is_clicked(event):
                sound.stop_all()
                state = 'menu'
                menu_buttons = make_menu_buttons(font_lg, save_exists)
            elif gameover_stats_btn.is_clicked(event):
                chart_data = stats.recorder.get_chart_data()
                state = 'stats'

        elif state == 'victory':
            if victory_btn.is_clicked(event):
                sound.stop_all()
                state = 'menu'
                menu_buttons = make_menu_buttons(font_lg, save_exists)
            elif victory_stats_btn.is_clicked(event):
                chart_data = stats.recorder.get_chart_data()
                state = 'stats'

        elif state == 'stats':
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                sound.stop_all()
                state = 'menu'
                menu_buttons = make_menu_buttons(font_lg, save_exists)

        elif state == 'playing':
            shop = cur_room.shop if cur_room else None
            if event.type == pygame.KEYDOWN and event.key == pygame.K_BACKQUOTE:
                dev_console.toggle()
            elif dev_console.open:
                dev_console.handle_event(event, player)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    show_settings = not show_settings
                    show_buffs = False
                elif event.key == pygame.K_TAB:
                    show_buffs = not show_buffs
                    show_settings = False
                elif show_settings or show_buffs:
                    pass  # block other keys while overlays are open
                elif event.key == pygame.K_SPACE:
                    if not (shop and shop.open):
                        player.perform_parry()
                elif event.key == pygame.K_m:
                    show_map = not show_map
                elif event.key == pygame.K_e and shop:
                    shop.toggle()
                elif event.key == pygame.K_F1:
                    advance_level()
                    break
                elif event.key == pygame.K_F2 and sublevel == 3:
                    boss_room = next((r for r in rooms if r.is_boss), None)
                    if boss_room:
                        player.x = boss_room.wx + ROOM_W // 2 - 16
                        player.y = boss_room.wy + ROOM_H // 2 - 16
                        player.rect.topleft = (int(player.x), int(player.y))
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if show_settings:
                    settings_overlay.handle_event(event)
                elif menu_btn_ig.is_clicked(event):
                    if not _in_tutorial:
                        write_save(player, rooms, floor_num, sublevel)
                    _in_tutorial = False
                    sound.stop_music()
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
        gameover_stats_btn.draw(screen)
        pygame.display.flip()
        continue

    # ── Victory ───────────────────────────────────────────────────────────
    if state == 'victory':
        screen.fill((5, 15, 5))
        txt = font_xl.render("YOU WIN!", True, (80, 220, 80))
        screen.blit(txt, txt.get_rect(centerx=SCREEN_W // 2, y=SCREEN_H // 2 - 80))
        victory_btn.draw(screen)
        victory_stats_btn.draw(screen)
        pygame.display.flip()
        continue

    # ── Stats screen ──────────────────────────────────────────────────────
    if state == 'stats':
        draw_stats_screen(screen, chart_data, font_lg, font_md, font_sm)
        pygame.display.flip()
        continue

    # ── Playing update ────────────────────────────────────────────────────
    cam_x, cam_y = get_camera(player, SCREEN_W, SCREEN_H)
    player.handle_input(pygame.key.get_pressed(), dt, cam_x, cam_y)

    cur_room = current_room(player, rooms)
    if cur_room:
        cur_room.visited = True
        cur_room.try_lock(player.rect)

    if cur_room and cur_room.is_boss and not cur_room.is_cleared:
        sound.play_music('boss')
    elif cur_room and cur_room.event_type == 'shop':
        sound.play_music('shop')
    elif cur_room and cur_room.is_locked:
        sound.play_music('fight')
    else:
        sound.play_music('normal')

    lock_walls   = [w for r in rooms if r.is_locked for w in r.lock_walls]
    active_walls = all_walls + lock_walls

    resolve_walls(player, active_walls)
    player.update(dt)
    update_all(dt)
    update_notifications(dt)
    dev_console.update(dt)
    sound.update(dt)
    cam_x, cam_y = get_camera(player, SCREEN_W, SCREEN_H)

    if player.hp <= 0:
        if save_exists():
            os.remove(SAVE_PATH)
        stats.recorder.end_run(cleared=False)
        state = 'gameover'
        continue

    if cur_room:
        cur_room.update(player, dt, active_walls)
        if cur_room.gate and cur_room.gate.rect.colliderect(player.rect):
            if _in_tutorial:
                init_game()
                stats.recorder.start_run()
            else:
                advance_level()
            continue

    # ── Playing draw ──────────────────────────────────────────────────────
    screen.fill(BG_COLOR)

    for hx, hy, tmx, door_rooms in hallway_floors:
        horizontal = (tmx is _hallway_h)
        nw = HALLWAY_LEN if horizontal else DOOR_SIZE
        nh = DOOR_SIZE   if horizontal else HALLWAY_LEN
        skip = tuple(door_rooms.keys())
        screen.blit(tmx.render(nw, nh, skip_layers=skip), (hx - cam_x, hy - cam_y))
        for layer, ctrl_room in door_rooms.items():
            if ctrl_room and ctrl_room.is_locked:
                screen.blit(tmx.render_layer(layer, nw, nh), (hx - cam_x, hy - cam_y))

    for room in rooms:
        room.draw(screen, cam_x, cam_y)

    for bullet in player.deflected_bullets:
        bullet.draw(screen, cam_x, cam_y)

    player.draw(screen, cam_x, cam_y)
    draw_all(screen, font_sm, cam_x, cam_y)
    draw_notifications(screen, font_md, font_sm)

    draw_hud(screen, player, cur_room, floor_num, sublevel, font_md)
    menu_btn_ig.draw(screen)

    if cur_room and cur_room.is_boss and cur_room.enemies:
        draw_boss_bar(screen, cur_room.enemies[0], font_sm)

    if show_map:
        draw_minimap(screen, rooms, cur_room, font_md)

    if cur_room and cur_room.shop:
        cur_room.shop.draw(screen)
        cur_room.shop.draw_hint(screen, font_md)

    if _in_tutorial and isinstance(cur_room, TutorialRoom):
        cur_room.draw_hint(screen)

    if show_buffs:
        draw_buff_screen(screen, player, font_md, font_lg, font_sm)

    if show_settings:
        settings_overlay.draw(screen)

    dev_console.draw(screen)
    pygame.display.flip()

pygame.quit()
sys.exit()
