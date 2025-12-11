import bpy
import math
import random
from mathutils import Vector

def create_pathless_walk():
    print("--------------------------------------------------")
    print("CREATING PATHLESS RANDOM WALK (CONTINUOUS)")
    print("--------------------------------------------------")

    if "character_controller" in bpy.data.objects:
        obj = bpy.data.objects["character_controller"]
        
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
        action = bpy.data.actions.new("RandomStroll")
        obj.animation_data.action = action
        
        # 4. Generate Walk
        total_frames = 1000
        key_interval = 20 # Keyframe every 20 frames
        speed_per_frame = 0.20 # Even Faster (was 0.10)
        
        current_pos = Vector((0,0,0))
        current_angle = math.pi 
        
        # Initial Keyframe
        obj.location = current_pos
        obj.rotation_euler.z = current_angle
        obj.keyframe_insert(data_path="location", frame=1)
        obj.keyframe_insert(data_path="rotation_euler", frame=1)
        
        for f in range(1 + key_interval, total_frames, key_interval):
            # A. Random Turn
            # Change angle by random amount (Reduced Rotation as requested)
            turn = math.radians(random.uniform(-10, 10)) # Was -45, 45
            current_angle += turn
            
            # B. Move Forward in New Direction
            # Assuming +X is Forward
            forward_vec = Vector((math.cos(current_angle), math.sin(current_angle), 0))
            
            distance = speed_per_frame * key_interval
            current_pos += forward_vec * distance
            
            # C. Set & Keyframe
            obj.location = current_pos
            obj.rotation_euler.z = current_angle
            
            obj.keyframe_insert(data_path="location", frame=f)
            obj.keyframe_insert(data_path="rotation_euler", frame=f)
            
        # 5. Set Interpolation to Linear
        # This ensures constant speed and smooth turning between keys
        for fcurve in action.fcurves:
            for k in fcurve.keyframe_points:
                k.interpolation = 'LINEAR'
                
        print(f"Generated random stroll for {total_frames} frames.")
        
    else:
        print("Error: character_controller not found.")

if __name__ == "__main__":
    create_pathless_walk()
