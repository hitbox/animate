import argparse
import contextlib
import itertools as it
import math
import os
import random

from collections import deque
from functools import singledispatch

with contextlib.redirect_stdout(open(os.devnull, 'w')):
    import pygame

class Animation:

    def __init__(
        self,
        durations,
        *values,
        lerpfunc = None,
        iterfunc = iter,
        **extra,
    ):
        self.durations = durations
        self.values = values
        if lerpfunc is None:
            lerpfunc = lerp
        self.lerpfunc = lerpfunc
        self.iterfunc = iterfunc
        self.__dict__.update(extra)
        #
        self.start()

    def start(self):
        self.frame = 0
        pairs = nwise(self.values)
        pairs = map(list, pairs)
        self.pairs = self.iterfunc(pairs)
        self.running = True
        self.next_pair()

    def next_pair(self):
        self.a, self.b = next(self.pairs)
        self.current_duration = next(self.durations)
        if hasattr(self, 'next_callback'):
            self.next_callback(self)

    def value(self):
        time = self.frame / self.current_duration
        return self.lerpfunc(self.a, self.b, time)

    def update(self, advance=1):
        if self.frame < self.current_duration:
            self.frame += advance
        elif self.frame >= self.current_duration:
            try:
                self.next_pair()
            except StopIteration:
                self.running = False
            else:
                self.frame = 0


class circlerp:

    def __init__(self, center, radius):
        self.centerx, self.centery = center
        self.radius = radius

    def __call__(self, start_angle, end_angle, time):
        angle = lerp(start_angle, end_angle, time)
        x = self.centerx + math.cos(angle) * self.radius
        y = self.centery - math.sin(angle) * self.radius
        return (x, y)


class wavey_y:

    def __init__(self, radius, centery, waves=1):
        self.radius = radius
        self.centery = centery
        self.waves = waves

    def __call__(self, position1, position2, time):
        x1, y1 = position1
        x2, y2 = position2
        x = lerp(x1, x2, time)
        time_to_x = invlerp(x1, x2, x)
        y = self.centery + math.sin(time_to_x * math.tau * self.waves) * self.radius
        return (x, y)


class AnimateDemo:

    def __init__(
        self,
        *,
        screen_size,
        frames_path = None,
        no_gui = False,
        repeat = False,
        background = None,
        debug_actor = False,
    ):
        self.screen_size = screen_size
        self.frames_path = frames_path
        self.show_gui = not no_gui
        self.repeat = repeat
        self.background_path = background
        self.debug_actor = debug_actor
        #
        self.frame_counter = it.count()
        self.animation = None
        self.reset()

    def reset(self):
        self.trail = deque(maxlen=60)
        self.trail_color1 = pygame.Color('#C33764')
        self.trail_color2 = pygame.Color('#1D2671')
        #
        self.running = False

    def events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    post_quit()

    def next_animation(self):
        try:
            self.animation = next(self.animations)
        except StopIteration:
            self.animation = None
        else:
            self.animation.start()

    def update(self):
        self.actor_animation.update()

        if self.animation:
            self.animation.update()
            setattr(self.rect, self.animation.attr, self.animation.value())
            self.trail.append(self.rect.center)
            if not self.animation.running:
                self.next_animation()
        elif self.trail:
            self.trail.popleft()
        else:
            post_quit()

    def draw(self):
        self.screen.blit(self.background, (0,)*2)

        self.screen.blit(self.actor_animation.value(), self.rect)

        ntrail = len(self.trail)
        if ntrail > 1:
            for index, (p1, p2) in enumerate(nwise(self.trail)):
                t = invlerp(0, ntrail, index)
                c = lerp(self.trail_color1, self.trail_color2, t)
                pygame.draw.line(self.screen, c, p1, p2)

        if self.show_gui:
            string = f'{self.clock.get_fps():.2f}'
            fps_text = self.gui_font.render(string, True, (200,)*3)
            fps_rect = fps_text.get_rect(bottomright = self.gui_frame.bottomright)
            self.screen.blit(fps_text, fps_rect)

            if self.debug_actor:
                string = (
                    f'{self.actor_animation.frame:03d}'
                    f' / {self.actor_animation.current_duration:03d}'
                )
                actor_text = self.huge_font.render(string, True, self.actor_animation.actor_color)
                actor_rect = actor_text.get_rect(midtop = self.rect.midbottom)
                self.screen.blit(actor_text, actor_rect)

            pygame.display.flip()

        if self.frames_path:
            filename = self.frames_path % (next(self.frame_counter),)
            pygame.image.save(self.screen, filename)
            print(f'saved: {filename}')

    def run(self):
        self.running = True
        while self.running:
            if self.show_gui:
                self.clock.tick(self.fps)
            self.events()
            self.update()
            self.draw()

    def start(self, actor_animation, rect, animations):
        self.actor_animation = actor_animation
        self.rect = rect
        self.animations = animations

        if not self.show_gui:
            get_screen = pygame.Surface
        else:
            get_screen = pygame.display.set_mode

        if self.background_path:
            self.background = pygame.image.load(self.background_path)
            self.screen = get_screen(self.background.get_size())
        else:
            self.screen = get_screen(self.screen_size)
            self.background = self.screen.copy()

        self.window = self.screen.get_rect()

        if self.show_gui:
            self.gui_frame = self.window.inflate(-20,-20)
            self.gui_font = pygame.font.Font(None, 40)

            self.huge_font = pygame.font.Font(None, 80)

            help_text = self.gui_font.render('Press Q or Escape to quit', True, (200,)*3)
            help_rect = help_text.get_rect(topright=self.gui_frame.topright)
            self.background.blit(help_text, help_rect)

            if self.repeat:
                help_text = self.gui_font.render('Repeating endlessly', True, (200,)*3)
                help_rect = help_text.get_rect(topright=help_rect.bottomright)
                self.background.blit(help_text, help_rect)

        self.clock = pygame.time.Clock()
        self.fps = 60

        self.next_animation()
        self.run()


