import bpy
import math
import random

# -------------------------------------------------------------------
# Utility helpers
# -------------------------------------------------------------------

def clear_scene():
    if bpy.context.active_object and bpy.context.active_object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    
    # Clear orphan data
    for block in bpy.data.meshes:
        if block.users == 0: bpy.data.meshes.remove(block)
    for block in bpy.data.armatures:
        if block.users == 0: bpy.data.armatures.remove(block)
    for block in bpy.data.curves:
        if block.users == 0: bpy.data.curves.remove(block)
    for block in bpy.data.actions:
        if block.users == 0: bpy.data.actions.remove(block)


def ensure_frame_range(end=250):
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = end


# -------------------------------------------------------------------
# Create leg base mesh with Skin modifier and armature
# -------------------------------------------------------------------

def create_leg_with_skin(creation_location=(0,0,0)):
    """
    Creates a simple vertical chain of vertices, adds a Skin modifier,
    and generates an armature from it.
    Returns: (leg_obj, armature_obj)
    """
    # Create an empty mesh and object
    mesh = bpy.data.meshes.new("LegMesh")
    obj = bpy.data.objects.new("Leg", mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = creation_location

    # Make it active
    bpy.context.view_layer.objects.active = obj

    # Build a simple 4-vertex chain along Z (0 -> 4)
    import bmesh
    bm = bmesh.new()
    v0 = bm.verts.new((0, 0, 0.0))
    v1 = bm.verts.new((0, 0, 1.3))
    v2 = bm.verts.new((0, 0, 2.6))
    v3 = bm.verts.new((0, 0, 4.0))
    bm.edges.new((v0, v1))
    bm.edges.new((v1, v2))
    bm.edges.new((v2, v3))
    bm.to_mesh(mesh)
    bm.free()

    # Add Skin modifier
    skin_mod = obj.modifiers.new("Skin", 'SKIN')

    # Skin vertices radii
    skin_layer = obj.data.skin_vertices[0].data
    skin_layer[0].radius = (0.35, 0.35)
    skin_layer[1].radius = (0.28, 0.28)
    skin_layer[2].radius = (0.2, 0.2)
    skin_layer[3].radius = (0.12, 0.12)

    # Mark root for Skin modifier
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.data.vertices[0].select = True
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.object.skin_root_mark()
    bpy.ops.object.mode_set(mode='OBJECT')

    # Generate armature from Skin modifier
    bpy.context.view_layer.objects.active = obj
    for o in bpy.context.selected_objects:
        o.select_set(False)
    obj.select_set(True)

    bpy.ops.object.skin_armature_create(modifier=skin_mod.name)

    armature = None
    for o in bpy.context.selected_objects:
        if o.type == 'ARMATURE':
            armature = o

    assert armature is not None, "Armature creation failed"

    return obj, armature


# -------------------------------------------------------------------
# IK setup
# -------------------------------------------------------------------

def setup_leg_ik(armature, name_suffix=""):
    """
    Adds an Empty as IK target for the last bone of the armature.
    Returns: ik_empty
    """
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')

    last_pbone = armature.pose.bones[-1]

    # Create empty at bone tail
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=armature.matrix_world @ last_pbone.tail)
    ik_empty = bpy.context.active_object
    ik_empty.name = f"IK_Target{name_suffix}"

    # Add IK constraint
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')

    ik_con = last_pbone.constraints.new('IK')
    ik_con.name = f"IK_Constraint{name_suffix}"
    ik_con.chain_count = 3
    ik_con.target = ik_empty

    bpy.ops.object.mode_set(mode='OBJECT')
    return ik_empty


# -------------------------------------------------------------------
# Body and fake joint
# -------------------------------------------------------------------

def create_body_and_joint():
    """
    Creates a cube body and a fake joint icosphere.
    Returns: (body_obj, joint_obj)
    """
    bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0, 0, 2.0))
    body = bpy.context.active_object
    body.name = "Body"

    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=0.4, location=(0.0, 0, 3.8))
    joint = bpy.context.active_object
    joint.name = "HipJoint"
    bpy.ops.object.shade_smooth()

    return body, joint


def parent_leg_to_body(leg_obj, armature, joint, body):
    # Parenting logic:
    # 1. Joint is parented to Body
    # 2. Armature is parented to Joint (so leg rotates with joint)
    # 3. Leg Mesh is parented to Body (or Armature, skinning handles deform usually)
    # Wait, simple parenting:
    joint.parent = body
    leg_obj.parent = body # In a real rig, mesh usually parented to Armature
    armature.parent = body # Or joint
    
    # Let's parent Armature to Body for now, and Joint to Body
    # Ideally Joint connects body and leg visual.
    
    joint.location = (leg_obj.location.x, leg_obj.location.y, 4.0) # Move joint to top of leg
    joint.parent = body
    armature.parent = body # Simple parenting
    

# -------------------------------------------------------------------
# Path and Follow Path constraint for IK target
# -------------------------------------------------------------------

