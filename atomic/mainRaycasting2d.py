"""
inspired by ghast's work

check:
https://github.com/davidpendergast/pygame-web

"""

############## game.py ##############
# TODO web exports only support a single src file right now (I think)... so everything is slapped into one mega file


import katagames_sdk as katasdk

import time
import collections
kataen = katasdk.engine
pygame = kataen.import_pygame()
EventReceiver = kataen.EventReceiver
EngineEvTypes = kataen.EngineEvTypes


class Game:
    """Base class for games."""

    def __init__(self, track_fps=True):
        self._fps_n_frames = 10 if track_fps else 0
        self._fps_tracker_logic = collections.deque()
        self._fps_tracker_rendering = collections.deque()
        self._tick = 0

        self._cached_info_text = None
        self._info_font = None

    def start(self):
        """Starts the game loop. This method will not exit until the game has finished execution."""
        kataen.init(self._get_mode_internal())

        li_recv = [kataen.get_game_ctrl(), self.build_controller()]
        for recv_obj in li_recv:
            recv_obj.turn_on()

        self.pre_update()

        li_recv[0].loop()
        kataen.cleanup()

    def get_mode(self) -> str:
        """returns: "HD', 'OLD_SCHOOL', or 'SUPER_RETRO'"""
        return 'OLD_SCHOOL'

    def is_running_in_web(self) -> bool:
        return kataen.runs_in_web()

    def get_screen_size(self):
        return kataen.get_screen().get_size()

    def get_tick(self) -> int:
        return self._tick

    def pre_update(self):
        pass

    def render(self, screen):
        raise NotImplementedError()

    def update(self, events, dt):
        raise NotImplementedError()

    def render_text(self, screen, text, size=12, pos=(0, 0), color=(255, 255, 255), bg_color=None):
        if self._info_font is None or self._info_font.get_height() != size:
            self._info_font = pygame.font.Font(None, size)
        lines = text.split("\n")
        y = pos[1]
        for l in lines:
            surf = self._info_font.render(l, True, color, bg_color)
            screen.blit(surf, (pos[0], y))
            y += surf.get_height()

    def get_fps(self, logical=True) -> float:
        q = self._fps_tracker_logic if logical else self._fps_tracker_rendering
        if len(q) <= 1:
            return 0
        else:
            total_time_secs = q[-1] - q[0]
            n_frames = len(q)
            if total_time_secs <= 0:
                return float('inf')
            else:
                return (n_frames - 1) / total_time_secs

    def _render_internal(self, screen):
        if self._fps_n_frames > 0:
            self._fps_tracker_rendering.append(time.time())
            if len(self._fps_tracker_rendering) > self._fps_n_frames:
                self._fps_tracker_rendering.popleft()
        self.render(screen)

    def _update_internal(self, events, dt):
        if self._fps_n_frames > 0:
            self._fps_tracker_logic.append(time.time())
            if len(self._fps_tracker_logic) > self._fps_n_frames:
                self._fps_tracker_logic.popleft()
        self.update(events, dt)
        self._tick += 1

    def _get_mode_internal(self):
        mode_str = self.get_mode().upper()
        if mode_str == 'HD':
            return kataen.HD_MODE
        elif mode_str == 'OLD_SCHOOL':
            return kataen.OLD_SCHOOL_MODE
        elif mode_str == 'SUPER_RETRO':
            return kataen.SUPER_RETRO_MODE
        else:
            raise ValueError("Unrecognized mode: {}".format(mode_str))

    class _GameViewController(EventReceiver):
        def __init__(self, game):
            super().__init__()
            self._game = game
            self._event_queue = []
            self._last_update_time = time.time()

        def proc_event(self, ev, source):
            if ev.type == EngineEvTypes.PAINT:
                self._game._render_internal(ev.screen)
            elif ev.type == EngineEvTypes.LOGICUPDATE:
                cur_time = ev.curr_t
                self._game._update_internal(self._event_queue, cur_time - self._last_update_time)
                self._last_update_time = cur_time
                self._event_queue.clear()
            else:
                self._event_queue.append(ev)

    def build_controller(self) -> EventReceiver:
        return Game._GameViewController(self)


