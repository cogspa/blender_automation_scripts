import bpy
import traceback
import math

def create_v25_nodes():
    group_name = "VoronoiCity_V25"
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

    add_socket("Resolution", 'NodeSocketInt', 30, 2)
    add_socket("Street Width", 'NodeSocketFloat', 0.75, 0.0, 1.0)
    add_socket("Min Height", 'NodeSocketFloat', 1.0, 0.0)
    add_socket("Max Height", 'NodeSocketFloat', 6.0, 0.0)
    add_socket("Seed", 'NodeSocketInt', 700)
    add_socket("Color Seed", 'NodeSocketInt', 123)
    add_socket("Min Taper", 'NodeSocketFloat', 0.8, 0.3, 1.0)
    add_socket("Max Taper", 'NodeSocketFloat', 1.0, 0.3, 1.0)
    add_socket("Taper Seed", 'NodeSocketInt', 456)
    add_socket("Window Density", 'NodeSocketFloat', 15.0, 1.0, 50.0)
    add_socket("Window Scale", 'NodeSocketFloat', 0.08, 0.01, 0.3)
    add_socket("Antenna Chance", 'NodeSocketFloat', 0.3, 0.0, 1.0)
    add_socket("Wire Density", 'NodeSocketFloat', 0.02, 0.0, 0.1)

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
    n_out.location = (6000, 0)
    n_out.is_active_output = True

    # =====================
    # 1. Grid
    # =====================
    n_grid = nodes.new('GeometryNodeMeshGrid')
    n_grid.location = (-2400, 0)
    n_grid.inputs[0].default_value = 50.0 
    n_grid.inputs[1].default_value = 50.0 
    link_safe(get_parameter("Resolution"), n_grid, "Vertices X")
    link_safe(get_parameter("Resolution"), n_grid, "Vertices Y")
    
    # =====================
    # 2. Distortion
    # =====================
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
    
    # =====================
    # 3. Voronoi (Dual Mesh)
    # =====================
    n_tri = nodes.new('GeometryNodeTriangulate')
    n_tri.location = (-2000, 0)
    link_safe(n_set_pos.outputs[0], n_tri, "Mesh")
    
    n_dual = nodes.new('GeometryNodeDualMesh')
    n_dual.location = (-1800, 0)
    link_safe(n_tri.outputs[0], n_dual, "Mesh")
    
    # =====================
    # 4. Generate MatID & TaperFactor per cell
    # =====================
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
    
    # TaperFactor per building
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
    
    # =====================
    # 5. Roads Branch
    # =====================
    n_mat_road = nodes.new('GeometryNodeSetMaterial') 
    n_mat_road.location = (-800, -400)
    link_safe(n_store_taper.outputs[0], n_mat_road, "Geometry")
    
    # =====================
    # 6. Buildings Branch - Split, Shrink, Multi-Extrude with Taper
    # =====================
    n_split = nodes.new('GeometryNodeSplitEdges')
    n_split.location = (-1200, 200)
    link_safe(n_store_taper.outputs[0], n_split, "Mesh")
    
    n_shrink = nodes.new('GeometryNodeScaleElements')
    n_shrink.location = (-1000, 200)
    n_shrink.domain = 'FACE'
    link_safe(n_split.outputs[0], n_shrink, "Geometry")
    link_safe(get_parameter("Street Width"), n_shrink, "Scale")
    
    # Height calculation
    n_rand_h = nodes.new('FunctionNodeRandomValue')
    n_rand_h.data_type = 'FLOAT'
    n_rand_h.location = (-1000, 600)
    link_safe(get_parameter("Min Height"), n_rand_h, "Min")
    link_safe(get_parameter("Max Height"), n_rand_h, "Max")
    link_safe(n_idx.outputs[0], n_rand_h, "ID")
    link_safe(get_parameter("Seed"), n_rand_h, "Seed")
    
    # Divide by 4 floors
    n_div_floors = nodes.new('ShaderNodeMath')
    n_div_floors.operation = 'DIVIDE'
    n_div_floors.location = (-800, 600)
    n_div_floors.inputs[1].default_value = 4.0
    link_safe(n_rand_h.outputs[1], n_div_floors, 0)
    
    # Read taper factor
    n_read_taper = nodes.new('GeometryNodeInputNamedAttribute')
    n_read_taper.data_type = 'FLOAT'
    n_read_taper.inputs['Name'].default_value = "TaperFactor"
    n_read_taper.location = (-800, 400)
    
    # =====================
    # Multi-floor extrusion (4 floors)
    # =====================
    
    # Floor 1
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
    
    # Floor 2
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
    
    # Floor 3
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
    
    # Floor 4
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
    
    # =====================
    # 7. Material Assignment
    # =====================
    n_read_mat = nodes.new('GeometryNodeInputNamedAttribute')
    n_read_mat.data_type = 'INT'
    n_read_mat.inputs['Name'].default_value = "MatID"
    n_read_mat.location = (1000, 600)
    
    # Mat 1 (Red)
    n_eq1 = nodes.new('FunctionNodeCompare')
    n_eq1.data_type = 'INT'
    n_eq1.operation = 'EQUAL'
    n_eq1.inputs[3].default_value = 1
    link_safe(n_read_mat.outputs["Attribute"], n_eq1, "A")
    
    n_set1 = nodes.new('GeometryNodeSetMaterial')
    n_set1.location = (1000, 200)
    link_safe(n_taper4.outputs[0], n_set1, "Geometry")
    link_safe(n_eq1.outputs["Result"], n_set1, "Selection")
    
    # Mat 2 (Blue)
    n_eq2 = nodes.new('FunctionNodeCompare')
    n_eq2.data_type = 'INT'
    n_eq2.operation = 'EQUAL'
    n_eq2.inputs[3].default_value = 2
    link_safe(n_read_mat.outputs["Attribute"], n_eq2, "A")
    
    n_set2 = nodes.new('GeometryNodeSetMaterial')
    n_set2.location = (1200, 200)
    link_safe(n_set1.outputs[0], n_set2, "Geometry")
    link_safe(n_eq2.outputs["Result"], n_set2, "Selection")
    
    # Mat 3 (Orange)
    n_eq3 = nodes.new('FunctionNodeCompare')
    n_eq3.data_type = 'INT'
    n_eq3.operation = 'EQUAL'
    n_eq3.inputs[3].default_value = 3
    link_safe(n_read_mat.outputs["Attribute"], n_eq3, "A")
    
    n_set3 = nodes.new('GeometryNodeSetMaterial')
    n_set3.location = (1400, 200)
    link_safe(n_set2.outputs[0], n_set3, "Geometry")
    link_safe(n_eq3.outputs["Result"], n_set3, "Selection")
    
    # Mat 4 (Green)
    n_eq4 = nodes.new('FunctionNodeCompare')
    n_eq4.data_type = 'INT'
    n_eq4.operation = 'EQUAL'
    n_eq4.inputs[3].default_value = 4
    link_safe(n_read_mat.outputs["Attribute"], n_eq4, "A")
    
    n_set4 = nodes.new('GeometryNodeSetMaterial')
    n_set4.location = (1600, 200)
    link_safe(n_set3.outputs[0], n_set4, "Geometry")
    link_safe(n_eq4.outputs["Result"], n_set4, "Selection")
    
    # =====================
    # 8. WINDOWS - Distribute on side faces
    # =====================
    # Separate side faces (normal.z close to 0)
    n_normal = nodes.new('GeometryNodeInputNormal')
    n_normal.location = (1800, 600)
    
    n_sep_z = nodes.new('ShaderNodeSeparateXYZ')
    n_sep_z.location = (2000, 600)
    link_safe(n_normal.outputs[0], n_sep_z, "Vector")
    
    # abs(normal.z) < 0.1 means side face
    n_abs = nodes.new('ShaderNodeMath')
    n_abs.operation = 'ABSOLUTE'
    n_abs.location = (2200, 600)
    link_safe(n_sep_z.outputs["Z"], n_abs, 0)
    
    n_side_check = nodes.new('ShaderNodeMath')
    n_side_check.operation = 'LESS_THAN'
    n_side_check.inputs[1].default_value = 0.1
    n_side_check.location = (2400, 600)
    link_safe(n_abs.outputs[0], n_side_check, 0)
    
    # Distribute points on side faces for windows
    n_dist_win = nodes.new('GeometryNodeDistributePointsOnFaces')
    n_dist_win.location = (2600, 400)
    n_dist_win.distribute_method = 'POISSON'
    link_safe(n_set4.outputs[0], n_dist_win, "Mesh")
    link_safe(n_side_check.outputs[0], n_dist_win, "Selection")
    link_safe(get_parameter("Window Density"), n_dist_win, "Density")
    link_safe(get_parameter("Seed"), n_dist_win, "Seed")
    
    # Window instance (small cube)
    n_win_cube = nodes.new('GeometryNodeMeshCube')
    n_win_cube.location = (2600, 200)
    n_win_cube.inputs['Size'].default_value = (0.15, 0.02, 0.2)
    
    # Scale windows
    n_win_transform = nodes.new('GeometryNodeTransform')
    n_win_transform.location = (2800, 200)
    link_safe(n_win_cube.outputs[0], n_win_transform, "Geometry")
    
    # Connect scale parameter
    n_win_scale_vec = nodes.new('ShaderNodeCombineXYZ')
    n_win_scale_vec.location = (2600, 50)
    link_safe(get_parameter("Window Scale"), n_win_scale_vec, "X")
    link_safe(get_parameter("Window Scale"), n_win_scale_vec, "Y")
    link_safe(get_parameter("Window Scale"), n_win_scale_vec, "Z")
    link_safe(n_win_scale_vec.outputs[0], n_win_transform, "Scale")
    
    # Instance windows on points
    n_inst_win = nodes.new('GeometryNodeInstanceOnPoints')
    n_inst_win.location = (3000, 400)
    link_safe(n_dist_win.outputs["Points"], n_inst_win, "Points")
    link_safe(n_win_transform.outputs[0], n_inst_win, "Instance")
    
    # Align windows to face normal
    n_align_rot = nodes.new('FunctionNodeAlignRotationToVector')
    n_align_rot.location = (2800, 500)
    n_align_rot.axis = 'Y'
    link_safe(n_dist_win.outputs["Normal"], n_align_rot, "Vector")
    link_safe(n_align_rot.outputs[0], n_inst_win, "Rotation")
    
    # Window material
    n_mat_win = nodes.new('GeometryNodeSetMaterial')
    n_mat_win.location = (3200, 400)
    link_safe(n_inst_win.outputs[0], n_mat_win, "Geometry")
    
    # =====================
    # 9. DOORS - At ground level on side faces
    # =====================
    n_pos = nodes.new('GeometryNodeInputPosition')
    n_pos.location = (1800, -200)
    
    n_sep_pos = nodes.new('ShaderNodeSeparateXYZ')
    n_sep_pos.location = (2000, -200)
    link_safe(n_pos.outputs[0], n_sep_pos, "Vector")
    
    # Z < 0.3 for ground level
    n_ground = nodes.new('ShaderNodeMath')
    n_ground.operation = 'LESS_THAN'
    n_ground.inputs[1].default_value = 0.3
    n_ground.location = (2200, -200)
    link_safe(n_sep_pos.outputs["Z"], n_ground, 0)
    
    # Combine: side face AND ground level
    n_door_sel = nodes.new('ShaderNodeMath')
    n_door_sel.operation = 'MULTIPLY'
    n_door_sel.location = (2400, -200)
    link_safe(n_side_check.outputs[0], n_door_sel, 0)
    link_safe(n_ground.outputs[0], n_door_sel, 1)
    
    # Distribute door points (sparse)
    n_dist_door = nodes.new('GeometryNodeDistributePointsOnFaces')
    n_dist_door.location = (2600, -200)
    n_dist_door.distribute_method = 'POISSON'
    n_dist_door.inputs['Density'].default_value = 0.5
    n_dist_door.inputs['Distance Min'].default_value = 1.5
    link_safe(n_set4.outputs[0], n_dist_door, "Mesh")
    link_safe(n_door_sel.outputs[0], n_dist_door, "Selection")
    
    # Door geometry (taller box)
    n_door_cube = nodes.new('GeometryNodeMeshCube')
    n_door_cube.location = (2600, -400)
    n_door_cube.inputs['Size'].default_value = (0.25, 0.03, 0.4)
    
    # Instance doors
    n_inst_door = nodes.new('GeometryNodeInstanceOnPoints')
    n_inst_door.location = (3000, -200)
    link_safe(n_dist_door.outputs["Points"], n_inst_door, "Points")
    link_safe(n_door_cube.outputs[0], n_inst_door, "Instance")
    
    # Align doors
    n_align_door = nodes.new('FunctionNodeAlignRotationToVector')
    n_align_door.location = (2800, -100)
    n_align_door.axis = 'Y'
    link_safe(n_dist_door.outputs["Normal"], n_align_door, "Vector")
    link_safe(n_align_door.outputs[0], n_inst_door, "Rotation")
    
    # Door material
    n_mat_door = nodes.new('GeometryNodeSetMaterial')
    n_mat_door.location = (3200, -200)
    link_safe(n_inst_door.outputs[0], n_mat_door, "Geometry")
    
    # =====================
    # 10. ANTENNAS - On roof tops
    # =====================
    # Top faces: normal.z > 0.9
    n_top_check = nodes.new('ShaderNodeMath')
    n_top_check.operation = 'GREATER_THAN'
    n_top_check.inputs[1].default_value = 0.9
    n_top_check.location = (2200, -500)
    link_safe(n_sep_z.outputs["Z"], n_top_check, 0)
    
    # High Z position (above 1.0)
    n_high_check = nodes.new('ShaderNodeMath')
    n_high_check.operation = 'GREATER_THAN'
    n_high_check.inputs[1].default_value = 1.0
    n_high_check.location = (2200, -650)
    link_safe(n_sep_pos.outputs["Z"], n_high_check, 0)
    
    # Combine top + high
    n_roof_sel = nodes.new('ShaderNodeMath')
    n_roof_sel.operation = 'MULTIPLY'
    n_roof_sel.location = (2400, -550)
    link_safe(n_top_check.outputs[0], n_roof_sel, 0)
    link_safe(n_high_check.outputs[0], n_roof_sel, 1)
    
    # Random selection for antenna chance
    n_rand_ant = nodes.new('FunctionNodeRandomValue')
    n_rand_ant.data_type = 'FLOAT'
    n_rand_ant.location = (2400, -700)
    n_rand_ant.inputs['Min'].default_value = 0.0
    n_rand_ant.inputs['Max'].default_value = 1.0
    
    n_ant_thresh = nodes.new('ShaderNodeMath')
    n_ant_thresh.operation = 'LESS_THAN'
    n_ant_thresh.location = (2600, -700)
    link_safe(n_rand_ant.outputs[1], n_ant_thresh, 0)
    link_safe(get_parameter("Antenna Chance"), n_ant_thresh, 1)
    
    n_ant_final = nodes.new('ShaderNodeMath')
    n_ant_final.operation = 'MULTIPLY'
    n_ant_final.location = (2800, -600)
    link_safe(n_roof_sel.outputs[0], n_ant_final, 0)
    link_safe(n_ant_thresh.outputs[0], n_ant_final, 1)
    
    # Distribute antenna points
    n_dist_ant = nodes.new('GeometryNodeDistributePointsOnFaces')
    n_dist_ant.location = (3000, -550)
    n_dist_ant.distribute_method = 'POISSON'
    n_dist_ant.inputs['Density'].default_value = 0.3
    n_dist_ant.inputs['Distance Min'].default_value = 2.0
    link_safe(n_set4.outputs[0], n_dist_ant, "Mesh")
    link_safe(n_ant_final.outputs[0], n_dist_ant, "Selection")
    
    # Antenna geometry (cylinder + sphere)
    n_ant_cyl = nodes.new('GeometryNodeMeshCylinder')
    n_ant_cyl.location = (3000, -750)
    n_ant_cyl.inputs['Radius'].default_value = 0.02
    n_ant_cyl.inputs['Depth'].default_value = 0.6
    n_ant_cyl.inputs['Vertices'].default_value = 8
    
    n_ant_sphere = nodes.new('GeometryNodeMeshUVSphere')
    n_ant_sphere.location = (3000, -900)
    n_ant_sphere.inputs['Radius'].default_value = 0.05
    n_ant_sphere.inputs['Segments'].default_value = 8
    n_ant_sphere.inputs['Rings'].default_value = 6
    
    # Move sphere to top of cylinder
    n_sphere_move = nodes.new('GeometryNodeTransform')
    n_sphere_move.location = (3200, -900)
    n_sphere_move.inputs['Translation'].default_value = (0, 0, 0.3)
    link_safe(n_ant_sphere.outputs[0], n_sphere_move, "Geometry")
    
    # Join antenna parts
    n_join_ant = nodes.new('GeometryNodeJoinGeometry')
    n_join_ant.location = (3400, -800)
    link_safe(n_ant_cyl.outputs["Mesh"], n_join_ant, "Geometry")
    link_safe(n_sphere_move.outputs[0], n_join_ant, "Geometry")
    
    # Instance antennas
    n_inst_ant = nodes.new('GeometryNodeInstanceOnPoints')
    n_inst_ant.location = (3600, -550)
    link_safe(n_dist_ant.outputs["Points"], n_inst_ant, "Points")
    link_safe(n_join_ant.outputs[0], n_inst_ant, "Instance")
    
    # Random rotation for variety
    n_rand_rot = nodes.new('FunctionNodeRandomValue')
    n_rand_rot.data_type = 'FLOAT_VECTOR'
    n_rand_rot.location = (3400, -500)
    n_rand_rot.inputs['Min'].default_value = (-0.2, -0.2, 0.0)
    n_rand_rot.inputs['Max'].default_value = (0.2, 0.2, 6.28)
    link_safe(n_rand_rot.outputs[1], n_inst_ant, "Rotation")
    
    # Antenna material
    n_mat_ant = nodes.new('GeometryNodeSetMaterial')
    n_mat_ant.location = (3800, -550)
    link_safe(n_inst_ant.outputs[0], n_mat_ant, "Geometry")
    
    # =====================
    # 11. WIRES - Curves between random rooftop points
    # =====================
    # Get points on rooftops for wire endpoints
    n_dist_wire = nodes.new('GeometryNodeDistributePointsOnFaces')
    n_dist_wire.location = (3000, -1100)
    n_dist_wire.distribute_method = 'POISSON'
    n_dist_wire.inputs['Distance Min'].default_value = 3.0
    link_safe(n_set4.outputs[0], n_dist_wire, "Mesh")
    link_safe(n_roof_sel.outputs[0], n_dist_wire, "Selection")
    link_safe(get_parameter("Wire Density"), n_dist_wire, "Density")
    
    # Offset points up slightly
    n_wire_offset = nodes.new('GeometryNodeSetPosition')
    n_wire_offset.location = (3200, -1100)
    link_safe(n_dist_wire.outputs["Points"], n_wire_offset, "Geometry")
    
    n_wire_up = nodes.new('ShaderNodeCombineXYZ')
    n_wire_up.inputs['Z'].default_value = 0.3
    link_safe(n_wire_up.outputs[0], n_wire_offset, "Offset")
    
    # Convert points to vertices for edge creation
    n_pts_to_verts = nodes.new('GeometryNodePointsToVertices')
    n_pts_to_verts.location = (3400, -1100)
    link_safe(n_wire_offset.outputs[0], n_pts_to_verts, "Points")
    
    # Create edges using Edge Paths (connect nearby vertices)
    n_edge_paths = nodes.new('GeometryNodeEdgePathsToSelection')
    n_edge_paths.location = (3600, -1100)
    
    # Alternative: Use Convex Hull for simple wire network
    n_convex = nodes.new('GeometryNodeConvexHull')
    n_convex.location = (3600, -1200)
    link_safe(n_pts_to_verts.outputs[0], n_convex, "Geometry")
    
    # Extract only edges from convex hull
    n_del_faces = nodes.new('GeometryNodeDeleteGeometry')
    n_del_faces.location = (3800, -1200)
    n_del_faces.domain = 'FACE'
    n_del_faces.mode = 'ALL'
    link_safe(n_convex.outputs[0], n_del_faces, "Geometry")
    
    # Convert edges to curve
    n_mesh_to_curve = nodes.new('GeometryNodeMeshToCurve')
    n_mesh_to_curve.location = (4000, -1200)
    link_safe(n_del_faces.outputs[0], n_mesh_to_curve, "Mesh")
    
    # Add sag to wires (set curve type to bezier and adjust handles would be complex)
    # Instead, subdivide and use Set Position with noise
    n_subdiv = nodes.new('GeometryNodeSubdivideCurve')
    n_subdiv.location = (4200, -1200)
    n_subdiv.inputs['Cuts'].default_value = 4
    link_safe(n_mesh_to_curve.outputs[0], n_subdiv, "Curve")
    
    # Add sag using position-based offset
    n_sag_pos = nodes.new('GeometryNodeSetPosition')
    n_sag_pos.location = (4400, -1200)
    link_safe(n_subdiv.outputs[0], n_sag_pos, "Geometry")
    
    # Spline parameter for sag curve (0 at ends, 1 at middle)
    n_spline_param = nodes.new('GeometryNodeSplineParameter')
    n_spline_param.location = (4000, -1350)
    
    # Parabolic sag: 4 * t * (1-t) peaks at 0.5
    n_one_minus = nodes.new('ShaderNodeMath')
    n_one_minus.operation = 'SUBTRACT'
    n_one_minus.inputs[0].default_value = 1.0
    n_one_minus.location = (4200, -1350)
    link_safe(n_spline_param.outputs["Factor"], n_one_minus, 1)
    
    n_sag_mult = nodes.new('ShaderNodeMath')
    n_sag_mult.operation = 'MULTIPLY'
    n_sag_mult.location = (4400, -1350)
    link_safe(n_spline_param.outputs["Factor"], n_sag_mult, 0)
    link_safe(n_one_minus.outputs[0], n_sag_mult, 1)
    
    n_sag_scale = nodes.new('ShaderNodeMath')
    n_sag_scale.operation = 'MULTIPLY'
    n_sag_scale.inputs[1].default_value = -0.5  # Negative for downward sag
    n_sag_scale.location = (4600, -1350)
    link_safe(n_sag_mult.outputs[0], n_sag_scale, 0)
    
    n_sag_vec = nodes.new('ShaderNodeCombineXYZ')
    n_sag_vec.location = (4800, -1350)
    link_safe(n_sag_scale.outputs[0], n_sag_vec, "Z")
    link_safe(n_sag_vec.outputs[0], n_sag_pos, "Offset")
    
    # Give wires thickness
    n_wire_profile = nodes.new('GeometryNodeCurvePrimitiveCircle')
    n_wire_profile.location = (4600, -1100)
    n_wire_profile.inputs['Radius'].default_value = 0.015
    n_wire_profile.inputs['Resolution'].default_value = 6
    
    n_curve_to_mesh = nodes.new('GeometryNodeCurveToMesh')
    n_curve_to_mesh.location = (4800, -1200)
    link_safe(n_sag_pos.outputs[0], n_curve_to_mesh, "Curve")
    link_safe(n_wire_profile.outputs[0], n_curve_to_mesh, "Profile Curve")
    
    # Wire material
    n_mat_wire = nodes.new('GeometryNodeSetMaterial')
    n_mat_wire.location = (5000, -1200)
    link_safe(n_curve_to_mesh.outputs[0], n_mat_wire, "Geometry")
    
    # =====================
    # 12. Final Join
    # =====================
    n_lift = nodes.new('GeometryNodeTransform')
    n_lift.location = (3400, 200)
    n_lift.inputs['Translation'].default_value = (0, 0, 0.005)
    link_safe(n_set4.outputs[0], n_lift, "Geometry")
    
    # Join everything
    n_join_all = nodes.new('GeometryNodeJoinGeometry')
    n_join_all.location = (5200, 0)
    link_safe(n_mat_road.outputs[0], n_join_all, "Geometry")
    link_safe(n_lift.outputs[0], n_join_all, "Geometry")
    link_safe(n_mat_win.outputs[0], n_join_all, "Geometry")
    link_safe(n_mat_door.outputs[0], n_join_all, "Geometry")
    link_safe(n_mat_ant.outputs[0], n_join_all, "Geometry")
    link_safe(n_mat_wire.outputs[0], n_join_all, "Geometry")
    
    link_safe(n_join_all.outputs[0], n_out, "Geometry")
    
    return ng

