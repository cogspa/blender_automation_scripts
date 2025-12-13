import bpy
import bmesh
import math
import random
import os
from mathutils import Vector, Matrix

# ==================================================================================================
# OBSTACLE AVOIDANCE (raycast-based steering)
# Mark obstacles with: obj["is_obstacle"] = True
# ==================================================================================================
def raycast_obstacles_world(origin: Vector, direction: Vector, max_dist: float = 6.0):
    """
    Raycast against marked obstacles using scene.ray_cast (Fast).
    Returns: (hit: bool, hit_dist: float|None)
    """
    depsgraph = bpy.context.evaluated_depsgraph_get()
    direction = direction.normalized()
    
    # Cast ray into the scene
    hit, loc, normal, index, hit_obj, matrix = bpy.context.scene.ray_cast(depsgraph, origin, direction, distance=max_dist)
    
    if hit and hit_obj.get("is_obstacle"):
         dist = (loc - origin).length
         return True, dist
         
    return False, None


# ==================================================================================================
# MODULE 1: SPIDER ASSEMBLY (Body, Leg 0, Rig, IK)
# ==================================================================================================
def create_spider_assembly(clean_scene=True):
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    if clean_scene:
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()
        for _ in range(3):
            bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    else:
        # Minimal cleanup: remove only spider objects (keep obstacles)
        for n in ["Spider_Body", "Leg_Mesh", "Leg_Rig", "IK_Target", "WalkPath",
                  "Direction_Controller", "character_controller"]:
            if n in bpy.data.objects:
                bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)

    skullbox_path = "/Users/joem/.gemini/antigravity/scratch/blender_bridge/skullbox.blend"
    imported = False
    if os.path.exists(skullbox_path):
        try:
            with bpy.data.libraries.load(skullbox_path, link=False) as (data_from, data_to):
                found_name = None
                for potential in ["Textured_Cube", "Cube", "Textured Cube"]:
                    if potential in data_from.objects:
                        found_name = potential
                        break
                if found_name: data_to.objects = [found_name]
                elif data_from.objects: data_to.objects = [data_from.objects[0]]
            if data_to.objects:
                body = data_to.objects[0]
                bpy.context.collection.objects.link(body)
                body.name = "Spider_Body"
                body.location = (0, 0, 3.0)
                bpy.context.view_layer.objects.active = body
                body.select_set(True)
                imported = True
        except: pass
    
    if not imported:
        bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 3.0))
        body = bpy.context.active_object
        body.name = "Spider_Body"

    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
    leg_mesh = bpy.context.active_object
    leg_mesh.name = "Leg_Mesh"
    leg_mesh.rotation_euler.x = math.radians(180)
    leg_mesh.location = Vector((0, -0.6, 3.0))
    
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.merge(type='CENTER')
    bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value":(0, 0, 4), "orient_type":'LOCAL'})
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.subdivide(number_cuts=2)
    
    bpy.ops.object.mode_set(mode='OBJECT')
    mod = leg_mesh.modifiers.new(name="Skin", type='SKIN')
    
    bpy.ops.object.mode_set(mode='EDIT')
    me = leg_mesh.data
    bm = bmesh.from_edit_mesh(me)
    skin_layer = bm.verts.layers.skin.verify()
    for v in bm.verts:
        z = v.co.z
        skin_data = v[skin_layer]
        radius = 0.5 - (z * 0.075)
        if radius < 0.1: radius = 0.1
        skin_data.radius = (radius, radius)
    bmesh.update_edit_mesh(me)

    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.objects.active = leg_mesh
    bpy.ops.object.skin_armature_create(modifier="Skin")
    armature = bpy.context.active_object
    armature.name = "Leg_Rig"
    
    target_loc = Vector((0, -2.4562, 0.28973))
    bpy.ops.object.empty_add(type='SPHERE', radius=0.4, location=target_loc)
    ik_target = bpy.context.active_object
    ik_target.name = "IK_Target"
    
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='POSE')
    target_bone = None
    dist_max = -1.0
    for pbone in armature.pose.bones:
        # NOTE: keeping your original selection logic unchanged
        tail_dist = pbone.tail.length
        if tail_dist > dist_max:
            dist_max = tail_dist
            target_bone = pbone
    if target_bone:
        c = target_bone.constraints.new('IK')
        c.target = ik_target
        c.chain_count = 0
        parent_bone = target_bone.parent
        if parent_bone:
             parent_bone.rotation_mode = 'XYZ'
             parent_bone.rotation_euler.x = math.radians(45)

    bpy.ops.object.mode_set(mode='OBJECT')
    leg_mesh.parent = body
    leg_mesh.matrix_parent_inverse = body.matrix_world.inverted()
    armature.parent = body
    armature.matrix_parent_inverse = body.matrix_world.inverted()

