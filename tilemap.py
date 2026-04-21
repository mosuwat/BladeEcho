import pygame
import xml.etree.ElementTree as ET
import os

_render_cache = {}   # (abs_path, w, h, skip_tuple) → Surface
_edge_cache   = {}   # (abs_path, w, h, layer, edge) → Surface


class TileMap:
    def __init__(self, path):
        self.path   = os.path.abspath(path)
        self.map_w  = self.map_h  = 0
        self.tile_w = self.tile_h = 16
        self._tiles  = {}   # gid → Surface
        self.layers  = {}   # name → [[gid, ...], ...]
        self._parse()

    # ── Parsing ───────────────────────────────────────────────────────────────

    def _parse(self):
        tree = ET.parse(self.path)
        root = tree.getroot()
        self.map_w  = int(root.get('width'))
        self.map_h  = int(root.get('height'))
        self.tile_w = int(root.get('tilewidth'))
        self.tile_h = int(root.get('tileheight'))

        for ts_elem in root.findall('tileset'):
            fgid = int(ts_elem.get('firstgid'))
            src  = ts_elem.get('source')
            if src:
                tsx = os.path.normpath(
                    os.path.join(os.path.dirname(self.path), src))
                self._load_tsx(fgid, tsx)

        for layer in root.findall('layer'):
            name = layer.get('name')
            raw  = layer.find('data').text.strip()
            gids = [int(g) for g in raw.split(',')]
            self.layers[name] = [
                gids[r * self.map_w:(r + 1) * self.map_w]
                for r in range(self.map_h)
            ]

    def _load_tsx(self, firstgid, tsx_path):
        try:
            tree = ET.parse(tsx_path)
            root = tree.getroot()
            tw = int(root.get('tilewidth',  self.tile_w))
            th = int(root.get('tileheight', self.tile_h))
            img = root.find('image')
            if img is None:
                return
            src      = img.get('source')
            img_path = os.path.normpath(
                os.path.join(os.path.dirname(tsx_path), src))
            sheet    = pygame.image.load(img_path).convert_alpha()
            cols     = sheet.get_width()  // tw
            rows_cnt = sheet.get_height() // th
            for r in range(rows_cnt):
                for c in range(cols):
                    gid = firstgid + r * cols + c
                    self._tiles[gid] = sheet.subsurface(c * tw, r * th, tw, th)
        except Exception:
            pass   # tileset unavailable; tiles render as nothing (fallback colour shows)

    # ── Rendering ─────────────────────────────────────────────────────────────

    def render(self, width, height, skip_layers=()):
        """Return a Surface of size (width, height) with all layers blitted.
        Result is cached — safe to call every frame."""
        key = (self.path, width, height, tuple(sorted(skip_layers)))
        if key in _render_cache:
            return _render_cache[key]

        surf = pygame.Surface((width, height))
        surf.fill((45, 45, 50))   # fallback floor colour

        if self._tiles:
            sx = width  / (self.map_w * self.tile_w)
            sy = height / (self.map_h * self.tile_h)
            tw = max(1, int(self.tile_w * sx))
            th = max(1, int(self.tile_h * sy))
            for name, layer in self.layers.items():
                if name in skip_layers:
                    continue
                for r, row in enumerate(layer):
                    for c, gid in enumerate(row):
                        if gid == 0:
                            continue
                        tile = self._tiles.get(gid)
                        if tile is None:
                            continue
                        scaled = pygame.transform.scale(tile, (tw, th))
                        surf.blit(scaled,
                                  (int(c * self.tile_w * sx),
                                   int(r * self.tile_h * sy)))

        _render_cache[key] = surf
        return surf

    def get_frames(self, frame_tile_w=1):
        """Extract animation frames. Each frame is frame_tile_w tiles wide × map_h tiles tall.
        Returns a list of SRCALPHA Surfaces at natural tile size."""
        layer = next(iter(self.layers.values()), [])
        n_frames = self.map_w // frame_tile_w
        fw = frame_tile_w * self.tile_w
        fh = self.map_h    * self.tile_h
        frames = []
        for fi in range(n_frames):
            surf = pygame.Surface((fw, fh), pygame.SRCALPHA)
            for r, row in enumerate(layer):
                for fc in range(frame_tile_w):
                    c = fi * frame_tile_w + fc
                    if c >= len(row):
                        continue
                    gid = row[c] if c < len(row) else 0
                    if gid == 0:
                        continue
                    tile = self._tiles.get(gid)
                    if tile:
                        surf.blit(tile, (fc * self.tile_w, r * self.tile_h))
            frames.append(surf)
        return frames

    # ── Collision rect helpers ────────────────────────────────────────────────

    def tile_rects(self, layer_name, ox, oy, width=None, height=None):
        """Return collision rects for all non-zero tiles in layer_name.
        If width/height given, tiles are scaled to fit that render size."""
        layer = self.layers.get(layer_name, [])
        rects = []
        if width and height:
            sx = width  / (self.map_w * self.tile_w)
            sy = height / (self.map_h * self.tile_h)
            tw = max(1, int(self.tile_w * sx))
            th = max(1, int(self.tile_h * sy))
        else:
            sx, sy = 1.0, 1.0
            tw, th = self.tile_w, self.tile_h
        for r, row in enumerate(layer):
            for c, gid in enumerate(row):
                if gid == 0:
                    continue
                rects.append(pygame.Rect(
                    ox + int(c * self.tile_w * sx),
                    oy + int(r * self.tile_h * sy),
                    tw, th))
        return rects

    def render_layer(self, layer_name, width, height):
        """Return a cached SRCALPHA surface containing only *layer_name*."""
        key = (self.path, width, height, layer_name)
        if key in _edge_cache:
            return _edge_cache[key]

        surf = pygame.Surface((width, height), pygame.SRCALPHA)
        layer = self.layers.get(layer_name, [])
        if layer and self._tiles:
            sx = width  / (self.map_w * self.tile_w)
            sy = height / (self.map_h * self.tile_h)
            tw = max(1, int(self.tile_w * sx))
            th = max(1, int(self.tile_h * sy))
            for r, row in enumerate(layer):
                for c, gid in enumerate(row):
                    if gid == 0:
                        continue
                    tile = self._tiles.get(gid)
                    if tile is None:
                        continue
                    surf.blit(pygame.transform.scale(tile, (tw, th)),
                              (int(c * self.tile_w * sx), int(r * self.tile_h * sy)))

        _edge_cache[key] = surf
        return surf

    # ── Door rect helpers ─────────────────────────────────────────────────────

    def door_rects_by_edge(self, layer_name, ox, oy, width, height):
        """Return door tile rects from *layer_name* grouped by edge letter.
        Tiles on col 0 → W, col map_w-1 → E,
        top half (non-edge cols) → N, bottom half → S."""
        layer = self.layers.get(layer_name, [])
        edges = {'N': [], 'S': [], 'W': [], 'E': []}
        if not layer:
            return edges

        sx   = width  / (self.map_w * self.tile_w)
        sy   = height / (self.map_h * self.tile_h)
        tw   = max(1, int(self.tile_w * sx))
        th   = max(1, int(self.tile_h * sy))
        mid  = self.map_h // 2

        for r, row in enumerate(layer):
            for c, gid in enumerate(row):
                if gid == 0:
                    continue
                rect = pygame.Rect(
                    ox + int(c * self.tile_w * sx),
                    oy + int(r * self.tile_h * sy),
                    tw, th)
                if c == 0:
                    edges['W'].append(rect)
                elif c == self.map_w - 1:
                    edges['E'].append(rect)
                elif r < mid:
                    edges['N'].append(rect)
                else:
                    edges['S'].append(rect)

        return edges


# ── Module-level helpers ──────────────────────────────────────────────────────

_loaded = {}   # abs_path → TileMap

def load(path):
    """Load (and cache) a TileMap by file path."""
    p = os.path.abspath(path)
    if p not in _loaded:
        _loaded[p] = TileMap(p)
    return _loaded[p]
