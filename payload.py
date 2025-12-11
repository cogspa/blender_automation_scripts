import bpy
import sys
import os
import imp

# Add path if needed
sys.path.append("/Users/joem/.gemini/antigravity/scratch/blender_bridge")

# TRIGGER EXECUTION
print("Running Payload to CREATE PATHLESS WALK...")

try:
    import create_pathless_walk
    imp.reload(create_pathless_walk)
    create_pathless_walk.create_pathless_walk()
except Exception as e:
    print(f"Error creating pathless walk: {e}")
    import traceback
    traceback.print_exc()
