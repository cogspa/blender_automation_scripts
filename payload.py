import bpy
import sys
import os
import imp

# Add path if needed
sys.path.append("/Users/joem/.gemini/antigravity/scratch/blender_bridge")

# TRIGGER EXECUTION
print("Running Payload to Create Master Controller...")

try:
    import create_master_controller
    imp.reload(create_master_controller)
    create_master_controller.create_master_controller()
except Exception as e:
    print(f"Error creating master controller: {e}")
