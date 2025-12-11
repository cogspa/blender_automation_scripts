import bpy
import sys
import os

print("--------------------------------------------------")
print("ANIMATING PATH (Height Adjustment)")
print("--------------------------------------------------")

script = """
import bpy
import math
from mathutils import Vector

# 1. Cleanup
if "WalkPath" in bpy.data.objects:
    bpy.data.objects.remove(bpy.data.objects["WalkPath"], do_unlink=True)

# 2. Parameters
target_loc = Vector((0, -2.4562, 0.28973))

# 3. Create Custom "Footstep" Curve
curve_data = bpy.data.curves.new(name="WalkPathData", type='CURVE')
curve_data.dimensions = '3D'

spline = curve_data.splines.new('BEZIER')
spline.use_cyclic_u = True 

r = 0.8
h = 1.2 # Raised Height
spline.bezier_points.add(2)

# Point 0: Back (-r, 0, 0)
p0 = spline.bezier_points[0]
p0.co = Vector((-r, 0, 0))
p0.handle_left = Vector((-r, 0, 0))
p0.handle_right = Vector((-r, 0, r))
p0.handle_left_type = 'VECTOR'
p0.handle_right_type = 'FREE'

# Point 1: Top (0, 0, h)
p1 = spline.bezier_points[1]
p1.co = Vector((0, 0, h)) # Uses h
p1.handle_left = Vector((-r*0.5, 0, h)) 
p1.handle_right = Vector((r*0.5, 0, h))
p1.handle_left_type = 'ALIGNED'
p1.handle_right_type = 'ALIGNED'

# Point 2: Front (r, 0, 0)
p2 = spline.bezier_points[2]
p2.co = Vector((r, 0, 0))
p2.handle_left = Vector((r, 0, r))
p2.handle_right = Vector((r, 0, 0))
p2.handle_left_type = 'FREE'
p2.handle_right_type = 'VECTOR'

# Location
object_loc = Vector((target_loc.x, target_loc.y, 0.0))

path = bpy.data.objects.new("WalkPath", curve_data)
path.location = object_loc
path.rotation_euler.z = math.radians(90)

bpy.context.collection.objects.link(path)
bpy.context.view_layer.objects.active = path

print(f"Created Custom 'WalkPath' (h={h}) at {object_loc}, Rotated 90 Z.")

# 4. Attach & Animate
if "IK_Target" in bpy.data.objects:
    ik_target = bpy.data.objects["IK_Target"]
    
    to_remove = [c for c in ik_target.constraints if c.type == 'FOLLOW_PATH']
    for c in to_remove:
        ik_target.constraints.remove(c)
    if ik_target.animation_data:
        ik_target.animation_data_clear()
    
    c = ik_target.constraints.new('FOLLOW_PATH')
    c.name = "WalkConstraint"
    c.target = path
    ik_target.location = (0, 0, 0)
    
    c.offset = 0
    c.keyframe_insert(data_path="offset", frame=10)
    c.offset = 100
    c.keyframe_insert(data_path="offset", frame=30)
    
    def recursive_fix(obj, visited=None):
        if visited is None: visited = set()
        if obj in visited: return
        visited.add(obj)
        if hasattr(obj, 'data_path') and hasattr(obj, 'keyframe_points') and hasattr(obj, 'extrapolation'):
             if 'WalkConstraint' in obj.data_path and 'offset' in obj.data_path:
                obj.extrapolation = 'LINEAR'
                for k in obj.keyframe_points:
                    k.interpolation = 'LINEAR'
                print("  [FIX] Applied LINEAR.")
             return
        for attr in ['layers', 'strips', 'channelbags', 'fcurves']:
            if hasattr(obj, attr):
                try:
                    for item in getattr(obj, attr):
                        recursive_fix(item, visited)
                except: pass

    if ik_target.animation_data and ik_target.animation_data.action:
        recursive_fix(ik_target.animation_data.action)

else:
    print("Warning: IK_Target object not found.")

"""

exec(script)
