import bpy
import bmesh
import math
import random
from mathutils import Vector

"""
WIRE GENERATOR (Auto-Select)
=============================
Automatically creates wires between random rooftop points.
Works on both standard meshes and Procedural (Geometry Nodes) objects!

USAGE:
1. Select a mesh object (building/city)
2. Run this script - no manual selection needed!

The script finds rooftop faces, samples random points,
and creates sagging wires between nearby points.

PARAMETERS (adjust below):
- NUM_WIRE_POINTS: How many connection points to create
- MAX_WIRE_DISTANCE: Maximum distance for wire connections
- MIN_WIRE_DISTANCE: Minimum distance (avoid very short wires)
- WIRE_RADIUS: Thickness of wires
- SAG_AMOUNT: How much wires droop
- ROOF_HEIGHT_THRESHOLD: Min Z to consider as rooftop
"""

# =====================
# PARAMETERS
# =====================
NUM_WIRE_POINTS = 50          # Number of points to sample on rooftops
MAX_WIRE_DISTANCE = 8.0       # Max distance between connected points
MIN_WIRE_DISTANCE = 2.0       # Min distance (skip very short wires)
WIRE_RADIUS = 0.015
WIRE_RESOLUTION = 6
SUBDIVISIONS = 8
SAG_AMOUNT = 0.25
WIRE_HEIGHT_OFFSET = 0.3      # How far above roof to place wire points
ROOF_NORMAL_THRESHOLD = 0.7   # Normal.z > this = rooftop face
ROOF_HEIGHT_THRESHOLD = 0.5   # Only roofs above this Z height
MAX_CONNECTIONS_PER_POINT = 3 # Limit connections per point
RANDOM_SEED = None            # Set to int for reproducible results, None for random
WIRE_MATERIAL_NAME = "Wire_Material"
WIRE_COLOR = (0.1, 0.1, 0.1, 1)


def get_rooftop_faces(obj):
    """Find upward-facing faces above height threshold (Evaluated Mesh)"""
    # Get evaluated mesh (includes Geometry Nodes)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = obj.evaluated_get(depsgraph)
    mesh = eval_obj.to_mesh()
    
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()
    
    rooftop_faces = []
    
    for face in bm.faces:
        # World space normal and center
        # Note: eval_obj matrices might need care, usually matrix_world is on original obj
        normal = (obj.matrix_world.to_3x3() @ face.normal).normalized()
        center = obj.matrix_world @ face.calc_center_median()
        
        # Check if upward-facing and above threshold
        if normal.z > ROOF_NORMAL_THRESHOLD and center.z > ROOF_HEIGHT_THRESHOLD:
            # Get world-space vertices for area calculation
            verts = [obj.matrix_world @ v.co for v in face.verts]
            rooftop_faces.append({
                'center': center,
                'normal': normal,
                'verts': verts,
                'area': face.calc_area(),
            })
    
    bm.free()
    eval_obj.to_mesh_clear() # Cleanup
    return rooftop_faces


def sample_points_on_faces(faces_data, num_points):
    """Randomly sample points on faces, weighted by area"""
    if not faces_data:
        return []
    
    # Weight faces by area
    total_area = sum(f['area'] for f in faces_data)
    if total_area == 0:
        return []
    
    points = []
    
    for _ in range(num_points):
        # Pick a random face weighted by area
        r = random.uniform(0, total_area)
        cumulative = 0
        chosen_face = faces_data[0]
        
        for face in faces_data:
            cumulative += face['area']
            if cumulative >= r:
                chosen_face = face
                break
        
        # Random point on face (using barycentric for triangles, or center with offset)
        center = chosen_face['center']
        
        # Add random offset within face bounds
        if len(chosen_face['verts']) >= 3:
            # Pick random point using vertices
            v0 = chosen_face['verts'][0]
            v1 = chosen_face['verts'][1]
            v2 = chosen_face['verts'][2]
            
            # Random barycentric coordinates
            u, v = random.random(), random.random()
            if u + v > 1:
                u, v = 1 - u, 1 - v
            
            point = v0 + u * (v1 - v0) + v * (v2 - v0)
        else:
            point = center.copy()
        
        # Offset upward
        point.z += WIRE_HEIGHT_OFFSET
        points.append(point)
    
    return points


