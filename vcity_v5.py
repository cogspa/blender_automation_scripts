import bpy
import traceback

def create_v5_nodes():
    group_name = "VoronoiCity_V5"
    if group_name in bpy.data.node_groups:
        bpy.data.node_groups.remove(bpy.data.node_groups[group_name])

    ng = bpy.data.node_groups.new(group_name, 'GeometryNodeTree')
    
    # --- Robust Socket Creator ---
    def add_socket(name, type_str, default, min_v=None, max_v=None):
        if hasattr(ng, 'interface'):
            sock = ng.interface.new_socket(name, in_out='INPUT', socket_type=type_str)
            sock.default_value = default
            if min_v is not None: sock.min_value = min_v
        else:
            sock = ng.inputs.new(type_str, name)
            sock.default_value = default

    if hasattr(ng, 'interface'):
        ng.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
        ng.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    else:
        ng.inputs.new('NodeSocketGeometry', 'Geometry')
        ng.outputs.new('NodeSocketGeometry', 'Geometry')

    # Inputs
    add_socket("Resolution", 'NodeSocketInt', 40, 2)
    add_socket("Distortion", 'NodeSocketFloat', 5.0, 0.0)
    add_socket("Inset Amount", 'NodeSocketFloat', 0.15, 0.0, 0.9) # The Gap
    add_socket("Height Scale", 'NodeSocketFloat', 0.12)
    add_socket("Height Amp", 'NodeSocketFloat', 8.0)
    add_socket("Seed", 'NodeSocketInt', 123)

    nodes = ng.nodes
    links = ng.links
    
    def link_safe(from_s, to_node, idx_name):
        try:
            if isinstance(idx_name, str):
                if idx_name in to_node.inputs: links.new(from_s, to_node.inputs[idx_name])
            elif isinstance(idx_name, int):
                if idx_name < len(to_node.inputs): links.new(from_s, to_node.inputs[idx_name])
        except: pass

    n_in = nodes.new('NodeGroupInput')
    n_in.location = (-1600, 0)
    n_out = nodes.new('NodeGroupOutput')
    n_out.location = (1600, 0)
    n_out.is_active_output = True

    # 1. Base Grid & Voronoi Logic
    n_grid = nodes.new('GeometryNodeMeshGrid')
    n_grid.location = (-1400, 0)
    n_grid.inputs[0].default_value = 50.0 # Size X
    n_grid.inputs[1].default_value = 50.0 # Size Y
    link_safe(n_in.outputs[1], n_grid, 2) # Res X
    link_safe(n_in.outputs[1], n_grid, 3) # Res Y
    
    # Distortion
    n_set_pos = nodes.new('GeometryNodeSetPosition')
    n_set_pos.location = (-1200, 0)
    n_noise = nodes.new('ShaderNodeTexNoise')
    n_noise.location = (-1400, -300)
    n_noise.inputs['Scale'].default_value = 5.0
    n_noise.noise_dimensions = '4D'
    link_safe(n_in.outputs[6], n_noise, 'W')
    
    n_sub = nodes.new('ShaderNodeVectorMath')
    n_sub.operation = 'SUBTRACT'
    n_sub.inputs[1].default_value = (0.5, 0.5, 0.5)
    link_safe(n_noise.outputs[0], n_sub, 0)
    n_scale = nodes.new('ShaderNodeVectorMath')
    n_scale.operation = 'SCALE'
    link_safe(n_sub.outputs[0], n_scale, 0)
    link_safe(n_in.outputs[2], n_scale, 3) # Distortion Amt
    
    n_flat = nodes.new('ShaderNodeVectorMath')
    n_flat.operation = 'MULTIPLY'
    n_flat.inputs[1].default_value = (1.0, 1.0, 0.0)
    link_safe(n_scale.outputs[0], n_flat, 0)
    
    # Offset only works with mesh connected
    link_safe(n_grid.outputs[0], n_set_pos, 0)
    link_safe(n_flat.outputs[0], n_set_pos, 2) # Offset
    
    # Dual Mesh
    n_tri = nodes.new('GeometryNodeTriangulate')
    n_tri.location = (-1000, 0)
    link_safe(n_set_pos.outputs[0], n_tri, 0)
    n_dual = nodes.new('GeometryNodeDualMesh')
    n_dual.location = (-800, 0)
    link_safe(n_tri.outputs[0], n_dual, 0)
    
    # --- V5 Branching ---
    
    # BRANCH A: The Ground (Outer Cells / Roads)
    # We want these flat.
    n_mat_ground = nodes.new('GeometryNodeSetMaterial')
    n_mat_ground.location = (500, -200)
    n_mat_ground.label = "Set Ground Material"
    # To avoid Z fighting, maybe extrude slightly DOWN or offset
    # Let's offset Z by -0.01
    n_offset_ground = nodes.new('GeometryNodeTransform') # transform is simpler usually
    n_offset_ground.location = (300, -200)
    n_offset_ground.inputs['Translation'].default_value = (0, 0, -0.02)
    
    link_safe(n_dual.outputs[0], n_offset_ground, 0)
    link_safe(n_offset_ground.outputs[0], n_mat_ground, 0)
    
    # BRANCH B: Buildings (Inset Cells)
    # Scale Elements
    n_inset = nodes.new('GeometryNodeScaleElements')
    n_inset.location = (-600, 200)
    n_inset.domain = 'FACE'
    
    n_gap_math = nodes.new('ShaderNodeMath')
    n_gap_math.operation = 'SUBTRACT'
    n_gap_math.inputs[0].default_value = 1.0
    link_safe(n_in.outputs[3], n_gap_math, 1) # Inset Amount
    
    link_safe(n_dual.outputs[0], n_inset, 0)
    link_safe(n_gap_math.outputs[0], n_inset, 'Scale')
    
    # Extrude
    n_ext = nodes.new('GeometryNodeExtrudeMesh')
    n_ext.location = (-300, 200)
    link_safe(n_inset.outputs[0], n_ext, 0)
    
    # Height Calculation
    n_h_noise = nodes.new('ShaderNodeTexNoise')
    n_h_noise.location = (-600, 500)
    link_safe(n_in.outputs[6], n_h_noise, 'W')
    link_safe(n_in.outputs[4], n_h_noise, 'Scale') # H Scale
    
    # Use Position for height map
    n_pos = nodes.new('GeometryNodeInputPosition')
    n_pos.location = (-800, 500)
    link_safe(n_pos.outputs[0], n_h_noise, 'Vector')
    
    n_h_mult = nodes.new('ShaderNodeMath')
    n_h_mult.operation = 'MULTIPLY'
    link_safe(n_h_noise.outputs[0], n_h_mult, 0)
    link_safe(n_in.outputs[5], n_h_mult, 1) # H Amp
    
    n_h_add = nodes.new('ShaderNodeMath')
    n_h_add.operation = 'ADD'
    n_h_add.inputs[1].default_value = 0.5 # Min height
    link_safe(n_h_mult.outputs[0], n_h_add, 0)
    
    link_safe(n_h_add.outputs[0], n_ext, 'Offset Scale')
    
    # Building Material
    n_mat_bldg = nodes.new('GeometryNodeSetMaterial')
    n_mat_bldg.location = (500, 200)
    n_mat_bldg.label = "Set Building Material"
    
    # Only assign to Top and Side?
    # n_ext outputs: 0:Mesh, 1:Top, 2:Side.
    # We want to assign simple material to whole mesh for now.
    link_safe(n_ext.outputs[0], n_mat_bldg, 0)
    
    # JOIN
    n_join = nodes.new('GeometryNodeJoinGeometry')
    n_join.location = (800, 0)
    link_safe(n_mat_ground.outputs[0], n_join, 0)
    link_safe(n_mat_bldg.outputs[0], n_join, 0)
    
    link_safe(n_join.outputs[0], n_out, 0)
    return ng

