"""
Documentation of the viewer state handler interface.

This module is not imported at runtime. It mirrors the handlers Houdini can
call and their signatures, as a reference for the state implementation.
"""

import abc
from typing import Any

import hou


class BaseState(abc.ABC):
    """Base class for Houdini viewer states.

    See the Houdini Python viewer states documentation
    (https://www.sidefx.com/docs/houdini/hom/python_states.html) for details on
    the arguments passed to each handler through the ``kwargs`` dictionary.
    """

    def __init__(
        self, state_name: str, scene_viewer: hou.SceneViewer, **kwargs: Any
    ) -> None:
        """Initialize the state.

        ``state_name`` is the state name string this state was registered
        under.
        ``scene_viewer`` is the hou.SceneViewer or hou.CompositorViewer for COP states
        the tool is operating in.
        """
        self.state_name = state_name
        self.scene_viewer = scene_viewer

    # Lifecycle

    def onEnter(self, kwargs: dict[str, Any]) -> None:
        """Called when the state is entered from an existing node."""

    def onGenerate(self, kwargs: dict[str, Any]) -> None:
        """Called when the state is entered without an existing node."""

    def onInterrupt(self, kwargs: dict[str, Any]) -> None:
        """Called when the state is interrupted (focus lost, pointer leaves
        the viewer, or a volatile tool is activated)."""

    def onResume(self, kwargs: dict[str, Any]) -> None:
        """Called when an interruption ends."""

    def onExit(self, kwargs: dict[str, Any]) -> None:
        """Called when the state is about to be exited."""

    # UI

    def onMouseEvent(self, kwargs: dict[str, Any]) -> None:
        """Called on mouse moves/clicks. Return True to consume the event."""

    def onMouseDoubleClickEvent(self, kwargs: dict[str, Any]) -> None:
        """Called on mouse double clicks."""

    def onMouseWheelEvent(self, kwargs: dict[str, Any]) -> None:
        """Called on mouse wheel scroll."""

    def onKeyEvent(self, kwargs: dict[str, Any]) -> None:
        """Called for key events."""

    def onKeyTransitEvent(self, kwargs: dict[str, Any]) -> None:
        """Called for key transition events."""

    def onMenuAction(self, kwargs: dict[str, Any]) -> None:
        """Called when a context menu choice is selected."""

    def onMenuPreOpen(self, kwargs: dict[str, Any]) -> None:
        """Called when the context menu is about to be shown, to update the
        state of the menu and its items."""

    def onParmChangeEvent(self, kwargs: dict[str, Any]) -> None:
        """Called when a state parameter changes."""

    def onNodeChangeEvent(self, kwargs: dict[str, Any]) -> None:
        """Called when an action or change occurs on the state's node."""

    def onPlaybackChangeEvent(self, kwargs: dict[str, Any]) -> None:
        """Called when a playbar change event occurs."""

    def onCommand(self, kwargs: dict[str, Any]) -> None:
        """Called by hou.SceneViewer.runStateCommand for general purpose
        command events."""

    # Handle

    def onHandleToState(self, kwargs: dict[str, Any]) -> None:
        """Called on user interaction with a bound handle."""

    def onStateToHandle(self, kwargs: dict[str, Any]) -> None:
        """Called when node parameters change, to update handle parameters."""

    def onBeginHandleToState(self, kwargs: dict[str, Any]) -> None:
        """Called at the start of user interaction with a handle."""

    def onEndHandleToState(self, kwargs: dict[str, Any]) -> None:
        """Called at the end of user interaction with a handle."""

    # Selection

    def onStartSelection(self, kwargs: dict[str, Any]) -> None:
        """Called when the user starts selecting."""

    def onSelection(self, kwargs: dict[str, Any]) -> None:
        """Called when the user selected geometry. Return True to accept the
        selection and stop the selector."""

    def onStopSelection(self, kwargs: dict[str, Any]) -> None:
        """Called when the user stops selecting."""

    def onLocateSelection(self, kwargs: dict[str, Any]) -> None:
        """Called when drawables are located with a drawable selector."""

    # Drag and Drop

    def onDragTest(self, kwargs: dict[str, Any]) -> None:
        """Called when the user initiates a drag event."""

    def onDropGetOptions(self, kwargs: dict[str, Any]) -> None:
        """Called to build a list of drop options for the user to choose
        from."""

    def onDropAccept(self, kwargs: dict[str, Any]) -> None:
        """Called to handle the selected drop option."""

    # Drawing

    def onDraw(self, kwargs: dict[str, Any]) -> None:
        """Called on interactive events or viewport redraws."""

    def onDrawInterrupt(self, kwargs: dict[str, Any]) -> None:
        """Called when the state is interrupted while drawing is required."""
