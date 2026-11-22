from typing import Any, ClassVar, cast

import hou
from sidefx_stroke import StrokeCursor  # ty: ignore[import-not-found]


def get_state_name(node_type: hou.OpNodeType) -> str:
    """Return the default state name."""

    definition = node_type.definition()
    if definition is None:
        raise RuntimeError('invalid node definition')
    sections = definition.sections()
    state_name = sections['DefaultState'].contents()
    return state_name


NODE_TYPE: hou.OpNodeType = kwargs['type']  # noqa: F821  # ty: ignore[unresolved-reference]
STATE_NAME = get_state_name(NODE_TYPE)
STATE_LABEL = 'Paint Surface'
STATE_CATEGORY = hou.sopNodeTypeCategory()
STATE_ICON = NODE_TYPE.icon()


class State:
    BRUSH_NAME = 'circle'
    RADIUS_PARM_NAME = 'radius'

    RESIZE_BASE = 1.01
    WHEEL_FACTOR = 10.0
    SHIFT_DRAG_FACTOR = 0.1

    TOOL_ADD = 0
    TOOL_ERASE = 1

    HUD_TEMPLATE: ClassVar[dict[str, Any]] = {
        'title': STATE_LABEL,
        'desc': '',
        'icon': STATE_ICON,
        'rows': [
            {'type': 'divider', 'label': 'Operations'},
            {'label': 'Paint', 'key': 'LMB'},
            {'label': 'Erase', 'key': 'Ctrl LMB'},
            {'type': 'divider', 'label': 'Brush'},
            {'label': 'Brush Radius', 'key': 'mousewheel'},
            {'label': 'Brush Radius (drag)', 'key': 'Ctrl Shift LMB'},
        ],
    }

    def __init__(
        self, state_name: str, scene_viewer: hou.SceneViewer, **kwargs: Any
    ) -> None:
        self.state_name = state_name
        self.scene_viewer = scene_viewer

        self.dragger = hou.ViewerStateDragger('meadow_paint_surface_dragger')
        self.cursor = SurfaceCursor(scene_viewer, state_name, self.BRUSH_NAME)
        self.stroke_drawable = hou.GeometryDrawable(
            self.scene_viewer,
            hou.drawableGeometryType.Face,
            'meadow_paint_surface_stroke',
            geometry=hou.Geometry(),
            params={'color1': (1.0, 1.0, 1.0, 1.0)},
        )
        self.stroke_drawable.show(False)

        self._node: hou.SopNode | None = None
        self._stroke_node: hou.SopNode | None = None
        self._result_node: hou.SopNode | None = None
        self._stroke_geo: hou.Geometry | None = None
        self._stroke_prim: hou.Face | None = None
        self._resizing = False
        self._last_mouse_x = 0
        self._last_mouse_y = 0

    def _init_nodes(self, node: hou.OpNode) -> None:
        """Initialize the state for a SOP node of this type."""

        if not isinstance(node, hou.SopNode) or node.type() != NODE_TYPE:
            return

        stroke_node = node.node('OUT_stroke')
        if not isinstance(stroke_node, hou.SopNode):
            return

        result_node = node.node('OUT_result')
        if not isinstance(result_node, hou.SopNode):
            return

        self._node = node
        self._stroke_node = stroke_node
        self._result_node = result_node

    @property
    def node(self) -> hou.SopNode:
        """Return the current node."""

        assert self._node is not None, 'state has no node'
        return self._node

    @property
    def stroke_node(self) -> hou.SopNode:
        """Return the stroke output node."""

        assert self._stroke_node is not None, 'state has no stroke node'
        return self._stroke_node

    @property
    def result_node(self) -> hou.SopNode:
        """Return the result output node."""

        assert self._result_node is not None, 'state has no result node'
        return self._result_node

    def onEnter(self, kwargs: dict[str, Any]) -> None:
        """Called when the state is entered from an existing node."""

        self._init_nodes(kwargs['node'])

        if not self.valid():
            return

        self._stroke_geo = None
        self._stroke_prim = None
        self._resizing = False

        radius = get_parm(self.node, self.RADIUS_PARM_NAME).evalAsFloat()
        self.cursor.update_xform({'scale': (radius, radius, radius)})
        self.cursor.hide()
        self.cursor.enable()
        self.cursor.show_prompt()
        self.scene_viewer.hudInfo(show=True, template=self.HUD_TEMPLATE)  # ty: ignore[missing-attribute]

    def onExit(self, kwargs: dict[str, Any]) -> None:
        """Called when the state is about to be exited."""

        self.cursor.hide()
        self._stroke_geo = None
        self._stroke_prim = None
        self._resizing = False

    def onInterrupt(self, kwargs: dict[str, Any]) -> None:
        """Called when the state is temporarily interrupted."""

        self.cursor.hide()

    def onResume(self, kwargs: dict[str, Any]) -> None:
        """Called when the state resumes from an interruption."""

        self.cursor.show()
        self.cursor.show_prompt()

    def onDraw(self, kwargs: dict[str, Any]) -> None:
        """Called every time the viewport renders. Draw the stroke preview."""

        self.stroke_drawable.draw(kwargs['draw_handle'])

    def onDrawInterrupt(self, kwargs: dict[str, Any]) -> None:
        """Called when drawing is interrupted. Hide the cursor."""

        self.cursor.hide()

    def onMouseWheelEvent(self, kwargs: dict[str, Any]) -> None:
        """Called on the mouse wheel. Resize the brush."""

        if not self.valid():
            return

        ui_event: hou.UIEvent = kwargs['ui_event']
        device = cast(hou.UIEventDevice, ui_event.device())
        dist = device.mouseWheel() * self.WHEEL_FACTOR
        if device.isShiftKey():
            dist *= self.SHIFT_DRAG_FACTOR
        self._resize_brush(dist)

    def onMouseEvent(self, kwargs: dict[str, Any]) -> bool:
        """Called for mouse events. Paint, erase, or resize the brush."""

        if not self.valid():
            return False

        ui_event: hou.UIEvent = kwargs['ui_event']
        device = cast(hou.UIEventDevice, ui_event.device())
        reason = ui_event.reason()

        self.cursor.update_model_xform(ui_event.curViewport())  # ty: ignore[missing-attribute]

        if (
            reason == hou.uiEventReason.Start
            and device.isShiftKey()
            and device.isCtrlKey()
        ):
            self._resizing = True
            self._last_mouse_x = device.mouseX()
            self._last_mouse_y = device.mouseY()
            self.scene_viewer.beginStateUndo('Brush Resize')
            return True

        if self._resizing:
            mouse_x = device.mouseX()
            mouse_y = device.mouseY()
            dist = (mouse_x - self._last_mouse_x) + (mouse_y - self._last_mouse_y)
            self._last_mouse_x = mouse_x
            self._last_mouse_y = mouse_y
            self._resize_brush(dist)
            if reason == hou.uiEventReason.Changed:
                self._resizing = False
                self.scene_viewer.endStateUndo()
            self.cursor.show()
            return True

        center_values = get_parm_tuple(self.node, 'projcenter').evalAsFloats()
        direction_values = get_parm_tuple(self.node, 'projdir').evalAsFloats()
        center = hou.Vector3(center_values[0], center_values[1], center_values[2])
        normal = hou.Vector3(
            direction_values[0], direction_values[1], direction_values[2]
        ).normalized()

        if reason in (hou.uiEventReason.Start, hou.uiEventReason.Picked):
            self.scene_viewer.beginStateUndo('Paint Surface Stroke')

            stroke_geo = hou.Geometry()
            self._stroke_geo = stroke_geo
            tool = self.TOOL_ERASE if device.isCtrlKey() else self.TOOL_ADD
            stroke_geo.addAttrib(hou.attribType.Global, 'stroke_tool', tool)
            color_name = 'erase_color' if tool == self.TOOL_ERASE else 'paint_color'
            color = get_parm_tuple(self.node, color_name).evalAsFloats()
            opacity = get_parm(self.node, 'opacity').evalAsFloat()
            self.stroke_drawable.setParams(
                {'color1': (color[0], color[1], color[2], opacity)}
            )

            self.dragger.startDragAlongPlane(ui_event, center, normal)  # ty: ignore[invalid-argument-type]
            self._stroke_prim = stroke_geo.createPolygon(is_closed=False)
            self._update_stroke()
            preview = self.stroke_node.geometry()
            if preview is not None:
                self.stroke_drawable.setGeometry(preview)

            self.stroke_drawable.show(True)
            self.cursor.show()
            if reason == hou.uiEventReason.Picked:
                self._end_stroke()
            return True

        if reason == hou.uiEventReason.Active:
            self.dragger.drag(ui_event)  # ty: ignore[invalid-argument-type]
            self._update_stroke()
            self._set_cursor_position(self.dragger.position(), normal)
            self.cursor.show()
            return True

        if reason == hou.uiEventReason.Changed:
            self.dragger.drag(ui_event)  # ty: ignore[invalid-argument-type]
            self._update_stroke()
            self._end_stroke()
            self.cursor.show()
            return True

        if reason == hou.uiEventReason.Located:
            ray_origin, ray_direction = ui_event.ray()  # ty: ignore[missing-attribute]
            pos = hou.hmath.intersectPlane(center, normal, ray_origin, ray_direction)
            self._set_cursor_position(pos, normal)
            self.cursor.show()
            return True

        return False

    def valid(self) -> bool:
        return (
            self._node is not None
            and self._stroke_node is not None
            and self._result_node is not None
        )

    def _set_cursor_position(self, pos: hou.Vector3, normal: hou.Vector3) -> None:
        """Move the brush cursor to a position on the plane, facing its normal."""

        radius = get_parm(self.node, self.RADIUS_PARM_NAME).evalAsFloat()
        rotation = hou.Quaternion(0.0, 0.0, 0.0, 1.0)
        rotation.setToVectors(hou.Vector3(0.0, 0.0, 1.0), normal)
        self.cursor.update_xform(
            {
                'translate': (pos.x(), pos.y(), pos.z()),
                'rotate': rotation.extractEulerRotates(),
                'scale': (radius, radius, radius),
            }
        )

    def _resize_brush(self, dist: float) -> None:
        """Scale the radius parm and the brush cursor by a mouse distance."""

        radius = get_parm(self.node, self.RADIUS_PARM_NAME).evalAsFloat()
        radius *= self.RESIZE_BASE**dist
        get_parm(self.node, self.RADIUS_PARM_NAME).set(radius)
        self.cursor.update_xform({'scale': (radius, radius, radius)})

    def _end_stroke(self) -> None:
        """Finish the stroke, write the result, and close the undo block."""

        self.dragger.endDrag()
        result = self.result_node.geometry()
        if result is None:
            result = hou.Geometry()

        get_parm(self.node, 'result_stash').set(result)
        self.stroke_drawable.show(False)
        self.scene_viewer.endStateUndo()

    def _update_stroke(self) -> None:
        """Add the dragger position to the stroke and update the stash parm."""

        if self._stroke_geo is None or self._stroke_prim is None:
            return

        point = self._stroke_geo.createPoint()
        point.setPosition(self.dragger.position())  # ty: ignore[invalid-argument-type]
        self._stroke_prim.addVertex(point)
        get_parm(self.node, 'stroke_stash').set(self._stroke_geo)
        self._stroke_geo.incrementAllDataIds()


class SurfaceCursor(StrokeCursor):
    """Cursor with a single surface brush."""

    def init_brushes(self) -> None:
        self.init_brushlist([(State.BRUSH_NAME, {})])


def get_parm(node: hou.OpNode, name: str) -> hou.Parm:
    """Return a parameter by name."""

    parm = node.parm(name)
    assert parm is not None, f'parameter does not exist: {name}'
    return parm


def get_parm_tuple(node: hou.OpNode, name: str) -> hou.ParmTuple:
    """Return a parameter tuple by name."""

    parm_tuple = node.parmTuple(name)
    assert parm_tuple is not None, f'parameter tuple does not exist: {name}'
    return parm_tuple


def createViewerStateTemplate() -> hou.ViewerStateTemplate:
    """Create and return the ViewerStateTemplate to register."""

    template = hou.ViewerStateTemplate(STATE_NAME, STATE_LABEL, STATE_CATEGORY)
    template.bindFactory(State)
    template.bindIcon(STATE_ICON)

    return template
