"""
Spider Bot - Version 5 (Parenting Fix)
=====================================
Fixes the "floating legs" issue caused by incorrect parenting transforms.
Now legs attach firmly to the body and reach down to the ground.
"""

import bpy
import math
from mathutils import Vector, Matrix


def clear_scene():
    if bpy.context.active_object and bpy.context.active_object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    for block in bpy.data.meshes: bpy.data.meshes.remove(block)
    for block in bpy.data.armatures: bpy.data.armatures.remove(block)
    for block in bpy.data.curves: bpy.data.curves.remove(block)
    for block in bpy.data.actions: bpy.data.actions.remove(block)


def create_material(name, color):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = 0.5
    bsdf.inputs["Roughness"].default_value = 0.4
    return mat


def create_leg_with_armature(name, length=2.0, num_segments=3):
    # Create mesh
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    leg_obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(leg_obj)
    
    # Vertices going DOWN (-Z)
    segment_len = length / num_segments
    verts = [(0, 0, -i * segment_len) for i in range(num_segments + 1)]
    edges = [(i, i + 1) for i in range(num_segments)]
    mesh.from_pydata(verts, edges, [])
    mesh.update()
    
    # Skin modifier
    bpy.context.view_layer.objects.active = leg_obj
    skin_mod = leg_obj.modifiers.new(name="Skin", type='SKIN')
    
    # Radii
    for i, vert in enumerate(mesh.vertices):
        skin_vert = leg_obj.data.skin_vertices[0].data[i]
        t = i / num_segments
        radius = 0.12 * (1 - t * 0.5)
        skin_vert.radius = (radius, radius)
    
    leg_obj.modifiers.new(name="Subsurf", type='SUBSURF').levels = 1
    
    # Create armature
    armature = bpy.data.armatures.new(f"{name}_armature")
    arm_obj = bpy.data.objects.new(f"{name}_rig", armature)
    bpy.context.collection.objects.link(arm_obj)
    
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='EDIT')
    
    # Bones going DOWN
    prev_bone = None
    for i in range(num_segments):
        bone = armature.edit_bones.new(f"{name}_bone_{i}")
        bone.head = Vector((0, 0, -i * segment_len))
        bone.tail = Vector((0, 0, -(i + 1) * segment_len))
        if prev_bone:
            bone.parent = prev_bone
            bone.use_connect = True
        prev_bone = bone
    
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Link mesh to armature
    leg_obj.parent = arm_obj
    mod = leg_obj.modifiers.new('Armature', 'ARMATURE')
    mod.object = arm_obj
    
    # Vertex groups for binding
    for i in range(num_segments):
        vg = leg_obj.vertex_groups.new(name=f"{name}_bone_{i}")
        vg.add([i, i+1], 1.0, 'REPLACE')
        
    return leg_obj, arm_obj


def setup_ik(arm_obj, target):
    # Add IK constraint to last bone
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    
    last_bone = arm_obj.pose.bones[-1]
    ik = last_bone.constraints.new('IK')
    ik.target = target
    ik.chain_count = 3
    
    bpy.ops.object.mode_set(mode='OBJECT')


