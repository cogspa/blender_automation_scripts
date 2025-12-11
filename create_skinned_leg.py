import bpy
import bmesh

def create_skinned_leg():
    # 1. Setup: Clean Start
    # Optional: Delete existing leg if present to avoid clutter
    if "Leg_Skinned" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["Leg_Skinned"], do_unlink=True)

    # 2. Create Base Geometry (Single Vert -> Extrude)
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = "Leg_Skinned"
    
    # Merge to center
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.merge(type='CENTER')
    
    # Extrude Up 4m
    bpy.ops.mesh.extrude_region_move(
        TRANSFORM_OT_translate={"value":(0, 0, 4)}
    )
    
    # 3. Apply Skin Modifier
    # We need to be in Object mode to add modifier cleanly? 
    # Actually we can add it, but to edit radii we need BMesh which works in Edit mode.
    # Let's switch to Object to add modifier first.
    bpy.ops.object.mode_set(mode='OBJECT')
    mod = obj.modifiers.new(name="Skin", type='SKIN')
    
    # 4. Adjust Skin Radii (Ctrl+A)
    # Switch back to Edit Mode to access BMesh data
    bpy.ops.object.mode_set(mode='EDIT')
    me = obj.data
    bm = bmesh.from_edit_mesh(me)
    
    # Get the Skin Vertex Layer
    # If it doesn't exist, verify() creates it
    skin_layer = bm.verts.layers.skin.verify()
    
    # Iterate vertices to set thickness
    for v in bm.verts:
        # Access skin data for this vert
        skin_data = v[skin_layer]
        
        # Check height (Z) to decide thickness
        # Logic: Bottom (z=0) -> Wide. Top (z=4) -> Thin.
        z = v.co.z
        
        if z < 0.1: # Bottom
            # Radius is (x, y)
            skin_data.radius = (0.5, 0.5)
        elif z > 3.9: # Top
            skin_data.radius = (0.2, 0.2)
        else:
            # Intermediate verts if any
            skin_data.radius = (0.35, 0.35)
            
    # Update mesh
    bmesh.update_edit_mesh(me)
    
    # 5. Finish
    bpy.ops.object.mode_set(mode='OBJECT')
    print("Created Skinned Leg: Tapered thickness applied.")

if __name__ == "__main__":
    create_skinned_leg()