def create_walk_path_and_constraint(ik_empty, name_suffix=""):
    """
    Creates a Bezier circle path, rotates it, and
    adds a Follow Path constraint to the IK target.
    Returns: path_curve_obj
    """
    # Create path near the leg's location
    bpy.ops.curve.primitive_bezier_circle_add(radius=1.5, location=(ik_empty.location.x, ik_empty.location.y, 0.0))
    path = bpy.context.active_object
    path.name = f"WalkPath{name_suffix}"

    # Rotate 90 degrees on X so it cycles vertically (step motion)
    path.rotation_euler[0] = math.radians(90)

    con = ik_empty.constraints.new('FOLLOW_PATH')
    con.name = f"FollowPath{name_suffix}"
    con.target = path
    con.use_fixed_location = True
    con.offset_factor = 0.0

    # Animate offset factor 0->1
    ik_empty.constraints[con.name].keyframe_insert(data_path="offset_factor", frame=1)
    ik_empty.constraints[con.name].offset_factor = 1.0
    ik_empty.constraints[con.name].keyframe_insert(data_path="offset_factor", frame=40)

    # Linear Extrapolation for looping
    if ik_empty.animation_data and ik_empty.animation_data.action:
        for fcurve in ik_empty.animation_data.action.fcurves:
            if "offset_factor" in fcurve.data_path:
                for kp in fcurve.keyframe_points:
                    kp.interpolation = 'LINEAR'
                fcurve.extrapolation = 'LINEAR'

    return path


# -------------------------------------------------------------------
# Direction controller
# -------------------------------------------------------------------

def create_direction_controller_and_constraints(paths):
    bpy.ops.object.empty_add(type='SPHERE', location=(0, 0, 5.0))
    direction_ctrl = bpy.context.active_object
    direction_ctrl.name = "Direction_Controller"
    direction_ctrl.empty_display_size = 0.5

    for path in paths:
        con = path.constraints.new('COPY_ROTATION')
        con.target = direction_ctrl
        # Usually we want Z rotation only for steering
        con.use_x = False
        con.use_y = False
        con.use_z = True

    return direction_ctrl


# -------------------------------------------------------------------
# Noise
# -------------------------------------------------------------------

def add_noise_to_body(body):
    bpy.context.view_layer.objects.active = body
    if not body.animation_data:
        body.animation_data_create()
    
    body.keyframe_insert(data_path="location", frame=1)
    body.keyframe_insert(data_path="rotation_euler", frame=1)

    action = body.animation_data.action
    
    def add_noise_mod(data_path, index, scale, strength, phase):
        fc = action.fcurves.find(data_path, index=index)
        if fc:
            # Check existing modifiers
            if len(fc.modifiers) == 0:
                mod = fc.modifiers.new('NOISE')
                mod.scale = scale
                mod.strength = strength
                mod.phase = phase

    # Add bobbing and weaving
    add_noise_mod("location", 0, 20, 0.5, 0) # X wobble
    add_noise_mod("location", 2, 10, 0.5, 10) # Z bob
    add_noise_mod("rotation_euler", 2, 30, 0.1, 5) # Z rotation wobble


# -------------------------------------------------------------------
# Character Controller (The missing piece)
# -------------------------------------------------------------------

def create_character_controller(body, direction_controller, paths, ik_targets):
    """
    Creates a big Empty, parents body, direction controller,
    paths, and IK targets to it, then animates it moving forward.
    """
    bpy.ops.object.empty_add(type='CUBE', location=(0, 0, 0))
    char_ctrl = bpy.context.active_object
    char_ctrl.name = "Character_Controller"
    char_ctrl.empty_display_size = 2.0
    
    # Parent everything to this controller
    # Use keep transform so they don't jump
    body.parent = char_ctrl
    body.matrix_parent_inverse = char_ctrl.matrix_world.inverted()
    
    direction_controller.parent = char_ctrl
    direction_controller.matrix_parent_inverse = char_ctrl.matrix_world.inverted()
    
    for p in paths:
        p.parent = char_ctrl
        p.matrix_parent_inverse = char_ctrl.matrix_world.inverted()
        
    for ik in ik_targets:
        # IK targets must move with character, but their local motion is controlled by path
        ik.parent = char_ctrl
        ik.matrix_parent_inverse = char_ctrl.matrix_world.inverted()
        
    # Animate walking forward (Y axis)
    char_ctrl.location.y = 0
    char_ctrl.keyframe_insert(data_path="location", frame=1)
    char_ctrl.location.y = 20
    char_ctrl.keyframe_insert(data_path="location", frame=100)
    
    # Linear movement
    if char_ctrl.animation_data and char_ctrl.animation_data.action:
        for fc in char_ctrl.animation_data.action.fcurves:
            if "location" in fc.data_path and fc.array_index == 1: # Y axis
                for kp in fc.keyframe_points:
                    kp.interpolation = 'LINEAR'
                fc.extrapolation = 'LINEAR'
                
    return char_ctrl

# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------

def main():
    clear_scene()
    ensure_frame_range(200)
    
    # Create Body
    body, joint = create_body_and_joint()
    
    # Create ONE Leg (as requested initially)
    # We can offset it slightly to the side
    leg_obj, armature = create_leg_with_skin()
    leg_obj.location = (1.5, 0, 3.5) # Position under body corner
    # Move armature to match leg
    armature.location = leg_obj.location
    armature.location.z = 0 # Armature root at 0? No, skin armature creation puts it at origin relative to mesh
    
    # Actually skin operator puts armature at mesh origin
    # Let's adjust armature and mesh locations together
    # Reset locations to origin for setup simplicity?
    # No, let's just accept where they are.
    
    # Setup IK
    ik_target = setup_leg_ik(armature, "_Left")
    
    # Create Path
    path = create_walk_path_and_constraint(ik_target, "_Left")
    
    # Setup Hierarchy
    parent_leg_to_body(leg_obj, armature, joint, body)
    
    # Direction Controller
    dir_ctrl = create_direction_controller_and_constraints([path])
    
    # Add noise
    add_noise_to_body(body)
    
    # Character Controller move
    create_character_controller(body, dir_ctrl, [path], [ik_target])
    
    print(" procedural leg setup complete.")

if __name__ == "__main__":
    main()
