import bpy

print("--------------------------------------------------")
print("OFFSETTING ANIMATION KEYS (-10 Frames)")
print("--------------------------------------------------")

target_names = ["IK_Target.001", "IK_Target.003"]
time_offset = -10.0

def shift_recursively(obj, shift_amount, visited=None):
    if visited is None: visited = set()
    if obj in visited: return
    visited.add(obj)
    
    # If it acts like an FCurve with keyframes
    if hasattr(obj, 'keyframe_points'):
        # Shift all points
        for k in obj.keyframe_points:
            original_frame = k.co[0]
            k.co[0] += shift_amount
            k.handle_left[0] += shift_amount
            k.handle_right[0] += shift_amount
        print(f"  Shifted {len(obj.keyframe_points)} keys on {getattr(obj, 'data_path', 'unknown curve')}")
        return

    # Recurse attributes
    search_attrs = ['layers', 'strips', 'channelbags', 'fcurves']
    for attr in search_attrs:
        if hasattr(obj, attr):
            try:
                for item in getattr(obj, attr):
                    shift_recursively(item, shift_amount, visited)
            except: pass

count = 0
for name in target_names:
    if name in bpy.data.objects:
        obj = bpy.data.objects[name]
        print(f"Processing {name}...")
        if obj.animation_data and obj.animation_data.action:
            shift_recursively(obj.animation_data.action, time_offset)
            count += 1
        else:
            print(f"  No Animation Data found on {name}.")
    else:
        print(f"  Object {name} not found.")

if count > 0:
    print(f"Successfully offset keys for {count} objects.")
else:
    print("No keys were shifted.")