def create_scene_v5():
    print("Creating Voronoi City V5 (Inset/Roads)...")
    if "CityV5" in bpy.data.objects:
        bpy.data.objects.remove(bpy.data.objects["CityV5"], do_unlink=True)
        
    mesh = bpy.data.meshes.new("CityV5Mesh")
    obj = bpy.data.objects.new("CityV5", mesh)
    if obj.name not in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    
    # Materials
    def get_mat(name, color):
        m = bpy.data.materials.get(name)
        if not m:
             m = bpy.data.materials.new(name)
             m.use_nodes = True
             n = m.node_tree.nodes.get('Principled BSDF')
             if n: n.inputs[0].default_value = color
        return m
        
    mat_road = get_mat("RoadMat", (0.05, 0.05, 0.07, 1)) # Dark Asphalt
    mat_bldg = get_mat("BuildingMat", (0.2, 0.3, 0.4, 1)) # Glassy Blue
    
    ng = create_v5_nodes()
    mod = obj.modifiers.new("CityGenV5", 'NODES')
    mod.node_group = ng
    
    # Assign Materials to Nodes
    for n in ng.nodes:
        if n.type == 'SET_MATERIAL':
            if "Ground" in n.label:
                n.inputs[2].default_value = mat_road
            elif "Building" in n.label:
                n.inputs[2].default_value = mat_bldg
                
    obj.data.materials.append(mat_road)
    obj.data.materials.append(mat_bldg)
    
    print("V5 Created.")

if __name__ == "__main__":
    try:
        create_scene_v5()
    except:
        traceback.print_exc()
