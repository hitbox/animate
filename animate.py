import argparse
import contextlib
import math
import os

from collections import deque
from functools import singledispatch
from itertools import cycle
from itertools import tee

with contextlib.redirect_stdout(open(os.devnull, 'w')):
    import pygame

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

def get_rect(rect, **kwargs):
    rect = rect.copy()
    for k, v in kwargs.items():
        setattr(rect, k, v)
    return rect

def nwise(iterable, n=2):
    """
    Take iterable in overlapping n-wise fashion, defaulting to 2-pairs.
    """
    pairs = tee(iterable, n)
    for index, pair in enumerate(pairs):
        for _ in range(index):
            next(pair)
    return zip(*pairs)

class Animation:

    def __init__(
        self,
        duration,
        *args,
        lerpfunc = lerp,
        iterfunc = iter,
        **extra,
    ):
        self.args = args
        self.iterfunc = iterfunc
        self.duration = duration
        self.time = 0 # TODO: time per pair?
        self.lerpfunc = lerpfunc
        self.__dict__.update(extra)
        self.start()

    def start(self):
        pairs = nwise(self.args)
        pairs = map(list, pairs)
        self.pairs = self.iterfunc(pairs)
        self.running = True
        self.time = 0
        self.next_pair()

    def next_pair(self):
        self.a, self.b = next(self.pairs)

    def value(self):
        timestep = self.time / self.duration
        return self.lerpfunc(self.a, self.b, timestep)

    def update(self, elapsed):
        if self.time < self.duration:
            self.time += elapsed
            if self.time >= self.duration:
                self.time = self.duration
                try:
                    self.next_pair()
                except StopIteration:
                    # done
                    self.running = False
                else:
                    self.time = 0


class circlerp:

    def __init__(self, center, radius):
        self.centerx, self.centery = center
        self.radius = radius

    def __call__(self, a, b, time):
        angle = lerp(a, b, time)
        x = self.centerx + math.cos(angle) * self.radius
        y = self.centery - math.sin(angle) * self.radius
        return (x, y)


def main(argv=None):
    """
    animate
    """
    parser = argparse.ArgumentParser(
        description = main.__doc__,
    )
    parser.add_argument(
        '--frames',
        help = 'Format string to write frames to.'
               ' e.g.: path/to/frames/%%04d.png',
    )
    args = parser.parse_args(argv)

    screen = pygame.display.set_mode((800,800))
    window = screen.get_rect()
    clock = pygame.time.Clock()
    fps = 60

    rect_image = pygame.Surface((200,)*2, pygame.SRCALPHA)
    rect = rect_image.get_rect()

    rect_hline = [
        (rect.centerx, rect.centery - rect.height / 4),
        (rect.centerx, rect.centery + rect.height / 4),
    ]

    rect_vline = [
        (rect.centerx - rect.width / 4, rect.centery),
        (rect.centerx + rect.width / 4, rect.centery),
    ]

    rect_color = (2*255/3,)*3
    pygame.draw.rect(rect_image, rect_color, rect, 1)
    pygame.draw.line(rect_image, rect_color, rect_hline[0], rect_hline[1], 1)
    pygame.draw.line(rect_image, rect_color, rect_vline[0], rect_vline[1], 1)

    rect.center = window.center
    trail = deque(maxlen=60)
    trail_color = (255/3, 255/3, 2*255/3)

    # TODO: duration per pair or repeat the one given
    duration = 1000
    radius = 300

    animate_center_to_right = Animation(
        duration,
        rect.topleft,
        get_rect(rect, centerx=window.centerx + radius).topleft,
        attr = 'topleft',
    )

    animate_circle_ccw = Animation(
        duration * 2,
        0,
        math.tau,
        lerpfunc = circlerp(window.center, radius),
        attr = 'center',
    )

    animate_right_to_left = Animation(
        duration,
        get_rect(rect, centerx=window.centerx + radius).topleft,
        get_rect(rect, centerx=window.centerx - radius).topleft,
        attr = 'topleft',
    )

    animate_circle_cw = Animation(
        duration * 2,
        math.pi,
        -math.pi,
        lerpfunc = circlerp(window.center, radius),
        attr = 'center',
    )

    animate_left_to_center = Animation(
        duration,
        get_rect(rect, centerx=window.centerx - radius).topleft,
        rect.topleft,
        attr = 'topleft',
    )

    animations = [
        animate_center_to_right,
        animate_circle_ccw,
        animate_right_to_left,
        animate_circle_cw,
        animate_left_to_center,
    ]

    animations = iter(animations)
    animation = next(animations)
    animation.running = True

    frame = 0
    running = True
    while running:
        elapsed = clock.tick(fps)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    pygame.event.post(pygame.event.Event(pygame.QUIT))
        #
        if animation:
            animation.update(elapsed)
            setattr(rect, animation.attr, animation.value())
            trail.append(rect.center)
            if not animation.running:
                try:
                    animation = next(animations)
                except StopIteration:
                    animation = None
                else:
                    animation.start()
        elif trail:
            trail.popleft()
        else:
            pygame.event.post(pygame.event.Event(pygame.QUIT))
        #
        screen.fill((0,)*3)
        if len(trail) > 1:
            for p1, p2 in nwise(trail):
                pygame.draw.line(screen, trail_color, p1, p2)

        screen.blit(rect_image, rect_image.get_rect(center=rect.center))
        pygame.display.flip()

        if args.frames:
            filename = args.frames % (frame,)
            pygame.image.save(screen, filename)
        frame += 1

if __name__ == '__main__':
    main()
