import bpy
import math
from mathutils import Vector

def create_circular_path():
    # 1. Cleanup
    if "WalkPath" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["WalkPath"], do_unlink=True)

    # 2. Parameters
    # IK Target Location (Hardcoded from previous steps)
    target_loc = Vector((0, -2.4562, 0.28973))
    
    
    # 3. Create Custom "Footstep" Curve
    # Instead of a circle, we build a D-shaped path (Flat bottom, Arched top).
    curve_data = bpy.data.curves.new(name="WalkPathData", type='CURVE')
    curve_data.dimensions = '3D'
    
    spline = curve_data.splines.new('BEZIER')
    spline.use_cyclic_u = True # Closed loop
    
    # Define Points for a semi-circle (D shape)
    # We want it in XZ plane (Y=0 local).
    # Flat bottom along X axis. Arch up in Z.
    # Radius 0.8.
    r = 0.8
    h = 1.2 # Height (Raised for better arc, was 0.8/r)
    
    # We define 3 points: Back-Bottom, Top, Front-Bottom.
    # Note: 1 point is created by default options, we add 2 more.
    spline.bezier_points.add(2)
    
    # Point 0: Back (-r, 0, 0)
    p0 = spline.bezier_points[0]
    p0.co = Vector((-r, 0, 0))
    p0.handle_left = Vector((-r, 0, 0))   # Flat bottom tangent
    p0.handle_right = Vector((-r, 0, r))  # Going up
    p0.handle_left_type = 'VECTOR'
    p0.handle_right_type = 'FREE'
    
    # Point 1: Top (0, 0, h) -> Uses 'h' now for higher arc
    p1 = spline.bezier_points[1]
    p1.co = Vector((0, 0, h))
    p1.handle_left = Vector((-r*0.5, 0, h)) 
    p1.handle_right = Vector((r*0.5, 0, h))
    p1.handle_left_type = 'ALIGNED'
    p1.handle_right_type = 'ALIGNED'

    # Point 2: Front (r, 0, 0)
    p2 = spline.bezier_points[2]
    p2.co = Vector((r, 0, 0))
    p2.handle_left = Vector((r, 0, r))   # Coming down
    p2.handle_right = Vector((r, 0, 0))  # Flat bottom tangent
    p2.handle_left_type = 'FREE'
    p2.handle_right_type = 'VECTOR'
    
    # Ensure Bottom Segment (P2 -> P0) is flat
    # P2 Right Handle is (r, 0, 0) -> Points to right? 
    # To connect P2 to P0 (which is to the left), handle should point towards P0?
    # No, handle_right of P2 is the exit vector.
    # If Handle Type is VECTOR, they point at the neighbor.
    
    # Position: User wants target to touch ground.
    # Place object at Z=0 global.
    object_loc = Vector((target_loc.x, target_loc.y, 0.0))
    
    path = bpy.data.objects.new("WalkPath", curve_data)
    path.location = object_loc
    
    # User Request: "rotate back 90 degrees"
    # Previously it was XZ (aligned with X). Rotating 90 Z makes it align with Y.
    path.rotation_euler.z = math.radians(90)
    
    bpy.context.collection.objects.link(path)
    bpy.context.view_layer.objects.active = path
    
    print(f"Created Custom 'WalkPath' (D-Shape) at {object_loc}, Rotated 90 Z.")

    # --------------------------------------------------------------------
    # 5. ATTACH IK TARGET TO PATH
    # --------------------------------------------------------------------
    # Find IK Target
    if "IK_Target" in bpy.data.objects:
        ik_target = bpy.data.objects["IK_Target"]
        
        # CLEANUP: Remove old Follow Path constraints to avoid stacking
        to_remove = [c for c in ik_target.constraints if c.type == 'FOLLOW_PATH']
        for c in to_remove:
            ik_target.constraints.remove(c)
            
        # CLEANUP: Clear old animation data (fcurves)
        if ik_target.animation_data:
            ik_target.animation_data_clear()
        
        # Add Follow Path Constraint with EXPLICIT NAME
        c = ik_target.constraints.new('FOLLOW_PATH')
        c.name = "WalkConstraint" # Unique name to track
        c.target = path
        
        # Reset Location (Alt+G)
        ik_target.location = (0, 0, 0)
        
        # --------------------------------------------------------------------
        # 6. ANIMATE OFFSET (Looping)
        # --------------------------------------------------------------------
        # Frame 10: Offset = 0
        c.offset = 0
        c.keyframe_insert(data_path="offset", frame=10)
        
        # Frame 30: Offset = 100
        c.offset = 100
        c.keyframe_insert(data_path="offset", frame=30)
        
        # Linear Extrapolation (Shift+E)
        if ik_target.animation_data and ik_target.animation_data.action:
            action = ik_target.animation_data.action
            found_curve = False
            
            print("Searching F-Curves for 'WalkConstraint'...")
            for fcurve in action.fcurves:
                print(f"Found FCurve: {fcurve.data_path}")
                # Check for our specific constraint name
                # Note: Blender might escape quotes differently sometimes, but usually straight quotes work.
                # Data path is usually: constraints["Name"].offset
                if 'WalkConstraint' in fcurve.data_path and 'offset' in fcurve.data_path:
                    # 1. Set Extrapolation
                    fcurve.extrapolation = 'LINEAR'
                    
                    # 2. Set Keyframe Interpolation to LINEAR (Avoids easing)
                    for k in fcurve.keyframe_points:
                        k.interpolation = 'LINEAR'
                        
                    print(f"SUCCESS: Applied LINEAR Extrapolation & Interpolation to: {fcurve.data_path}")
                    found_curve = True
            
            if not found_curve:
                print("Error: Could not find the specific F-Curve for 'WalkConstraint'.")
        
        print("Animated Follow Path Offset (Frame 10->30, 0->100, Linear Loop).")
    else:
        print("Warning: IK_Target object not found. Created path but did not attach.")

if __name__ == "__main__":
    create_circular_path()
