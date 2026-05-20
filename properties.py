import bpy

from .constants import ZERO_COLOR


_CAPTURE_LOCK = False


def add_color(scene, color, group_index=None):
    if len(scene.WittyMing_color_palette_groups) == 0:
        add_group(scene)
    if group_index is None:
        group_index = scene.WittyMing_color_palette_active_group
    group_index = max(0, min(group_index, len(scene.WittyMing_color_palette_groups) - 1))
    item = scene.WittyMing_color_palette_colors.add()
    item.name = f"{len(scene.WittyMing_color_palette_colors):02d}"
    item.color = color
    item.group = group_index
    scene.WittyMing_color_palette_active_group = group_index


def add_group(scene):
    group = scene.WittyMing_color_palette_groups.add()
    group.name = f"Group {len(scene.WittyMing_color_palette_groups):02d}"
    for item in scene.WittyMing_color_palette_colors:
        item.group += 1
    scene.WittyMing_color_palette_active_group = 0
    return group


def remove_group(scene, index):
    groups = scene.WittyMing_color_palette_groups
    if not (0 <= index < len(groups)) or len(groups) <= 1:
        return
    remove_indices = [i for i, item in enumerate(scene.WittyMing_color_palette_colors) if item.group == index]
    for item_index in reversed(remove_indices):
        scene.WittyMing_color_palette_colors.remove(item_index)
    for item in scene.WittyMing_color_palette_colors:
        if item.group > index:
            item.group -= 1
    groups.remove(index)
    scene.WittyMing_color_palette_active_group = max(0, min(scene.WittyMing_color_palette_active_group, len(groups) - 1))


def remove_color(scene, index):
    if 0 <= index < len(scene.WittyMing_color_palette_colors):
        scene.WittyMing_color_palette_colors.remove(index)


def capture_color_update(scene, context):
    global _CAPTURE_LOCK
    if _CAPTURE_LOCK:
        return
    color = tuple(scene.WittyMing_color_palette_capture)
    if color == ZERO_COLOR:
        return
    add_color(scene, color)
    _CAPTURE_LOCK = True
    try:
        scene.WittyMing_color_palette_capture = ZERO_COLOR
    finally:
        _CAPTURE_LOCK = False


class RA_ColorPaletteSlot(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="名称", default="Color")
    group: bpy.props.IntProperty(name="分组", default=0, min=0)
    color: bpy.props.FloatVectorProperty(
        name="颜色",
        subtype="COLOR",
        size=4,
        min=0.0,
        max=1.0,
        default=(1.0, 1.0, 1.0, 1.0),
    )


class RA_ColorPaletteGroup(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="名称", default="Group")
