import bpy

print("--------------------------------------------------")
print("CLEARING ROTATION OF WALK PATHS")
print("--------------------------------------------------")

# 1. Deselect All
bpy.ops.object.select_all(action='DESELECT')

# 2. Select Objects starting with "WalkPath"
paths = []
for obj in bpy.data.objects:
    if obj.name.startswith("WalkPath"):
        obj.select_set(True)
        paths.append(obj)

if paths:
    print(f"Selected {len(paths)} paths: {[p.name for p in paths]}")
    
    # Set active object
    bpy.context.view_layer.objects.active = paths[0]
    
    # 3. Clear Rotation (Alt + R)
    bpy.ops.object.rotation_clear(clear_delta=False)
    
    print("Rotation cleared successfully.")
else:
    print("No WalkPaths found.")