# ==================================================================================================
# MODULE 2: WALK PATH
# ==================================================================================================
def create_circular_path():
    if "WalkPath" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["WalkPath"], do_unlink=True)

    target_loc = Vector((0, -2.4562, 0.28973))
    curve_data = bpy.data.curves.new(name="WalkPathData", type='CURVE')
    curve_data.dimensions = '3D'
    spline = curve_data.splines.new('BEZIER')
    spline.use_cyclic_u = True
    r = 0.8
    h = 1.2
    spline.bezier_points.add(2)
    p0 = spline.bezier_points[0]
    p0.co = Vector((-r, 0, 0))
    p0.handle_left = Vector((-r, 0, 0))
    p0.handle_right = Vector((-r, 0, r))
    p0.handle_left_type = 'VECTOR'
    p0.handle_right_type = 'FREE'
    p1 = spline.bezier_points[1]
    p1.co = Vector((0, 0, h))
    p1.handle_left = Vector((-r*0.5, 0, h)) 
    p1.handle_right = Vector((r*0.5, 0, h))
    p1.handle_left_type = 'ALIGNED'
    p1.handle_right_type = 'ALIGNED'
    p2 = spline.bezier_points[2]
    p2.co = Vector((r, 0, 0))
    p2.handle_left = Vector((r, 0, r))
    p2.handle_right = Vector((r, 0, 0))
    p2.handle_left_type = 'FREE'
    p2.handle_right_type = 'VECTOR'
    
    object_loc = Vector((target_loc.x, target_loc.y, 0.0))
    path = bpy.data.objects.new("WalkPath", curve_data)
    path.location = object_loc
    path.rotation_euler.z = math.radians(90)
    bpy.context.collection.objects.link(path)
    bpy.context.view_layer.objects.active = path

    if "IK_Target" in bpy.data.objects:
        ik_target = bpy.data.objects["IK_Target"]
        to_remove = [c for c in ik_target.constraints if c.type == 'FOLLOW_PATH']
        for c in to_remove: ik_target.constraints.remove(c)
        if ik_target.animation_data: ik_target.animation_data_clear()
        
        c = ik_target.constraints.new('FOLLOW_PATH')
        c.name = "WalkConstraint"
        c.target = path
        ik_target.location = (0, 0, 0)
        c.offset = 0
        c.keyframe_insert(data_path="offset", frame=10)
        c.offset = 100
        c.keyframe_insert(data_path="offset", frame=30)
        
        if ik_target.animation_data and ik_target.animation_data.action:
            action = ik_target.animation_data.action
            def recursive_fix(obj, visited=None):
                if visited is None: visited = set()
                if obj in visited: return
                visited.add(obj)
                if hasattr(obj, 'data_path') and hasattr(obj, 'keyframe_points') and hasattr(obj, 'extrapolation'):
                     if 'WalkConstraint' in obj.data_path and 'offset' in obj.data_path:
                        obj.extrapolation = 'LINEAR'
                        for k in obj.keyframe_points: k.interpolation = 'LINEAR'
                     return
                search_attrs = ['layers', 'strips', 'channelbags', 'fcurves']
                for attr in search_attrs:
                    if hasattr(obj, attr):
                        try:
                            for item in getattr(obj, attr): recursive_fix(item, visited)
                        except: pass
            recursive_fix(action)

