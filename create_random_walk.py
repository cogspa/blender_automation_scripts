import bpy
import random
from mathutils import Vector

def create_random_walk_path():
    print("--------------------------------------------------")
    print("CREATING RANDOM WALK PATH & ATTACHING CONTROLLER")
    print("--------------------------------------------------")

    # 1. Cleanup Old Path
    if "GlobalWalkPath" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["GlobalWalkPath"], do_unlink=True)

    # 2. Create Bezier Curve
    curve_data = bpy.data.curves.new(name="GlobalWalkPathData", type='CURVE')
    curve_data.dimensions = '3D'
    
    spline = curve_data.splines.new('BEZIER')
    spline.bezier_points.add(4) # Total 5 points
    
    # 3. Random Points logic
    # Start at current location of character_controller to avoid snap?
    start_loc = Vector((0,0,0))
    if "character_controller" in bpy.data.objects:
        start_loc = bpy.data.objects["character_controller"].location
        
    points = [start_loc]
    current_pos = start_loc
    
    for i in range(4):
        # Move forward roughly X amount, random Y
        # Or random walk?
        dx = random.uniform(5, 15)
        dy = random.uniform(-10, 10)
        # Assuming X is forward for the spider? 
        # Actually spider faces Y? Or X?
        # Leg 0 was at +X. Body at 0.
        # Usually X is forward.
        
        move_vec = Vector((dx, dy, 0))
        current_pos = current_pos + move_vec
        points.append(current_pos)
        
    # Assign points
    for i, point in enumerate(points):
        bp = spline.bezier_points[i]
        bp.co = point
        bp.handle_left_type = 'AUTO'
        bp.handle_right_type = 'AUTO'
        
    path_obj = bpy.data.objects.new("GlobalWalkPath", curve_data)
    bpy.context.collection.objects.link(path_obj)
    
    print(f"Created Global Path with {len(points)} points.")
    
    # 4. Attach Master Controller
    if "character_controller" in bpy.data.objects:
        master = bpy.data.objects["character_controller"]
        
        # Add Follow Path Constraint
        c = master.constraints.new('FOLLOW_PATH')
        c.target = path_obj
        c.use_curve_follow = True # Makes it steer!
        c.forward_axis = 'FORWARD_X' # Assuming X is forward
        c.up_axis = 'UP_Z'
        
        # Animate Offset
        # We need to animate the 'offset_factor' (0.0 to 1.0) usually?
        # Or 'offset' frame?
        # Fixed Position = True gives manual control via offset_factor.
        c.use_fixed_location = True # Use Offset Factor (0-1)
        
        master.animation_data_create()
        master.animation_data.action = bpy.data.actions.new(name="WalkAlongPath")
        
        # Frame 1: 0
        c.offset_factor = 0.0
        c.keyframe_insert(data_path="offset_factor", frame=1)
        
        # Frame 200: 1.0
        c.offset_factor = 1.0
        c.keyframe_insert(data_path="offset_factor", frame=200)
        
        # Reset Location (Parent inverse might mess up if not cleared)
        master.location = (0,0,0)
        
        print("Attached Master Controller to Path (Follow Curve enabled).")
        
    else:
        print("Error: character_controller not found.")

if __name__ == "__main__":
    create_random_walk_path()
