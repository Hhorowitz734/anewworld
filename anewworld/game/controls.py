"""
Input handling and control routing.
"""

from dataclasses import dataclass

import pygame

from anewworld.render.camera import Camera


@dataclass(slots=True)
class Controls:
    """
    Route raw pygame events into game control actions.
    """

    camera: Camera
    """
    Camera controlled by input events.
    """

    pan_button: int = 1
    """
    Mouse button used to pan camera.

    1 -> left click
    2 -> middle button
    """

    def handle_event(self, event: pygame.event.Event) -> None:
        """
        Handle a pygame event.

        Parameters
        ----------
        event: pygame.event.Event
            Event to process.
        """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == self.pan_button:
            mx, my = event.pos
            self.camera.begin_drag(mouse_x=mx, mouse_y=my)
            return

        if event.type == pygame.MOUSEBUTTONUP and event.button == self.pan_button:
            self.camera.end_drag()
            return

        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            self.camera.drag_to(mouse_x=mx, mouse_y=my)
            return