# ==================================================================================================
# MODULE 3: MASTER CONTROLLER
# ==================================================================================================
def create_master_controller():
    if "character_controller" in bpy.data.objects:
        master = bpy.data.objects["character_controller"]
    else:
        bpy.ops.object.empty_add(type='CUBE', location=(0,0,0))
        master = bpy.context.active_object
        master.name = "character_controller"
        master.empty_display_size = 5.0

    # Use DIRECT parenting instead of bpy.ops.object.parent_set
    children_to_parent = []
    if "Direction_Controller" in bpy.data.objects: 
        children_to_parent.append(bpy.data.objects["Direction_Controller"])
    if "Spider_Body" in bpy.data.objects: 
        children_to_parent.append(bpy.data.objects["Spider_Body"])
    for obj in bpy.data.objects:
        if obj.name.startswith("WalkPath"): 
            children_to_parent.append(obj)
        # NOTE: IK_Targets are constrained to WalkPath, which is parented.
        # Parenting IK_Targets to master might cause double-transform or constraint conflicts.
        # We rely on 'create_swarm' constraint recursion to duplicate them.
            
    # Direct parenting assignment (more reliable than operator)
    for child in children_to_parent:
        if child.parent != master:
            child.parent = master
            child.matrix_parent_inverse = master.matrix_world.inverted()
    
    # Force update
    bpy.context.view_layer.update()

# ==================================================================================================
# MODULE 4: BODY NOISE
# ==================================================================================================
def add_body_noise(target_name="Spider_Body"):
    if target_name in bpy.data.objects:
        body = bpy.data.objects[target_name]
        body.keyframe_insert(data_path="rotation_euler", frame=1)
        if body.animation_data and body.animation_data.action:
            action = body.animation_data.action
            def process_fcurves(fcurves, visited=None):
                if visited is None: visited = set()
                for fcurve in fcurves:
                    if fcurve in visited: continue
                    visited.add(fcurve)
                    mod_noise = fcurve.modifiers.new('NOISE')
                    mod_noise.scale = 20.0
                    mod_noise.strength = 0.05
                    mod_noise.phase = random.uniform(0, 100)
            def recursive_find_curves(obj, visited=None):
                if visited is None: visited = set()
                if obj in visited: return
                visited.add(obj)
                if hasattr(obj, 'fcurves'): process_fcurves(obj.fcurves)
                search_attrs = ['layers', 'strips', 'channelbags']
                for attr in search_attrs:
                    if hasattr(obj, attr):
                        try:
                            for item in getattr(obj, attr): recursive_find_curves(item, visited)
                        except: pass
            recursive_find_curves(action)

