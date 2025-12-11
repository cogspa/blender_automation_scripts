import bpy
import sys
import os
import imp
import create_spider_assembly

print("--------------------------------------------------")
print("RUNNING SPIDER ASSEMBLY (Bend Fix +45)")
print("--------------------------------------------------")

sys.path.append("/Users/joem/.gemini/antigravity/scratch/blender_bridge")
try:
    imp.reload(create_spider_assembly)
    create_spider_assembly.create_spider_assembly()
    print("Assembly Complete.")
except Exception as e:
    import traceback
    traceback.print_exc()
