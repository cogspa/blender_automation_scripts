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
    
    # 4. Rotate Geometry in EDIT MODE
    # User requested: "rotate so circle lies on x axis (rotate in z 90degrees)"
    # Originally we rotated 90 on X (Vertical loop in YZ plane).
    # If we rotate 90 on Z now:
    # Original (Flat XY) -> Rot X 90 -> (Vertical YZ) -> Rot Z 90 -> (Vertical XZ).
    # Is that what "lies on x axis" means? A loop along the leg's walking direction (usually X or Y)?
    # Spider leg is at Y=-2.45. It probably walks forward/back in X.
    # So the loop should be in the XZ plane.
    
    # Scale up a bit: User requested bigger
    radius = 0.8 # Was 0.5.
    
    # Recalculate position with new radius
    path_loc = target_loc.copy()
    path_loc.z -= radius
    
    # User requested: "raise it up .5 m in z"
    path_loc.z += 0.5

    bpy.ops.curve.primitive_bezier_circle_add(radius=radius, location=path_loc)
    path = bpy.context.active_object
    path.name = "WalkPath"

    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.curve.select_all(action='SELECT')
    
    # 1. Rotate 90 X (Vertical)
    bpy.ops.transform.rotate(value=math.radians(90), orient_axis='X')
    
    # 2. Rotate 90 Z (Align with X-axis / Walk Direction)
    bpy.ops.transform.rotate(value=math.radians(90), orient_axis='Z')
    
    
    bpy.ops.object.mode_set(mode='OBJECT')
    
    print(f"Created 'WalkPath' (XZ Plane) centered at {path_loc} with radius {radius}.")

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
