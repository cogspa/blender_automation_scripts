import bpy
import traceback

def create_v4_nodes():
    group_name = "VoronoiCity_V4"
    if group_name in bpy.data.node_groups:
        bpy.data.node_groups.remove(bpy.data.node_groups[group_name])

    ng = bpy.data.node_groups.new(group_name, 'GeometryNodeTree')
    
    # --- Interface ---
    # Robust socket creation
    def add_socket(name, type_str, default, min_v=None, max_v=None):
        if hasattr(ng, 'interface'): # 4.0+
            sock = ng.interface.new_socket(name, in_out='INPUT', socket_type=type_str)
            sock.default_value = default
            if min_v is not None: sock.min_value = min_v
            if max_v is not None: sock.max_value = max_v
        else: # 3.x
            sock = ng.inputs.new(type_str, name)
            sock.default_value = default

    # Add Params
    add_socket("Resolution", 'NodeSocketInt', 50, 2, 500)
    add_socket("Distortion", 'NodeSocketFloat', 5.0, 0.0, 50.0) # Controls how 'organic' the cells are
    add_socket("Road Gap", 'NodeSocketFloat', 0.1, 0.0, 0.99)
    add_socket("Height Noise Scale", 'NodeSocketFloat', 0.150) # Scale of the "Downtown" blobs
    add_socket("Height Amplitude", 'NodeSocketFloat', 8.0) # How tall buildings get
    add_socket("Seed", 'NodeSocketInt', 0)

    # Output
    if hasattr(ng, 'interface'):
        ng.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
        ng.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    else:
        ng.inputs.new('NodeSocketGeometry', 'Geometry')
        ng.outputs.new('NodeSocketGeometry', 'Geometry')

    # --- Nodes ---
    nodes = ng.nodes
    links = ng.links
    
    n_in = nodes.new('NodeGroupInput')
    n_in.location = (-1600, 0)
    n_out = nodes.new('NodeGroupOutput')
    n_out.location = (1400, 0)
    n_out.is_active_output = True
    
    # helper for safe linking
    def link_safe(from_socket, node_to, input_name_or_index):
        to_socket = None
        if isinstance(input_name_or_index, str):
            if input_name_or_index in node_to.inputs:
                to_socket = node_to.inputs[input_name_or_index]
        elif isinstance(input_name_or_index, int):
            if input_name_or_index < len(node_to.inputs):
                to_socket = node_to.inputs[input_name_or_index]
        
        if to_socket:
            links.new(from_socket, to_socket)
        else:
            print(f"Warning: Could not link to {node_to.name} socket {input_name_or_index}")

    # 1. Grid
    n_grid = nodes.new('GeometryNodeMeshGrid')
    n_grid.location = (-1400, 0)
    n_grid.inputs[0].default_value = 40.0 # Size X
    n_grid.inputs[1].default_value = 40.0 # Size Y
    # Inputs: [Geo, Res, Distort, Gap, HScale, HAmp, Seed]
    # Indices: 0    1    2        3    4       5     6
    link_safe(n_in.outputs[1], n_grid, 'Vertices X')
    link_safe(n_in.outputs[1], n_grid, 'Vertices Y')
    
    # 2. Distortion (The "Invisible" Fix)
    n_set_pos = nodes.new('GeometryNodeSetPosition')
    n_set_pos.location = (-1200, 0)
    
    n_noise = nodes.new('ShaderNodeTexNoise')
    n_noise.location = (-1400, -300)
    n_noise.inputs['Scale'].default_value = 5.0 # Fine detail noise for jitter
    n_noise.noise_dimensions = '4D'
    link_safe(n_in.outputs[6], n_noise, 'W')

    n_sub = nodes.new('ShaderNodeVectorMath')
    n_sub.operation = 'SUBTRACT'
    n_sub.inputs[1].default_value = (0.5, 0.5, 0.5)
    link_safe(n_noise.outputs['Color'], n_sub, 0)
    
    n_scale = nodes.new('ShaderNodeVectorMath')
    n_scale.operation = 'SCALE'
    link_safe(n_sub.outputs[0], n_scale, 0)
    # Correctly finding Scale input. Usually index 3 for 'SCALE' op.
    link_safe(n_in.outputs[2], n_scale, 3) 
    
    n_mult_z = nodes.new('ShaderNodeVectorMath')
    n_mult_z.operation = 'MULTIPLY'
    n_mult_z.inputs[1].default_value = (1.0, 1.0, 0.0) # Flatten Z
    link_safe(n_scale.outputs[0], n_mult_z, 0)
    
    link_safe(n_grid.outputs[0], n_set_pos, 'Geometry')
    link_safe(n_mult_z.outputs[0], n_set_pos, 'Offset')
    
    # 3. Triangulate -> Dual Mesh
    n_tri = nodes.new('GeometryNodeTriangulate')
    n_tri.location = (-1000, 0)
    link_safe(n_set_pos.outputs[0], n_tri, 0)
    
    n_dual = nodes.new('GeometryNodeDualMesh')
    n_dual.location = (-800, 0)
    link_safe(n_tri.outputs[0], n_dual, 0)
    
    # 4. Scale Elements (Roads)
    n_scale_el = nodes.new('GeometryNodeScaleElements')
    n_scale_el.location = (-600, 0)
    n_scale_el.domain = 'FACE'
    
    n_math_gap = nodes.new('ShaderNodeMath')
    n_math_gap.operation = 'SUBTRACT'
    n_math_gap.inputs[0].default_value = 1.0
    link_safe(n_in.outputs[3], n_math_gap, 1) # Gap
    
    link_safe(n_dual.outputs[0], n_scale_el, 'Geometry')
    link_safe(n_math_gap.outputs[0], n_scale_el, 'Scale')
    
    # 5. Extrude with HEIGHT MAP (The new feature)
    n_extrude = nodes.new('GeometryNodeExtrudeMesh')
    n_extrude.location = (-300, 0)
    link_safe(n_scale_el.outputs[0], n_extrude, 'Mesh')
    
    # Height Noise Logic
    n_h_noise = nodes.new('ShaderNodeTexNoise')
    n_h_noise.location = (-600, -400)
    # Use Position as vector so "Downtown" stays in place
    n_pos = nodes.new('GeometryNodeInputPosition')
    n_pos.location = (-800, -400)
    link_safe(n_pos.outputs[0], n_h_noise, 'Vector')
    link_safe(n_in.outputs[4], n_h_noise, 'Scale') # Height Scale (Zoom)
    
    # Multiply Noise * Height Amplitude
    n_math_amp = nodes.new('ShaderNodeMath')
    n_math_amp.operation = 'MULTIPLY'
    # Use 'Factor' (grayscale)
    link_safe(n_h_noise.outputs['Factor'], n_math_amp, 0)
    link_safe(n_in.outputs[5], n_math_amp, 1) # Height Amp
    
    # Add Minimum Height (so nothing is flat)
    n_math_min = nodes.new('ShaderNodeMath')
    n_math_min.operation = 'ADD'
    n_math_min.inputs[1].default_value = 0.2
    link_safe(n_math_amp.outputs[0], n_math_min, 0)
    
    link_safe(n_math_min.outputs[0], n_extrude, 'Offset Scale')
    
    # 6. Capture Height for Color (Bonus)
    n_store = nodes.new('GeometryNodeStoreNamedAttribute')
    n_store.location = (0, 0)
    n_store.data_type = 'FLOAT_COLOR'
    n_store.domain = 'CORNER'
    n_store.name = "BuildingColor" # Store internally or just use Set Material?
    # Simpler: Just Set Material
    
    n_mat = nodes.new('GeometryNodeSetMaterial')
    n_mat.location = (200, 0)
    link_safe(n_extrude.outputs[0], n_mat, 0)
    
    link_safe(n_mat.outputs[0], n_out, 0)
    
    return ng

def create_scene_v4():
    print("Creating Voronoi City V4 (Smart Heights)...")
    
    if "CityV4" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["CityV4"], do_unlink=True)
        
    mesh = bpy.data.meshes.new("CityV4Mesh")
    obj = bpy.data.objects.new("CityV4", mesh)
    
    if obj.name not in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.link(obj)
    
    bpy.context.view_layer.objects.active = obj
    
    # Create Material
    mat = bpy.data.materials.new(name="CityMatV4")
    mat.use_nodes = True
    obj.data.materials.append(mat)
    
    # Setup Geometry Nodes
    try:
        ng = create_v4_nodes()
        mod = obj.modifiers.new("CityGenV4", 'NODES')
        mod.node_group = ng
        
        # Link Material
        set_mat = next((n for n in ng.nodes if n.type == 'SET_MATERIAL'), None)
        if set_mat:
            set_mat.inputs[2].default_value = mat
            
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()

    print("Voronoi V4 Created.")

if __name__ == "__main__":
    create_scene_v4()
