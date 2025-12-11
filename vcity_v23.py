import bpy
import traceback

def create_v23_nodes():
    group_name = "VoronoiCity_V23"
    if group_name in bpy.data.node_groups:
        bpy.data.node_groups.remove(bpy.data.node_groups[group_name])

    ng = bpy.data.node_groups.new(group_name, 'GeometryNodeTree')
    
    # Interface
    def add_socket(name, type_str, default, min_v=None, max_v=None):
        if hasattr(ng, 'interface'):
            sock = ng.interface.new_socket(name, in_out='INPUT', socket_type=type_str)
            sock.default_value = default
            if min_v is not None: sock.min_value = min_v
            if max_v is not None: sock.max_value = max_v
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
    add_socket("Street Width", 'NodeSocketFloat', 0.8, 0.0, 1.0)
    add_socket("Min Height", 'NodeSocketFloat', 2.0, 0.0) # Increased default
    add_socket("Max Height", 'NodeSocketFloat', 8.0, 0.0) # Increased default for towers
    add_socket("Seed", 'NodeSocketInt', 700)
    add_socket("Color Seed", 'NodeSocketInt', 123)
    add_socket("Floors", 'NodeSocketInt', 4, 1, 10)
    add_socket("Min Taper", 'NodeSocketFloat', 0.8, 0.1, 1.2)
    add_socket("Max Taper", 'NodeSocketFloat', 1.0, 0.1, 1.2)
    add_socket("Taper Seed", 'NodeSocketInt', 456)

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
    n_out.location = (5000, 0)
    n_out.is_active_output = True

    # 1. Grid
    n_grid = nodes.new('GeometryNodeMeshGrid')
    n_grid.location = (-2400, 0)
    n_grid.inputs[0].default_value = 50.0 
    n_grid.inputs[1].default_value = 50.0 
    link_safe(get_parameter("Resolution"), n_grid, "Vertices X")
    link_safe(get_parameter("Resolution"), n_grid, "Vertices Y")
    
    # 2. Distortion
    n_set_pos = nodes.new('GeometryNodeSetPosition')
    n_set_pos.location = (-2200, 0)
    
    n_noise = nodes.new('ShaderNodeTexNoise')
    n_noise.location = (-2400, -300)
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
    n_tri.location = (-2000, 0)
    link_safe(n_set_pos.outputs[0], n_tri, "Mesh")
    
    n_dual = nodes.new('GeometryNodeDualMesh')
    n_dual.location = (-1800, 0)
    link_safe(n_tri.outputs[0], n_dual, "Mesh")
    
    # 4. Generate MatID & TaperFactor
    n_idx = nodes.new('GeometryNodeInputIndex')
    n_idx.location = (-1800, 400)
    
    # MatID (1-4)
    n_rand_mat = nodes.new('FunctionNodeRandomValue')
    n_rand_mat.data_type = 'FLOAT'
    n_rand_mat.location = (-1600, 500)
    n_rand_mat.inputs['Min'].default_value = 1.0
    n_rand_mat.inputs['Max'].default_value = 4.99
    link_safe(n_idx.outputs[0], n_rand_mat, "ID")
    link_safe(get_parameter("Color Seed"), n_rand_mat, "Seed")
    
    n_floor_mat = nodes.new('ShaderNodeMath')
    n_floor_mat.operation = 'FLOOR'
    n_floor_mat.location = (-1400, 500)
    link_safe(n_rand_mat.outputs[1], n_floor_mat, 0)
    
    # TaperFactor
    n_rand_taper = nodes.new('FunctionNodeRandomValue')
    n_rand_taper.data_type = 'FLOAT'
    n_rand_taper.location = (-1600, 300)
    link_safe(get_parameter("Min Taper"), n_rand_taper, "Min")
    link_safe(get_parameter("Max Taper"), n_rand_taper, "Max")
    link_safe(n_idx.outputs[0], n_rand_taper, "ID")
    link_safe(get_parameter("Taper Seed"), n_rand_taper, "Seed")
    
    # Store MatID
    n_store_mat = nodes.new('GeometryNodeStoreNamedAttribute')
    n_store_mat.location = (-1600, 0)
    n_store_mat.data_type = 'INT'
    n_store_mat.domain = 'FACE'
    n_store_mat.inputs['Name'].default_value = "MatID"
    link_safe(n_dual.outputs[0], n_store_mat, "Geometry")
    link_safe(n_floor_mat.outputs[0], n_store_mat, "Value")
    
    # Store TaperFactor
    n_store_taper = nodes.new('GeometryNodeStoreNamedAttribute')
    n_store_taper.location = (-1400, 0)
    n_store_taper.data_type = 'FLOAT'
    n_store_taper.domain = 'FACE'
    n_store_taper.inputs['Name'].default_value = "TaperFactor"
    link_safe(n_store_mat.outputs[0], n_store_taper, "Geometry")
    link_safe(n_rand_taper.outputs[1], n_store_taper, "Value")
    
    # 5. Roads
    n_mat_road = nodes.new('GeometryNodeSetMaterial') 
    n_mat_road.location = (-800, -400)
    link_safe(n_store_taper.outputs[0], n_mat_road, "Geometry")
    
    # 6. Buildings - Split & Tapered Extrusions
    n_split = nodes.new('GeometryNodeSplitEdges')
    n_split.location = (-1200, 200)
    link_safe(n_store_taper.outputs[0], n_split, "Mesh")
    
    n_shrink = nodes.new('GeometryNodeScaleElements')
    n_shrink.location = (-1000, 200)
    n_shrink.domain = 'FACE'
    link_safe(n_split.outputs[0], n_shrink, "Geometry")
    link_safe(get_parameter("Street Width"), n_shrink, "Scale")
    
    # Calculate Height Step
    n_rand_h = nodes.new('FunctionNodeRandomValue')
    n_rand_h.data_type = 'FLOAT'
    n_rand_h.location = (-1000, 600)
    link_safe(get_parameter("Min Height"), n_rand_h, "Min")
    link_safe(get_parameter("Max Height"), n_rand_h, "Max")
    link_safe(n_idx.outputs[0], n_rand_h, "ID")
    link_safe(get_parameter("Seed"), n_rand_h, "Seed")
    
    n_div_floors = nodes.new('ShaderNodeMath')
    n_div_floors.operation = 'DIVIDE'
    n_div_floors.location = (-800, 600)
    link_safe(n_rand_h.outputs[1], n_div_floors, 0)
    link_safe(get_parameter("Floors"), n_div_floors, 1)
    
    n_read_taper = nodes.new('GeometryNodeInputNamedAttribute')
    n_read_taper.data_type = 'FLOAT'
    n_read_taper.inputs['Name'].default_value = "TaperFactor"
    n_read_taper.location = (-800, 400)
    
    # Extrude 1
    n_ext1 = nodes.new('GeometryNodeExtrudeMesh')
    n_ext1.location = (-600, 200)
    link_safe(n_shrink.outputs[0], n_ext1, "Mesh")
    link_safe(n_div_floors.outputs[0], n_ext1, "Offset Scale")
    
    n_taper1 = nodes.new('GeometryNodeScaleElements')
    n_taper1.location = (-400, 200)
    n_taper1.domain = 'FACE'
    link_safe(n_ext1.outputs[0], n_taper1, "Geometry")
    link_safe(n_ext1.outputs["Top"], n_taper1, "Selection")
    link_safe(n_read_taper.outputs["Attribute"], n_taper1, "Scale")
    
    # Extrude 2
    n_ext2 = nodes.new('GeometryNodeExtrudeMesh')
    n_ext2.location = (-200, 200)
    link_safe(n_taper1.outputs[0], n_ext2, "Mesh")
    link_safe(n_ext1.outputs["Top"], n_ext2, "Selection")
    link_safe(n_div_floors.outputs[0], n_ext2, "Offset Scale")
    
    n_taper2 = nodes.new('GeometryNodeScaleElements')
    n_taper2.location = (0, 200)
    n_taper2.domain = 'FACE'
    link_safe(n_ext2.outputs[0], n_taper2, "Geometry")
    link_safe(n_ext2.outputs["Top"], n_taper2, "Selection")
    link_safe(n_read_taper.outputs["Attribute"], n_taper2, "Scale")
    
    # Extrude 3
    n_ext3 = nodes.new('GeometryNodeExtrudeMesh')
    n_ext3.location = (200, 200)
    link_safe(n_taper2.outputs[0], n_ext3, "Mesh")
    link_safe(n_ext2.outputs["Top"], n_ext3, "Selection")
    link_safe(n_div_floors.outputs[0], n_ext3, "Offset Scale")
    
    n_taper3 = nodes.new('GeometryNodeScaleElements')
    n_taper3.location = (400, 200)
    n_taper3.domain = 'FACE'
    link_safe(n_ext3.outputs[0], n_taper3, "Geometry")
    link_safe(n_ext3.outputs["Top"], n_taper3, "Selection")
    link_safe(n_read_taper.outputs["Attribute"], n_taper3, "Scale")
    
    # Extrude 4
    n_ext4 = nodes.new('GeometryNodeExtrudeMesh')
    n_ext4.location = (600, 200)
    link_safe(n_taper3.outputs[0], n_ext4, "Mesh")
    link_safe(n_ext3.outputs["Top"], n_ext4, "Selection")
    link_safe(n_div_floors.outputs[0], n_ext4, "Offset Scale")
    
    n_taper4 = nodes.new('GeometryNodeScaleElements')
    n_taper4.location = (800, 200)
    n_taper4.domain = 'FACE'
    link_safe(n_ext4.outputs[0], n_taper4, "Geometry")
    link_safe(n_ext4.outputs["Top"], n_taper4, "Selection")
    link_safe(n_read_taper.outputs["Attribute"], n_taper4, "Scale")
    
    # 7. Material Assignment
    n_read_mat = nodes.new('GeometryNodeInputNamedAttribute')
    n_read_mat.data_type = 'INT'
    n_read_mat.inputs['Name'].default_value = "MatID"
    n_read_mat.location = (1000, 600)
    
    # Mat 1
    n_eq1 = nodes.new('FunctionNodeCompare')
    n_eq1.data_type = 'INT'
    n_eq1.operation = 'EQUAL'
    n_eq1.inputs[3].default_value = 1
    link_safe(n_read_mat.outputs["Attribute"], n_eq1, "A")
    
    n_set1 = nodes.new('GeometryNodeSetMaterial')
    n_set1.location = (1000, 200)
    link_safe(n_taper4.outputs[0], n_set1, "Geometry")
    link_safe(n_eq1.outputs["Result"], n_set1, "Selection")
    
    # Mat 2
    n_eq2 = nodes.new('FunctionNodeCompare')
    n_eq2.data_type = 'INT'
    n_eq2.operation = 'EQUAL'
    n_eq2.inputs[3].default_value = 2
    link_safe(n_read_mat.outputs["Attribute"], n_eq2, "A")
    
    n_set2 = nodes.new('GeometryNodeSetMaterial')
    n_set2.location = (1200, 200)
    link_safe(n_set1.outputs[0], n_set2, "Geometry")
    link_safe(n_eq2.outputs["Result"], n_set2, "Selection")
    
    # Mat 3
    n_eq3 = nodes.new('FunctionNodeCompare')
    n_eq3.data_type = 'INT'
    n_eq3.operation = 'EQUAL'
    n_eq3.inputs[3].default_value = 3
    link_safe(n_read_mat.outputs["Attribute"], n_eq3, "A")
    
    n_set3 = nodes.new('GeometryNodeSetMaterial')
    n_set3.location = (1400, 200)
    link_safe(n_set2.outputs[0], n_set3, "Geometry")
    link_safe(n_eq3.outputs["Result"], n_set3, "Selection")
    
    # Mat 4
    n_eq4 = nodes.new('FunctionNodeCompare')
    n_eq4.data_type = 'INT'
    n_eq4.operation = 'EQUAL'
    n_eq4.inputs[3].default_value = 4
    link_safe(n_read_mat.outputs["Attribute"], n_eq4, "A")
    
    n_set4 = nodes.new('GeometryNodeSetMaterial')
    n_set4.location = (1600, 200)
    link_safe(n_set3.outputs[0], n_set4, "Geometry")
    link_safe(n_eq4.outputs["Result"], n_set4, "Selection")
    
    # 8. Lift & Join
    n_lift = nodes.new('GeometryNodeTransform')
    n_lift.location = (1800, 200)
    n_lift.inputs['Translation'].default_value = (0, 0, 0.005)
    link_safe(n_set4.outputs[0], n_lift, "Geometry")
    
    n_join = nodes.new('GeometryNodeJoinGeometry')
    n_join.location = (2000, 0)
    link_safe(n_mat_road.outputs[0], n_join, "Geometry")
    link_safe(n_lift.outputs[0], n_join, "Geometry")
    
    link_safe(n_join.outputs[0], n_out, "Geometry")
    
    return ng