def draw_crosshairs(
    surf,
    color,
    cross_divisor = 4,
    line_width = 1,
    rect = None,
):
    """
    Draw a box with crosshairs on a surface.
    """
    if rect is None:
        rect = surf.get_rect()
    rect_hline = [
        (rect.centerx, rect.centery - rect.height / cross_divisor),
        (rect.centerx, rect.centery + rect.height / cross_divisor),
    ]
    rect_vline = [
        (rect.centerx - rect.width / cross_divisor, rect.centery),
        (rect.centerx + rect.width / cross_divisor, rect.centery),
    ]
    pygame.draw.line(surf, color, rect_hline[0], rect_hline[1], line_width)
    pygame.draw.line(surf, color, rect_vline[0], rect_vline[1], line_width)

def _lerp(a, b, t):
    return a * (1 - t) + b * t

@singledispatch
def lerp(a, b, t):
    pass

@lerp.register
def _(a:int, b:int, t):
    return _lerp(a, b, t)

@lerp.register
def _(a:float, b:float, t):
    return _lerp(a, b, t)

@lerp.register
def _(a:tuple, b:tuple, t):
    return tuple(lerp(item1, item2, t) for item1, item2 in zip(a, b))

@lerp.register
def _(a:pygame.Color, b:pygame.Color, t):
    rgba = (lerp(rgba1, rgba2, t) for rgba1, rgba2 in zip(a, b))
    return pygame.Color(*map(int, rgba))

@lerp.register
def _(a:pygame.Surface, b:pygame.Surface, t):
    if t > .5:
        return b
    else:
        return a

def _invlerp(a, b, x):
    return (x - a) / (b - a)

@singledispatch
def invlerp(a, b, x):
    pass

@invlerp.register
def _(a:int, b:int, x):
    return _invlerp(a, b, x)

@invlerp.register
def _(a:tuple, b:tuple, x):
    return tuple(_invlerp(i1, i2, t) for i1, i2 in zip(a, b))

def get_rect(rect, **kwargs):
    rect = rect.copy()
    for k, v in kwargs.items():
        setattr(rect, k, v)
    return rect

def nwise(iterable, n=2):
    """
    Take iterable in overlapping n-wise fashion, defaulting to 2-pairs.
    """
    pairs = it.tee(iterable, n)
    for index, pair in enumerate(pairs):
        for _ in range(index):
            next(pair)
    return zip(*pairs)

def post_quit():
    pygame.event.post(pygame.event.Event(pygame.QUIT))

