import bpy

def create_leg_from_single_vert():
    # 1. Start with the single vertex
    # We will recreate it to be sure, or we could assume it exists.
    # Let's recreate it for a clean state.
    
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = "Leg_Base"
    
    # 2. Enter Edit Mode
    bpy.ops.object.mode_set(mode='EDIT')
    
    # 3. Merge to Center (Make single vert)
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.merge(type='CENTER')
    
    # 4. Extrude Upward (E -> Z -> 4)
    # Note: After merge, the single vert is selected.
    
    # Extrude region (creates new vert) + translate (moves it)
    bpy.ops.mesh.extrude_region_move(
        MESH_OT_extrude_region={"use_normal_flip":False, "use_dissolve_ortho_edges":False, "mirror":False},
        TRANSFORM_OT_translate={"value":(0, 0, 4), "orient_type":'GLOBAL'}
    )
    
    # 5. Return to Object Mode
    bpy.ops.object.mode_set(mode='OBJECT')
    print("Created Leg: Single vert extruded up 4m.")

if __name__ == "__main__":
    create_leg_from_single_vert()