# ==================================================================================================
# MODULE 5: PATHLESS WALK (Delta Animation) + OBSTACLE AVOIDANCE
# ==================================================================================================
def create_pathless_walk(target_obj_name="character_controller", explicit_start_angle=None):
    if target_obj_name in bpy.data.objects:
        obj = bpy.data.objects[target_obj_name]
        if not obj.animation_data: obj.animation_data_create()
        action =  bpy.data.actions.new(name=f"Walk_{target_obj_name}")
        obj.animation_data.action = action
        
        total_frames = 3000
        key_interval = 20
        speed_per_frame = 0.20

        # Avoidance tuning
        look_ahead = 10.0
        side_angle = math.radians(35)
        avoid_turn = math.radians(35)
        brake_factor = 0.55

        current_delta_pos = Vector((0,0,0))
        orientation_offset = math.pi 
        current_delta_rot = orientation_offset 
        
        obj.delta_location = current_delta_pos
        obj.delta_rotation_euler.z = current_delta_rot
        obj.keyframe_insert(data_path="delta_location", frame=1)
        obj.keyframe_insert(data_path="delta_rotation_euler", frame=1)
        
        if explicit_start_angle is not None:
             base_rot_z = explicit_start_angle
        else:
             base_rot_z = obj.rotation_euler.z
        
        start_delta_rot = orientation_offset
        cycle_period = 600
        return_duration = 120 
        
        for f in range(1 + key_interval, total_frames, key_interval):
            time_in_cycle = f % cycle_period
            if time_in_cycle < return_duration and f > 100:
                target = start_delta_rot
                curr = current_delta_rot
                diff = target - curr
                while diff > math.pi: diff -= 2*math.pi
                while diff < -math.pi: diff += 2*math.pi
                max_turn = math.radians(20) 
                if abs(diff) < max_turn: turn = diff
                else: turn = max_turn if diff > 0 else -max_turn
            else:
                turn = math.radians(random.uniform(-10, 10))

            # --- Obstacle avoidance
            origin = obj.location + current_delta_pos
            heading = base_rot_z + current_delta_rot
            fwd = Vector((math.cos(heading), math.sin(heading), 0.0))
            left = Vector((math.cos(heading + side_angle), math.sin(heading + side_angle), 0.0))
            right = Vector((math.cos(heading - side_angle), math.sin(heading - side_angle), 0.0))

            hit_f, dist_f = raycast_obstacles_world(origin, fwd, max_dist=look_ahead)
            if hit_f:
                hit_l, _ = raycast_obstacles_world(origin, left, max_dist=look_ahead * 0.8)
                hit_r, _ = raycast_obstacles_world(origin, right, max_dist=look_ahead * 0.8)

                if hit_l and not hit_r:
                    turn -= avoid_turn   # go right
                elif hit_r and not hit_l:
                    turn += avoid_turn   # go left
                else:
                    turn += avoid_turn if (hash(obj.name) % 2 == 0) else -avoid_turn

                if dist_f is not None:
                    closeness = max(0.0, min(1.0, 1.0 - (dist_f / look_ahead)))
                    slow = 1.0 - (closeness * (1.0 - brake_factor))
                else:
                    slow = 1.0
            else:
                slow = 1.0

            current_delta_rot += turn
            move_angle = base_rot_z + current_delta_rot
            forward_vec = Vector((math.cos(move_angle), math.sin(move_angle), 0))
            distance = (speed_per_frame * key_interval) * slow
            current_delta_pos += forward_vec * distance
            obj.delta_location = current_delta_pos
            obj.delta_rotation_euler.z = current_delta_rot
            obj.keyframe_insert(data_path="delta_location", frame=f)
            obj.keyframe_insert(data_path="delta_rotation_euler", frame=f)
            
        def set_linear_recursive(obj, visited=None):
            if visited is None: visited = set()
            if obj in visited: return
            visited.add(obj)
            def process_fcurves(fcurves_collection):
                for fcurve in fcurves_collection:
                    for k in fcurve.keyframe_points: k.interpolation = 'LINEAR'
            if hasattr(obj, 'fcurves'):
                try: process_fcurves(obj.fcurves)
                except: pass
            search_attrs = ['layers', 'strips', 'channelbags']
            for attr in search_attrs:
                if hasattr(obj, attr):
                    try:
                        for item in getattr(obj, attr): set_linear_recursive(item, visited)
                    except: pass
        set_linear_recursive(action)

# ==================================================================================================
# MODULE 6: LOGIC HELPERS
# ==================================================================================================
def duplicate_legs_logic():
    bpy.ops.object.select_all(action='DESELECT')
    if "Spider_Body" in bpy.data.objects:
        body = bpy.data.objects["Spider_Body"]
        body.select_set(True)
        bpy.ops.object.select_all(action='INVERT')
        body.select_set(False)
    else: return
    base_objs = bpy.context.selected_objects
    if not base_objs: return
    bpy.context.view_layer.objects.active = base_objs[0]
    angles = [90, 180, 270]
    for angle_deg in angles:
        bpy.ops.object.select_all(action='DESELECT')
        for obj in base_objs: obj.select_set(True)
        bpy.ops.object.duplicate(linked=False)
        new_objs = bpy.context.selected_objects
        rad = math.radians(angle_deg)
        rot_mat = Matrix.Rotation(rad, 4, 'Z')
        for obj in new_objs: obj.matrix_world = rot_mat @ obj.matrix_world
    paths = [o for o in bpy.data.objects if o.name.startswith("WalkPath")]
    for p in paths: p.rotation_euler = (0,0,0) 
    targets = [o for o in bpy.data.objects if o.name.startswith("IK_Target")]
    for t in targets: t.location = (0,0,0) 

