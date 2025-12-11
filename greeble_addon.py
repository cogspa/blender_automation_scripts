bl_info = {
    "name": "Advanced Greeble Generator",
    "author": "Antigravity",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Object > Effects > Add Greeble",
    "description": "Adds complex greeble details to selected faces",
    "category": "Object",
}

import bpy
import bmesh
import math
import random
from bpy.props import FloatProperty, IntProperty, EnumProperty, BoolProperty, FloatVectorProperty

class GreebleGenerator:
    def __init__(self, obj, config):
        self.obj = obj
        self.config = config
        self.bm = None
        
    def setup(self):
        if self.obj.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        
        # Duplicate checks handled by operator usually, but here we operate on active
        self.bm = bmesh.new()
        self.bm.from_mesh(self.obj.data)
        self.bm.faces.ensure_lookup_table()
        
    def get_eligible_faces(self):
        eligible = []
        c = self.config
        
        for face in self.bm.faces:
            area = face.calc_area()
            if area < c.min_face_area or area > c.max_face_area:
                continue
            
            nz = face.normal.z
            if c.face_type == 'SIDE' and abs(nz) > 0.3: continue
            elif c.face_type == 'TOP' and nz < 0.7: continue
            elif c.face_type == 'BOTTOM' and nz > -0.7: continue
            
            eligible.append(face)
        return eligible
    
    def select_random_faces(self, faces):
        return [f for f in faces if random.random() < self.config.face_selection_chance]
    
    def calculate_inset(self, face):
        c = self.config
        if c.use_relative_inset:
            area = face.calc_area()
            size = math.sqrt(area)
            return max(0.005, size * c.relative_inset_factor)
        return c.inset_thickness

    def inset_face(self, face):
        c = self.config
        inset_amount = self.calculate_inset(face)
        try:
            bmesh.ops.inset_individual(
                self.bm, faces=[face], thickness=inset_amount, depth=c.inset_depth
            )
            return True
        except:
            return False

    def get_face_at_location(self, location, tolerance=0.1): # Increased tolerance slightly
        # Optimized search could be spatial, but linear is ok for reasonable counts
        min_dist = tolerance
        best_face = None
        for face in self.bm.faces:
            if face.is_valid:
                dist = (face.calc_center_median() - location).length
                if dist < min_dist:
                    min_dist = dist
                    best_face = face
        return best_face

    def subdivide_face(self, face):
        c = self.config
        if not face.is_valid: return []
        
        cuts = random.randint(c.min_cuts, c.max_cuts)
        try:
            res = bmesh.ops.subdivide_edges(
                self.bm, edges=list(face.edges), cuts=cuts, use_grid_fill=True
            )
            return res.get('geom_inner', [])
        except:
            return []

    def extrude_face(self, face, distance):
        if not face.is_valid: return None
        normal = face.normal.copy()
        try:
            res = bmesh.ops.extrude_face_region(self.bm, geom=[face])
            verts = [v for v in res['geom'] if isinstance(v, bmesh.types.BMVert)]
            bmesh.ops.translate(self.bm, verts=verts, vec=normal * distance)
            new_faces = [f for f in res['geom'] if isinstance(f, bmesh.types.BMFace)]
            return new_faces[0] if new_faces else None
        except:
            return None

    def inset_and_extrude(self, face, inset_amt, extrude_amt):
        if not face.is_valid: return None
        center = face.calc_center_median()
        try:
            bmesh.ops.inset_individual(self.bm, faces=[face], thickness=inset_amt, depth=0)
            inner = self.get_face_at_location(center, tolerance=0.05)
            if inner: return self.extrude_face(inner, extrude_amt)
        except: pass
        return None

    def process_face(self, face):
        if not face.is_valid: return
        c = self.config
        
        orig_center = face.calc_center_median()
        orig_normal = face.normal.copy()
        
        if not self.inset_face(face): return
        
        # Fix: ensure lookup after ops
        self.bm.faces.ensure_lookup_table() 
        inner = self.get_face_at_location(orig_center, tolerance=0.1)
        if not inner: return
        
        self.subdivide_face(inner)
        self.bm.faces.ensure_lookup_table()
        
        # Find grid cells
        grid_faces = []
        for f in self.bm.faces:
            if f.is_valid:
                if (f.calc_center_median() - orig_center).length < 2.0: # simplistic radius
                    if f.normal.dot(orig_normal) > 0.9:
                        grid_faces.append(f)
                        
        extruded = []
        for gf in grid_faces:
            if not gf.is_valid: continue
            if random.random() > c.primary_extrude_chance: continue
            
            dist = random.uniform(c.primary_extrude_min, c.primary_extrude_max)
            if random.random() < c.primary_recess_chance: dist = -dist
            
            nf = self.extrude_face(gf, dist)
            if nf: extruded.append(nf)
            
        if c.secondary_detail:
            secondary = []
            for ef in extruded:
                if not ef.is_valid: continue
                if random.random() > c.secondary_extrude_chance: continue
                
                inset = random.uniform(c.secondary_inset_min, c.secondary_inset_max)
                ext = random.uniform(c.secondary_extrude_min, c.secondary_extrude_max)
                if random.random() < 0.4: ext = -ext
                
                sf = self.inset_and_extrude(ef, inset, ext)
                if sf: secondary.append(sf)
            
            if c.tertiary_detail:
                for sf in secondary:
                    if not sf.is_valid: continue
                    if random.random() > c.tertiary_chance: continue
                    ext = random.uniform(c.tertiary_extrude_min, c.tertiary_extrude_max)
                    if random.random() < 0.5: ext = -ext
                    self.extrude_face(sf, ext)

    def finalize(self):
        self.bm.to_mesh(self.obj.data)
        self.bm.free()
        self.obj.data.update()

    def generate(self):
        if self.config.random_seed >= 0:
            random.seed(self.config.random_seed)
            
        self.setup()
        eligible = self.get_eligible_faces()
        if not eligible: return
        
        selected = self.select_random_faces(eligible)
        for face in selected:
            self.process_face(face)
            
        self.finalize()


