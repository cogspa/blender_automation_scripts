import bpy
import random

def create_random_cube():
    # Context
    bpy.ops.mesh.primitive_cube_add(
        size=2, 
        location=(
            random.uniform(-5, 5), 
            random.uniform(-5, 5), 
            random.uniform(0, 5)
        )
    )
    
    # Get active object
    obj = bpy.context.active_object
    
    # Random color (only works in material preview/render)
    mat = bpy.data.materials.new(name="RandomColor")
    mat.use_nodes = False
    mat.diffuse_color = (
        random.random(), 
        random.random(), 
        random.random(), 
        1
    )
    obj.data.materials.append(mat)
    
    print(f"Created cube at {obj.location}")

# Run
create_random_cube()
