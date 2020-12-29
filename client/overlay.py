import contextlib
with contextlib.redirect_stdout(None):
    import pygame
import win32gui, win32api, win32con
from time import sleep
from threading import Thread

class OverlayUi(Thread):
    def __init__(self, client, *args, **kwargs) -> None:
        self.client = client
        super().__init__(*args, **kwargs)

    def run(self):

        while True:
            try:
                if not self.client.closing:
                    res = self.get_game_window()
                    if res is not None:
                        _, _, w, h, hwnd = res

                        pygame.display.init()
                        pygame.font.init()
                        self.overlay = self.create_overlay(w, h)
                        win32gui.BringWindowToTop(hwnd)

                        self.render_loop()

                sleep(1)
            except Exception as e:
                print(e)

    def render_loop(self):
        font_size = 40
        text_renderer = pygame.font.SysFont("Courier", font_size)

        while not self.client.closing:
            try:
                res = self.get_game_window()
                if res is None:
                    break

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        break

                x, y, w, h, hwnd = res
                window_focused = hwnd == win32gui.GetForegroundWindow()
                self.overlay.fill((255, 0, 128))

                if window_focused:
                    to_blit = []
                    if self.client.imposter_chat:
                        to_blit.append(text_renderer.render("IMPOSTER ONLY", False, (255, 0, 0)))
                    if self.client.muted:
                        to_blit.append(text_renderer.render("MUTED", False, (0, 10, 200)))

                    for i, blittable in enumerate(to_blit):
                        self.overlay.blit(blittable, (w/2, 30+(i*font_size)))

                self.reset_overlay(x, y)
                pygame.display.flip()

                sleep(0.1)
            except Exception as e:
                print(e)

        pygame.quit()

    def get_game_window(self, hwnd_name="Among Us"):
        try:
            hwnd = win32gui.FindWindow(None, hwnd_name)
            window_rect = win32gui.GetWindowRect(hwnd)
            x = window_rect[0] - 5
            y = window_rect[1]
            width = window_rect[2] - x
            height = window_rect[3] - y
            return x, y, width, height, hwnd
        except:
            return None

    def create_overlay(self, width, height):
        screen = pygame.display.set_mode((width, height), pygame.NOFRAME | pygame.DOUBLEBUF)
        hwnd = pygame.display.get_wm_info()["window"]
        win32gui.SetWindowLong(
            hwnd, win32con.GWL_EXSTYLE, win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED
        )
        win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(255, 0, 128), 0, win32con.LWA_COLORKEY)
        return screen

    def reset_overlay(self, x, y):
        win32gui.SetWindowPos(pygame.display.get_wm_info()["window"], -1, x, y, 0, 0, 0x0001)