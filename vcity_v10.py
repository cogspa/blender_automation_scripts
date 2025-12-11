import bpy
import traceback

def create_v10_nodes():
    group_name = "VoronoiCity_V10"
    if group_name in bpy.data.node_groups:
        bpy.data.node_groups.remove(bpy.data.node_groups[group_name])

    ng = bpy.data.node_groups.new(group_name, 'GeometryNodeTree')
    
    # --- Interface ---
    # We will use explicit names for referencing later
    
    # Helper to create interface socket
    def add_input(name, type_str, default, min_v=None):
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

    # Create Inputs
    add_input("Resolution", 'NodeSocketInt', 40, 2)
    add_input("Distortion", 'NodeSocketFloat', 5.0, 0.0)
    add_input("Street Width", 'NodeSocketFloat', 0.8, 0.0)
    add_input("Min Height", 'NodeSocketFloat', 0.2, 0.0)
    add_input("Max Height", 'NodeSocketFloat', 4.0, 0.0)
    add_input("Seed", 'NodeSocketInt', 300)

    nodes = ng.nodes
    links = ng.links
    
    # --- PROPER NAME-BASED LINKING ---
    def link_safe(from_socket, to_node, input_name_or_idx):
        target = None
        # Try by Name first
        if isinstance(input_name_or_idx, str):
            if input_name_or_idx in to_node.inputs:
                target = to_node.inputs[input_name_or_idx]
        
        # Try by Index
        if not target and isinstance(input_name_or_idx, int):
            if input_name_or_idx < len(to_node.inputs):
                target = to_node.inputs[input_name_or_idx]
        
        # Fallback to Index 0 if typical geometry node
        if not target and len(to_node.inputs) > 0:
            target = to_node.inputs[0]

        if target:
            links.new(from_socket, target)
        else:
            print(f"FAILED LINK: {to_node.name} -> {input_name_or_idx}")

    n_in = nodes.new('NodeGroupInput')
    n_in.location = (-2200, 0)
    n_out = nodes.new('NodeGroupOutput')
    n_out.location = (2200, 0)
    n_out.is_active_output = True
    
    # Helper to get Group Input by Name
    def get_input_socket(name):
        if name in n_in.outputs:
            return n_in.outputs[name]
        # Fallback to index if name fails (legacy blender)
        # We know our order: 0:Geo, 1:Res, 2:Dist, 3:Street, 4:Min, 5:Max, 6:Seed
        ordering = ["Geometry", "Resolution", "Distortion", "Street Width", "Min Height", "Max Height", "Seed"]
        if name in ordering:
            return n_in.outputs[ordering.index(name)]
        return None

    # 1. Grid
    n_grid = nodes.new('GeometryNodeMeshGrid')
    n_grid.location = (-2000, 0)
    n_grid.inputs[0].default_value = 50.0 
    n_grid.inputs[1].default_value = 50.0 
    link_safe(get_input_socket("Resolution"), n_grid, 2)
    link_safe(get_input_socket("Resolution"), n_grid, 3)
    
    # 2. Distortion
    n_set_pos = nodes.new('GeometryNodeSetPosition')
    n_set_pos.location = (-1800, 0)
    
    n_noise = nodes.new('ShaderNodeTexNoise')
    n_noise.location = (-2000, -300)
    n_noise.inputs['Scale'].default_value = 5.0
    n_noise.noise_dimensions = '4D'
    link_safe(get_input_socket("Seed"), n_noise, 'W')

    n_sub = nodes.new('ShaderNodeVectorMath')
    n_sub.operation = 'SUBTRACT'
    n_sub.inputs[1].default_value = (0.5, 0.5, 0.5)
    link_safe(n_noise.outputs[0], n_sub, 0)
    
    n_scale = nodes.new('ShaderNodeVectorMath')
    n_scale.operation = 'SCALE'
    link_safe(n_sub.outputs[0], n_scale, 0)
    link_safe(get_input_socket("Distortion"), n_scale, 3) 
    
    n_flat = nodes.new('ShaderNodeVectorMath')
    n_flat.operation = 'MULTIPLY'
    n_flat.inputs[1].default_value = (1.0, 1.0, 0.0)
    link_safe(n_scale.outputs[0], n_flat, 0)
    
    link_safe(n_grid.outputs[0], n_set_pos, 0)
    link_safe(n_flat.outputs[0], n_set_pos, "Offset")
    
    # 3. Voronoi
    n_tri = nodes.new('GeometryNodeTriangulate')
    n_tri.location = (-1600, 0)
    link_safe(n_set_pos.outputs[0], n_tri, 0)
    
    n_dual = nodes.new('GeometryNodeDualMesh')
    n_dual.location = (-1400, 0)
    link_safe(n_tri.outputs[0], n_dual, 0)
    
    # BRANCH A: ROADS
    n_mat_road = nodes.new('GeometryNodeSetMaterial')
    n_mat_road.location = (-600, -200)
    n_mat_road.label = "Set Road Mat"
    link_safe(n_dual.outputs[0], n_mat_road, 0)
    
    # BRANCH B: BUILDINGS
    n_split = nodes.new('GeometryNodeSplitEdges')
    n_split.location = (-1200, 200)
    link_safe(n_dual.outputs[0], n_split, 0)
    
    n_shrink = nodes.new('GeometryNodeScaleElements')
    n_shrink.location = (-1000, 200)
    n_shrink.domain = 'FACE'
    link_safe(n_split.outputs[0], n_shrink, 0)
    link_safe(get_input_socket("Street Width"), n_shrink, 2)
    
    n_ext = nodes.new('GeometryNodeExtrudeMesh')
    n_ext.location = (-800, 200)
    link_safe(n_shrink.outputs[0], n_ext, 0)
    
    # RANDOM HEIGHT Logic
    n_rand = nodes.new('FunctionNodeRandomValue')
    n_rand.location = (-1000, 500)
    n_rand.data_type = 'FLOAT'
    
    n_idx = nodes.new('GeometryNodeInputIndex')
    n_idx.location = (-1200, 500)
    
    # IMPORTANT: Ensure 'Min' and 'Max' are linked correctly using names/indices
    link_safe(get_input_socket("Min Height"), n_rand, 0) # Min
    link_safe(get_input_socket("Max Height"), n_rand, 1) # Max
    link_safe(n_idx.outputs[0], n_rand, 2) # ID
    link_safe(get_input_socket("Seed"), n_rand, 3) # Seed
    
    # Link Random -> Extrude Offset Scale
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

