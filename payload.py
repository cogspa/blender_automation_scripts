import bpy
import sys
import os
import imp

# Add path if needed
sys.path.append("/Users/joem/.gemini/antigravity/scratch/blender_bridge")

# TRIGGER EXECUTION (Run 2)
print("Running Payload to Apply Body Noise (Attempt 2)...")

try:
    import create_body_noise
    imp.reload(create_body_noise)
    create_body_noise.add_body_noise()
except Exception as e:
    print(f"Error adding noise: {e}")
