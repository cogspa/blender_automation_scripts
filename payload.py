import bpy
import sys
import os
import imp
import random

sys.path.append("/Users/joem/.gemini/antigravity/scratch/blender_bridge")

print("Running Payload: SWARM 2 (Final Working Version - 40 Bots)...")

# 1. Cleanup
if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
# Robust Clean
for obj in list(bpy.data.objects):
    try: bpy.data.objects.remove(obj, do_unlink=True)
    except: pass
    
for _ in range(5):
    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

try:
    # 2. Obstacles
    for i in range(8):
        x = random.uniform(-80, 80)
        y = random.uniform(-80, 80)
        if abs(x) < 20 and abs(y) < 20: continue
        bpy.ops.mesh.primitive_cylinder_add(radius=3, depth=10, location=(x, y, 5))
        obs = bpy.context.active_object
        obs.name = f"Obstacle_{i}"
        obs["is_obstacle"] = True  
        
    # 3. Run Swarm 2
    import swarm2
    imp.reload(swarm2)
    # Restoring decent swarm size (40 duplicates + 1 Source = 41)
    swarm2.create_swarm(count=40, range_x=130, range_y=130) 
    
    bpy.context.scene.frame_end = 3000
    print("Swarm Generated Successfully.")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