############## game.py ##############

############## raycaster.py ##############

import math
import random


class Vector2:
    # TODO pygame.Vector2 doesn't seem to be supported yet. So I made my own >:(

    def __init__(self, x, y=0.0):
        if isinstance(x, Vector2):
            self.x = x.x
            self.y = x.y
        else:
            self.x = x
            self.y = y

    def __getitem__(self, idx):
        if idx == 0:
            return self.x
        else:
            return self.y

    def __len__(self):
        return 2

    def __iter__(self):
        return (v for v in (self.x, self.y))

    def __add__(self, other: 'Vector2'):
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: 'Vector2'):
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, other: float):
        return Vector2(self.x * other, self.y * other)

    def __neg__(self):
        return Vector2(-self.x, -self.y)

    def __eq__(self, other: 'Vector2'):
        return self.x == other.x and self.y == other.y

    def __hash__(self):
        return hash((self.x, self.y))

    def rotate_ip(self, degrees):
        theta = math.radians(degrees)
        cs = math.cos(theta)
        sn = math.sin(theta)
        x = self.x * cs - self.y * sn
        y = self.x * sn + self.y * cs
        self.x = x
        self.y = y

    def rotate(self, degrees):
        res = Vector2(self)
        res.rotate_ip(degrees)
        return res

    def to_ints(self):
        return Vector2(int(self.x), int(self.y))

    def length(self):
        return math.sqrt(self.x * self.x + self.y * self.y)

    def length_squared(self):
        return self.x * self.x + self.y * self.y

    def scale_to_length(self, length):
        cur_length = self.length()
        if cur_length == 0 and length != 0:
            raise ValueError("Cannot scale vector with length 0")
        else:
            mult = length / cur_length
            self.x *= mult
            self.y *= mult


class RayEmitter:

    def __init__(self, xy, direction, fov, n_rays, max_depth=100):
        self.xy = xy
        self.direction = direction
        self.fov = fov
        self.n_rays = max(n_rays, 3)
        self.max_depth = max_depth

    def get_rays(self):
        left_ray = self.direction.rotate(-self.fov / 2)
        for i in range(self.n_rays):
            yield left_ray.rotate((i + 0.5) * self.fov / self.n_rays)


class RayCastPlayer(RayEmitter):

    def __init__(self, xy, direction, fov, n_rays, max_depth=100):
        super().__init__(xy, direction, fov, n_rays, max_depth=max_depth)
        self.move_speed = 75  # units per second
        self.turn_speed = 160

    def move(self, forward, strafe, dt):
        if forward != 0:
            self.xy = self.xy + self.direction * forward * self.move_speed * dt

        if strafe != 0:
            right = self.direction.rotate(90)
            self.xy = self.xy + right * strafe * self.move_speed * dt

    def turn(self, direction, dt):
        self.direction.rotate_ip(direction * self.turn_speed * dt)