def shift_keys_recursive(obj, shift_val, visited=None):
    if visited is None: visited = set()
    if obj in visited: return
    visited.add(obj)
    if hasattr(obj, 'keyframe_points'):
        for k in obj.keyframe_points:
            k.co[0] += shift_val
            k.handle_left[0] += shift_val
            k.handle_right[0] += shift_val
    search_attrs = ['layers', 'strips', 'channelbags', 'fcurves']
    for attr in search_attrs:
        if hasattr(obj, attr):
            try:
                for item in getattr(obj, attr): shift_keys_recursive(item, shift_val, visited)
            except: pass

def offset_gait_logic():
    targets_to_offset = ["IK_Target.001", "IK_Target.003"]
    offset = -10.0
    for name in targets_to_offset:
        if name in bpy.data.objects:
            obj = bpy.data.objects[name]
            if obj.animation_data and obj.animation_data.action:
                shift_keys_recursive(obj.animation_data.action, offset)

def create_steering_logic():
    if "Direction_Controller" not in bpy.data.objects:
        bpy.ops.object.empty_add(type='SPHERE', location=(0,0,0))
        ctrl = bpy.context.active_object
        ctrl.name = "Direction_Controller"
        ctrl.empty_display_size = 3.0
    ctrl = bpy.data.objects["Direction_Controller"]
    paths = [o for o in bpy.data.objects if o.name.startswith("WalkPath")]
    for p in paths:
        already_has = False
        for c in p.constraints:
            if c.type == 'COPY_ROTATION' and c.target == ctrl: already_has = True
        if not already_has:
            c = p.constraints.new('COPY_ROTATION')
            c.target = ctrl
            c.name = "Steering"

def build_spider():
    # IMPORTANT: keep obstacle geometry in the scene
    create_spider_assembly(clean_scene=False)
    create_circular_path()
    duplicate_legs_logic()
    offset_gait_logic()
    create_steering_logic()
    create_master_controller()
    
    # Verify and Force Parenting for Duplication Stability
    if "character_controller" in bpy.data.objects and "Spider_Body" in bpy.data.objects:
        master = bpy.data.objects["character_controller"]
        body = bpy.data.objects["Spider_Body"]
        if body.parent != master:
            body.parent = master
            body.matrix_parent_inverse = master.matrix_world.inverted()
            
    add_body_noise()

