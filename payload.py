import bpy
import sys
import os

print("--------------------------------------------------")
print("ANIMATING PATH (Recursive Search Fix)")
print("--------------------------------------------------")

script = """
import bpy

def recursive_fix(obj, visited=None):
    if visited is None: visited = set()
    if obj in visited: return
    visited.add(obj)
    
    # Check if this object IS an FCurve
    # FCurves have 'data_path' and 'keyframe_points'
    if hasattr(obj, 'data_path') and hasattr(obj, 'keyframe_points') and hasattr(obj, 'extrapolation'):
        print(f"Found FCurve: {obj.data_path}")
        if 'WalkConstraint' in obj.data_path and 'offset' in obj.data_path:
            obj.extrapolation = 'LINEAR'
            print("  [FIX] Set Extrapolation to LINEAR")
            for k in obj.keyframe_points:
                k.interpolation = 'LINEAR'
            print("  [FIX] Set Keyframes to LINEAR")
        return

    # Traversal List for Layered Action Structure
    # Action -> layers -> strips -> channelbags -> fcurve?
    traversal_attrs = ['layers', 'strips', 'channelbags', 'fcurves']
    
    for attr in traversal_attrs:
        if hasattr(obj, attr):
            collection = getattr(obj, attr)
            # It might be a collection (bpy_prop_collection) or list
            try:
                for item in collection:
                    recursive_fix(item, visited)
            except TypeError:
                # Not iterable?
                pass
            except Exception as e:
                print(f"Error traversing {attr}: {e}")

# Main Execution
if "IK_Target" in bpy.data.objects:
    ik_target = bpy.data.objects["IK_Target"]
    if ik_target.animation_data and ik_target.animation_data.action:
        action = ik_target.animation_data.action
        print(f"Scanning Action: {action.name}")
        recursive_fix(action)
    else:
        print("No Action to scan.")
else:
    print("IK_Target found.")
"""

exec(script)
