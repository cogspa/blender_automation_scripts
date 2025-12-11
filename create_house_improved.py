import bpy
import bmesh
import random
from mathutils import Vector

# ------------------------------------------------------------------------
# Core Construction Functions
# ------------------------------------------------------------------------

def create_house_mesh(width=4.0, depth=3.0, wall_height=2.5, roof_height=1.5, overhang=0.3):
    """
    Creates the main house body with a gable roof and overhang.
    """
    # 1. Start clean: create a new mesh and object for the house
    mesh = bpy.data.meshes.new("House_Random_Mesh")
    house = bpy.data.objects.new("House_Random", mesh)
    bpy.context.collection.objects.link(house)
    
    # 2. Build geometry using BMesh
    bm = bmesh.new()
    
    # -- WALLS --
    w2 = width / 2
    d2 = depth / 2
    
    # Bottom corners (z=0)
    v_bl = bm.verts.new((-w2, -d2, 0))
    v_br = bm.verts.new((w2, -d2, 0))
    v_tr = bm.verts.new((w2, d2, 0))
    v_tl = bm.verts.new((-w2, d2, 0))
    
    # Top corners (z=wall_height)
    v_t_bl = bm.verts.new((-w2, -d2, wall_height))
    v_t_br = bm.verts.new((w2, -d2, wall_height))
    v_t_tr = bm.verts.new((w2, d2, wall_height))
    v_t_tl = bm.verts.new((-w2, d2, wall_height))
    
    bm.verts.ensure_lookup_table()
    
    # Wall Faces
    bm.faces.new((v_bl, v_br, v_t_br, v_t_bl)) # Front
    bm.faces.new((v_br, v_tr, v_t_tr, v_t_br)) # Right
    bm.faces.new((v_tr, v_tl, v_t_tl, v_t_tr)) # Back
    bm.faces.new((v_tl, v_bl, v_t_bl, v_t_tl)) # Left
    bm.faces.new((v_bl, v_tl, v_tr, v_br))     # Floor
    
    # -- ROOF --
    # Roof dimensions including overhang
    rw2 = (width + overhang * 2) / 2
    rd2 = (depth + overhang * 2) / 2
    rh_z = wall_height + roof_height
    
    # Roof Base corners (at wall_height)
    rv_bl = bm.verts.new((-rw2, -rd2, wall_height))
    rv_br = bm.verts.new((rw2, -rd2, wall_height))
    rv_tr = bm.verts.new((rw2, rd2, wall_height))
    rv_tl = bm.verts.new((-rw2, rd2, wall_height))
    
    # Ridge Vertices (Centered on X, running along Y)
    ridge_front = bm.verts.new((0, -rd2, rh_z))
    ridge_back  = bm.verts.new((0, rd2, rh_z))
    
    bm.verts.ensure_lookup_table()
    
    # Roof Faces
    # Gables (Triangular fills between wall and roof? 
    # Usually easier to just make the roof a solid prism sitting on top)
    
    # Right Slope
    bm.faces.new((rv_br, rv_tr, ridge_back, ridge_front))
    # Left Slope
    bm.faces.new((rv_tl, rv_bl, ridge_front, ridge_back))
    
    # Gable Ends (Triangles)
    bm.faces.new((rv_bl, rv_br, ridge_front)) # Front Gable
    bm.faces.new((rv_tr, rv_tl, ridge_back))  # Back Gable
    
    # Roof Base (Ceiling)
    bm.faces.new((rv_bl, rv_tl, rv_tr, rv_br))
    
    # Write to mesh
    bm.to_mesh(mesh)
    bm.free()
    
    return house

def create_cutter_cube(name, location, scale):
    bpy.ops.mesh.primitive_cube_add(size=1)
    obj = bpy.context.active_object
    obj.name = name
    obj.location = location
    obj.scale = scale
    obj.display_type = 'WIRE'
    obj.hide_render = True
    return obj

def apply_boolean(obj, cutter):
    mod = obj.modifiers.new(name="Bool", type='BOOLEAN')
    mod.object = cutter
    mod.operation = 'DIFFERENCE'

# ------------------------------------------------------------------------
# Parameterized Random House Logic
# ------------------------------------------------------------------------

