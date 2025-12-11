import bpy
import traceback

# --- 1. NODE GRAPH CREATOR ---
def create_v9_nodes():
    group_name = "VoronoiCity_V9"
    if group_name in bpy.data.node_groups:
        bpy.data.node_groups.remove(bpy.data.node_groups[group_name])

    ng = bpy.data.node_groups.new(group_name, 'GeometryNodeTree')
    
    # Interface Helper
    def add_socket(name, type_str, default, min_v=None):
        if hasattr(ng, 'interface'):
            sock = ng.interface.new_socket(name, in_out='INPUT', socket_type=type_str)
            sock.default_value = default
        else:
            sock = ng.inputs.new(type_str, name)
            sock.default_value = default

    if hasattr(ng, 'interface'):
        ng.interface.new_socket("Geometry", in_out='INPUT', socket_type='NodeSocketGeometry')
        ng.interface.new_socket("Geometry", in_out='OUTPUT', socket_type='NodeSocketGeometry')
    else:
        ng.inputs.new('NodeSocketGeometry', 'Geometry')
        ng.outputs.new('NodeSocketGeometry', 'Geometry')

    # Add Inputs
    add_socket("Resolution", 'NodeSocketInt', 40, 2)
    add_socket("Distortion", 'NodeSocketFloat', 5.0, 0.0)
    add_socket("Street Width", 'NodeSocketFloat', 0.8, 0.0)
    add_socket("Min Height", 'NodeSocketFloat', 0.2, 0.0)
    add_socket("Max Height", 'NodeSocketFloat', 4.0, 0.0)
    add_socket("Seed", 'NodeSocketInt', 200)

    nodes = ng.nodes
    links = ng.links
    
    # Link Helper
    def link_safe(from_s, to_node, idx_or_name=0):
        target = None
        if isinstance(idx_or_name, str):
            if idx_or_name in to_node.inputs: target = to_node.inputs[idx_or_name]
        elif isinstance(idx_or_name, int):
             if idx_or_name < len(to_node.inputs): target = to_node.inputs[idx_or_name]
        if not target and len(to_node.inputs) > 0: target = to_node.inputs[0]
        
        if target: links.new(from_s, target)
        else: print(f"!!! FAILED LINK: {to_node.name} Socket {idx_or_name}")

    n_in = nodes.new('NodeGroupInput')
    n_in.location = (-2200, 0)
    n_out = nodes.new('NodeGroupOutput')
    n_out.location = (2200, 0)
    n_out.is_active_output = True

    # 1. Grid
    n_grid = nodes.new('GeometryNodeMeshGrid')
    n_grid.location = (-2000, 0)
    n_grid.inputs[0].default_value = 50.0 
    n_grid.inputs[1].default_value = 50.0 
    link_safe(n_in.outputs[1], n_grid, 2)
    link_safe(n_in.outputs[1], n_grid, 3)
    
    # 2. Distortion
    n_set_pos = nodes.new('GeometryNodeSetPosition')
    n_set_pos.location = (-1800, 0)
    
    n_noise = nodes.new('ShaderNodeTexNoise')
    n_noise.location = (-2000, -300)
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
    
    link_safe(n_grid.outputs[0], n_set_pos, 0)
    link_safe(n_flat.outputs[0], n_set_pos, "Offset")
    
    # 3. Voronoi Core (Triangulate -> Dual Mesh)
    n_tri = nodes.new('GeometryNodeTriangulate')
    n_tri.location = (-1600, 0)
    link_safe(n_set_pos.outputs[0], n_tri, 0)
    
    n_dual = nodes.new('GeometryNodeDualMesh')
    n_dual.location = (-1400, 0)
    link_safe(n_tri.outputs[0], n_dual, 0)
    
    # --- BRANCH A: ROADS ---
    n_mat_road = nodes.new('GeometryNodeSetMaterial')
    n_mat_road.location = (-600, -200)
    n_mat_road.label = "Set Road Mat"
    link_safe(n_dual.outputs[0], n_mat_road, 0)
    
    # --- BRANCH B: BUILDINGS ---
    n_split = nodes.new('GeometryNodeSplitEdges')
    n_split.location = (-1200, 200)
    link_safe(n_dual.outputs[0], n_split, 0)
    
    n_shrink = nodes.new('GeometryNodeScaleElements')
    n_shrink.location = (-1000, 200)
    n_shrink.domain = 'FACE'
    link_safe(n_split.outputs[0], n_shrink, 0)
    link_safe(n_in.outputs[3], n_shrink, 2) # Street Width Scale
    
    n_ext = nodes.new('GeometryNodeExtrudeMesh')
    n_ext.location = (-800, 200)
    link_safe(n_shrink.outputs[0], n_ext, 0)
    
    # Random Height
    n_rand = nodes.new('FunctionNodeRandomValue')
    n_rand.location = (-1000, 500)
    n_rand.data_type = 'FLOAT'
    
    n_idx = nodes.new('GeometryNodeInputIndex')
    n_idx.location = (-1200, 500)
    
    link_safe(n_in.outputs[4], n_rand, 0) # Min
    link_safe(n_in.outputs[5], n_rand, 1) # Max
    link_safe(n_idx.outputs[0], n_rand, 2) # Use Index as Seed/ID
    link_safe(n_in.outputs[6], n_rand, 3) # Global Seed
    
    link_safe(n_rand.outputs[1], n_ext, "Offset Scale")
    
    n_mat_bldg = nodes.new('GeometryNodeSetMaterial')
    n_mat_bldg.location = (-600, 200)
    n_mat_bldg.label = "Set Bldg Mat"
    link_safe(n_ext.outputs[0], n_mat_bldg, 0)
    
    # Join
    n_join = nodes.new('GeometryNodeJoinGeometry')
    n_join.location = (-200, 0)
    link_safe(n_mat_road.outputs[0], n_join, 0)
    link_safe(n_mat_bldg.outputs[0], n_join, 0)
    
    link_safe(n_join.outputs[0], n_out, 0)
    
    return ng


