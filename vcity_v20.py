import bpy
import traceback

def create_v20_nodes():
    group_name = "VoronoiCity_V20_Fix"
    if group_name in bpy.data.node_groups:
        bpy.data.node_groups.remove(bpy.data.node_groups[group_name])

    ng = bpy.data.node_groups.new(group_name, 'GeometryNodeTree')
    
    # Interface
    def add_socket(name, type_str, default, min_v=None):
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

    add_socket("Resolution", 'NodeSocketInt', 40, 2)
    add_socket("Street Width", 'NodeSocketFloat', 0.8, 0.0)
    add_socket("Min Height", 'NodeSocketFloat', 0.2, 0.0)
    add_socket("Max Height", 'NodeSocketFloat', 4.0, 0.0)
    add_socket("Seed", 'NodeSocketInt', 700)
    add_socket("Color Seed", 'NodeSocketInt', 123)

    nodes = ng.nodes
    links = ng.links
    
    def get_parameter(name):
        n = nodes.new('NodeGroupInput')
        n.hide = True 
        if name in n.outputs:
            return n.outputs[name]
        return None

    def link_safe(from_socket, to_node, idx_or_name):
        if not from_socket: return
        target = None
        if isinstance(idx_or_name, str):
            if idx_or_name in to_node.inputs: target = to_node.inputs[idx_or_name]
        elif isinstance(idx_or_name, int):
            if idx_or_name < len(to_node.inputs): target = to_node.inputs[idx_or_name]
        if not target and len(to_node.inputs) > 0: target = to_node.inputs[0]
        if target: links.new(from_socket, target)

    n_out = nodes.new('NodeGroupOutput')
    n_out.location = (4000, 0) # Far out
    n_out.is_active_output = True

    # 1. Grid
    n_grid = nodes.new('GeometryNodeMeshGrid')
    n_grid.location = (-2200, 0)
    n_grid.inputs[0].default_value = 50.0 
    n_grid.inputs[1].default_value = 50.0 
    link_safe(get_parameter("Resolution"), n_grid, "Vertices X")
    link_safe(get_parameter("Resolution"), n_grid, "Vertices Y")
    
    # 2. Distortion
    n_set_pos = nodes.new('GeometryNodeSetPosition')
    n_set_pos.location = (-2000, 0)
    
    n_noise = nodes.new('ShaderNodeTexNoise')
    n_noise.location = (-2200, -300)
    n_noise.inputs['Scale'].default_value = 5.0
    n_noise.noise_dimensions = '4D'
    link_safe(get_parameter("Seed"), n_noise, "W")

    n_sub = nodes.new('ShaderNodeVectorMath')
    n_sub.operation = 'SUBTRACT'
    n_sub.inputs[1].default_value = (0.5, 0.5, 0.5)
    link_safe(n_noise.outputs[0], n_sub, 0)
    
    n_scale = nodes.new('ShaderNodeVectorMath')
    n_scale.operation = 'SCALE'
    n_scale.inputs[3].default_value = 5.0
    link_safe(n_sub.outputs[0], n_scale, 0)
    
    n_flat = nodes.new('ShaderNodeVectorMath')
    n_flat.operation = 'MULTIPLY'
    n_flat.inputs[1].default_value = (1.0, 1.0, 0.0)
    link_safe(n_scale.outputs[0], n_flat, 0)
    
    link_safe(n_grid.outputs[0], n_set_pos, "Geometry")
    link_safe(n_flat.outputs[0], n_set_pos, "Offset")
    
    # 3. Voronoi
    n_tri = nodes.new('GeometryNodeTriangulate')
    n_tri.location = (-1800, 0)
    link_safe(n_set_pos.outputs[0], n_tri, "Mesh")
    
    n_dual = nodes.new('GeometryNodeDualMesh')
    n_dual.location = (-1600, 0)
    link_safe(n_tri.outputs[0], n_dual, "Mesh")
    
    # --- GENERATE ID ---
    # Noise Texture -> Value -> Map to Integer
    n_id_noise = nodes.new('ShaderNodeTexNoise')
    n_id_noise.location = (-1600, 400)
    n_id_noise.noise_dimensions = '4D' # Use W for seed
    n_id_noise.inputs['Scale'].default_value = 100.0 # High freq
    
    n_pos_in = nodes.new('GeometryNodeInputPosition')
    link_safe(n_pos_in.outputs[0], n_id_noise, "Vector")
    link_safe(get_parameter("Color Seed"), n_id_noise, "W")
    
    # Map 0.0-1.0 to 1-5
    n_map = nodes.new('ShaderNodeMapRange')
    n_map.location = (-1400, 400)
    n_map.inputs['From Min'].default_value = 0.0
    n_map.inputs['From Max'].default_value = 1.0
    n_map.inputs['To Min'].default_value = 1.0
    n_map.inputs['To Max'].default_value = 4.99
    link_safe(n_id_noise.outputs['Fac'], n_map, "Value")
    
    n_round = nodes.new('ShaderNodeMath')
    n_round.operation = 'FLOOR' # 1, 2, 3, 4
    n_round.location = (-1200, 400)
    link_safe(n_map.outputs[0], n_round, 0)
    
    # Store "MatID"
    n_store = nodes.new('GeometryNodeStoreNamedAttribute')
    n_store.location = (-1400, 0)
    n_store.data_type = 'INT'
    n_store.domain = 'FACE'
    n_store.name = "MatID"
    
    link_safe(n_dual.outputs[0], n_store, "Geometry")
    link_safe(n_round.outputs[0], n_store, "Value")
    
    # --- SPLIT ---
    # Roads (Branch A)
    n_mat_road = nodes.new('GeometryNodeSetMaterial') 
    n_mat_road.location = (-800, -300)
    link_safe(n_store.outputs[0], n_mat_road, "Geometry") 
    # Logic to assign road material will happen at end via Join or separate branch.
    # Actually, road is always Mat 0.
    
    # Buildings (Branch B)
    n_split = nodes.new('GeometryNodeSplitEdges')
    n_split.location = (-1200, 200)
    link_safe(n_store.outputs[0], n_split, "Mesh")
    
    n_shrink = nodes.new('GeometryNodeScaleElements')
    n_shrink.location = (-1000, 200)
    n_shrink.domain = 'FACE'
    link_safe(n_split.outputs[0], n_shrink, "Geometry")
    link_safe(get_parameter("Street Width"), n_shrink, "Scale")
    
    n_ext = nodes.new('GeometryNodeExtrudeMesh')
    n_ext.location = (-800, 200)
    link_safe(n_shrink.outputs[0], n_ext, "Mesh")
    
    # Height
    n_rand_h = nodes.new('FunctionNodeRandomValue')
    n_rand_h.location = (-1000, 500)
    link_safe(get_parameter("Min Height"), n_rand_h, "Min")
    link_safe(get_parameter("Max Height"), n_rand_h, "Max")
    link_safe(n_pos_in.outputs[0], n_rand_h, "ID") 
    link_safe(get_parameter("Seed"), n_rand_h, "Seed")
    link_safe(n_rand_h.outputs[1], n_ext, "Offset Scale")
    
    # --- MATERIAL ASSIGNMENT BY BRANCHING ---
    # Reading MatID
    n_read = nodes.new('GeometryNodeInputNamedAttribute')
    n_read.data_type = 'INT'
    n_read.name = "MatID"
    n_read.location = (-600, 600)
    
    # We need to assign Mat 1 if ID=1, Mat 2 if ID=2...
    # We will use "Set Material" nodes with Selection.
    
    # Mat 1 (Red)
    n_eq1 = nodes.new('FunctionNodeCompare')
    n_eq1.data_type = 'INT'
    n_eq1.operation = 'EQUAL'
    n_eq1.inputs[3].default_value = 1 # B=1
    link_safe(n_read.outputs["Attribute"], n_eq1, "A")
    
    n_set1 = nodes.new('GeometryNodeSetMaterial')
    n_set1.location = (-400, 200)
    link_safe(n_ext.outputs[0], n_set1, "Geometry")
    link_safe(n_eq1.outputs["Result"], n_set1, "Selection")
    
    # Mat 2 (Blue) - Chain it or Parallel?
    # Set Material overrides. So we can chain them.
    # But Selection must be specific.
    
    n_eq2 = nodes.new('FunctionNodeCompare')
    n_eq2.data_type = 'INT'
    n_eq2.operation = 'EQUAL'
    n_eq2.inputs[3].default_value = 2
    link_safe(n_read.outputs["Attribute"], n_eq2, "A")
    
    n_set2 = nodes.new('GeometryNodeSetMaterial')
    n_set2.location = (-200, 200)
    link_safe(n_set1.outputs[0], n_set2, "Geometry")
    link_safe(n_eq2.outputs["Result"], n_set2, "Selection")
    
    # Mat 3 (Orange)
    n_eq3 = nodes.new('FunctionNodeCompare')
    n_eq3.data_type = 'INT'
    n_eq3.operation = 'EQUAL'
    n_eq3.inputs[3].default_value = 3
    link_safe(n_read.outputs["Attribute"], n_eq3, "A")
    
    n_set3 = nodes.new('GeometryNodeSetMaterial')
    n_set3.location = (0, 200)
    link_safe(n_set2.outputs[0], n_set3, "Geometry")
    link_safe(n_eq3.outputs["Result"], n_set3, "Selection")
    
    # Mat 4 (Green)
    n_eq4 = nodes.new('FunctionNodeCompare')
    n_eq4.data_type = 'INT'
    n_eq4.operation = 'EQUAL'
    n_eq4.inputs[3].default_value = 4
    link_safe(n_read.outputs["Attribute"], n_eq4, "A")
    
    n_set4 = nodes.new('GeometryNodeSetMaterial')
    n_set4.location = (200, 200)
    link_safe(n_set3.outputs[0], n_set4, "Geometry")
    link_safe(n_eq4.outputs["Result"], n_set4, "Selection")
    
    # Lift
    n_lift = nodes.new('GeometryNodeTransform')
    n_lift.location = (400, 200)
    n_lift.inputs['Translation'].default_value = (0, 0, 0.005)
    link_safe(n_set4.outputs[0], n_lift, "Geometry")
    
    # Join
    n_join = nodes.new('GeometryNodeJoinGeometry')
    n_join.location = (600, 0)
    link_safe(n_mat_road.outputs[0], n_join, "Geometry")
    link_safe(n_lift.outputs[0], n_join, "Geometry")
    
    link_safe(n_join.outputs[0], n_out, "Geometry")
    
    return ng

