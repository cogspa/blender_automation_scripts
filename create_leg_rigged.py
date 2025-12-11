import bpy
import bmesh

def create_rigged_leg():
    # 1. Setup
    if "Leg_Rigged" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Leg_Rigged"], do_unlink=True)
    # Also clean up the armature if it was created before
    if "Armature" in bpy.data.objects:
        # This might be too aggressive if user has other armatures, but for this standalone test it's fine.
        # Better: find armature linked to the object? 
        # For now let's just create the object.
        pass

    # 2. Base Leg (Vert + Extrude)
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = "Leg_Rigged"
    
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.merge(type='CENTER')
    
    # 3. Extrude Up
    bpy.ops.mesh.extrude_region_move(
        TRANSFORM_OT_translate={"value":(0, 0, 4)}
    )
    
    # Subdivide
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.subdivide(number_cuts=2)
    
    # 4. Apply Skin Modifier
    bpy.ops.object.mode_set(mode='OBJECT')
    mod = obj.modifiers.new(name="Skin", type='SKIN')
    
    # 5. Adjust Radii
    bpy.ops.object.mode_set(mode='EDIT')
    me = obj.data
    bm = bmesh.from_edit_mesh(me)
    skin_layer = bm.verts.layers.skin.verify()
    
    for v in bm.verts:
        z = v.co.z
        skin_data = v[skin_layer]
        radius = 0.5 - (z * 0.075)
        skin_data.radius = (radius, radius)
            
    bmesh.update_edit_mesh(me)
    
    # 6. Create Armature from Skin
    # Must be in Object Mode
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # The operator works on the active object
    bpy.context.view_layer.objects.active = obj
    
    print("Generating Armature from Skin...")
    bpy.ops.object.skin_armature_create(modifier="Skin")
    
    print("Created Rigged Leg: Armature generated from Skin modifier.")

if __name__ == "__main__":
    create_rigged_leg()
