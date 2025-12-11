import bpy
import bmesh

def create_house():
    # 1. Setup: Clear existing objects (optional, mostly for clean testing)
    # Warning: This deletes everything in the scene!
    # bpy.ops.object.select_all(action='SELECT')
    # bpy.ops.object.delete()
    
    # 2. Create the main cube
    # Size 2 means it goes from -1 to 1 in each dimension relative to its center
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0,0,1))
    house = bpy.context.active_object
    house.name = "House"
    
    # 3. Create the Peaked Roof
    # We will use bmesh to simulate a "loop cut" and drag the edge up
    bpy.ops.object.mode_set(mode='EDIT')
    bm = bmesh.from_edit_mesh(house.data)
    
    # Select all faces/edges/verts to ensure bisect works on everything
    # (Though bisect usually works on passed geometry)
    geom_all = [v for v in bm.verts] + [e for e in bm.edges] + [f for f in bm.faces]
    
    # Bisect the mesh down the middle (along YZ plane, normal=(1,0,0))
    # clear_inner/outer=False keeps both sides and just makes a cut
    bmesh.ops.bisect_plane(
        bm, 
        geom=geom_all, 
        dist=0.0001, 
        plane_co=(0,0,0), 
        plane_no=(1,0,0)
    )
    
    # Ensure lookups are current after operation
    bm.verts.ensure_lookup_table()
    
    # Find the top-middle vertices to pull up
    # The cube was size 2 at z=1, so top is z=2. Middle is x=0.
    top_middle_verts = []
    for v in bm.verts:
        # Check if vertex is roughly at x=0 and z=2
        if abs(v.co.x) < 0.001 and abs(v.co.z - 2.0) < 0.001:
            top_middle_verts.append(v)
            
    # Move them up to make the peak
    # Let's move them up by 1 unit
    for v in top_middle_verts:
        v.co.z += 1.0
        
    bmesh.update_edit_mesh(house.data)
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # 4. Create Boolean Cutters (Door and Windows)
    
    # --- Door ---
    # Centered on X, positioned at front face (y=-1)
    bpy.ops.mesh.primitive_cube_add(size=1)
    door_cutter = bpy.context.active_object
    door_cutter.name = "Cutter_Door"
    # Scale: width(x)=0.6, depth(y)=0.5, height(z)=1.2
    # Note: Primitive cube is size 1 here for easier scaling math? Actually primitive_cube_add defaults to size 2 usually unless specified.
    # explicit size=1 makes it -0.5 to 0.5.
    
    door_cutter.scale = (0.6, 1.0, 1.2)
    # Position: Slightly protruding from y=-1. 
    # Height: base must be at z=0. 
    # Current z center is 0. So bottom is -0.6 (if scale z is 1.2 and original was 1 unit tall centered).
    # Wait, primitive cube size=1 is 1x1x1 centered at 0.
    # Scaled by 1.2 in Z -> 1.2 height, centered at 0. Range -0.6 to 0.6.
    # We want bottom at 0. So move Z up by 0.6.
    door_cutter.location = (0, -1.0, 0.6) 
    door_cutter.display_type = 'WIRE'
    
    # --- Window 1 ---
    bpy.ops.mesh.primitive_cube_add(size=1)
    win1 = bpy.context.active_object
    win1.name = "Cutter_Window1"
    win1.scale = (0.4, 1.0, 0.4)
    # Position: Left of door, higher up.
    # X = -0.6? 
    # Y = -1.0 (on face)
    # Z = 1.0 (mid height)
    win1.location = (-0.7, -1.0, 1.2)
    win1.display_type = 'WIRE'
    
    # --- Window 2 ---
    bpy.ops.mesh.primitive_cube_add(size=1)
    win2 = bpy.context.active_object
    win2.name = "Cutter_Window2"
    win2.scale = (0.4, 1.0, 0.4)
    win2.location = (0.7, -1.0, 1.2)
    win2.display_type = 'WIRE'
    
    # 5. Apply Boolean Modifiers to House
    
    cutters = [door_cutter, win1, win2]
    
    for cutter in cutters:
        bool_mod = house.modifiers.new(type="BOOLEAN", name=f"Bool_{cutter.name}")
        bool_mod.object = cutter
        bool_mod.operation = 'DIFFERENCE'
        
        # Optional: Hide the cutters so we see the result immediately
        cutter.hide_render = True
        # We keep them visible in viewport as wireframe (set above) so user can see them
        # If user wants them totally hidden:
        # cutter.hide_viewport = True

    # Select the house to finish
    bpy.context.view_layer.objects.active = house
    house.select_set(True)

if __name__ == "__main__":
    create_house()
