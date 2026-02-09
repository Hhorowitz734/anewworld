"""
Camera utilities for rendering.
"""

from dataclasses import dataclass


@dataclass(slots=True)
class Camera:
    """
    2D camera describing the visible region of the world.
    """

    x_px: int = 0
    """
    Camera X position in world pixels.
    """

    y_px: int = 0
    """
    Camera Y position in world pixels.
    """

    dragging: bool = False
    """
    Whether the user is currently dragging the camera.
    """

    _drag_start_mouse_x: int = 0
    """
    Mouse X position at the start of a drag, in screen pixels.
    """

    _drag_start_mouse_y: int = 0
    """
    Mouse Y position at the start of a drag, in screen pixels.
    """

    _drag_start_cam_x: int = 0
    """
    Camera X position at the start of a drag, in world pixels.
    """

    _drag_start_cam_y: int = 0
    """
    Camera Y position at the start of a drag, in world pixels.
    """

    def begin_drag(self, *, mouse_x: int, mouse_y: int) -> None:
        """
        Begin a drag interaction.

        Parameters
        ----------
        mouse_x : int
            Mouse X position in screen pixels.
        mouse_y : int
            Mouse Y position in screen pixels.
        """
        self.dragging = True
        self._drag_start_mouse_x = mouse_x
        self._drag_start_mouse_y = mouse_y
        self._drag_start_cam_x = self.x_px
        self._drag_start_cam_y = self.y_px

    def end_drag(self) -> None:
        """
        End a drag interaction.
        """
        self.dragging = False

    def drag_to(self, *, mouse_x: int, mouse_y: int) -> None:
        """
        Update camera position given a drag mouse position.

        Parameters
        ----------
        mouse_x : int
            Current mouse X position in screen pixels.
        mouse_y : int
            Current mouse Y position in screen pixels.
        """
        if not self.dragging:
            return

        dx = mouse_x - self._drag_start_mouse_x
        dy = mouse_y - self._drag_start_mouse_y

        self.x_px = self._drag_start_cam_x - dx
        self.y_px = self._drag_start_cam_y - dy

    def viewport_px(
        self,
        *,
        screen_width: int,
        screen_height: int,
    ) -> tuple[int, int, int, int]:
        """
        Return the visible world rectangle in pixels.

        Parameters
        ----------
        screen_width : int
            Screen width in pixels.
        screen_height : int
            Screen height in pixels.

        Returns
        -------
        tuple[int, int, int, int]
            (left, top, right, bottom) in world pixels.
        """
        left = self.x_px
        top = self.y_px
        right = self.x_px + screen_width - 1
        bottom = self.y_px + screen_height - 1
        return left, top, right, bottom
