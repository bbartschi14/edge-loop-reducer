bl_info = {
    "name": "Edge Loop Reducer",
    "author": "Ben Bartschi",
    "version": (1, 0),
    "blender": (2, 80, 0),
    "location": "View3D > N",
    "description": "Quickly repologizes faces for proper edge loop reduction",
    "warning": "",
    "wiki_url": "",
    "category": "",
}

import bpy
from bpy.types import (Panel,Operator)
from bpy.utils import register_class, unregister_class
import bmesh
import numpy as np
from mathutils import Vector

# Defines the minimum number of existing vertices to perform each operation
type_definitions = {
        "1to2" : [1,1],
        "1to3" : [1,1],
        "1to4" : [1,1],
        "3to1" : [3,3],
        "4to1" : [3,4],
        "2to1" : [3,2],
        "4to2" : [3,4],
        "5to3" : [3,5]
        }
        
def furthest_along_normal(origin, axis, vertices):
    """
    Take in an origin vertex, an axis (x+, x-, etc),
    and a list of other vertices. Return the vertex
    that is the greatest distance away along the axis.
    """
    max_dist = 0
    to_local = bpy.context.object.matrix_world.inverted()
    factor = np.sign(axis)
    origin_world_co = origin.co
    furthest = None
    for v in vertices:
        pos = v.co
        dist = factor*(pos[abs(axis)-1] - origin_world_co[abs(axis)-1]) 
        if (dist > max_dist):
            max_dist = dist
            furthest = v
            
    return furthest

def select_grid(bm, num_rows, num_columns, directions):
    """
    Create a 2D array of vertices that represents a grid of size
    (rows x columns), starting from the active vertex and going in directions
    defined by directions. 
    """
    normal_direction = 1
    selected_verts = [v for v in bm.verts if v.select]
    print(selected_verts)
    if (len(selected_verts) != 1):
        print("Need to select a single vertex")
    selected_v = selected_verts[0]
    rows = []
    for i in range(num_rows+1):
        row = [selected_v]
        
        for j in range(num_columns):
            others = []
            for edge in selected_v.link_edges:
                others.append(edge.other_vert(selected_v))

            furthest = furthest_along_normal(selected_v, directions[0], others)

            furthest.select = True
            selected_v = furthest
            row.append(selected_v)
                    
        rows.append(row)
        others = []
        for edge in row[0].link_edges:
            others.append(edge.other_vert(row[0]))
            
        furthest = furthest_along_normal(selected_v, directions[1], others)
        selected_v = furthest
        if (selected_v is not None):
             selected_v.select = True
        
    return rows