class OBJECT_OT_add_greeble(bpy.types.Operator):
    """Generate detailed greeble panels on the selected mesh"""
    bl_idname = "object.add_greeble"
    bl_label = "Add Greeble Detail"
    bl_options = {'REGISTER', 'UNDO'}

    # Properties
    face_selection_chance: FloatProperty(name="Selection Chance", default=0.3, min=0, max=1)
    face_type: EnumProperty(
        name="Face Type",
        items=[('SIDE', "Sides", ""), ('TOP', "Top", ""), ('BOTTOM', "Bottom", ""), ('ALL', "All", "")],
        default='SIDE'
    )
    min_face_area: FloatProperty(name="Min Area", default=0.1)
    max_face_area: FloatProperty(name="Max Area", default=50.0)
    
    use_relative_inset: BoolProperty(name="Relative Inset", default=True)
    relative_inset_factor: FloatProperty(name="Relative Factor", default=0.03)
    inset_thickness: FloatProperty(name="Fixed Inset", default=0.015)
    inset_depth: FloatProperty(name="Inset Depth", default=0.008)
    
    min_cuts: IntProperty(name="Min Cuts", default=1, min=1)
    max_cuts: IntProperty(name="Max Cuts", default=3, min=1)
    
    primary_extrude_chance: FloatProperty(name="Prim. Extrude Chance", default=0.7)
    primary_extrude_min: FloatProperty(name="Prim. Min", default=0.01)
    primary_extrude_max: FloatProperty(name="Prim. Max", default=0.12)
    primary_recess_chance: FloatProperty(name="Prim. Recess Chance", default=0.35)
    
    secondary_detail: BoolProperty(name="Secondary Detail", default=True)
    secondary_helper_expand: BoolProperty(name="Expand Settings", default=False)
    secondary_extrude_chance: FloatProperty(name="Sec. Chance", default=0.5)
    secondary_inset_min: FloatProperty(name="Sec. Inset Min", default=0.005)
    secondary_inset_max: FloatProperty(name="Sec. Inset Max", default=0.015)
    secondary_extrude_min: FloatProperty(name="Sec. Extrude Min", default=0.005)
    secondary_extrude_max: FloatProperty(name="Sec. Extrude Max", default=0.04)
    
    tertiary_detail: BoolProperty(name="Tertiary Detail", default=True)
    tertiary_chance: FloatProperty(name="Tert. Chance", default=0.25)
    tertiary_extrude_min: FloatProperty(name="Tert. Min", default=0.002)
    tertiary_extrude_max: FloatProperty(name="Tert. Max", default=0.015)
    
    modify_original: BoolProperty(name="Modify Original", default=False, description="If False, duplicates object first")
    random_seed: IntProperty(name="Seed", default=0)

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Active object must be a Mesh")
            return {'CANCELLED'}
        
        target_obj = obj
        if not self.modify_original:
            bpy.ops.object.duplicate()
            target_obj = context.active_object
            target_obj.name = obj.name + "_Greebled"
            
        gen = GreebleGenerator(target_obj, self)
        gen.generate()
        
        return {'FINISHED'}

def menu_func(self, context):
    self.layout.operator(OBJECT_OT_add_greeble.bl_idname, text="Add Greebles", icon='MOD_BUILD')

def register():
    bpy.utils.register_class(OBJECT_OT_add_greeble)
    bpy.types.VIEW3D_MT_object.append(menu_func)

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_add_greeble)
    bpy.types.VIEW3D_MT_object.remove(menu_func)

if __name__ == "__main__":
    register()