def build_random_house(seed=0):
    rng = random.Random(seed)
    
    # 1. Dimensions
    width = rng.uniform(4.0, 9.0)
    depth = rng.uniform(4.0, 8.0)
    wall_h = rng.uniform(2.5, 3.5)
    roof_h = rng.uniform(1.0, 2.5)
    overhang = rng.uniform(0.2, 0.5)
    
    # Create House
    house = create_house_mesh(width, depth, wall_h, roof_h, overhang)
    bpy.context.view_layer.objects.active = house
    house.select_set(True)
    
    # Collection for Cutters
    col_name = "House_Cutters"
    if col_name not in bpy.data.collections:
        col = bpy.data.collections.new(col_name)
        bpy.context.scene.collection.children.link(col)
    else:
        col = bpy.data.collections[col_name]
    
    # 2. Door (Front Wall, Y = -depth/2)
    door_w = rng.uniform(0.9, 1.2)
    door_h = rng.uniform(2.0, 2.2)
    
    # Position X: usually center, sometimes offset
    door_x = 0
    if width > 6 and rng.choice([True, False]):
        door_x = rng.uniform(-width/4, width/4)
        
    door_pos = Vector((door_x, -depth/2, door_h/2))
    # Depth of cutter needs to be thick enough
    door_cutter = create_cutter_cube("Cutter_Door", door_pos, (door_w, 1.0, door_h))
    
    # Move to collection
    for c in door_cutter.users_collection: c.objects.unlink(door_cutter)
    col.objects.link(door_cutter)
    
    apply_boolean(house, door_cutter)
    
    # 3. Windows
    # Helper to create window
    def make_window(x, y, z, w, h, axis_aligned='Y'):
        # if axis is Y (front/back wall), thickness is Y
        size = (w, 1.0, h) if axis_aligned == 'Y' else (1.0, w, h)
        c = create_cutter_cube("Cutter_Win", (x, y, z), size)
        for c_col in c.users_collection: c_col.objects.unlink(c)
        col.objects.link(c)
        apply_boolean(house, c)

    # Front Windows
    # Avoid door area
    keep_out_min = door_x - door_w/2 - 0.4
    keep_out_max = door_x + door_w/2 + 0.4
    
    front_y = -depth/2
    
    # Try Left Side
    space_left = (-width/2 + 0.5, keep_out_min)
    if space_left[1] - space_left[0] > 0.8:
        # 1 or 2 windows
        n = rng.randint(0, 2)
        steps = (space_left[1] - space_left[0]) / (n + 1)
        for i in range(n):
            wx = space_left[0] + steps * (i + 1)
            wz = rng.uniform(1.2, wall_h - 0.5)
            ww = rng.uniform(0.6, 1.0)
            wh = rng.uniform(0.8, 1.2)
            make_window(wx, front_y, wz, ww, wh, 'Y')

    # Try Right Side
    space_right = (keep_out_max, width/2 - 0.5)
    if space_right[1] - space_right[0] > 0.8:
        n = rng.randint(0, 2)
        steps = (space_right[1] - space_right[0]) / (n + 1)
        for i in range(n):
            wx = space_right[0] + steps * (i + 1)
            wz = rng.uniform(1.2, wall_h - 0.5)
            ww = rng.uniform(0.6, 1.0)
            wh = rng.uniform(0.8, 1.2)
            make_window(wx, front_y, wz, ww, wh, 'Y')

    # Side Walls (Left/Right)
    # Left (X = -width/2)
    n_side = rng.randint(0, 3)
    for i in range(n_side):
        # Distributed along Y
        y_pos = -depth/2 + (depth / (n_side + 1)) * (i + 1)
        wz = rng.uniform(1.2, wall_h - 0.5)
        # width of window is actually along Y now
        ww = rng.uniform(0.6, 1.2) 
        wh = rng.uniform(0.8, 1.2)
        make_window(-width/2, y_pos, wz, ww, wh, 'X')
        
    return house

# ------------------------------------------------------------------------
# Operator
# ------------------------------------------------------------------------

class AB_OT_create_random_house(bpy.types.Operator):
    """Create a Random Procedural House"""
    bl_idname = "mesh.ab_create_random_house"
    bl_label = "Create Random House"
    bl_options = {'REGISTER', 'UNDO'}

    seed: bpy.props.IntProperty(name="Seed", default=0, description="Seed for Random Generator")

    def execute(self, context):
        # Clean scene first? Optional. Let's not delete *everything* in operator, risky.
        # But we will select the new house.
        
        # Build it
        build_random_house(self.seed)
        
        return {'FINISHED'}

def register():
    bpy.utils.register_class(AB_OT_create_random_house)

def unregister():
    bpy.utils.unregister_class(AB_OT_create_random_house)

if __name__ == "__main__":
    try:
        unregister()
    except:
        pass
    register()
    
    print("--------------------------------------------------")
    print("Operator 'Create Random House' registered.")
    print("Press F3 and search for 'Create Random House'.")
    print("--------------------------------------------------")
