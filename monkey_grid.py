import bpy
import random

def create_monkey_grid():
    # clear existing monkeys first (optional, be careful deleting)
    # bpy.ops.object.select_all(action='DESELECT')
    # bpy.ops.object.select_by_type(type='MESH')
    # bpy.ops.object.delete()
    
    for x in range(3):
        for y in range(3):
            bpy.ops.mesh.primitive_monkey_add(
                size=1,
                location=(x * 2.5, y * 2.5, 0)
            )
            obj = bpy.context.active_object
            obj.name = f"Monkey_{x}_{y}"
            
            # Add subdivision surface for smoothness
            mod = obj.modifiers.new(name="Subsurf", type='SUBSURF')
            mod.levels = 2
            
            # Smooth shading
            bpy.ops.object.shade_smooth()

create_monkey_grid()
print("Monkey Grid Created!")