def setup_scene_v10():
    print("=" * 40)
    print("Creating V10 (Robust Input Linking)...")
    
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for c in bpy.data.collections: bpy.data.collections.remove(c)
    for _ in range(3): bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

    ng = create_v10_nodes()
    
    # Create Object
    mesh = bpy.data.meshes.new("CityV10Mesh")
    obj = bpy.data.objects.new("CityV10", mesh)
    bpy.context.scene.collection.objects.link(obj)
    
    m_road = bpy.data.materials.new("RoadMatV10")
    m_road.use_nodes = True
    m_road.node_tree.nodes['Principled BSDF'].inputs[0].default_value = (0.05, 0.05, 0.05, 1)

    m_bldg = bpy.data.materials.new("BldgMatV10")
    m_bldg.use_nodes = True
    m_bldg.node_tree.nodes['Principled BSDF'].inputs[0].default_value = (0.8, 0.4, 0.0, 1)
    
    obj.data.materials.append(m_road)
    obj.data.materials.append(m_bldg)
    
    bpy.context.view_layer.objects.active = obj
    mod = obj.modifiers.new("CityGenV10", 'NODES')
    mod.node_group = ng
    
    # Assign Materials
    for n in ng.nodes:
        if n.type == 'SET_MATERIAL':
            if "Road" in n.label: n.inputs[2].default_value = m_road
            elif "Bldg" in n.label: n.inputs[2].default_value = m_bldg
            
    print("V10 Success.")

if __name__ == "__main__":
    try:
        setup_scene_v10()
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