def retopo1to2(bm, vertex_rows, dissolve):
    """
    Take in 2D list of vertices and update mesh topology.
    Increases 1 face loop to 2.
    """
    original_face_indices = [vertex_rows[0][0].index, vertex_rows[0][1].index, 
                             vertex_rows[1][0].index, vertex_rows[1][1].index]
    edge_1 = [vertex_rows[0][0].index, vertex_rows[0][1].index]
    edge_2 = [vertex_rows[0][0].index, vertex_rows[1][0].index]
    edge_3 = [vertex_rows[1][0].index, vertex_rows[1][1].index]
    edge_4 = [vertex_rows[0][1].index, vertex_rows[1][1].index]
    
    to_delete = []
    for f in bm.faces:
       is_orig = True
       for v in f.verts:
            if v.index not in original_face_indices:
                is_orig = False
       if (is_orig):
           #bmesh.ops.delete(bm, geom=[f], context='FACES_KEEP_BOUNDARY')
           to_delete.append(f)
           
    if dissolve:
        for e in bm.edges:
           is_one = True
           is_two = True
           is_three = True
           is_four = True
           for v in e.verts:
                if v.index not in edge_1:
                    is_one = False
                if v.index not in edge_2:
                    is_two = False
                if v.index not in edge_3:
                    is_three = False
                if v.index not in edge_4:
                    is_four = False
           if (is_one or is_two or is_three or is_four):
               to_delete.append(e)
               
        bmesh.ops.delete(bm, geom=to_delete, context='EDGES_FACES')
    else:
        bmesh.ops.delete(bm, geom=to_delete, context='FACES_KEEP_BOUNDARY')
            
    vert_1 = bm.verts.new((vertex_rows[0][0].co + vertex_rows[0][1].co)/2)   
    vert_2 = bm.verts.new((vertex_rows[0][0].co + (vertex_rows[1][0].co - vertex_rows[0][0].co)/3))    
    vert_4 = bm.verts.new((vertex_rows[0][1].co + (vertex_rows[1][1].co - vertex_rows[0][1].co)/3))
    vert_3 = bm.verts.new((vert_2.co + vert_4.co)/2)       
    vert_5 = bm.verts.new((vertex_rows[0][0].co + (vertex_rows[1][0].co - vertex_rows[0][0].co)*.66))    
    vert_6 = bm.verts.new((vertex_rows[0][1].co + (vertex_rows[1][1].co - vertex_rows[0][1].co)*.66))
    vert_7 = bm.verts.new(vert_5.co + (vertex_rows[0][1].co - vertex_rows[0][0].co)/3)
    vert_8 = bm.verts.new(vert_5.co + (vertex_rows[0][1].co - vertex_rows[0][0].co)*.66)  
    vert_7.co += (vert_2.co - vert_5.co)/2
    vert_8.co += (vert_2.co - vert_5.co)/2
    
    new_faces = [(vertex_rows[0][0], vert_1, vert_3, vert_2),
                 (vert_1, vertex_rows[0][1], vert_4, vert_3),
                 (vert_2, vert_3, vert_7, vert_5),
                 (vert_3, vert_4, vert_6, vert_8),
                 (vert_3, vert_7, vert_8),
                 (vert_7, vert_8, vert_6, vert_5),
                 (vert_5, vert_6, vertex_rows[1][1], vertex_rows[1][0])
                 ]
    created_faces = []
    for f in new_faces:        
        created_faces.append(bm.faces.new(f))
    bmesh.ops.recalc_face_normals(bm, faces=created_faces)    

