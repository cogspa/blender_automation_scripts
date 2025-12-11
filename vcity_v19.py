import bpy
import traceback

def create_v19_nodes():
    group_name = "VoronoiCity_V19"
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
    
    # Store Material Index Attribute
    n_rand_idx = nodes.new('FunctionNodeRandomValue')
    n_rand_idx.data_type = 'INT'
    n_rand_idx.location = (-1600, 400)
    n_rand_idx.inputs['Min'].default_value = 1 
    n_rand_idx.inputs['Max'].default_value = 5
    
    # Position ID for randomness
    n_pos_seed = nodes.new('GeometryNodeInputPosition')
    link_safe(n_pos_seed.outputs[0], n_rand_idx, "ID")
    link_safe(get_parameter("Color Seed"), n_rand_idx, "Seed")
    
    n_store = nodes.new('GeometryNodeStoreNamedAttribute')
    n_store.location = (-1400, 400)
    n_store.data_type = 'INT'
    n_store.domain = 'FACE'
    n_store.name = "MatIdx"
    
    link_safe(n_dual.outputs[0], n_store, "Geometry")
    link_safe(n_rand_idx.outputs["Value"], n_store, "Value")
    
    # Roads
    n_mat_road = nodes.new('GeometryNodeSetMaterialIndex') 
    n_mat_road.location = (-800, -300)
    link_safe(n_store.outputs[0], n_mat_road, "Geometry")
    n_mat_road.inputs["Material Index"].default_value = 0 # Road
    
    # Buildings
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
    n_rand_h.data_type = 'FLOAT'
    n_pos = nodes.new('GeometryNodeInputPosition')
    link_safe(get_parameter("Min Height"), n_rand_h, "Min")
    link_safe(get_parameter("Max Height"), n_rand_h, "Max")
    link_safe(n_pos.outputs[0], n_rand_h, "ID") 
    link_safe(get_parameter("Seed"), n_rand_h, "Seed")
    link_safe(n_rand_h.outputs[1], n_ext, "Offset Scale")
    
    # Read Back Mat Idx
    n_read = nodes.new('GeometryNodeInputNamedAttribute')
    n_read.data_type = 'INT'
    n_read.name = "MatIdx"
    n_read.location = (-800, 600)
    
    n_set_idx = nodes.new('GeometryNodeSetMaterialIndex')
    n_set_idx.location = (-600, 200)
    link_safe(n_ext.outputs[0], n_set_idx, "Geometry")
    link_safe(n_read.outputs["Attribute"], n_set_idx, "Material Index")
    
    # Lift
    n_lift = nodes.new('GeometryNodeTransform')
    n_lift.location = (-400, 200)
    n_lift.inputs['Translation'].default_value = (0, 0, 0.005)
    link_safe(n_set_idx.outputs[0], n_lift, "Geometry")
    
    # Join
    n_join = nodes.new('GeometryNodeJoinGeometry')
    n_join.location = (0, 0)
    link_safe(n_mat_road.outputs[0], n_join, "Geometry")
    link_safe(n_lift.outputs[0], n_join, "Geometry")
    
    link_safe(n_join.outputs[0], n_out, "Geometry")
    
    return ng

def setup_scene_v19():
    print("=" * 40)
    print("Creating V19 (Viewport Colors Fixed)...")
    
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for c in bpy.data.collections: bpy.data.collections.remove(c)
    
    mesh = bpy.data.meshes.new("CityV19Mesh")
    obj = bpy.data.objects.new("CityV19", mesh)
    bpy.context.scene.collection.objects.link(obj)
    
    colors = [
        (0.05, 0.05, 0.05, 1), # 0
        (0.8, 0.2, 0.2, 1),    # 1: Red
        (0.2, 0.2, 0.8, 1),    # 2: Blue
        (0.8, 0.5, 0.0, 1),    # 3: Orange
        (0.2, 0.8, 0.2, 1),    # 4: Green
    ]
    
    for i, col in enumerate(colors):
        mat = bpy.data.materials.new(f"Mat_City_{i}")
        mat.use_nodes = True
        mat.node_tree.nodes['Principled BSDF'].inputs[0].default_value = col
        # CRITICAL FIX FOR SOLID VIEW:
        mat.diffuse_color = col 
        obj.data.materials.append(mat)
    
    ng = create_v19_nodes()
    bpy.context.view_layer.objects.active = obj
    mod = obj.modifiers.new("CityGenV19", 'NODES')
    mod.node_group = ng
    
    print("V19 Success.")

if __name__ == "__main__":
    try:
        setup_scene_v19()
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
