import bpy

try:
    from ctypes import c_float, c_void_p
    from mathutils import Vector
except Exception:
    c_float = None
    c_void_p = None
    Vector = None


def is_material_shader_editor(context):
    space = context.space_data
    return bool(
        context.area
        and context.area.type == "NODE_EDITOR"
        and space
        and space.type == "NODE_EDITOR"
        and getattr(space, "tree_type", "") == "ShaderNodeTree"
        and getattr(space, "shader_type", "OBJECT") == "OBJECT"
    )


def color_tuple(color):
    if len(color) >= 4:
        return tuple(color[:4])
    return (color[0], color[1], color[2], 1.0)


def window_region(area):
    if not area:
        return None
    return next((region for region in area.regions if region.type == "WINDOW"), None)


def _node_abs_location(node):
    if hasattr(node, "location_absolute"):
        return node.location_absolute.x, node.location_absolute.y
    x, y = node.location.x, node.location.y
    parent = node.parent
    while parent:
        x += parent.location.x
        y += parent.location.y
        parent = parent.parent
    return x, y


def _node_bounds(node):
    scale = bpy.context.preferences.system.ui_scale
    x, y = _node_abs_location(node)
    x_min = x * scale
    x_max = x_min + node.dimensions.x
    if node.hide and node.type not in {"REROUTE", "FRAME"}:
        y_min = y * scale - 9 * scale - node.dimensions.y / 2
        y_max = y * scale - 9 * scale + node.dimensions.y / 2
    else:
        y_min = y * scale
        y_max = y_min - node.dimensions.y
    return x_min, x_max, y_min, y_max


def _node_socket_coords(node):
    if not c_float or not c_void_p or not Vector:
        return []
    if node.type == "FRAME":
        return []
    scale = bpy.context.preferences.system.ui_scale
    if node.type == "REROUTE":
        x, y = _node_abs_location(node)
        socket = node.inputs[0] if node.inputs else None
        return [(socket, x * scale, y * scale)] if socket else []

    runtime_offset = 520
    location_offset = 24
    if bpy.app.version >= (5, 1, 0):
        runtime_offset = 456
    if bpy.app.version >= (5, 2, 0):
        location_offset = 32

    coords = []
    for sockets in (node.inputs, node.outputs):
        for socket in sockets:
            if not getattr(socket, "enabled", True):
                continue
            try:
                runtime = c_void_p.from_address(socket.as_pointer() + runtime_offset).value
                if not runtime:
                    continue
                loc = Vector((c_float * 2).from_address(runtime + location_offset))
                if getattr(socket, "is_icon_visible", True):
                    coords.append((socket, loc.x, loc.y))
            except Exception:
                continue
    return coords


def active_node_tree(context):
    try:
        if hasattr(context.space_data, "path") and len(context.space_data.path) > 0:
            return context.space_data.path[-1].node_tree
        return context.space_data.node_tree
    except Exception:
        return None


def closest_node(context, region, mouse_xy):
    tree = active_node_tree(context)
    if not tree or not region:
        return None
    rx, ry = region.view2d.region_to_view(mouse_xy[0], mouse_xy[1])
    best_inside = None
    best_dist = None
    near = []

    for node in tree.nodes:
        try:
            x_min, x_max, y_min, y_max = _node_bounds(node)
        except Exception:
            continue
        left, right = min(x_min, x_max), max(x_min, x_max)
        bottom, top = min(y_min, y_max), max(y_min, y_max)
        cx = (left + right) * 0.5
        cy = (bottom + top) * 0.5
        dist = (cx - rx) ** 2 + (cy - ry) ** 2
        near.append((dist, node))
        if left <= rx <= right and bottom <= ry <= top:
            if best_inside is None or dist < best_dist:
                best_inside = node
                best_dist = dist

    if best_inside:
        return best_inside
    near.sort(key=lambda item: item[0])
    return near[0][1] if near else None