def retopo1to3(bm, vertex_rows, dissolve):
    """
    Take in 2D list of vertices and update mesh topology.
    Increases 1 face loop to 3.
    """
    original_face_indices = [vertex_rows[0][0].index, vertex_rows[0][1].index, 
                             vertex_rows[1][0].index, vertex_rows[1][1].index]
    edge_1 = [vertex_rows[0][0].index, vertex_rows[0][1].index]
    edge_2 = [vertex_rows[0][0].index, vertex_rows[1][0].index]
    edge_3 = [vertex_rows[1][0].index, vertex_rows[1][1].index]
    edge_4 = [vertex_rows[0][1].index, vertex_rows[1][1].index]
    
    to_delete = []
    for f in bm.faces:
       is_orig = True
       for v in f.verts:
            if v.index not in original_face_indices:
                is_orig = False
       if (is_orig):
           #bmesh.ops.delete(bm, geom=[f], context='FACES_KEEP_BOUNDARY')
           to_delete.append(f)
           
    if dissolve:
        for e in bm.edges:
           is_one = True
           is_two = True
           is_three = True
           is_four = True
           for v in e.verts:
                if v.index not in edge_1:
                    is_one = False
                if v.index not in edge_2:
                    is_two = False
                if v.index not in edge_3:
                    is_three = False
                if v.index not in edge_4:
                    is_four = False
           if (is_one or is_two or is_three or is_four):
               to_delete.append(e)
               
        bmesh.ops.delete(bm, geom=to_delete, context='EDGES_FACES')
    else:
        bmesh.ops.delete(bm, geom=to_delete, context='FACES_KEEP_BOUNDARY')
            
    vert_1 = bm.verts.new((vertex_rows[0][0].co + (vertex_rows[0][1].co - vertex_rows[0][0].co)*.33)) 
    vert_2 = bm.verts.new((vertex_rows[0][0].co + (vertex_rows[0][1].co - vertex_rows[0][0].co)*.66))   
    vert_3 = bm.verts.new((vertex_rows[0][0].co + (vertex_rows[1][0].co - vertex_rows[0][0].co)/3))    
      
    vert_6 = bm.verts.new((vertex_rows[0][1].co + (vertex_rows[1][1].co - vertex_rows[0][1].co)/3))
    vert_4 = bm.verts.new((vert_3.co + (vert_6.co - vert_3.co)*.33))  
    vert_5 = bm.verts.new((vert_3.co + (vert_6.co - vert_3.co)*.66)) 
    vert_7 = bm.verts.new((vertex_rows[0][0].co + (vertex_rows[1][0].co - vertex_rows[0][0].co)*.66))    
    vert_10 = bm.verts.new((vertex_rows[0][1].co + (vertex_rows[1][1].co - vertex_rows[0][1].co)*.66))
    
    
    vert_8 = bm.verts.new(vert_7.co + (vertex_rows[0][1].co - vertex_rows[0][0].co)/3)
    vert_9 = bm.verts.new(vert_7.co + (vertex_rows[0][1].co - vertex_rows[0][0].co)*.66)  
    vert_8.co += (vert_3.co - vert_7.co)/2
    vert_9.co += (vert_3.co - vert_7.co)/2
    
    new_faces = [(vertex_rows[0][0], vert_1, vert_4, vert_3),
                 (vert_1, vert_2, vert_5, vert_4),
                 (vert_2, vertex_rows[0][1], vert_6, vert_5),
                 (vert_3, vert_4, vert_8, vert_7),
                 (vert_4, vert_5, vert_9, vert_8),
                 (vert_5, vert_6, vert_10, vert_9),
                 (vert_7, vert_8, vert_9, vert_10),
                 (vert_7, vert_10, vertex_rows[1][1], vertex_rows[1][0])
                 ]
    created_faces = []
    for f in new_faces:        
        created_faces.append(bm.faces.new(f))
    bmesh.ops.recalc_face_normals(bm, faces=created_faces) 
    
