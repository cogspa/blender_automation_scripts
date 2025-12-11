import bpy
import math
from mathutils import Vector, Matrix

def duplicate_legs():
    print("--------------------------------------------------")
    print("DUPLICATING LEGS (Invert Selection Approach)")
    print("--------------------------------------------------")
    
    # Check for duplicates first
    if bpy.data.objects.get("Spider_Leg.001"):
        print("Duplicates detected. Skipping to avoid mess.")
        return

    # 1. Selection Strategy as requested:
    # "Select Body and Invert Selection"
    bpy.ops.object.select_all(action='DESELECT')
    
    body = bpy.data.objects.get("Spider_Body")
    if body:
        # Select Body
        body.select_set(True)
        # Invert -> Selects everything else (Leg, Armature, Path, Target, Lights?)
        bpy.ops.object.select_all(action='INVERT')
        
        # Ensure Body is NOT selected (Invert handles this, but double check)
        body.select_set(False)
    else:
        print("Error: Spider_Body not found.")
        return

    # Capture what we selected
    # This list is what we will duplicate.
    base_objs = bpy.context.selected_objects
    print(f"Selected {len(base_objs)} objects to duplicate: {[o.name for o.name in base_objs]}")
    
    if not base_objs:
        return

    # 2. Set Context Object
    # We need an active object for the duplicate operator usually.
    # Pick the first one.
    bpy.context.view_layer.objects.active = base_objs[0]

    # 3. Rotation Loop
    # Rotate 90, 180, 270 around Z=0
    angles = [90, 180, 270]
    
    for i, angle_deg in enumerate(angles):
        rad = math.radians(angle_deg)
        rot_mat = Matrix.Rotation(rad, 4, 'Z')
        
        # Duplicate
        # Note: We must re-select the 'base_objs' before each duplicate?
        # NO. Standard workflow:
        # 1. Select Base.
        # 2. Duplicate -> Result is New Selection.
        # 3. Rotate New Selection.
        # 4. Re-Select Base? Or Duplicate New Selection?
        # Using Base as source is safer.
        
        # Re-Select Base Set
        bpy.ops.object.select_all(action='DESELECT')
        for obj in base_objs:
            obj.select_set(True)
            
        bpy.ops.object.duplicate(linked=False)
        
        # Get New Objects
        new_objs = bpy.context.selected_objects
        
        # Rotate them using Matrix Math (Robust)
        for obj in new_objs:
            mw = obj.matrix_world.copy()
            obj.matrix_world = rot_mat @ mw
            print(f"  Created copy at {angle_deg} deg: {obj.name}")
            
    print("Duplication Complete.")

if __name__ == "__main__":
    duplicate_legs()
