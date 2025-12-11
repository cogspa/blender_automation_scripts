import bpy
import sys
import os
import imp
import create_leg_ik

print("--------------------------------------------------")
print("RESET & RERUN REQUESTED")
print("--------------------------------------------------")

# 1. Reset
if bpy.context.object and bpy.context.object.mode != 'OBJECT':
    bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
for _ in range(3):
    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

# 2. Run
sys.path.append("/Users/joem/.gemini/antigravity/scratch/blender_bridge")
try:
    imp.reload(create_leg_ik)
    create_leg_ik.create_leg_with_ik()
    print("Script execution finished.")
except Exception as e:
    import traceback
    traceback.print_exc()