def setup_scene_v20():
    print("=" * 40)
    print("Creating V20 (Explicit Material Sets)...")
    
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for c in bpy.data.collections: bpy.data.collections.remove(c)
    
    mesh = bpy.data.meshes.new("CityV20Mesh")
    obj = bpy.data.objects.new("CityV20", mesh)
    bpy.context.scene.collection.objects.link(obj)
    
    colors = [
        (0.05, 0.05, 0.05, 1), # 0 Road
        (0.8, 0.1, 0.1, 1),    # 1 Red
        (0.1, 0.1, 0.8, 1),    # 2 Blue
        (1.0, 0.5, 0.0, 1),    # 3 Orange
        (0.1, 0.8, 0.1, 1),    # 4 Green
    ]
    
    mats = []
    for i, col in enumerate(colors):
        mat = bpy.data.materials.new(f"Mat_City_{i}")
        mat.use_nodes = True
        mat.node_tree.nodes['Principled BSDF'].inputs[0].default_value = col
        mat.diffuse_color = col 
        obj.data.materials.append(mat)
        mats.append(mat)
    
    ng = create_v20_nodes()
    bpy.context.view_layer.objects.active = obj
    mod = obj.modifiers.new("CityGenV20", 'NODES')
    mod.node_group = ng
    
    # Bind Materials to Set Material Nodes using Labels or Locations
    # Since we can't easily find nodes by index, we will iterate and check connectivity or type
    # Wait, simple loop logic:
    
    # Find Set Material Nodes.
    # 0 -> Road (-800, -300)
    # 1 -> Red (-400, 200)
    # 2 -> Blue (-200, 200)
    # 3 -> Orange (0, 200)
    # 4 -> Green (200, 200)
    
    # We can assume order of creation or location X
    set_mat_nodes = [n for n in ng.nodes if n.type == 'SET_MATERIAL']
    # Sort by Location X
    set_mat_nodes.sort(key=lambda n: n.location.x)
    
    # Expected order based on X:
    # Road (-800) -> Red (-400) -> Blue (-200) -> Orange (0) -> Green (200)
    
    if len(set_mat_nodes) >= 5:
        set_mat_nodes[0].inputs[2].default_value = mats[0] # Road
        set_mat_nodes[1].inputs[2].default_value = mats[1] # Red
        set_mat_nodes[2].inputs[2].default_value = mats[2] # Blue
        set_mat_nodes[3].inputs[2].default_value = mats[3] # Orange
        set_mat_nodes[4].inputs[2].default_value = mats[4] # Green
        
    print("V20 Success.")

if __name__ == "__main__":
    try:
        setup_scene_v20()
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
