import bpy

def create_single_vertex_object():
    """
    Creates a single vertex by adding a plane and merging it, 
    replicating the manual workflow: 
    Shift+A (Plane) -> Tab (Edit) -> Merge (At Center)
    """
    
    # 1. Add a Plane
    # "radius" property is deprecated/removed in newer Blender versions in favor of "size"
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = "Single_Vert"
    
    # 2. Enter Edit Mode
    bpy.ops.object.mode_set(mode='EDIT')
    
    # 3. Select All (Just in case)
    bpy.ops.mesh.select_all(action='SELECT')
    
    # 4. Merge Vertices -> At Center
    bpy.ops.mesh.merge(type='CENTER')
    
    # 5. Return to Object Mode to see the result
    bpy.ops.object.mode_set(mode='OBJECT')
    
    print(f"Created single vertex object: '{obj.name}'")

if __name__ == "__main__":
    create_single_vertex_object()
