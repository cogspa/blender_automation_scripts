import bpy
import traceback
import math

def create_v24_nodes():
    group_name = "VoronoiCity_V24_Details"
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
    
    # Divide by 4 floors (Hardcoded segments)
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
    
    # Extrude Loops
    n_prev = n_shrink
    
    # Loop for 4 floors
    for i in range(4):
        # Extrude
        n_ext = nodes.new('GeometryNodeExtrudeMesh')
        n_ext.location = (-600 + (i*400), 200)
        link_safe(n_prev.outputs[0], n_ext, "Mesh")
        link_safe(n_div_floors.outputs[0], n_ext, "Offset Scale")
        if i > 0:
            link_safe(n_prev.outputs["Top"], n_ext, "Selection")
        
        # Taper
        n_taper = nodes.new('GeometryNodeScaleElements')
        n_taper.location = (-400 + (i*400), 200)
        n_taper.domain = 'FACE'
        link_safe(n_ext.outputs[0], n_taper, "Geometry")
        link_safe(n_ext.outputs["Top"], n_taper, "Selection")
        link_safe(n_read_taper.outputs["Attribute"], n_taper, "Scale")
        
        n_prev = n_taper
    
    n_main_geo = n_prev
    
    # =====================
    # 7. Material Assignment
    # =====================
    n_read_mat = nodes.new('GeometryNodeInputNamedAttribute')
    n_read_mat.data_type = 'INT'
    n_read_mat.inputs['Name'].default_value = "MatID"
    n_read_mat.location = (1000, 600)
    
    n_curr_geo = n_main_geo
    
    for i in range(1, 5):
        n_eq = nodes.new('FunctionNodeCompare')
        n_eq.data_type = 'INT'
        n_eq.operation = 'EQUAL'
        n_eq.inputs[3].default_value = i
        link_safe(n_read_mat.outputs["Attribute"], n_eq, "A")
        
        n_set = nodes.new('GeometryNodeSetMaterial')
        n_set.location = (1000 + (i*200), 200)
        link_safe(n_curr_geo.outputs[0], n_set, "Geometry")
        link_safe(n_eq.outputs["Result"], n_set, "Selection")
        n_curr_geo = n_set
        
    n_bldg_final = n_curr_geo
    
    # =====================
    # 8. WINDOWS
    # =====================
    n_normal = nodes.new('GeometryNodeInputNormal')
    n_normal.location = (1800, 600)
    
    n_sep_z = nodes.new('ShaderNodeSeparateXYZ')
    n_sep_z.location = (2000, 600)
    link_safe(n_normal.outputs[0], n_sep_z, "Vector")
    
    n_abs = nodes.new('ShaderNodeMath')
    n_abs.operation = 'ABSOLUTE'
    n_abs.location = (2200, 600)
    link_safe(n_sep_z.outputs["Z"], n_abs, 0)
    
    n_side_check = nodes.new('ShaderNodeMath')
    n_side_check.operation = 'LESS_THAN'
    n_side_check.inputs[1].default_value = 0.1
    n_side_check.location = (2400, 600)
    link_safe(n_abs.outputs[0], n_side_check, 0)
    
    n_dist_win = nodes.new('GeometryNodeDistributePointsOnFaces')
    n_dist_win.location = (2600, 400)
    n_dist_win.distribute_method = 'POISSON'
    link_safe(n_bldg_final.outputs[0], n_dist_win, "Mesh")
    link_safe(n_side_check.outputs[0], n_dist_win, "Selection")
    link_safe(get_parameter("Window Density"), n_dist_win, "Density")
    link_safe(get_parameter("Seed"), n_dist_win, "Seed")
    
    n_win_cube = nodes.new('GeometryNodeMeshCube')
    n_win_cube.location = (2600, 200)
    n_win_cube.inputs['Size'].default_value = (0.15, 0.02, 0.2)
    
    n_win_transform = nodes.new('GeometryNodeTransform')
    n_win_transform.location = (2800, 200)
    link_safe(n_win_cube.outputs[0], n_win_transform, "Geometry")
    
    n_win_scale_vec = nodes.new('ShaderNodeCombineXYZ')
    n_win_scale_vec.location = (2600, 50)
    link_safe(get_parameter("Window Scale"), n_win_scale_vec, "X")
    link_safe(get_parameter("Window Scale"), n_win_scale_vec, "Y")
    link_safe(get_parameter("Window Scale"), n_win_scale_vec, "Z")
    link_safe(n_win_scale_vec.outputs[0], n_win_transform, "Scale")
    
    n_inst_win = nodes.new('GeometryNodeInstanceOnPoints')
    n_inst_win.location = (3000, 400)
    link_safe(n_dist_win.outputs["Points"], n_inst_win, "Points")
    link_safe(n_win_transform.outputs[0], n_inst_win, "Instance")
    
    n_align_rot = nodes.new('FunctionNodeAlignRotationToVector')
    n_align_rot.location = (2800, 500)
    n_align_rot.axis = 'Y'
    link_safe(n_dist_win.outputs["Normal"], n_align_rot, "Vector")
    link_safe(n_align_rot.outputs[0], n_inst_win, "Rotation")
    
    n_mat_win = nodes.new('GeometryNodeSetMaterial')
    n_mat_win.location = (3200, 400)
    link_safe(n_inst_win.outputs[0], n_mat_win, "Geometry")
    
    # =====================
    # 9. DOORS
    # =====================
    n_pos = nodes.new('GeometryNodeInputPosition')
    n_pos.location = (1800, -200)
    
    n_sep_pos = nodes.new('ShaderNodeSeparateXYZ')
    n_sep_pos.location = (2000, -200)
    link_safe(n_pos.outputs[0], n_sep_pos, "Vector")
    
    n_ground = nodes.new('ShaderNodeMath')
    n_ground.operation = 'LESS_THAN'
    n_ground.inputs[1].default_value = 0.3
    n_ground.location = (2200, -200)
    link_safe(n_sep_pos.outputs["Z"], n_ground, 0)
    
    n_door_sel = nodes.new('ShaderNodeMath')
    n_door_sel.operation = 'MULTIPLY'
    n_door_sel.location = (2400, -200)
    link_safe(n_side_check.outputs[0], n_door_sel, 0)
    link_safe(n_ground.outputs[0], n_door_sel, 1)
    
    n_dist_door = nodes.new('GeometryNodeDistributePointsOnFaces')
    n_dist_door.location = (2600, -200)
    n_dist_door.distribute_method = 'POISSON'
    n_dist_door.inputs['Density'].default_value = 0.5
    n_dist_door.inputs['Distance Min'].default_value = 1.5
    link_safe(n_bldg_final.outputs[0], n_dist_door, "Mesh")
    link_safe(n_door_sel.outputs[0], n_dist_door, "Selection")
    
    n_door_cube = nodes.new('GeometryNodeMeshCube')
    n_door_cube.location = (2600, -400)
    n_door_cube.inputs['Size'].default_value = (0.25, 0.03, 0.4)
    
    n_inst_door = nodes.new('GeometryNodeInstanceOnPoints')
    n_inst_door.location = (3000, -200)
    link_safe(n_dist_door.outputs["Points"], n_inst_door, "Points")
    link_safe(n_door_cube.outputs[0], n_inst_door, "Instance")
    
    n_align_door = nodes.new('FunctionNodeAlignRotationToVector')
    n_align_door.location = (2800, -100)
    n_align_door.axis = 'Y'
    link_safe(n_dist_door.outputs["Normal"], n_align_door, "Vector")
    link_safe(n_align_door.outputs[0], n_inst_door, "Rotation")
    
    n_mat_door = nodes.new('GeometryNodeSetMaterial')
    n_mat_door.location = (3200, -200)
    link_safe(n_inst_door.outputs[0], n_mat_door, "Geometry")
    
    # =====================
    # 10. ANTENNAS
    # =====================
    n_top_check = nodes.new('ShaderNodeMath')
    n_top_check.operation = 'GREATER_THAN'
    n_top_check.inputs[1].default_value = 0.9
    n_top_check.location = (2200, -500)
    link_safe(n_sep_z.outputs["Z"], n_top_check, 0)
    
    n_high_check = nodes.new('ShaderNodeMath')
    n_high_check.operation = 'GREATER_THAN'
    n_high_check.inputs[1].default_value = 1.0
    n_high_check.location = (2200, -650)
    link_safe(n_sep_pos.outputs["Z"], n_high_check, 0)
    
    n_roof_sel = nodes.new('ShaderNodeMath')
    n_roof_sel.operation = 'MULTIPLY'
    n_roof_sel.location = (2400, -550)
    link_safe(n_top_check.outputs[0], n_roof_sel, 0)
    link_safe(n_high_check.outputs[0], n_roof_sel, 1)
    
    n_dist_ant = nodes.new('GeometryNodeDistributePointsOnFaces')
    n_dist_ant.location = (3000, -550)
    n_dist_ant.distribute_method = 'POISSON'
    n_dist_ant.inputs['Density'].default_value = 0.3
    n_dist_ant.inputs['Distance Min'].default_value = 2.0
    link_safe(n_bldg_final.outputs[0], n_dist_ant, "Mesh")
    link_safe(n_roof_sel.outputs[0], n_dist_ant, "Selection")
    
    n_ant_cyl = nodes.new('GeometryNodeMeshCylinder')
    n_ant_cyl.location = (3000, -750)
    n_ant_cyl.inputs['Radius'].default_value = 0.02
    n_ant_cyl.inputs['Depth'].default_value = 0.6
    n_ant_cyl.inputs['Vertices'].default_value = 8
    
    n_inst_ant = nodes.new('GeometryNodeInstanceOnPoints')
    n_inst_ant.location = (3600, -550)
    link_safe(n_dist_ant.outputs["Points"], n_inst_ant, "Points")
    link_safe(n_ant_cyl.outputs["Mesh"], n_inst_ant, "Instance")
    
    n_mat_ant = nodes.new('GeometryNodeSetMaterial')
    n_mat_ant.location = (3800, -550)
    link_safe(n_inst_ant.outputs[0], n_mat_ant, "Geometry")
    
    # =====================
    # 11. WIRES
    # =====================
    # Wires logic from user code was complex, simplified to Convex Hull for robustness
    n_dist_wire = nodes.new('GeometryNodeDistributePointsOnFaces')
    n_dist_wire.location = (3000, -1100)
    n_dist_wire.distribute_method = 'POISSON'
    n_dist_wire.inputs['Distance Min'].default_value = 3.0
    link_safe(n_bldg_final.outputs[0], n_dist_wire, "Mesh")
    link_safe(n_roof_sel.outputs[0], n_dist_wire, "Selection")
    link_safe(get_parameter("Wire Density"), n_dist_wire, "Density")
    
    n_pts_to_verts = nodes.new('GeometryNodePointsToVertices')
    n_pts_to_verts.location = (3400, -1100)
    link_safe(n_dist_wire.outputs["Points"], n_pts_to_verts, "Points")
    
    n_convex = nodes.new('GeometryNodeConvexHull')
    n_convex.location = (3600, -1200)
    link_safe(n_pts_to_verts.outputs[0], n_convex, "Geometry")
    
    n_del_faces = nodes.new('GeometryNodeDeleteGeometry')
    n_del_faces.location = (3800, -1200)
    n_del_faces.domain = 'FACE'
    n_del_faces.mode = 'ALL'
    link_safe(n_convex.outputs[0], n_del_faces, "Geometry")
    
    n_mesh_to_curve = nodes.new('GeometryNodeMeshToCurve')
    n_mesh_to_curve.location = (4000, -1200)
    link_safe(n_del_faces.outputs[0], n_mesh_to_curve, "Mesh")
    
    n_wire_profile = nodes.new('GeometryNodeCurvePrimitiveCircle')
    n_wire_profile.location = (4600, -1100)
    n_wire_profile.inputs['Radius'].default_value = 0.015
    n_wire_profile.inputs['Resolution'].default_value = 4
    
    n_curve_to_mesh = nodes.new('GeometryNodeCurveToMesh')
    n_curve_to_mesh.location = (4800, -1200)
    link_safe(n_mesh_to_curve.outputs[0], n_curve_to_mesh, "Curve")
    link_safe(n_wire_profile.outputs[0], n_curve_to_mesh, "Profile Curve")
    
    n_mat_wire = nodes.new('GeometryNodeSetMaterial')
    n_mat_wire.location = (5000, -1200)
    link_safe(n_curve_to_mesh.outputs[0], n_mat_wire, "Geometry")
    
    # =====================
    # 12. Final Join
    # =====================
    n_lift = nodes.new('GeometryNodeTransform')
    n_lift.location = (3400, 200)
    n_lift.inputs['Translation'].default_value = (0, 0, 0.005)
    link_safe(n_bldg_final.outputs[0], n_lift, "Geometry")
    
    n_join_all = nodes.new('GeometryNodeJoinGeometry')
    n_join_all.location = (5400, 0)
    link_safe(n_mat_road.outputs[0], n_join_all, "Geometry")
    link_safe(n_lift.outputs[0], n_join_all, "Geometry")
    link_safe(n_mat_win.outputs[0], n_join_all, "Geometry")
    link_safe(n_mat_door.outputs[0], n_join_all, "Geometry")
    link_safe(n_mat_ant.outputs[0], n_join_all, "Geometry")
    link_safe(n_mat_wire.outputs[0], n_join_all, "Geometry")
    
    link_safe(n_join_all.outputs[0], n_out, "Geometry")
    
    return ng