def retopo1to4(bm, vertex_rows, dissolve):
    """
    Take in 2D list of vertices and update mesh topology.
    Increases 1 face loop to 4.
    """
    original_face_indices = [vertex_rows[0][0].index, vertex_rows[0][1].index, 
                             vertex_rows[1][0].index, vertex_rows[1][1].index]
    edge_1 = [vertex_rows[0][0].index, vertex_rows[0][1].index]
    edge_2 = [vertex_rows[0][0].index, vertex_rows[1][0].index]
    edge_3 = [vertex_rows[1][0].index, vertex_rows[1][1].index]
    edge_4 = [vertex_rows[0][1].index, vertex_rows[1][1].index]
    
    to_delete = []
    for f in bm.faces:
       is_orig = True
       for v in f.verts:
            if v.index not in original_face_indices:
                is_orig = False
       if (is_orig):
           #bmesh.ops.delete(bm, geom=[f], context='FACES_KEEP_BOUNDARY')
           to_delete.append(f)
           
    if dissolve:
        for e in bm.edges:
           is_one = True
           is_two = True
           is_three = True
           is_four = True
           for v in e.verts:
                if v.index not in edge_1:
                    is_one = False
                if v.index not in edge_2:
                    is_two = False
                if v.index not in edge_3:
                    is_three = False
                if v.index not in edge_4:
                    is_four = False
           if (is_one or is_two or is_three or is_four):
               to_delete.append(e)
               
        bmesh.ops.delete(bm, geom=to_delete, context='EDGES_FACES')
    else:
        bmesh.ops.delete(bm, geom=to_delete, context='FACES_KEEP_BOUNDARY')
            
    vert_1 = bm.verts.new((vertex_rows[0][0].co + (vertex_rows[0][1].co - vertex_rows[0][0].co)*.25)) 
    vert_2 = bm.verts.new((vertex_rows[0][0].co + (vertex_rows[0][1].co - vertex_rows[0][0].co)*.5)) 
    vert_3 = bm.verts.new((vertex_rows[0][0].co + (vertex_rows[0][1].co - vertex_rows[0][0].co)*.75)) 
      
    vert_4 = bm.verts.new((vertex_rows[0][0].co + (vertex_rows[1][0].co - vertex_rows[0][0].co)/3))    
      
    vert_8 = bm.verts.new((vertex_rows[0][1].co + (vertex_rows[1][1].co - vertex_rows[0][1].co)/3))
    vert_5 = bm.verts.new((vert_4.co + (vert_8.co - vert_4.co)*.25))  
    vert_6 = bm.verts.new((vert_4.co + (vert_8.co - vert_4.co)*.5))  
    vert_7 = bm.verts.new((vert_4.co + (vert_8.co - vert_4.co)*.75))  
    
    vert_9 = bm.verts.new((vertex_rows[0][0].co + (vertex_rows[1][0].co - vertex_rows[0][0].co)*.66))    
    vert_13 = bm.verts.new((vertex_rows[0][1].co + (vertex_rows[1][1].co - vertex_rows[0][1].co)*.66))
    vert_10 = bm.verts.new((vert_9.co + (vert_13.co - vert_9.co)*.35))  
    vert_12 = bm.verts.new((vert_9.co + (vert_13.co - vert_9.co)*.65)) 
 
    vert_10.co += (vert_4.co - vert_9.co)/2
    vert_12.co += (vert_4.co - vert_9.co)/2
    
    new_faces = [(vertex_rows[0][0], vert_1, vert_5, vert_4),
                 (vert_1, vert_2, vert_6, vert_5),
                 (vert_2, vert_3, vert_7, vert_6),
                 (vert_3, vertex_rows[0][1], vert_8, vert_7),
                 (vert_4, vert_5, vert_10, vert_9),
                 (vert_5, vert_6, vert_7, vert_12, vert_10),
                 (vert_7, vert_8, vert_13, vert_12),
                 (vert_9, vert_10, vert_12, vert_13),
                 (vert_9, vert_13, vertex_rows[1][1], vertex_rows[1][0])
                 ]
    created_faces = []
    for f in new_faces:        
        created_faces.append(bm.faces.new(f))
    bmesh.ops.recalc_face_normals(bm, faces=created_faces) 
    
def retopo2to1(bm, vertex_rows, dissolve):
    """
    Take in 2D list of vertices and update mesh topology.
    Reduces 2 face loops to 1.
    """
    first_indices = [vertex_rows[3][1].index, vertex_rows[2][1].index]
    second_indices = [vertex_rows[2][1].index, vertex_rows[2][2].index]
    for e in bm.edges:
        if e.verts[0].index in first_indices and e.verts[1].index in first_indices:
            bmesh.ops.dissolve_edges(bm, edges=[e])
    dist = (vertex_rows[1][0].co - vertex_rows[1][1].co)/3    
    vertex_rows[2][1].co += (vertex_rows[1][1].co - vertex_rows[2][1].co)/2  
    vertex_rows[2][1].co += dist
    bmesh.ops.connect_verts(bm, verts=[vertex_rows[2][0], vertex_rows[2][2]])    
     
    face_indices_one = [vertex_rows[2][0].index, vertex_rows[2][2].index, vertex_rows[2][1].index]
    face_indices_two = [vertex_rows[1][1].index, vertex_rows[2][1].index, 
                        vertex_rows[2][2].index, vertex_rows[1][2].index]
                        
    to_delete = []
    for f in bm.faces:
        is_one = True
        is_two = True
        for v in f.verts:
            print(v.index)
            if v.index not in face_indices_one:
                is_one = False
            if v.index not in face_indices_two:
                is_two = False
        if (is_one or is_two):
            to_delete.append(f)
            
    bmesh.ops.delete(bm, geom=to_delete, context='FACES_KEEP_BOUNDARY')
    
    new_vert = bm.verts.new(vertex_rows[2][1].co - dist*2)
    new_faces = [(vertex_rows[2][0], vertex_rows[2][1], new_vert, vertex_rows[2][2]),
                 (vertex_rows[1][1],vertex_rows[2][1], new_vert),
                 (vertex_rows[1][1],vertex_rows[1][2],vertex_rows[2][2], new_vert)]
    created_faces = []
    for f in new_faces:        
        created_faces.append(bm.faces.new(f))
    bmesh.ops.recalc_face_normals(bm, faces=created_faces)    
    
    if (dissolve):
        bmesh.ops.dissolve_verts(bm, verts=[vertex_rows[3][1]]) 