def setup_scene_v25():
    print("=" * 40)
    print("Creating V25 (Full Detailed City as 'v25')...")
    
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for c in bpy.data.collections: bpy.data.collections.remove(c)
    
    mesh = bpy.data.meshes.new("CityV25Mesh")
    obj = bpy.data.objects.new("CityV25", mesh)
    bpy.context.scene.collection.objects.link(obj)
    
    # Materials
    mat_colors = {
        "Road": (0.05, 0.05, 0.05, 1),
        "Building_Red": (0.7, 0.15, 0.15, 1),
        "Building_Blue": (0.15, 0.15, 0.7, 1),
        "Building_Orange": (0.9, 0.45, 0.1, 1),
        "Building_Green": (0.15, 0.6, 0.15, 1),
        "Window": (0.6, 0.8, 1.0, 1),  
        "Door": (0.35, 0.2, 0.1, 1),   
        "Antenna": (0.3, 0.3, 0.3, 1), 
        "Wire": (0.1, 0.1, 0.1, 1),    
    }
    
    mats = {}
    for name, col in mat_colors.items():
        mat = bpy.data.materials.new(f"Mat_{name}")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes['Principled BSDF']
        bsdf.inputs[0].default_value = col
        if name == "Window":
            bsdf.inputs['Roughness'].default_value = 0.1
            bsdf.inputs['Metallic'].default_value = 0.9
            # Robust Emission Check
            if 'Emission' in bsdf.inputs:
                bsdf.inputs['Emission'].default_value = (0.2, 0.4, 0.6, 1)
            elif 'Emission Color' in bsdf.inputs:
                bsdf.inputs['Emission Color'].default_value = (0.2, 0.4, 0.6, 1)
                if 'Emission Strength' in bsdf.inputs:
                    bsdf.inputs['Emission Strength'].default_value = 5.0
                    
        elif name == "Antenna":
            bsdf.inputs['Metallic'].default_value = 1.0
        
        mat.diffuse_color = col
        obj.data.materials.append(mat)
        mats[name] = mat
    
    ng = create_v25_nodes()
    bpy.context.view_layer.objects.active = obj
    mod = obj.modifiers.new("CityGenV25", 'NODES')
    mod.node_group = ng
    
    # Assign materials
    set_mat_nodes = [n for n in ng.nodes if n.type == 'SET_MATERIAL']
    set_mat_nodes.sort(key=lambda n: n.location.x)
    
    mat_list = [mats["Road"], mats["Building_Red"], mats["Building_Blue"], mats["Building_Orange"], mats["Building_Green"],
                mats["Window"], mats["Door"], mats["Antenna"], mats["Wire"]]
    
    for i, node in enumerate(set_mat_nodes):
        if i < len(mat_list):
            node.inputs[2].default_value = mat_list[i]
    
    print("V25 Success!")
    
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'SOLID'
                    space.shading.color_type = 'MATERIAL'

if __name__ == "__main__":
    try:
        setup_scene_v25()
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
