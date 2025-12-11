import bpy
import bmesh

def create_subdivided_leg():
    # 1. Setup
    if "Leg_Segmented" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Leg_Segmented"], do_unlink=True)

    # 2. Base Leg (Vert + Extrude)
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = "Leg_Segmented"
    
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.merge(type='CENTER')
    
    # 3. Extrude Up
    bpy.ops.mesh.extrude_region_move(
        TRANSFORM_OT_translate={"value":(0, 0, 4)}
    )
    
    # --- NEW STEP: Subdivide ---
    # Select everything (both verts and the edge)
    bpy.ops.mesh.select_all(action='SELECT')
    # Subdivide with 2 cuts -> Creates 3 segments
    bpy.ops.mesh.subdivide(number_cuts=2)
    
    # 4. Apply Skin Modifier
    bpy.ops.object.mode_set(mode='OBJECT')
    mod = obj.modifiers.new(name="Skin", type='SKIN')
    
    # 5. Adjust Radii (Tapering with intermediate steps)
    bpy.ops.object.mode_set(mode='EDIT')
    me = obj.data
    bm = bmesh.from_edit_mesh(me)
    skin_layer = bm.verts.layers.skin.verify()
    
    # Sort verts by height to apply nice gradient maybe?
    # Or just simple logic
    for v in bm.verts:
        z = v.co.z
        skin_data = v[skin_layer]
        
        # Linear interpolation for radius
        # Height 0 -> 4. Radius 0.5 -> 0.2
        # r = 0.5 - (z / 4.0) * (0.5 - 0.2)
        # r = 0.5 - (z * 0.075)
        
        radius = 0.5 - (z * 0.075)
        skin_data.radius = (radius, radius)
            
    bmesh.update_edit_mesh(me)
    bpy.ops.object.mode_set(mode='OBJECT')
    
    print("Created Segmented Leg: Subdivided into 3 segments.")

if __name__ == "__main__":
    create_subdivided_leg()
