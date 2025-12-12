import bpy
import math
import random
from mathutils import Vector

def create_pathless_walk(target_obj_name="character_controller"):
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
        
        total_frames = 1000
        key_interval = 20
        speed_per_frame = 0.20
        
        # Start Deltas at 0
        current_delta_pos = Vector((0,0,0))
        current_delta_angle = 0.0 # Relative to base rotation
        
        # Initial Keyframe
        obj.delta_location = current_delta_pos
        obj.delta_rotation_euler.z = current_delta_angle
        
        obj.keyframe_insert(data_path="delta_location", frame=1)
        obj.keyframe_insert(data_path="delta_rotation_euler", frame=1)
        
        # Random initial direction (relative)
        current_delta_angle = math.pi 
        
        for f in range(1 + key_interval, total_frames, key_interval):
            # A. Random Turn
            turn = math.radians(random.uniform(-10, 10))
            current_delta_angle += turn
            
            # B. Move Forward
            # Direction is based on Base Rotation + Delta Angle.
            # Ideally, we just compute forward based on Delta Angle, 
            # and the Base Rotation rotates the whole path.
            # So forward = (cos(delta), sin(delta))
            
            forward_vec = Vector((math.cos(current_delta_angle), math.sin(current_delta_angle), 0))
            
            distance = speed_per_frame * key_interval
            current_delta_pos += forward_vec * distance
            
            # C. Set & Keyframe Deltas
            obj.delta_location = current_delta_pos
            obj.delta_rotation_euler.z = current_delta_angle
            
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