def retopo3to1(bm, vertex_rows, dissolve):
    """
    Take in 2D list of vertices and update mesh topology.
    Reduces 3 face loops to 1.
    """
    
    first_indices = [vertex_rows[3][1].index, vertex_rows[2][1].index]
    second_indices = [vertex_rows[2][2].index, vertex_rows[3][2].index]
    for e in bm.edges:
        if e.verts[0].index in first_indices and e.verts[1].index in first_indices:
            bmesh.ops.dissolve_edges(bm, edges=[e])
        elif e.verts[0].index in second_indices and e.verts[1].index in second_indices:
            bmesh.ops.dissolve_edges(bm, edges=[e]) 
    vertex_rows[2][1].co += (vertex_rows[1][1].co - vertex_rows[2][1].co)/2
    vertex_rows[2][2].co += (vertex_rows[1][2].co - vertex_rows[2][2].co)/2
    bmesh.ops.connect_verts(bm, verts=[vertex_rows[2][0], vertex_rows[2][3]])
    
    if (dissolve):
        bmesh.ops.dissolve_verts(bm, verts=[vertex_rows[3][1],vertex_rows[3][2]]) 
        
        
def retopo4to1(bm, vertex_rows, dissolve):
    """
    Take in 2D list of vertices and update mesh topology.
    Reduces 4 face loops to 1.
    """
    
    first_indices = [vertex_rows[3][1].index, vertex_rows[2][1].index]
    second_indices = [vertex_rows[3][2].index, vertex_rows[2][2].index]
    third_indices = [vertex_rows[3][3].index, vertex_rows[2][3].index]
    for e in bm.edges:
        if e.verts[0].index in first_indices and e.verts[1].index in first_indices:
            bmesh.ops.dissolve_edges(bm, edges=[e])
        elif e.verts[0].index in second_indices and e.verts[1].index in second_indices:
            bmesh.ops.dissolve_edges(bm, edges=[e]) 
        elif e.verts[0].index in third_indices and e.verts[1].index in third_indices:
            bmesh.ops.dissolve_edges(bm, edges=[e]) 
    bmesh.ops.dissolve_verts(bm, verts=[vertex_rows[2][2]]) 
    vertex_rows[2][1].co += (vertex_rows[1][1].co - vertex_rows[2][1].co)/2
    vertex_rows[2][3].co += (vertex_rows[1][3].co - vertex_rows[2][3].co)/2
    dist1 = (vertex_rows[2][1].co - vertex_rows[2][3].co)/4
    dist2 = (vertex_rows[2][3].co - vertex_rows[2][1].co)/4
    vertex_rows[2][1].co += dist2
    vertex_rows[2][3].co += dist1
    bmesh.ops.connect_verts(bm, verts=[vertex_rows[2][0], vertex_rows[2][4]])
    bmesh.ops.connect_verts(bm, verts=[vertex_rows[2][1], vertex_rows[2][3]])
    
    if (dissolve):
        bmesh.ops.dissolve_verts(bm, verts=[vertex_rows[3][1],vertex_rows[3][2],vertex_rows[3][3]]) 
        
