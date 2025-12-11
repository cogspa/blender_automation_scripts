import bpy
import sys
import imp

# Setup path
sys.path.append("/Users/joem/.gemini/antigravity/scratch/blender_bridge")

# Import and Run
import create_body
imp.reload(create_body)
create_body.create_body()
