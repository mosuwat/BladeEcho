import pygame
import os

_DIR           = os.path.join(os.path.dirname(__file__), 'Sound')
_sounds        = {}
_current_music = None
_pending_music = None
_fading_out    = False
_fade_timer    = 0.0

_FADE_OUT_MS = 600
_FADE_IN_MS  = 800

SFX_VOL   = 1.0   # 0.0 – 1.0
MUSIC_VOL = 0.5   # 0.0 – 1.0


def _trim_sound(path, skip_seconds):
    snd  = pygame.mixer.Sound(path)
    freq, _, _ = pygame.mixer.get_init()
    skip = int(freq * skip_seconds)
    arr  = pygame.sndarray.array(snd)
    if skip < len(arr):
        arr = arr[skip:]
    return pygame.sndarray.make_sound(arr)


def _load():
    global _sounds
    if _sounds:
        return

    def s(name, rel):
        try:
            snd = pygame.mixer.Sound(os.path.join(_DIR, rel))
            snd.set_volume(SFX_VOL)
            _sounds[name] = snd
        except Exception:
            pass

    def st(name, rel, skip):
        try:
            snd = _trim_sound(os.path.join(_DIR, rel), skip)
            snd.set_volume(SFX_VOL)
            _sounds[name] = snd
        except Exception:
            s(name, rel)   # fall back to untrimmed

    s('arrow_shot',        'ArrowShot.mp3')
    s('hit_normal',        'hit/normalHit.mp3')
    s('hit_slime',         'hit/slimeHit.mp3')
    s('hit_weaken',        'hit/weakenHit.mp3')
    s('parry_melee',       'parry/Meleeparry.mp3')
    st('parry_projectile', 'parry/ProjectileParry.mp3', 1.0)


def play(name):
    _load()
    snd = _sounds.get(name)
    if snd:
        snd.play()


def play_music(track):
    global _current_music, _pending_music, _fading_out, _fade_timer
    paths = {
        'normal': 'backgroundMusic/Normal.mp3',
        'fight':  'backgroundMusic/FightNormal.mp3',
        'boss':   'backgroundMusic/FightBoss.mp3',
        'shop':   'backgroundMusic/Shop.mp3',
    }
    path = os.path.join(_DIR, paths[track])
    if (_current_music == path and not _fading_out) or _pending_music == path:
        return
    _pending_music = path
    if _current_music is None:
        # First track — fade in only, no fade out needed
        _current_music = path
        _pending_music = None
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(MUSIC_VOL)
        pygame.mixer.music.play(-1, fade_ms=_FADE_IN_MS)
    elif not _fading_out:
        _fading_out = True
        _fade_timer = _FADE_OUT_MS / 1000.0
        pygame.mixer.music.fadeout(_FADE_OUT_MS)


def update(dt):
    global _current_music, _pending_music, _fading_out, _fade_timer
    if not _fading_out:
        return
    _fade_timer -= dt
    if _fade_timer <= 0:
        _fading_out = False
        if _pending_music:
            _current_music = _pending_music
            _pending_music = None
            pygame.mixer.music.load(_current_music)
            pygame.mixer.music.set_volume(MUSIC_VOL)
            pygame.mixer.music.play(-1, fade_ms=_FADE_IN_MS)