def find_wire_connections(points):
    """Find pairs of points to connect with wires"""
    connections = []
    connection_count = {i: 0 for i in range(len(points))}
    
    # Sort potential connections by distance
    potential = []
    for i, p1 in enumerate(points):
        for j, p2 in enumerate(points):
            if i >= j:
                continue
            dist = (p1 - p2).length
            if MIN_WIRE_DISTANCE <= dist <= MAX_WIRE_DISTANCE:
                potential.append((dist, i, j))
    
    # Sort by distance (prefer shorter connections)
    potential.sort(key=lambda x: x[0])
    
    # Add connections respecting max per point
    for dist, i, j in potential:
        if (connection_count[i] < MAX_CONNECTIONS_PER_POINT and 
            connection_count[j] < MAX_CONNECTIONS_PER_POINT):
            connections.append((points[i], points[j]))
            connection_count[i] += 1
            connection_count[j] += 1
    
    return connections


def create_wire_curve(connections, name="Wires"):
    """Create curve object from point pairs with sag"""
    if not connections:
        return None
    
    curve_data = bpy.data.curves.new(name, type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.resolution_u = 12
    curve_data.bevel_depth = WIRE_RADIUS
    curve_data.bevel_resolution = WIRE_RESOLUTION
    
    for start, end in connections:
        spline = curve_data.splines.new('POLY')
        
        num_points = SUBDIVISIONS + 1
        spline.points.add(num_points - 1)
        
        wire_length = (end - start).length
        
        for j in range(num_points):
            t = j / (num_points - 1)
            
            # Linear interpolation
            x = start.x + t * (end.x - start.x)
            y = start.y + t * (end.y - start.y)
            z = start.z + t * (end.z - start.z)
            
            # Parabolic sag
            sag = SAG_AMOUNT * wire_length * 4 * t * (1 - t)
            z -= sag
            
            spline.points[j].co = (x, y, z, 1)
    
    curve_obj = bpy.data.objects.new(name, curve_data)
    bpy.context.collection.objects.link(curve_obj)
    
    return curve_obj


def create_wire_material():
    """Create or get wire material"""
    if WIRE_MATERIAL_NAME in bpy.data.materials:
        return bpy.data.materials[WIRE_MATERIAL_NAME]
    
    mat = bpy.data.materials.new(WIRE_MATERIAL_NAME)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    
    if bsdf:
        bsdf.inputs[0].default_value = WIRE_COLOR
        # Robust Socket Check
        if 'Metallic' in bsdf.inputs:
            bsdf.inputs['Metallic'].default_value = 0.8
        if 'Roughness' in bsdf.inputs:
            bsdf.inputs['Roughness'].default_value = 0.4
    
    mat.diffuse_color = WIRE_COLOR
    return mat


def main():
    print("-" * 30)
    print("Running Auto-Wire Generator...")
    # Set random seed if specified
    if RANDOM_SEED is not None:
        random.seed(RANDOM_SEED)
    
    obj = bpy.context.active_object
    if not obj or obj.type != 'MESH':
        print("Error: Please select a mesh object")
        return
    
    # Ensure object mode
    if obj.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    
    print(f"Analyzing mesh: {obj.name}")
    
    # Find rooftop faces (using Evaluated Mesh for Proc Gen support!)
    rooftop_faces = get_rooftop_faces(obj)
    
    if not rooftop_faces:
        print("Error: No rooftop faces found")
        print(f"  - Looking for faces with normal.z > {ROOF_NORMAL_THRESHOLD}")
        print(f"  - And center.z > {ROOF_HEIGHT_THRESHOLD}")
        return
    
    print(f"Found {len(rooftop_faces)} rooftop faces")
    
    # Sample random points
    points = sample_points_on_faces(rooftop_faces, NUM_WIRE_POINTS)
    print(f"Sampled {len(points)} wire connection points")
    
    # Find connections
    connections = find_wire_connections(points)
    
    if not connections:
        print("Error: No valid wire connections found")
        print(f"  - Try increasing MAX_WIRE_DISTANCE or NUM_WIRE_POINTS")
        return
    
    print(f"Creating {len(connections)} wire connections")
    
    # Create wire curve
    wire_curve = create_wire_curve(connections, name="Auto_Wires")
    
    if wire_curve:
        # Apply material
        wire_mat = create_wire_material()
        wire_curve.data.materials.append(wire_mat)
        
        # Select the new object
        bpy.ops.object.select_all(action='DESELECT')
        wire_curve.select_set(True)
        bpy.context.view_layer.objects.active = wire_curve
        
        print(f"Created wire object: {wire_curve.name}")
        print(f"  - {len(connections)} wires")
        print(f"  - Radius: {WIRE_RADIUS}")
        print(f"  - Sag: {SAG_AMOUNT}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