class RayCastWorld:

    def __init__(self, grid_dims, cell_size, bg_color=(0, 0, 0)):
        self.grid = []
        for _ in range(grid_dims[0]):
            self.grid.append([None] * grid_dims[1])
        self.cell_size = cell_size
        self.bg_color = bg_color

    def randomize(self, chance=0.2, n_colors=5):
        colors = []
        for _ in range(n_colors):
            colors.append((random.randint(50, 255),
                           random.randint(50, 255),
                           random.randint(50, 255)))
        for xy in self.all_cells():
            if random.random() < chance:
                color = random.choice(colors)
                self.set_cell(xy, color)
        return self

    def set_cell(self, xy, color):
        self.grid[xy[0]][xy[1]] = color

    def get_cell(self, xy):
        return self.grid[xy[0]][xy[1]]

    def get_cell_coords_at(self, x, y):
        return (int(x / self.cell_size), int(y / self.cell_size))

    def get_cell_value_at(self, x, y):
        coords = self.get_cell_coords_at(x, y)
        return self.get_cell(coords)

    def all_cells(self, in_rect=None):
        dims = self.get_dims()
        x_min = 0 if in_rect is None else max(0, int(in_rect[0] / self.cell_size))
        y_min = 0 if in_rect is None else max(0, int(in_rect[1] / self.cell_size))
        x_max = dims[0] if in_rect is None else min(dims[0], int((in_rect[0] + in_rect[2]) / self.cell_size) + 1)
        y_max = dims[1] if in_rect is None else min(dims[1], int((in_rect[1] + in_rect[3]) / self.cell_size) + 1)
        for x in range(x_min, x_max):
            for y in range(y_min, y_max):
                yield (x, y)

    def get_dims(self):
        if len(self.grid) == 0:
            return (0, 0)
        else:
            return (len(self.grid), len(self.grid[0]))

    def get_size(self):
        dims = self.get_dims()
        return (dims[0] * self.cell_size, dims[1] * self.cell_size)

    def get_width(self):
        return self.get_size()[0]

    def get_height(self):
        return self.get_size()[1]


class RayState:
    """The state of a single ray."""
    def __init__(self, start, end, ray, color):
        self.start = start
        self.end = end
        self.ray = ray
        self.color = color

    def dist(self):
        if self.end is None:
            return float('inf')
        else:
            return (self.end - self.start).length()


class RayCastState:

    def __init__(self, player: RayCastPlayer, world: RayCastWorld):
        self.player = player
        self.world = world

        self.ray_states = []

    def update_ray_states(self):
        self.ray_states.clear()
        for ray in self.player.get_rays():
            self.ray_states.append(self.cast_ray(self.player.xy, ray, self.player.max_depth))

    def cast_ray(self, start_xy, ray, max_dist) -> RayState:
        # yoinked from https://theshoemaker.de/2016/02/ray-casting-in-2d-grids/
        dirSignX = ray[0] > 0 and 1 or -1
        dirSignY = ray[1] > 0 and 1 or -1

        tileOffsetX = (ray[0] > 0 and 1 or 0)
        tileOffsetY = (ray[1] > 0 and 1 or 0)

        curX, curY = start_xy[0], start_xy[1]
        tileX, tileY = self.world.get_cell_coords_at(curX, curY)
        t = 0

        gridW, gridH = self.world.get_dims()
        cell_size = self.world.cell_size

        maxX = start_xy[0] + ray[0] * max_dist
        maxY = start_xy[1] + ray[1] * max_dist

        if ray.length() > 0:
            while ((0 <= tileX < gridW and 0 <= tileY < gridH)
                   and (curX <= maxX if ray[0] >= 0 else curX >= maxX)
                   and (curY <= maxY if ray[1] >= 0 else curY >= maxY)):

                color_at_cur_xy = self.world.get_cell((tileX, tileY))
                if color_at_cur_xy is not None:
                    return RayState(start_xy, Vector2(curX, curY), ray, color_at_cur_xy)

                dtX = float('inf') if ray[0] == 0 else ((tileX + tileOffsetX) * cell_size - curX) / ray[0]
                dtY = float('inf') if ray[1] == 0 else ((tileY + tileOffsetY) * cell_size - curY) / ray[1]

                if dtX < dtY:
                    t = t + dtX
                    tileX = tileX + dirSignX
                else:
                    t = t + dtY
                    tileY = tileY + dirSignY

                curX = start_xy[0] + ray[0] * t
                curY = start_xy[1] + ray[1] * t

        return RayState(start_xy, None, ray, None)


def lerp(v1, v2, a):
    if isinstance(v1, float) or isinstance(v1, int):
        return v1 + a * (v2 - v1)
    else:
        return tuple(lerp(v1[i], v2[i], a) for i in range(len(v1)))