def setup_scene_v24():
    print("=" * 40)
    print("Creating V24 (Full Cyberpunk City!)...")
    
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for c in bpy.data.collections: bpy.data.collections.remove(c)
    
    mesh = bpy.data.meshes.new("CityV24Mesh")
    obj = bpy.data.objects.new("CityV24", mesh)
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
            bsdf.inputs['Emission'].default_value = (0.2, 0.4, 0.6, 1) # Glowing windows
        elif name == "Antenna":
            bsdf.inputs['Metallic'].default_value = 1.0
        
        mat.diffuse_color = col
        obj.data.materials.append(mat)
        mats[name] = mat
    
    ng = create_v24_nodes()
    bpy.context.view_layer.objects.active = obj
    mod = obj.modifiers.new("CityGenV24", 'NODES')
    mod.node_group = ng
    
    # Assign materials to Set Material nodes
    # Sort by X location to match creation order order
    set_mat_nodes = [n for n in ng.nodes if n.type == 'SET_MATERIAL']
    set_mat_nodes.sort(key=lambda n: n.location.x)
    
    # Order based on the creation function
    # Road (-800 X)
    # Red (1000 X)
    # Blue (1200 X)
    # Orange (1400 X)
    # Green (1600 X)
    # Window (3200 X, 400 Y)
    # Door (3200 X, -200 Y) -> Same X, sort by Y? NO, sorting is by X. They are equal.
    # Python Sort is Stable. Window created first.
    # Antenna (3800 X)
    # Wire (5000 X)
    
    mat_list = [mats["Road"], mats["Building_Red"], mats["Building_Blue"], mats["Building_Orange"], mats["Building_Green"],
                mats["Window"], mats["Door"], mats["Antenna"], mats["Wire"]]
    
    for i, node in enumerate(set_mat_nodes):
        if i < len(mat_list):
            node.inputs[2].default_value = mat_list[i]
    
    print("V24 Success!")
    
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    space.shading.type = 'SOLID'
                    space.shading.color_type = 'MATERIAL'

if __name__ == "__main__":
    try:
        setup_scene_v24()
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
