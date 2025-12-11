import bpy
import math
from mathutils import Vector, Matrix
import imp
import sys
import random

# Add path to sys.path to ensure imports work
sys.path.append("/Users/joem/.gemini/antigravity/scratch/blender_bridge")

# Import our modules
import create_spider_assembly
import create_path
import create_body_noise
import create_master_controller

def build_spider():
    print("==================================================")
    print("BUILDING FULL SPIDER RIG FROM SCRATCH")
    print("==================================================")

    # 1. Reset Scene (Optional but recommended)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # 2. Base Assembly (Body + Leg 0)
    print("[1/7] Creating Base Assembly...")
    imp.reload(create_spider_assembly)
    create_spider_assembly.create_spider_assembly()

    # 3. Path for Leg 0
    print("[2/7] Creating Path & Animation...")
    imp.reload(create_path)
    create_path.create_circular_path()
    
    # 4. Duplication (Legs 1, 2, 3)
    print("[3/7] Duplicating Legs...")
    duplicate_legs_logic()
    
    # 5. Gait Offset (Legs 1 & 3)
    print("[4/7] Offsetting Gait...")
    offset_gait_logic()
    
    # 6. Steering Controller
    print("[5/7] Creating Steering Controller...")
    create_steering_logic()
    
    # 7. Master Controller
    print("[6/7] Creating Master Controller...")
    imp.reload(create_master_controller)
    create_master_controller.create_master_controller()
    
    # 8. Organic Noise
    print("[7/7] Adding Organic Noise...")
    imp.reload(create_body_noise)
    create_body_noise.add_body_noise()
    
    print("==================================================")
    print("SPIDER BUILD COMPLETE!")
    print("==================================================")

# ------------------------------------------------------------------------
# HELPER LOGIC (Ported from manual steps)
# ------------------------------------------------------------------------

def duplicate_legs_logic():
    # Strategy: Select Body -> Invert -> Duplicate -> Rotate
    
    # 1. Select Everything EXCEPT Body
    bpy.ops.object.select_all(action='DESELECT')
    if "Spider_Body" in bpy.data.objects:
        body = bpy.data.objects["Spider_Body"]
        body.select_set(True)
        bpy.ops.object.select_all(action='INVERT')
        body.select_set(False) # Ensure body is NOT selected
    else:
        print("Error: Spider_Body not found for duplication.")
        return

    # Base objects to be duplicated
    base_objs = bpy.context.selected_objects
    if not base_objs:
        print("Nothing selected to duplicate!")
        return
        
    # Active Object for Context
    bpy.context.view_layer.objects.active = base_objs[0]

    # 2. Duplicate & Rotate 3 times (90, 180, 270)
    # We use Matrix Rotation around Z (World Origin)
    angles = [90, 180, 270]
    
    # Clear Rotation of Paths FIRST? No, create_path rotates object 90.
    # If we duplicate and rotate, we add to that.
    
    for angle_deg in angles:
        # Re-Select Bases (Since duplicate changes selection)
        bpy.ops.object.select_all(action='DESELECT')
        for obj in base_objs:
            obj.select_set(True)
            
        # Duplicate
        bpy.ops.object.duplicate(linked=False)
        new_objs = bpy.context.selected_objects
        
        # Rotate
        rad = math.radians(angle_deg)
        rot_mat = Matrix.Rotation(rad, 4, 'Z')
        
        for obj in new_objs:
            # Apply Rotation Matrix to World Matrix
            obj.matrix_world = rot_mat @ obj.matrix_world

    print("  Legs duplicated.")
    
    # 3. Clear Location of IK Targets (Snapping to Path)
    # And Clear Rotation of Paths (As per manual step 592 instruction)
    
    # Clear Rotation of Paths (Resets them to X-Axis alignment? Or just 0 offset?)
    # Manual step 592 said "select 4 walk paths... clear rotation".
    # This undoes the 90 deg rotation from create_path?
    # Actually, let's stick to what we did manually:
    paths = [o for o in bpy.data.objects if o.name.startswith("WalkPath")]
    for p in paths:
        p.rotation_euler = (0,0,0) # Force Clear Rotation
        
    # Clear Location of Targets
    targets = [o for o in bpy.data.objects if o.name.startswith("IK_Target")]
    for t in targets:
        t.location = (0,0,0) # Snaps to Path

def offset_gait_logic():
    # Offset Legs 1 (Reference .001?) and 3 (Reference .003?)
    # The suffixes depend on duplication order.
    # Usually: Original, .001, .002, .003.
    # Offset .001 and .003 by -10 frames.
    
    targets_to_offset = ["IK_Target.001", "IK_Target.003"]
    offset = -10.0
    
    for name in targets_to_offset:
        if name in bpy.data.objects:
            obj = bpy.data.objects[name]
            if obj.animation_data and obj.animation_data.action:
                shift_keys_recursive(obj.animation_data.action, offset)

def shift_keys_recursive(obj, shift_val, visited=None):
    if visited is None: visited = set()
    if obj in visited: return
    visited.add(obj)
    
    if hasattr(obj, 'keyframe_points'):
        for k in obj.keyframe_points:
            k.co[0] += shift_val
            k.handle_left[0] += shift_val
            k.handle_right[0] += shift_val
            
    search_attrs = ['layers', 'strips', 'channelbags', 'fcurves']
    for attr in search_attrs:
        if hasattr(obj, attr):
            try:
                for item in getattr(obj, attr):
                    shift_keys_recursive(item, shift_val, visited)
            except: pass

def create_steering_logic():
    # 1. Create Controller if missing (master controller script does this too? No, it parents it)
    if "Direction_Controller" not in bpy.data.objects:
        bpy.ops.object.empty_add(type='SPHERE', location=(0,0,0))
        ctrl = bpy.context.active_object
        ctrl.name = "Direction_Controller"
        ctrl.empty_display_size = 3.0
    
    ctrl = bpy.data.objects["Direction_Controller"]
    
    # 2. Constrain Paths
    paths = [o for o in bpy.data.objects if o.name.startswith("WalkPath")]
    for p in paths:
        # Check existing
        already_has = False
        for c in p.constraints:
            if c.type == 'COPY_ROTATION' and c.target == ctrl:
                already_has = True
        
        if not already_has:
            c = p.constraints.new('COPY_ROTATION')
            c.target = ctrl
            c.name = "Steering"

if __name__ == "__main__":
    build_spider()
