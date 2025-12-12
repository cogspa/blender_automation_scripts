import bpy
import sys
import os
import imp

sys.path.append("/Users/joem/.gemini/antigravity/scratch/blender_bridge")

print("Running Payload: BUILD + SWARM (120 SPIDERS)...")

# 1. Clear Scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

try:
    # 2. Run Swarm (count=119 duplicates + 1 Source = 120 Total)
    import create_spider_swarm
    imp.reload(create_spider_swarm)
    create_spider_swarm.create_swarm(count=119, range_x=150, range_y=150) 
    
    bpy.context.scene.frame_end = 3000
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