def retopo4to2(bm, vertex_rows, dissolve):
    """
    Take in 2D list of vertices and update mesh topology.
    Reduces 4 face loops to 2.
    """
    
    first_indices = [vertex_rows[3][1].index, vertex_rows[2][1].index]
    third_indices = [vertex_rows[3][3].index, vertex_rows[2][3].index]
    for e in bm.edges:
        if e.verts[0].index in first_indices and e.verts[1].index in first_indices:
            bmesh.ops.dissolve_edges(bm, edges=[e])
        elif e.verts[0].index in third_indices and e.verts[1].index in third_indices:
            bmesh.ops.dissolve_edges(bm, edges=[e]) 
    vertex_rows[2][1].co += (vertex_rows[1][1].co - vertex_rows[2][1].co)/2
    vertex_rows[2][2].co += (vertex_rows[1][2].co - vertex_rows[2][2].co)/2
    vertex_rows[2][3].co += (vertex_rows[1][3].co - vertex_rows[2][3].co)/2

    face_indices_one = [vertex_rows[3][0].index, vertex_rows[2][0].index, vertex_rows[2][1].index,
                        vertex_rows[2][2].index, vertex_rows[3][2].index, vertex_rows[3][1].index]
    face_indices_two = [vertex_rows[3][2].index, vertex_rows[2][2].index, vertex_rows[3][4].index,
                        vertex_rows[2][3].index, vertex_rows[2][4].index, vertex_rows[3][3].index]
    to_delete = []
    for f in bm.faces:
        is_one = True
        is_two = True
        for v in f.verts:
            if v.index not in face_indices_one:
                is_one = False
            if v.index not in face_indices_two:
                is_two = False
        if (is_one or is_two):
            to_delete.append(f)
    
    bmesh.ops.delete(bm, geom=to_delete, context='FACES_KEEP_BOUNDARY') 
    
    new_vert = bm.verts.new((vertex_rows[2][0].co + vertex_rows[2][4].co)/2)
    new_faces = [(vertex_rows[3][0], vertex_rows[2][0], new_vert, vertex_rows[3][2], vertex_rows[3][1]),
                 (vertex_rows[3][2], new_vert, vertex_rows[2][4], vertex_rows[3][4],vertex_rows[3][3]),
                 (vertex_rows[2][0],vertex_rows[2][1], vertex_rows[2][2], new_vert),
                 (vertex_rows[2][2],vertex_rows[2][3], vertex_rows[2][4], new_vert)
                 ]
    created_faces = []
    for f in new_faces:        
        created_faces.append(bm.faces.new(f))
    bmesh.ops.recalc_face_normals(bm, faces=created_faces)    
    
    #if (dissolve):
    #    bmesh.ops.dissolve_verts(bm, verts=[vertex_rows[3][1],vertex_rows[3][3]]) 

