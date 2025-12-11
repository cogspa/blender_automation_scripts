import bpy
import bmesh
import math
from mathutils import Vector

def create_leg_with_ik():
    # ---------------------------------------------------------
    # 1. Clean up previous
    # ---------------------------------------------------------
    for name in ["Leg_Mesh", "Leg_Rig_IK", "Leg_IK_Target"]:
        if name in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
            
    # ---------------------------------------------------------
    # 2. Geometry & Skin
    # ---------------------------------------------------------
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
    mesh_obj = bpy.context.active_object
    mesh_obj.name = "Leg_Mesh"
    
    # Merge & Extrude
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.merge(type='CENTER')
    # Extrude Up 4m
    bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value":(0, 0, 4)})
    # Subdivide (2 cuts -> 3 segments)
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.subdivide(number_cuts=2)
    
    # Skin Modifier
    bpy.ops.object.mode_set(mode='OBJECT')
    mod = mesh_obj.modifiers.new(name="Skin", type='SKIN')
    
    # Tapering
    bpy.ops.object.mode_set(mode='EDIT')
    me = mesh_obj.data
    bm = bmesh.from_edit_mesh(me)
    skin_layer = bm.verts.layers.skin.verify()
    for v in bm.verts:
        z = v.co.z
        skin_data = v[skin_layer]
        radius = 0.5 - (z * 0.075)
        skin_data.radius = (radius, radius)
    bmesh.update_edit_mesh(me)
    
    # ---------------------------------------------------------
    # 3. Create Armature
    # ---------------------------------------------------------
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.objects.active = mesh_obj
    
    bpy.ops.object.skin_armature_create(modifier="Skin")
    
    armature = bpy.context.active_object
    armature.name = "Leg_Rig_IK"
    
    # ---------------------------------------------------------
    # 4. Setup IK
    # ---------------------------------------------------------
    
    # A. Identify the specific bone (the tip)
    bpy.ops.object.mode_set(mode='POSE')
    
    last_bone = None
    max_z = -99999.0
    
    for pbone in armature.pose.bones:
        # Get tail in world space
        tail_loc = armature.matrix_world @ pbone.tail
        if tail_loc.z > max_z:
            max_z = tail_loc.z
            last_bone = pbone
            
    if not last_bone:
        return

    # B. Create Target Empty at Bone Tip
    bpy.ops.object.mode_set(mode='OBJECT') 
    
    # Create the empty
    bpy.ops.object.empty_add(type='SPHERE', radius=0.5, location=(0,0,0))
    ik_target = bpy.context.active_object
    ik_target.name = "Leg_IK_Target"
    
    # --- UPDATE: Set Exact Position from User Image ---
    # Location from screenshot: X=0, Y=-2.4562, Z=0.28973
    ik_target.location = Vector((0, -2.4562, 0.28973))
    print(f"Positioned IK Target at: {ik_target.location}")
    
    # C. Add IK Constraint to Bone
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')
    
    pbone = armature.pose.bones[last_bone.name]
    
    c = pbone.constraints.new('IK')
    c.target = ik_target
    c.chain_count = 0 
    
    print("Full Leg IK Setup Complete (Target Positioned, No Rotation Fixes).")

if __name__ == "__main__":
    create_leg_with_ik()
