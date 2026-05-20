import bpy

from .hud import RA_OT_ColorPaletteHUD
from .node_utils import is_material_shader_editor


class RA_PT_ColorPalettePanel(bpy.types.Panel):
    bl_idname = "RA_PT_color_palette"
    bl_label = "色板"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_category = "色 板"

    @classmethod
    def poll(cls, context):
        return is_material_shader_editor(context)

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = False
        layout.use_property_decorate = False
        icon = "HIDE_OFF" if RA_OT_ColorPaletteHUD.is_running() else "HIDE_ON"
        text = "关闭 GPU 色板" if RA_OT_ColorPaletteHUD.is_running() else "打开 GPU 色板"
        layout.operator(RA_OT_ColorPaletteHUD.bl_idname, text=text, icon=icon)
