import bpy
import sys
import os
import imp

print("--------------------------------------------------")
print("FULL SCENE RESET & REBUILD (Final Fix)")
print("--------------------------------------------------")

sys.path.append("/Users/joem/.gemini/antigravity/scratch/blender_bridge")

# 1. Reset Scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# 2. Spider Assembly
try:
    import create_spider_assembly
    imp.reload(create_spider_assembly)
    create_spider_assembly.create_spider_assembly()
except Exception as e:
    print(f"Assembly Error: {e}")

# 3. Path & Animation (With Fix)
try:
    import create_path
    imp.reload(create_path)
    create_path.create_circular_path()
except Exception as e:
    print(f"Path Error: {e}")