# ==================================================================================================
# MODULE 7: SWARM GENERATOR
# ==================================================================================================
def create_swarm(count=49, range_x=100, range_y=100):
    source_name = "character_controller"
    if source_name not in bpy.data.objects:
        build_spider()
        if source_name not in bpy.data.objects: return

    # FORCE view layer update to ensure parenting is resolved
    bpy.context.view_layer.update()
    
    source_obj = bpy.data.objects[source_name]
    
    # DEBUG: Verify children exist
    print(f"Source children BEFORE loop: {[c.name for c in source_obj.children]}")
    
    # If Spider_Body not a child, fix it now
    if "Spider_Body" in bpy.data.objects:
        body = bpy.data.objects["Spider_Body"]
        if body.parent != source_obj:
            print("WARNING: Spider_Body not parented! Fixing...")
            body.parent = source_obj
            body.matrix_parent_inverse = source_obj.matrix_world.inverted()
            bpy.context.view_layer.update()
            print(f"Source children AFTER fix: {[c.name for c in source_obj.children]}")

    spawned_positions = []
    spawned_positions.append(source_obj.location.to_2d())
    create_pathless_walk(source_name)
    
    rx = random.uniform(-range_x, range_x)
    ry = random.uniform(-range_y, range_y)
    source_obj.location.x = rx
    source_obj.location.y = ry
    spawned_positions[0] = source_obj.location.to_2d()

    for i in range(count):
        source_master = bpy.data.objects[source_name]
        objects_to_dup = set()
        objects_to_dup.add(source_master)
        def recurse(obj):
            for child in obj.children:
                if child.name not in [o.name for o in objects_to_dup]:
                    objects_to_dup.add(child)
                    recurse(child)
        recurse(source_master)
        
        if i == 0:
            msg = f"DEBUG: Source Master Children: {[c.name for c in source_master.children]}\n"
            msg += f"DEBUG: Objects to Dup ({len(objects_to_dup)}): {[o.name for o in objects_to_dup]}\n"
            print(msg)
            try:
                with open("/Users/joem/.gemini/antigravity/scratch/blender_bridge/swarm_debug_log.txt", "w") as f:
                    f.write(msg)
            except: pass

        base_list = list(objects_to_dup)
        for obj in base_list:
            for c in obj.constraints:
                if c.target and c.target not in objects_to_dup: objects_to_dup.add(c.target)
            if obj.type == 'ARMATURE':
                for pb in obj.pose.bones:
                    for c in pb.constraints:
                        if c.target and c.target not in objects_to_dup: objects_to_dup.add(c.target)

        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects_to_dup: obj.select_set(True)
        bpy.context.view_layer.objects.active = source_master
        bpy.ops.object.duplicate(linked=False)
        new_master = bpy.context.view_layer.objects.active
        
        found_spot = False
        attempts = 0
        min_dist = 15.0 
        rx, ry = 0, 0
        while not found_spot and attempts < 100:
            rx = random.uniform(-range_x, range_x)
            ry = random.uniform(-range_y, range_y)
            pos_2d = Vector((rx, ry))
            too_close = False
            for p in spawned_positions:
                if (p - pos_2d).length < min_dist:
                    too_close = True
                    break
            if not too_close: found_spot = True
            else: attempts += 1
        spawned_positions.append(Vector((rx, ry)))
        
        group_idx = i % 4
        directions = [0, math.pi/2, math.pi, 3*math.pi/2]
        rz = directions[group_idx] + random.uniform(-0.2, 0.2)
        
        new_master.location.x = rx
        new_master.location.y = ry
        new_master.rotation_euler.z = rz
        new_master.animation_data_clear() 
        for obj in bpy.context.selected_objects:
            if "IK_Target" in obj.name: obj.location = (0,0,0)
            
        # FIX CONSTRAINT REFERENCES (Smart Re-bind by Rotation)
        new_objects = bpy.context.selected_objects
        local_paths = [o for o in new_objects if o.name.startswith("WalkPath")]
        local_targets = [o for o in new_objects if "IK_Target" in o.name]
        
        for targ in local_targets:
            best_path = None
            
            # ONE: Try Exact Component Name Suffix Match (e.g. Target.007 -> Path.007)
            # This relies on Blender incrementing names consistently in a duplicate operation.
            target_suffix = targ.name.split('.')[-1] if '.' in targ.name else ""
            for path in local_paths:
                path_suffix = path.name.split('.')[-1] if '.' in path.name else ""
                if path_suffix == target_suffix:
                    best_path = path
                    break
            
            # TWO: Fallback to Rotation Match
            if not best_path:
                min_diff = 1000.0
                t_rot = targ.rotation_euler.z % (2*math.pi)
                for path in local_paths:
                    p_rot = path.rotation_euler.z % (2*math.pi)
                    diff = abs(p_rot - t_rot)
                    if diff > math.pi: diff = (2*math.pi) - diff
                    if diff < min_diff:
                        min_diff = diff
                        best_path = path if min_diff < 0.2 else None

            # Bind 
            if best_path: 
                 for c in targ.constraints:
                        if c.type == 'FOLLOW_PATH':
                            c.target = best_path
                            
        bpy.context.view_layer.update()
        create_pathless_walk(new_master.name, explicit_start_angle=rz)
        for obj in bpy.context.selected_objects:
            if "Spider_Body" in obj.name: add_body_noise(obj.name)

    controllers = [o for o in bpy.data.objects if o.name.startswith("character_controller")]
    for ctrl in controllers:
        if ctrl.location.length < 0.1:
             rx = random.uniform(-range_x, range_x)
             ry = random.uniform(-range_y, range_y)
             ctrl.location.x = rx
             ctrl.location.y = ry
    print(f"Swarm Created: {len(controllers)} Spiders.")

if __name__ == "__main__":
    create_swarm(count=119, range_x=150, range_y=150)
    bpy.context.scene.frame_end = 3000
  