def build_animations(rect, window, repeat=False):
    # TODO: duration per pair or repeat the one given
    duration = 1000 # milliseconds as in accumulating clock.tick
    number_frames = it.repeat(60)
    radius = 300

    animate_center_to_right = Animation(
        number_frames,
        rect.topleft,
        get_rect(rect, centerx=window.centerx + radius).topleft,
        attr = 'topleft',
    )

    animate_circle_ccw = Animation(
        it.repeat(60 * 2),
        0,
        math.tau,
        lerpfunc = circlerp(window.center, radius),
        attr = 'center',
    )

    animate_right_to_left = Animation(
        number_frames,
        get_rect(rect, centerx=window.centerx + radius).topleft,
        get_rect(rect, centerx=window.centerx - radius).topleft,
        attr = 'topleft',
    )

    animate_wavey_right_to_left = Animation(
        it.repeat(60 * 2),
        get_rect(rect, centerx=window.centerx + radius).center,
        get_rect(rect, centerx=window.centerx - radius).center,
        lerpfunc = wavey_y(
            radius / 2,
            window.centery,
            waves = 3,
        ),
        attr = 'center',
    )

    animate_circle_cw = Animation(
        it.repeat(60 * 2),
        math.pi,
        -math.pi,
        lerpfunc = circlerp(window.center, radius),
        attr = 'center',
    )

    animate_left_to_center = Animation(
        number_frames,
        get_rect(rect, centerx=window.centerx - radius).topleft,
        rect.topleft,
        attr = 'topleft',
    )

    animations = [
        animate_center_to_right,
        animate_wavey_right_to_left,
        animate_circle_cw,
        animate_left_to_center,
    ]

    if repeat:
        animation_iterator = it.cycle
    else:
        animation_iterator = iter

    animations = animation_iterator(animations)
    return animations

def main(args):
    """
    """
    pygame.display.init()
    pygame.font.init()

    if args.background:
        bg = pygame.image.load(args.background)
        window_size = bg.get_size()
        # TODO: close this file?
    else:
        window_size = args.size

    window = pygame.Rect((0,0), window_size)

    actor_colors = it.cycle([
        pygame.Color('red'),
        pygame.Color('green'),
        pygame.Color('blue'),
    ])
    def actor_color_callback(animation):
        animation.actor_color = next(actor_colors)

    def hold(a, b, t):
        return a

    surfaces = list(map(pygame.image.load, args.actor))
    actor_animation = Animation(
        it.cycle([
            30, # 0 -> 1, open eyes
            15, # 1 -> 2, half shut
            15, # 2 -> 0, open immediately
        ]),
        *(surfaces + [surfaces[-1]]),
        iterfunc = it.cycle,
        lerpfunc = hold,
        next_callback = actor_color_callback,
    )
    sizes = (surf.get_size() for surf in surfaces)
    widths, heights = zip(*sizes)
    rect = pygame.Rect((0,0), (max(widths), max(heights)))

    rect.center = window.center
    animations = build_animations(rect, window, repeat=args.repeat)

    demo = AnimateDemo(
        screen_size = window.size,
        frames_path = args.output,
        no_gui = args.no_gui,
        repeat = args.repeat,
        background = args.background,
    )
    demo.start(actor_animation, rect, animations)

def sizetype(string):
    """
    Tuple of integers separated by whitespace or commas.
    """
    return tuple(map(int, string.replace(',', ' ').split()))

def cli(argv=None):
    """
    animate
    """
    parser = argparse.ArgumentParser(
        description = cli.__doc__,
    )
    parser.add_argument(
        '--size',
        type = sizetype,
        default = '600,600',
    )
    parser.add_argument(
        '--output',
        help = 'Format string to write frames to.'
               ' e.g.: path/to/frames/%%04d.png',
    )
    parser.add_argument(
        '--repeat',
        action = 'store_true',
        help = 'Endlessly repeat.',
    )
    parser.add_argument(
        '--no-gui',
        action = 'store_true',
    )
    parser.add_argument(
        '--actor',
        action = 'append',
        help = 'Path to image to animate.'
    )
    parser.add_argument(
        '--background',
        help = 'Path to background image. Overrides --size.'
    )
    args = parser.parse_args(argv)
    main(args)

if __name__ == '__main__':
    cli()
