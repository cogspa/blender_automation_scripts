import bpy
import sys
import os
import imp

sys.path.append("/Users/joem/.gemini/antigravity/scratch/blender_bridge")

print("Running Payload: BUILD + SWARM (With Post-Validation)...")

# 1. Clear Scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

try:
    # 2. Run Swarm
    import create_spider_swarm
    imp.reload(create_spider_swarm)
    create_spider_swarm.create_swarm(count=3, range_x=80, range_y=80) 
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