def color_at_mouse(context, region, mouse_xy):
    tree = active_node_tree(context)
    if not tree or not region:
        return None
    rx, ry = region.view2d.region_to_view(mouse_xy[0], mouse_xy[1])
    candidates = []
    for node in tree.nodes:
        try:
            x_min, x_max, y_min, y_max = _node_bounds(node)
        except Exception:
            continue
        left, right = min(x_min, x_max), max(x_min, x_max)
        bottom, top = min(y_min, y_max), max(y_min, y_max)
        if left - 12 <= rx <= right + 12 and bottom - 12 <= ry <= top + 12:
            cx = (left + right) * 0.5
            cy = (bottom + top) * 0.5
            candidates.append(((cx - rx) ** 2 + (cy - ry) ** 2, node, left, right))

    for _dist, node, left, right in sorted(candidates, key=lambda item: item[0]):
        socket_hits = []
        for socket, sx, sy in _node_socket_coords(node):
            color = socket_color(socket)
            if not color:
                continue
            row_hit = abs(ry - sy) <= 22 and left - 12 <= rx <= right + 18
            socket_hit = (rx - sx) ** 2 + (ry - sy) ** 2 <= 34 * 34
            if row_hit or socket_hit:
                socket_hits.append((abs(ry - sy), color))
        if socket_hits:
            socket_hits.sort(key=lambda item: item[0])
            return socket_hits[0][1]

        color = color_from_node(node)
        if color and _color_node_body_hit(node, rx, ry, left, right):
            return color
    return None


def _color_node_body_hit(node, rx, ry, left, right):
    if node.type not in {"RGB", "VALTORGB", "MIX_RGB"}:
        return False
    try:
        _x_min, _x_max, y_min, y_max = _node_bounds(node)
    except Exception:
        return False
    bottom, top = min(y_min, y_max), max(y_min, y_max)
    return left - 8 <= rx <= right + 8 and bottom - 8 <= ry <= top + 8


def node_under_mouse(context, region, mouse_xy):
    tree = active_node_tree(context)
    if not tree or not region:
        return None
    rx, ry = region.view2d.region_to_view(mouse_xy[0], mouse_xy[1])
    best_node = None
    best_dist = None
    for node in tree.nodes:
        try:
            x_min, x_max, y_min, y_max = _node_bounds(node)
        except Exception:
            continue
        left, right = min(x_min, x_max), max(x_min, x_max)
        bottom, top = min(y_min, y_max), max(y_min, y_max)
        if not (left <= rx <= right and bottom <= ry <= top):
            continue
        cx = (left + right) * 0.5
        cy = (bottom + top) * 0.5
        dist = (cx - rx) ** 2 + (cy - ry) ** 2
        if best_node is None or dist < best_dist:
            best_node = node
            best_dist = dist
    return best_node


def socket_color(socket):
    if not socket or not hasattr(socket, "default_value"):
        return None
    value = socket.default_value
    if not hasattr(value, "__len__"):
        return None
    if len(value) == 4:
        return tuple(value[:4])
    if len(value) == 3:
        return (value[0], value[1], value[2], 1.0)
    return None


def color_from_node(node):
    if not node:
        return None
    names = ("Base Color", "Color", "颜色", "BaseColor", "Tint")
    sockets = list(getattr(node, "inputs", [])) + list(getattr(node, "outputs", []))
    for name in names:
        socket = next((s for s in sockets if s.name == name and hasattr(s, "default_value")), None)
        color = socket_color(socket)
        if color:
            return color
    for socket in sockets:
        color = socket_color(socket)
        if color:
            return color
    return None


def apply_color_to_node(node, color):
    if not node:
        return False
    names = ("Base Color", "Color", "颜色", "BaseColor", "Tint")
    socket_groups = (list(getattr(node, "inputs", [])), list(getattr(node, "outputs", [])))
    for sockets in socket_groups:
        for name in names:
            socket = next((s for s in sockets if s.name == name and hasattr(s, "default_value")), None)
            if socket:
                try:
                    socket.default_value = color
                    return True
                except Exception:
                    pass
        for socket in sockets:
            value = getattr(socket, "default_value", None)
            if hasattr(value, "__len__") and len(value) in {3, 4}:
                try:
                    socket.default_value = color[:len(value)]
                    return True
                except Exception:
                    continue
    return False
