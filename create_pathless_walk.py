import bpy
import math
import random
from mathutils import Vector

def create_pathless_walk(target_obj_name="character_controller", explicit_start_angle=None):
    print(f"--------------------------------------------------")
    print(f"CREATING PATHLESS RANDOM WALK FOR: {target_obj_name}")
    print(f"--------------------------------------------------")

    if target_obj_name in bpy.data.objects:
        obj = bpy.data.objects[target_obj_name]
        
        # 1. Cleanup: Remove Follow Path Constraint if exists
        to_remove = [c for c in obj.constraints if c.type == 'FOLLOW_PATH']
        for c in to_remove:
            obj.constraints.remove(c)
            print("Removed existing Follow Path constraint.")

        # 2. Reset Location/Rotation
        obj.location = (0,0,0)
        obj.rotation_euler = (0,0,0)

        # 3. Create/Reset Action
        if not obj.animation_data:
            obj.animation_data_create()
            
        # New Action
        action = bpy.data.actions.new("RandomStrollDelta")
        obj.animation_data.action = action
        
        # 4. Generate Walk (Using DELTA Transforms)
        # This allows the user to manually move the object's main Location/Rotation
        # without fighting the animation.
        
        total_frames = 3000
        key_interval = 20
        speed_per_frame = 0.20
        
        # Start Deltas at 0
        current_delta_pos = Vector((0,0,0))
        # Initial offset for orientation (e.g. if model faces -Y)
        # We start walking in the direction of the Base Rotation + Offset
        orientation_offset = math.pi 
        current_delta_rot = orientation_offset 
        
        # Initial Keyframe
        obj.delta_location = current_delta_pos
        obj.delta_rotation_euler.z = current_delta_rot
        
        obj.keyframe_insert(data_path="delta_location", frame=1)
        obj.keyframe_insert(data_path="delta_rotation_euler", frame=1)
        
        obj.keyframe_insert(data_path="delta_rotation_euler", frame=1)
        
        # Get Base Rotation (Static for the Walk)
        if explicit_start_angle is not None:
             base_rot_z = explicit_start_angle
             print(f"DEBUG: Using EXPLICIT Start Angle: {math.degrees(base_rot_z):.2f}")
        else:
             base_rot_z = obj.rotation_euler.z
             print(f"DEBUG: Read Object Rotation: {math.degrees(base_rot_z):.2f}")
        
        # Logic for "Return to Start"
        start_delta_rot = orientation_offset
        cycle_period = 600
        return_duration = 120 # Duration (frames) to steer back
        
        for f in range(1 + key_interval, total_frames, key_interval):
            
            # Determine if we should steer back to start
            # Every 600 frames, for a brief window
            # e.g., if (f % 600) < 120
            time_in_cycle = f % cycle_period
            
            if time_in_cycle < return_duration and f > 100:
                # Steer towards start_delta_rot
                target = start_delta_rot
                curr = current_delta_rot
                diff = target - curr
                # Normalize -pi to pi
                while diff > math.pi: diff -= 2*math.pi
                while diff < -math.pi: diff += 2*math.pi
                
                # Apply strong bias
                max_turn = math.radians(20) # Sharper turn to return
                if abs(diff) < max_turn:
                    turn = diff
                else:
                    turn = max_turn if diff > 0 else -max_turn
            else:
                # Normal Random Wander
                turn = math.radians(random.uniform(-10, 10))

            current_delta_rot += turn
            
            # B. Move Forward in World Space
            # Direction = Base Rotation + Delta Rotation
            # This ensures we walk "Forward" relative to how the spider is facing
            move_angle = base_rot_z + current_delta_rot
            
            # Calculate World Space vector from Angle
            # Assuming +X is 0 radians. 
            # If the spider "Forward" is -Y (270 deg / pi*1.5)
            # We added 'orientation_offset = pi' above. 
            # So if base=0, rot=pi. Angle=pi (+X? No pi is -X).
            # If offset=pi, forward is -X?
            # Let's trust the math.pi offset works for the model alignment.
            
            forward_vec = Vector((math.cos(move_angle), math.sin(move_angle), 0))
            
            distance = speed_per_frame * key_interval
            current_delta_pos += forward_vec * distance
            
            # C. Set & Keyframe Deltas
            obj.delta_location = current_delta_pos
            obj.delta_rotation_euler.z = current_delta_rot
            
            obj.keyframe_insert(data_path="delta_location", frame=f)
            obj.keyframe_insert(data_path="delta_rotation_euler", frame=f)
            
        # 5. Set Interpolation to Linear
        # Recursive fix for Blender 4.3+ Layered Actions
        def set_linear_recursive(obj, visited=None):
            if visited is None: visited = set()
            if obj in visited: return
            visited.add(obj)
            
            # Helper to set interpolation on found curves
            def process_fcurves(fcurves_collection):
                for fcurve in fcurves_collection:
                    for k in fcurve.keyframe_points:
                        k.interpolation = 'LINEAR'

            if hasattr(obj, 'fcurves'):
                try: process_fcurves(obj.fcurves)
                except: pass
                
            search_attrs = ['layers', 'strips', 'channelbags']
            for attr in search_attrs:
                if hasattr(obj, attr):
                    try:
                        for item in getattr(obj, attr):
                            set_linear_recursive(item, visited)
                    except: pass

        set_linear_recursive(action)
                
        print(f"Generated random stroll for {total_frames} frames (Action: {action.name}).")
        
    else:
        print("Error: character_controller not found.")

if __name__ == "__main__":
    create_pathless_walk()
