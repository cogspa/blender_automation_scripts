import bpy
import traceback

def create_v11_nodes():
    group_name = "VoronoiCity_V11"
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
    add_socket("Seed", 'NodeSocketInt', 400)

    nodes = ng.nodes
    links = ng.links
    
    # Helper: Create a fresh Group Input node for every parameter usage
    # This ensures valid linking and prevents "greyed out" sockets
    def get_parameter(name):
        n = nodes.new('NodeGroupInput')
        n.hide = True # Keep graph clean
        # Find the output named 'name'
        if name in n.outputs:
            return n.outputs[name]
        return None

    def link_to_name(from_socket, to_node, name):
        if name in to_node.inputs and from_socket:
            links.new(from_socket, to_node.inputs[name])
        elif from_socket and len(to_node.inputs) > 0:
             # Fallback index 0 if specific name fails
             links.new(from_socket, to_node.inputs[0])

    n_out = nodes.new('NodeGroupOutput')
    n_out.location = (2000, 0)
    n_out.is_active_output = True

    # 1. Grid
    n_grid = nodes.new('GeometryNodeMeshGrid')
    n_grid.location = (-1800, 0)
    n_grid.inputs[0].default_value = 50.0 
    n_grid.inputs[1].default_value = 50.0 
    link_to_name(get_parameter("Resolution"), n_grid, "Vertices X")
    link_to_name(get_parameter("Resolution"), n_grid, "Vertices Y")
    
    # 2. Distortion
    n_set_pos = nodes.new('GeometryNodeSetPosition')
    n_set_pos.location = (-1600, 0)
    
    n_noise = nodes.new('ShaderNodeTexNoise')
    n_noise.location = (-1800, -300)
    n_noise.inputs['Scale'].default_value = 5.0
    n_noise.noise_dimensions = '4D'
    link_to_name(get_parameter("Seed"), n_noise, "W")

    n_sub = nodes.new('ShaderNodeVectorMath')
    n_sub.operation = 'SUBTRACT'
    n_sub.inputs[1].default_value = (0.5, 0.5, 0.5)
    link_to_name(n_noise.outputs[0], n_sub, 0)
    
    n_scale = nodes.new('ShaderNodeVectorMath')
    n_scale.operation = 'SCALE'
    link_to_name(n_sub.outputs[0], n_scale, 0)
    link_to_name(get_parameter("Distortion"), n_scale, "Scale")
    
    n_flat = nodes.new('ShaderNodeVectorMath')
    n_flat.operation = 'MULTIPLY'
    n_flat.inputs[1].default_value = (1.0, 1.0, 0.0)
    link_to_name(n_scale.outputs[0], n_flat, 0)
    
    link_to_name(n_grid.outputs[0], n_set_pos, "Geometry")
    link_to_name(n_flat.outputs[0], n_set_pos, "Offset")
    
    # 3. Voronoi
    n_tri = nodes.new('GeometryNodeTriangulate')
    n_tri.location = (-1400, 0)
    link_to_name(n_set_pos.outputs[0], n_tri, "Mesh")
    
    n_dual = nodes.new('GeometryNodeDualMesh')
    n_dual.location = (-1200, 0)
    link_to_name(n_tri.outputs[0], n_dual, "Mesh")
    
    # 4. Roads Branch
    n_mat_road = nodes.new('GeometryNodeSetMaterial')
    n_mat_road.location = (-600, -200)
    link_to_name(n_dual.outputs[0], n_mat_road, "Geometry")
    
    # 5. Buildings Branch
    n_split = nodes.new('GeometryNodeSplitEdges')
    n_split.location = (-1000, 200)
    link_to_name(n_dual.outputs[0], n_split, "Mesh")
    
    n_shrink = nodes.new('GeometryNodeScaleElements')
    n_shrink.location = (-800, 200)
    n_shrink.domain = 'FACE'
    link_to_name(n_split.outputs[0], n_shrink, "Geometry")
    link_to_name(get_parameter("Street Width"), n_shrink, "Scale")
    
    n_ext = nodes.new('GeometryNodeExtrudeMesh')
    n_ext.location = (-600, 200)
    link_to_name(n_shrink.outputs[0], n_ext, "Mesh")
    
    # Random Height
    n_rand = nodes.new('FunctionNodeRandomValue')
    n_rand.location = (-800, 500)
    n_rand.data_type = 'FLOAT'
    
    n_idx = nodes.new('GeometryNodeInputIndex')
    n_idx.location = (-1000, 500)
    
    link_to_name(get_parameter("Min Height"), n_rand, "Min")
    link_to_name(get_parameter("Max Height"), n_rand, "Max")
    link_to_name(n_idx.outputs[0], n_rand, "ID")
    link_to_name(get_parameter("Seed"), n_rand, "Seed")
    
    link_to_name(n_rand.outputs[1], n_ext, "Offset Scale")
    
    n_mat_bldg = nodes.new('GeometryNodeSetMaterial')
    n_mat_bldg.location = (-400, 200)
    link_to_name(n_ext.outputs[0], n_mat_bldg, "Geometry")
    
    # Join
    n_join = nodes.new('GeometryNodeJoinGeometry')
    n_join.location = (-200, 0)
    link_to_name(n_mat_road.outputs[0], n_join, "Geometry")
    link_to_name(n_mat_bldg.outputs[0], n_join, "Geometry")
    
    link_to_name(n_join.outputs[0], n_out, "Geometry")
    
    return ng

def setup_scene_v11():
    print("=" * 40)
    print("Creating V11 (Fresh Group Inputs)...")
    
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for c in bpy.data.collections: bpy.data.collections.remove(c)
    for _ in range(3): bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

    ng = create_v11_nodes()
    
    mesh = bpy.data.meshes.new("CityV11Mesh")
    obj = bpy.data.objects.new("CityV11", mesh)
    bpy.context.scene.collection.objects.link(obj)
    
    m_road = bpy.data.materials.new("RoadMatV11")
    m_road.use_nodes = True
    m_road.node_tree.nodes['Principled BSDF'].inputs[0].default_value = (0.05, 0.05, 0.05, 1)

    m_bldg = bpy.data.materials.new("BldgMatV11")
    m_bldg.use_nodes = True
    m_bldg.node_tree.nodes['Principled BSDF'].inputs[0].default_value = (0.8, 0.4, 0.0, 1)
    
    obj.data.materials.append(m_road)
    obj.data.materials.append(m_bldg)
    
    bpy.context.view_layer.objects.active = obj
    mod = obj.modifiers.new("CityGenV11", 'NODES')
    mod.node_group = ng
    
    # Assign Materials
    for n in ng.nodes:
        if n.type == 'SET_MATERIAL':
            # Basic label check might fail if I didn't set labels above
            # But we can check location or connection
            if n.location[1] > 0: # Building branch is typically Y > 0
                n.inputs[2].default_value = m_bldg
            else:
                n.inputs[2].default_value = m_road
            
    print("V11 Success.")

if __name__ == "__main__":
    try:
        setup_scene_v11()
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