def retopo5to3(bm, vertex_rows, dissolve):
    """
    Take in 2D list of vertices and update mesh topology.
    Reduces 5 face loops to 3.
    """
    
    first_indices = [vertex_rows[3][1].index, vertex_rows[2][1].index]
    third_indices = [vertex_rows[3][4].index, vertex_rows[2][4].index]
    for e in bm.edges:
        if e.verts[0].index in first_indices and e.verts[1].index in first_indices:
            bmesh.ops.dissolve_edges(bm, edges=[e])
        elif e.verts[0].index in third_indices and e.verts[1].index in third_indices:
            bmesh.ops.dissolve_edges(bm, edges=[e]) 
    vertex_rows[2][1].co += (vertex_rows[1][1].co - vertex_rows[2][1].co)/2
    vertex_rows[2][2].co += (vertex_rows[1][2].co - vertex_rows[2][2].co)/2
    vertex_rows[2][3].co += (vertex_rows[1][3].co - vertex_rows[2][3].co)/2
    vertex_rows[2][4].co += (vertex_rows[1][4].co - vertex_rows[2][4].co)/2
   
    face_indices_one = [vertex_rows[3][0].index, vertex_rows[2][0].index, vertex_rows[2][1].index,
                        vertex_rows[2][2].index, vertex_rows[3][2].index, vertex_rows[3][1].index]
    face_indices_two = [vertex_rows[2][2].index, vertex_rows[2][3].index, vertex_rows[3][3].index,
                       vertex_rows[3][2].index]
    face_indices_three = [vertex_rows[2][3].index, vertex_rows[2][4].index, vertex_rows[2][5].index,
                        vertex_rows[3][5].index, vertex_rows[3][4].index, vertex_rows[3][3].index]
    to_delete = []
    for f in bm.faces:
        is_one = True
        is_two = True
        is_three = True
        for v in f.verts:
            if v.index not in face_indices_one:
                is_one = False
            if v.index not in face_indices_two:
                is_two = False
            if v.index not in face_indices_three:
                is_three = False
        if (is_one or is_two or is_three):
            to_delete.append(f)
    
    bmesh.ops.delete(bm, geom=to_delete, context='FACES_KEEP_BOUNDARY') 
    
    vertex_rows[3][2].co = vertex_rows[3][0].co + (vertex_rows[3][5].co-vertex_rows[3][0].co)*.33
    vertex_rows[3][3].co = vertex_rows[3][0].co + (vertex_rows[3][5].co-vertex_rows[3][0].co)*.66
    
    new_vert_1 = bm.verts.new(vertex_rows[2][0].co + (vertex_rows[2][5].co-vertex_rows[2][0].co)*.33)
    new_vert_2 = bm.verts.new(vertex_rows[2][0].co + (vertex_rows[2][5].co-vertex_rows[2][0].co)*.66)
    
    new_faces = [(vertex_rows[2][0], vertex_rows[2][1], vertex_rows[2][2], new_vert_1),
                 (vertex_rows[2][2], vertex_rows[2][3], new_vert_2, new_vert_1),
                 (vertex_rows[2][3],vertex_rows[2][4], vertex_rows[2][5], new_vert_2),
                 (new_vert_2, vertex_rows[2][5], vertex_rows[3][5], vertex_rows[3][3]),
                 (new_vert_1, new_vert_2, vertex_rows[3][3], vertex_rows[3][2]),
                 (vertex_rows[2][0], new_vert_1, vertex_rows[3][2], vertex_rows[3][0])
                 ]
    created_faces = []
    for f in new_faces:        
        created_faces.append(bm.faces.new(f))
    bmesh.ops.recalc_face_normals(bm, faces=created_faces)    
    
    if (dissolve):
        bmesh.ops.dissolve_verts(bm, verts=[vertex_rows[3][1],vertex_rows[3][4]]) 
        
def main(type, directions, dissolve):
    global type_definitions
    grid_info = type_definitions[type]
    me = bpy.context.object.data
    bm = bmesh.from_edit_mesh(me)
    if (type == "1to2"): 
        vertex_rows = select_grid(bm,grid_info[0],grid_info[1],directions)
        retopo1to2(bm, vertex_rows, dissolve)
    elif (type == "1to3"): 
        vertex_rows = select_grid(bm,grid_info[0],grid_info[1],directions)
        retopo1to3(bm, vertex_rows, dissolve)
    elif (type == "1to4"): 
        vertex_rows = select_grid(bm,grid_info[0],grid_info[1],directions)
        retopo1to4(bm, vertex_rows, dissolve)
    elif (type == "2to1"): 
        vertex_rows = select_grid(bm,grid_info[0],grid_info[1],directions)
        retopo2to1(bm, vertex_rows, dissolve)
    elif (type == "3to1"): 
        vertex_rows = select_grid(bm,grid_info[0],grid_info[1],directions)
        retopo3to1(bm, vertex_rows, dissolve)
    elif (type == "4to1"):
        vertex_rows = select_grid(bm,grid_info[0],grid_info[1],directions)
        retopo4to1(bm, vertex_rows, dissolve)
    elif (type == "4to2"):
        vertex_rows = select_grid(bm,grid_info[0],grid_info[1],directions)
        retopo4to2(bm, vertex_rows, dissolve)
    elif (type == "5to3"):
        vertex_rows = select_grid(bm,grid_info[0],grid_info[1],directions)
        retopo5to3(bm, vertex_rows, dissolve)
    bmesh.update_edit_mesh(me)
    
    
