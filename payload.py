import bpy
import sys
import os
import imp
import random

sys.path.append("/Users/joem/.gemini/antigravity/scratch/blender_bridge")

print("Running Payload: SWARM 2 (User Suggested Fixes Applied)...")

# 1. Clear Scene
if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

for _ in range(3):
    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

try:
    # 2. Setup Obstacles
    for i in range(5):
        x = random.uniform(-100, 100)
        y = random.uniform(-100, 100)
        if abs(x) < 20 and abs(y) < 20: continue
        bpy.ops.mesh.primitive_cylinder_add(radius=3, depth=10, location=(x, y, 5))
        obs = bpy.context.active_object
        obs.name = f"Obstacle_{i}"
        obs["is_obstacle"] = True  
        
    # 3. Run Swarm 2
    import swarm2
    imp.reload(swarm2)
    swarm2.create_swarm(count=40, range_x=120, range_y=120) 
    
    bpy.context.scene.frame_end = 3000
    print("Swarm 2 Generation Complete.")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