def create_walker():
    print("Building Spider Bot v5...")
    clear_scene()
    
    # Parameters
    BODY_HEIGHT = 2.0
    LEG_SPREAD_XY = 0.8
    FOOT_REACH = 2.2
    
    # 1. Create Body
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0)
    body = bpy.context.active_object
    body.name = "SpiderBody"
    body.scale = (1.0, 1.2, 0.5)
    bpy.ops.object.transform_apply(scale=True)
    body.location = (0, 0, BODY_HEIGHT)
    
    mat_body = create_material("BodyMat", (0.1, 0.1, 0.1))
    body.data.materials.append(mat_body)
    
    # 2. Controllers
    bpy.ops.object.empty_add(type='CUBE', radius=2.5, location=(0,0,0))
    char_ctrl = bpy.context.active_object
    char_ctrl.name = "Character_Controller"
    
    bpy.ops.object.empty_add(type='CIRCLE', radius=1.5, location=(0,0,BODY_HEIGHT))
    dir_ctrl = bpy.context.active_object
    dir_ctrl.name = "Direction_Controller"
    
    # Body hierarchy
    body.parent = dir_ctrl
    dir_ctrl.parent = char_ctrl
    
    # 3. Create Legs
    corners = [
        (1, 1, 45), (-1, 1, 135), (-1, -1, 225), (1, -1, 315)
    ]
    
    for i, (dx, dy, angle_deg) in enumerate(corners):
        # Calculate attach point relative to body
        local_x = dx * LEG_SPREAD_XY
        local_y = dy * LEG_SPREAD_XY
        
        # Create Leg Rig
        # Note: Leg creation makes it pointing DOWN at (0,0,0)
        leg_mesh, leg_rig = create_leg_with_armature(f"Leg_{i}")
        
        # Parenting Strategy:
        # Parent Rig to Body FIRST, then set Local Location
        leg_rig.parent = body
        leg_rig.location = (local_x, local_y, 0) # Relative to body center!
        
        # Rotation: Point outward
        # Leg points -Z. Rotate X positive to swing out?
        # A rotation of X=45 swings it from -Z towards +Y (in local space)
        # Then rotation Z orients that swing.
        angle_rad = math.radians(angle_deg)
        leg_rig.rotation_euler = (math.radians(40), 0, angle_rad - math.radians(90))
        # -90 on Z is usually needed depending on how "Forward" is defined. 
        # If leg swings to +Y, and we want it at 45 deg (X=Y), we rotate Z by -45?
        # Let's trust standard rotation: RotX swings Y-ward.
        # If angle is 45, we want X+Y. 45-90 = -45.
        
        # 4. IK Targets and Paths
        # Foot position in World Space (approximate)
        # We place path on ground
        
        foot_world_x = math.cos(angle_rad) * FOOT_REACH
        foot_world_y = math.sin(angle_rad) * FOOT_REACH
        
        # Path
        bpy.ops.curve.primitive_bezier_circle_add(radius=0.5, location=(foot_world_x, foot_world_y, 0))
        path = bpy.context.active_object
        path.name = f"Path_{i}"
        
        # Flatten path bottom
        # Rotate path to be vertical
        path.rotation_euler.x = math.radians(90)
        path.rotation_euler.z = angle_rad
        
        # Parent Path to Dir Controller (so it rotates with body steering)
        # But we need to be careful—if Char Controller moves, path moves.
        path.parent = dir_ctrl
        
        # Create IK Target Empty
        bpy.ops.object.empty_add(type='SPHERE', radius=0.1)
        ik_target = bpy.context.active_object
        ik_target.name = f"IK_{i}"
        
        # Constrain IK Target to Path
        follow = ik_target.constraints.new('FOLLOW_PATH')
        follow.target = path
        follow.use_fixed_location = True
        
        # Animate
        phase = 0.0 if i % 2 == 0 else 0.5
        ik_target["phase"] = phase # Custom prop just for info
        
        # Driver or Keyframes for walking
        # Let's use keyframes 0..40
        follow.offset_factor = 0.0
        follow.keyframe_insert("offset_factor", frame=1 + int(40*phase))
        follow.offset_factor = 1.0
        follow.keyframe_insert("offset_factor", frame=41 + int(40*phase))
        
        # Loop animation
        if ik_target.animation_data and ik_target.animation_data.action:
            for fc in ik_target.animation_data.action.fcurves:
                fc.extrapolation = 'LINEAR'
                for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
        
        # Setup IK on Leg
        setup_ik(leg_rig, ik_target)
        
        # Parent IK target to Dir Controller?
        # No, IK target is constrained to Path, Path is parented to Dir Controller.
        # So IK target moves with Path. Parent IK target to char_ctrl just for cleanup?
        # Actually IK target location is overridden by Constraint. Parenting determines "Rest" pos.
        ik_target.parent = dir_ctrl
        
    
    # 5. Animate Body Bob
    body.keyframe_insert("location", frame=1)
    if body.animation_data and body.animation_data.action:
        fc = body.animation_data.action.fcurves.find("location", index=2) # Z
        if fc:
            mod = fc.modifiers.new('NOISE')
            mod.scale = 10
            mod.strength = 0.1
            
    # 6. Animate Char Controller Forward
    char_ctrl.keyframe_insert("location", frame=1)
    char_ctrl.location.y = 10
    char_ctrl.keyframe_insert("location", frame=100)
    if char_ctrl.animation_data:
        for fc in char_ctrl.animation_data.action.fcurves:
            fc.extrapolation = 'LINEAR'

    # Ground
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0,0,0))
    
    print("Spider Bot v5 Complete.")

if __name__ == "__main__":
    create_walker()
