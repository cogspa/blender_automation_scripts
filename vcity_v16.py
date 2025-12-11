import bpy
import traceback

def create_v16_nodes():
    group_name = "VoronoiCity_V16"
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
    add_socket("Seed", 'NodeSocketInt', 700)
    add_socket("Color Seed", 'NodeSocketInt', 999)

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
    
    # Random Height - Position Based
    n_pos = nodes.new('GeometryNodeInputPosition')
    n_pos.location = (-1600, 500)
    
    # Random Color - Position Based (Bulletproof ID)
    # Use Sine of position logic or Random Value seeded by position
    n_rand_pos = nodes.new('FunctionNodeRandomValue')
    n_rand_pos.data_type = 'FLOAT'
    n_rand_pos.location = (-1200, 500)
    
    link_safe(get_parameter("Min Height"), n_rand_pos, "Min")
    link_safe(get_parameter("Max Height"), n_rand_pos, "Max")
    link_safe(get_parameter("Seed"), n_rand_pos, "Seed") # Seed
    # Vector ID!
    link_safe(n_pos.outputs[0], n_rand_pos, "ID") # Vector/Int/Float - If ID accepts vector, good.
    # FunctionNodeRandomValue "ID" input is Integer. If you connect Vector, it converts.
    # To be safe, let's hash coordinates manually? No, default conversion usually sums or length.
    
    link_safe(n_rand_pos.outputs[1], n_ext, "Offset Scale")
    
    # --- RANDOM COLOR (POSITION BASED) ---
    n_rand_col = nodes.new('FunctionNodeRandomValue')
    n_rand_col.location = (-1000, 700)
    n_rand_col.data_type = 'FLOAT'
    n_rand_col.inputs['Min'].default_value = 0.0
    n_rand_col.inputs['Max'].default_value = 1.0
    
    link_safe(n_pos.outputs[0], n_rand_col, "ID") # Use Position as ID
    link_safe(get_parameter("Color Seed"), n_rand_col, "Seed")
    
    # Store on POINT to be safe for shader interpolation
    n_store_col = nodes.new('GeometryNodeStoreNamedAttribute')
    n_store_col.location = (-800, 500)
    n_store_col.data_type = 'FLOAT'
    n_store_col.domain = 'POINT' # Store on Points (Vertices)
    n_store_col.name = "ColorFactor"
    
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

def setup_scene_v16():
    print("=" * 40)
    print("Creating V16 (Position-Based Randomness)...")
    
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for c in bpy.data.collections: bpy.data.collections.remove(c)
    for _ in range(3): bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

    ng = create_v16_nodes()
    
    mesh = bpy.data.meshes.new("CityV16Mesh")
    obj = bpy.data.objects.new("CityV16", mesh)
    bpy.context.scene.collection.objects.link(obj)
    
    m_road = bpy.data.materials.new("RoadMatV16")
    m_road.use_nodes = True
    m_road.node_tree.nodes['Principled BSDF'].inputs[0].default_value = (0.05, 0.05, 0.05, 1)

    m_bldg = bpy.data.materials.new("BldgMatV16")
    m_bldg.use_nodes = True
    nodes = m_bldg.node_tree.nodes
    links = m_bldg.node_tree.links
    bsdf = nodes['Principled BSDF']
    
    # Attribute Node -> Look for "ColorFactor"
    attr_node = nodes.new('ShaderNodeAttribute')
    attr_node.attribute_name = "ColorFactor"
    attr_node.location = (-500, 200)
    
    # Ramp
    ramp = nodes.new('ShaderNodeValToRGB')
    ramp.location = (-300, 200)
    ramp.color_ramp.elements[0].color = (1.0, 0.2, 0.2, 1) # Red
    ramp.color_ramp.elements[1].color = (0.2, 0.2, 1.0, 1) # Blue
    ramp.color_ramp.elements.new(0.5)
    ramp.color_ramp.elements[1].color = (0.2, 1.0, 0.2, 1) # Green
    
    links.new(attr_node.outputs['Fac'], ramp.inputs['Fac'])
    links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
    
    obj.data.materials.append(m_road)
    obj.data.materials.append(m_bldg)
    
    bpy.context.view_layer.objects.active = obj
    mod = obj.modifiers.new("CityGenV16", 'NODES')
    mod.node_group = ng
    
    for n in ng.nodes:
        if n.type == 'SET_MATERIAL':
            if n.location[1] > 0: n.inputs[2].default_value = m_bldg
            else: n.inputs[2].default_value = m_road
            
    print("V16 Success.")

if __name__ == "__main__":
    try:
        setup_scene_v16()
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