# --- 2. SCENE MANAGER ---
def setup_scene_v9():
    print("=" * 40)
    print("RESETTING SCENE + Creating V9.1 (Unique Func Names)...")
    
    # 1. Reset
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for c in bpy.data.collections: bpy.data.collections.remove(c)
    for _ in range(3): bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

    # 2. Materials
    m_road = bpy.data.materials.new("RoadMatV9")
    m_road.use_nodes = True
    m_road.node_tree.nodes['Principled BSDF'].inputs[0].default_value = (0.05, 0.05, 0.05, 1)

    m_bldg = bpy.data.materials.new("BldgMatV9")
    m_bldg.use_nodes = True
    m_bldg.node_tree.nodes['Principled BSDF'].inputs[0].default_value = (0.8, 0.4, 0.0, 1)

    # 3. Object & Nodes
    ng = create_v9_nodes() # Call the node creator
    
    mesh = bpy.data.meshes.new("CityV9Mesh")
    obj = bpy.data.objects.new("CityV9", mesh)
    bpy.context.scene.collection.objects.link(obj)
    
    obj.data.materials.append(m_road)
    obj.data.materials.append(m_bldg)
    
    bpy.context.view_layer.objects.active = obj
    mod = obj.modifiers.new("CityGenV9", 'NODES')
    mod.node_group = ng
    
    # Assign Materials in Node Group
    for n in ng.nodes:
        if n.type == 'SET_MATERIAL':
            if "Road" in n.label: n.inputs[2].default_value = m_road
            elif "Bldg" in n.label: n.inputs[2].default_value = m_bldg
            
    print("V9.1 Success.")

if __name__ == "__main__":
    try:
        setup_scene_v9()
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
