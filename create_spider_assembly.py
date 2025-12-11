import bpy
import bmesh
import math
from mathutils import Vector

def create_spider_assembly():
    # --------------------------------------------------------------------
    # 1. CLEANUP
    # --------------------------------------------------------------------
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for _ in range(3):
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

    # --------------------------------------------------------------------
    # 2. CREATE BODY (Cube)
    # --------------------------------------------------------------------
    # "lower the cube in z" -> Let's put it at Z=3.0 (was 5.0)
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 3.0))
    body = bpy.context.active_object
    body.name = "Spider_Body"
    # Make it transparent-ish to see inside? User had semi-transparent blue.
    # We'll just leave default grey for now, user can see wireframe.
    
    print("Created Body at Z=3.0")

    # --------------------------------------------------------------------
    # 3. CREATE LEG MESH
    # --------------------------------------------------------------------
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
    leg_mesh = bpy.context.active_object
    leg_mesh.name = "Leg_Mesh"
    
    # -- Orientation & Position --
    # "move the whole leg a bit in y ... so it si slightly inside the cube"
    # We want the Leg ROOT (Wide Part) inside the Cube.
    # The Leg Geometry generates Wide at Local (0,0,0) and Thin at Local (0,0,4).
    # We want Wide at Top (Body), Thin at Bottom (Ground).
    # Solution: Rotate 180 on X.
    leg_mesh.rotation_euler.x = math.radians(180)
    
    # Move to Body Position, offset in Y?
    # Body extends from Y=-1 to Y=1.
    # Let's put leg at Y = -0.6 (Inside).
    # Z should be near Body Center (3.0).
    leg_mesh.location = Vector((0, -0.6, 3.0))
    
    # -- Geometry Gen (Same as before) --
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.merge(type='CENTER')
    # Extrude 4m (Along Loc Z, which is Global -Z due to rotation? No, extrude is local usually? 
    # Extrude region move transform uses Global by default if not specified, 
    # but let's assume we are extruding along Normal which is Z).
    # To be safe: Extrude (0,0,4) Local.
    bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value":(0, 0, 4), "orient_type":'LOCAL'})
    
    # Subdivide
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.subdivide(number_cuts=2)
    
    # -- Skin Modifier --
    bpy.ops.object.mode_set(mode='OBJECT')
    mod = leg_mesh.modifiers.new(name="Skin", type='SKIN')
    
    # -- Tapering --
    bpy.ops.object.mode_set(mode='EDIT')
    me = leg_mesh.data
    bm = bmesh.from_edit_mesh(me)
    skin_layer = bm.verts.layers.skin.verify()
    
    for v in bm.verts:
        # v.co is Local Coordinates.
        # Base is at 0, Tip is at 4.
        z = v.co.z
        skin_data = v[skin_layer]
        
        # Wide at 0 (Base), Thin at 4 (Tip)
        # Radius 0.5 -> 0.2
        radius = 0.5 - (z * 0.075)
        if radius < 0.1: radius = 0.1
        skin_data.radius = (radius, radius)
        
    bmesh.update_edit_mesh(me)

    # --------------------------------------------------------------------
    # 4. GENERATE ARMATURE
    # --------------------------------------------------------------------
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.objects.active = leg_mesh
    bpy.ops.object.skin_armature_create(modifier="Skin")
    
    armature = bpy.context.active_object
    armature.name = "Leg_Rig"
    
    # --------------------------------------------------------------------
    # 5. IK TARGET
    # --------------------------------------------------------------------
    # Target at user requested location
    target_loc = Vector((0, -2.4562, 0.28973))
    
    bpy.ops.object.empty_add(type='SPHERE', radius=0.4, location=target_loc)
    ik_target = bpy.context.active_object
    ik_target.name = "IK_Target"
    
    # --------------------------------------------------------------------
    # 6. APPLY IK
    # --------------------------------------------------------------------
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')
    
    # Find the Tip Bone.
    # Since we rotated 180, Global Z of tip is lower.
    # But checking pose bones, we want the one furthest along the chain (Local Z=4).
    # Relying on "max Z" might be inverted now?
    # Actually, let's just find the bone with the highest LOCAL Z coordinate of tail?
    # Or just iterate and find the one that is distance ~4 from root?
    
    target_bone = None
    dist_max = -1.0
    
    for pbone in armature.pose.bones:
        # Distance of head from (0,0,0) local?
        head_dist = pbone.head.length
        tail_dist = pbone.tail.length
        if tail_dist > dist_max:
            dist_max = tail_dist
            target_bone = pbone
            
    if target_bone:
        c = target_bone.constraints.new('IK')
        c.target = ik_target
        c.chain_count = 0
        print(f"IK Applied to bone: {target_bone.name}")
        
        # FIX BEND DIRECTION
        parent_bone = target_bone.parent
        if parent_bone:
             parent_bone.rotation_mode = 'XYZ'
             parent_bone.rotation_euler.x = math.radians(45)
             print(f"Applied rotation hint to {parent_bone.name}")

    else:
        print("Error: Could not find tip bone.")

    # --------------------------------------------------------------------
    # 7. PARENT LEG TO BODY
    # --------------------------------------------------------------------
    # Parent Armature -> Body
    # Parent Leg Mesh -> Body
    # Usually parenting the Armature is enough if the mesh is parented to armature or moved by it.
    # The Mesh is "Skinned" to the armature.
    
    # User instructions: "Select Armature, Select Leg, Shift-select body, Parent Object".
    # This means Parent BOTH Armature and Mesh to Body.
    
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # 1. Parent Leg Mesh to Body
    leg_mesh.parent = body
    # Keeping transformation correct
    leg_mesh.matrix_parent_inverse = body.matrix_world.inverted()
    
    # 2. Parent Armature to Body
    armature.parent = body
    armature.matrix_parent_inverse = body.matrix_world.inverted()
    
    print("Parented Leg Mesh and Armature to Body.")

if __name__ == "__main__":
    create_spider_assembly()