class TopologyProperties(bpy.types.PropertyGroup):
    type_enum : bpy.props.EnumProperty(
        name="Topo Types",
        description="Select an option",
        items=[("1to2", "1 to 2", "1 face to 2"),
               ("1to3", "1 to 3", "1 face to 3"),
               ("1to4", "1 to 4", "1 face to 4"),
               ("2to1", "2 to 1", "2 faces to 1"),
               ('3to1', "3 to 1", "3 faces to 1"),
               ("4to1", "4 to 1", "4 faces to 1"),
               ("4to2", "4 to 2", "4 faces to 2"),
               ("5to3", "5 to 3", "5 faces to 3")
               ]
    )
    
    across_enum : bpy.props.EnumProperty(
        name="Across Direction",
        description="Select an option",
        items=[('1', "+X", ""),
               ("-1", "-X", ""),
               ('2', "+Y", ""),
               ("-2", "-Y", ""),
               ('3', "+Z", ""),
               ("-3", "-Z", "")]
    )
    
    down_enum : bpy.props.EnumProperty(
        name="Down Direction",
        description="Select an option",
        items=[('1', "+X", ""),
               ("-1", "-X", ""),
               ('2', "+Y", ""),
               ("-2", "-Y", ""),
               ('3', "+Z", ""),
               ("-3", "-Z", "")]
    )
    
    dissolve_bool : bpy.props.BoolProperty(
        name="Dissolve Extra Verts",
        default = False)
    
class TopologyOperator(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.topology_operator"
    bl_label = "Topology Operator"
    
    
    @classmethod
    def poll(cls, context):
        global type_definitions
       
        
        scene = context.scene
        topo_props = scene.topo_props
        type = topo_props.type_enum
        grid_info = type_definitions[type]
        directions = [int(topo_props.across_enum), int(topo_props.down_enum)]
        if (context.active_object is None):
            return False
        else:
            if (bpy.context.active_object.mode == "EDIT"):
                me = bpy.context.object.data
                bm = bmesh.from_edit_mesh(me)
                selected_verts = [v for v in bm.verts if v.select]
                if (len(selected_verts) == 1):
                    vert_index = selected_verts[0].index
                    try:
                        select_grid(bm, grid_info[0],grid_info[1],directions)
                        for v in bm.verts:
                            if (v.index != vert_index):
                                v.select = False
                    except:
                        for v in bm.verts:
                            if (v.index != vert_index):
                                v.select = False                        
                        return False 
                else:
                    return False
            else:
                return False
            
       
        return True

    def execute(self, context):
        scene = context.scene
        topo_props = scene.topo_props
        directions = [int(topo_props.across_enum), int(topo_props.down_enum)]
        main(topo_props.type_enum, directions,topo_props.dissolve_bool)
        return {'FINISHED'}

class TopologyPanel(bpy.types.Panel):
    """Creates a Panel"""
    bl_label = "Topology Add-on"
    bl_idname = "OBJECT_PT_topology"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Topology"
    
    def draw(self, context):
        layout = self.layout
        scene = context.scene
        topo_props = scene.topo_props

        obj = context.object
        col = layout.column()
        
        col.prop(topo_props, "type_enum")
        col.prop(topo_props, "across_enum")
        col.prop(topo_props, "down_enum")
        col.prop(topo_props, "dissolve_bool")
        col.operator(TopologyOperator.bl_idname, text="Retopologize!", icon="MESH_GRID")
    
_classes = [TopologyProperties, TopologyOperator, TopologyPanel]        
      
def register():
    for cls in _classes:
        register_class(cls)
        
        bpy.types.Scene.topo_props = bpy.props.PointerProperty(type=TopologyProperties)

def unregister():
    for cls in _classes:
        unregister_class(cls)
        del bpy.types.Scene.topo_props

if __name__ == "__main__":
    register()