def bound(v, lower, upper):
    if isinstance(v, float) or isinstance(v, int):
        if v > upper:
            return upper
        elif v < lower:
            return lower
        else:
            return v
    else:
        return tuple(bound(v[i], lower, upper) for i in range(len(v)))


def round_tuple(v):
    return tuple(round(v[i]) for i in range(len(v)))


def lerp_color(c1, c2, a):
    return bound(round_tuple(lerp(c1, c2, a)), 0, 255)


class RayCastRenderer:

    def __init__(self):
        pass

    def render(self, screen, state: RayCastState):
        p_xy = state.player.xy

        cs = state.world.cell_size
        screen_size = screen.get_size()
        cam_offs = Vector2(-p_xy[0] + screen_size[0] // 2,
                           -p_xy[1] + screen_size[1] // 2)

        bg_color = lerp_color(state.world.bg_color, (255, 255, 255), 0.05)

        for r in state.ray_states:
            color = r.color if r.color is not None else bg_color
            if r.end is not None:
                color = lerp_color(color, bg_color, r.dist() / state.player.max_depth)
                pygame.draw.line(screen, color, r.start + cam_offs, r.end + cam_offs)
            else:
                pygame.draw.line(screen, color, r.start + cam_offs, r.start + r.ray * state.player.max_depth + cam_offs)

        camera_rect = [p_xy[0] - screen_size[0] // 2, p_xy[1] - screen_size[1] // 2, screen_size[0], screen_size[1]]

        for xy in state.world.all_cells(in_rect=camera_rect):
            color = state.world.get_cell(xy)
            if color is not None:
                r = [xy[0] * cs + cam_offs[0], xy[1] * cs + cam_offs[1], cs, cs]
                pygame.draw.rect(screen, color, r)


class RayCasterGame(Game):

    def __init__(self):
        super().__init__()
        self.state = None
        self.renderer = RayCastRenderer()
        self.show_fps = True

    def _build_initial_state(self):
        w = RayCastWorld(self.get_screen_size(), 16).randomize()
        xy = Vector2(w.get_width() / 2, w.get_height() / 2)
        direction = Vector2(0, 1)
        p = RayCastPlayer(xy,
                          direction,
                          60,
                          25, max_depth=200)
        return RayCastState(p, w)

    def get_mode(self):
        return 'SUPER_RETRO'

    def update(self, events, dt):
        if self.state is None:
            self.state = self._build_initial_state()
        if self.get_tick() % 20 == 0:
            dims = self.get_screen_size()
            cap = "Raycaster (DIMS={}, FPS={:.1f})".format(dims, self.get_fps(logical=False))
            pygame.display.set_caption(cap)

        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_r:
                    print("Reseting!")
                    self.state = self._build_initial_state()

        pressed = pygame.key.get_pressed()

        turn = 0
        if pressed[pygame.K_q] or pressed[pygame.K_LEFT]:
            turn -= 1
        if pressed[pygame.K_e] or pressed[pygame.K_RIGHT]:
            turn += 1

        forward = 0
        if pressed[pygame.K_w] or pressed[pygame.K_UP]:
            forward += 1
        if pressed[pygame.K_s] or pressed[pygame.K_DOWN]:
            forward -= 1

        strafe = 0
        if pressed[pygame.K_a]:
            strafe -= 1
        if pressed[pygame.K_d]:
            strafe += 1

        self.state.player.turn(turn, dt)
        self.state.player.move(forward, strafe, dt)
        self.state.update_ray_states()

    def render(self, screen):
        screen.fill((0, 0, 0))
        self.renderer.render(screen, self.state)

        if self.show_fps:
            fps_text = "FPS {:.1f}".format(self.get_fps(logical=False))
            self.render_text(screen, fps_text, bg_color=(0, 0, 0), size=16)

############## raycaster.py ##############

############## main.py ##############


def run_game():
    """Entry point for packaged web runs"""
    g = RayCasterGame()
    g.start()


if __name__ == '__main__':
    """Entry point for offline runs"""
    run_game()

############## main.py ##############
