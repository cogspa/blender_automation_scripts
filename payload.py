import bpy
import sys
import os
import imp
import random

sys.path.append("/Users/joem/.gemini/antigravity/scratch/blender_bridge")

print("Running Payload: SWARM 2 (Skullbox + Obstacles)...")

# 1. Clear Scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

try:
    # 2. Setup Obstacles
    for i in range(10):
        x = random.uniform(-100, 100)
        y = random.uniform(-100, 100)
        # Don't spawn too close to center (0,0) where swarm starts
        if abs(x) < 20 and abs(y) < 20: continue
        
        bpy.ops.mesh.primitive_cylinder_add(radius=3, depth=10, location=(x, y, 5))
        obs = bpy.context.active_object
        obs.name = f"Obstacle_{i}"
        obs["is_obstacle"] = True  # MARK AS OBSTACLE
        
    # 3. Run Swarm 2
    import swarm2
    imp.reload(swarm2)
    
    # Run Swarm (50 Spiders for performance testing, but optimized now!)
    # Let's do 80.
    swarm2.create_swarm(count=79, range_x=120, range_y=120) 
    
    bpy.context.scene.frame_end = 3000
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