def setup_scene_v23():
    print("=" * 40)
    print("Creating V23 (Tapered Buildings, Floor Segments)...")
    
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for c in bpy.data.collections: bpy.data.collections.remove(c)
    
    mesh = bpy.data.meshes.new("CityV23Mesh")
    obj = bpy.data.objects.new("CityV23", mesh)
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
    
    ng = create_v23_nodes()
    bpy.context.view_layer.objects.active = obj
    mod = obj.modifiers.new("CityGenV23", 'NODES')
    mod.node_group = ng
    
    # Fix Assignments
    set_mat_nodes = [n for n in ng.nodes if n.type == 'SET_MATERIAL']
    set_mat_nodes.sort(key=lambda n: n.location.x)
    if len(set_mat_nodes) >= 5:
        set_mat_nodes[0].inputs[2].default_value = mats[0]
        set_mat_nodes[1].inputs[2].default_value = mats[1]
        set_mat_nodes[2].inputs[2].default_value = mats[2]
        set_mat_nodes[3].inputs[2].default_value = mats[3]
        set_mat_nodes[4].inputs[2].default_value = mats[4]
        
    print("V23 Success.")
    
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'SOLID'
                    space.shading.color_type = 'MATERIAL'

if __name__ == "__main__":
    try:
        setup_scene_v23()
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
