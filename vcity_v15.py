import bpy
import traceback

def create_v15_nodes():
    group_name = "VoronoiCity_V15"
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
    add_socket("Distortion", 'NodeSocketFloat', 5.0, 0.0)
    add_socket("Street Width", 'NodeSocketFloat', 0.8, 0.0)
    add_socket("Min Height", 'NodeSocketFloat', 0.2, 0.0)
    add_socket("Max Height", 'NodeSocketFloat', 4.0, 0.0)
    add_socket("Seed", 'NodeSocketInt', 600)
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
    n_out.location = (2500, 0)
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
    link_safe(n_sub.outputs[0], n_scale, 0)
    link_safe(get_parameter("Distortion"), n_scale, "Scale")
    
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
    
    # ROADS
    n_mat_road = nodes.new('GeometryNodeSetMaterial')
    n_mat_road.location = (-800, -300)
    link_safe(n_dual.outputs[0], n_mat_road, "Geometry")
    
    # BUILDINGS
    n_split = nodes.new('GeometryNodeSplitEdges')
    n_split.location = (-1400, 200)
    link_safe(n_dual.outputs[0], n_split, "Mesh")
    
    n_shrink = nodes.new('GeometryNodeScaleElements')
    n_shrink.location = (-1200, 200)
    n_shrink.domain = 'FACE'
    link_safe(n_split.outputs[0], n_shrink, "Geometry")
    link_safe(get_parameter("Street Width"), n_shrink, "Scale")
    
    n_ext = nodes.new('GeometryNodeExtrudeMesh')
    n_ext.location = (-1000, 200)
    link_safe(n_shrink.outputs[0], n_ext, "Mesh")
    
    # Random Height
    n_rand = nodes.new('FunctionNodeRandomValue')
    n_rand.location = (-1200, 500)
    n_rand.data_type = 'FLOAT'
    
    # Try using MESH ISLAND INDEX if available, else standard Index
    # Since we Split Edges, each building is an island.
    # We will try to find "Mesh Island" node
    n_island = None
    try:
        n_island = nodes.new('GeometryNodeInputMeshIsland')
        n_island.location = (-1400, 500)
        idx_socket = n_island.outputs['Island Index']
    except:
        # Fallback for older Blender
        n_idx = nodes.new('GeometryNodeInputIndex')
        n_idx.location = (-1400, 500)
        idx_socket = n_idx.outputs[0]
    
    link_safe(get_parameter("Min Height"), n_rand, "Min")
    link_safe(get_parameter("Max Height"), n_rand, "Max")
    link_safe(idx_socket, n_rand, "ID")
    link_safe(get_parameter("Seed"), n_rand, "Seed")
    
    link_safe(n_rand.outputs[1], n_ext, "Offset Scale")
    
    # --- STORE RANDOM COLOR ATTRIBUTE ---
    n_rand_col = nodes.new('FunctionNodeRandomValue')
    n_rand_col.location = (-1000, 700)
    n_rand_col.data_type = 'FLOAT'
    n_rand_col.inputs['Min'].default_value = 0.0
    n_rand_col.inputs['Max'].default_value = 1.0
    
    link_safe(idx_socket, n_rand_col, "ID")
    link_safe(get_parameter("Color Seed"), n_rand_col, "Seed")
    
    # Store as 'Col' (Standard) and on FACE
    n_store_col = nodes.new('GeometryNodeStoreNamedAttribute')
    n_store_col.location = (-800, 500)
    n_store_col.data_type = 'FLOAT'
    n_store_col.domain = 'FACE'
    n_store_col.name = "Col" 
    
    link_safe(n_ext.outputs[0], n_store_col, "Geometry")
    link_safe(n_rand_col.outputs[1], n_store_col, "Value")
    
    n_mat_bldg = nodes.new('GeometryNodeSetMaterial')
    n_mat_bldg.location = (-600, 200)
    link_safe(n_store_col.outputs[0], n_mat_bldg, "Geometry")
    
    # Lift
    n_lift = nodes.new('GeometryNodeTransform')
    n_lift.location = (-400, 200)
    n_lift.inputs['Translation'].default_value = (0, 0, 0.005)
    link_safe(n_mat_bldg.outputs[0], n_lift, "Geometry")
    
    # Join
    n_join = nodes.new('GeometryNodeJoinGeometry')
    n_join.location = (0, 0)
    link_safe(n_mat_road.outputs[0], n_join, "Geometry")
    link_safe(n_lift.outputs[0], n_join, "Geometry")
    
    link_safe(n_join.outputs[0], n_out, "Geometry")
    
    return ng

def setup_scene_v15():
    print("=" * 40)
    print("Creating V15 (Mesh Island fix)...")
    
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for c in bpy.data.collections: bpy.data.collections.remove(c)
    for _ in range(3): bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

    ng = create_v15_nodes()
    
    mesh = bpy.data.meshes.new("CityV15Mesh")
    obj = bpy.data.objects.new("CityV15", mesh)
    bpy.context.scene.collection.objects.link(obj)
    
    m_road = bpy.data.materials.new("RoadMatV15")
    m_road.use_nodes = True
    m_road.node_tree.nodes['Principled BSDF'].inputs[0].default_value = (0.05, 0.05, 0.05, 1)

    m_bldg = bpy.data.materials.new("BldgMatV15")
    m_bldg.use_nodes = True
    nodes = m_bldg.node_tree.nodes
    links = m_bldg.node_tree.links
    
    bsdf = nodes['Principled BSDF']
    
    # Attribute Node -> Now looking for "Col"
    attr_node = nodes.new('ShaderNodeAttribute')
    attr_node.attribute_name = "Col"
    attr_node.location = (-500, 200)
    
    # Color Ramp
    ramp = nodes.new('ShaderNodeValToRGB')
    ramp.location = (-300, 200)
    ramp.color_ramp.interpolation = 'CONSTANT' # Hard cuts for distinct building colors
    ramp.color_ramp.elements[0].color = (0.8, 0.1, 0.1, 1) # Red
    ramp.color_ramp.elements.new(0.33)
    ramp.color_ramp.elements[1].color = (0.1, 0.8, 0.1, 1) # Green
    ramp.color_ramp.elements.new(0.66)
    ramp.color_ramp.elements[2].color = (0.1, 0.1, 0.8, 1) # Blue
    
    links.new(attr_node.outputs['Fac'], ramp.inputs['Fac'])
    links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
    
    obj.data.materials.append(m_road)
    obj.data.materials.append(m_bldg)
    
    bpy.context.view_layer.objects.active = obj
    mod = obj.modifiers.new("CityGenV15", 'NODES')
    mod.node_group = ng
    
    for n in ng.nodes:
        if n.type == 'SET_MATERIAL':
            if n.location[1] > 0: 
                n.inputs[2].default_value = m_bldg
            else:
                n.inputs[2].default_value = m_road
            
    print("V15 Success.")

if __name__ == "__main__":
    try:
        setup_scene_v15()
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
