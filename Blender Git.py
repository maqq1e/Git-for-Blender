import bpy
import os
from pathlib import Path

# DEF

def render_preview(context, directory):
    # Set render settings
    bpy.data.scenes[0].render.resolution_x = 128
    bpy.data.scenes[0].render.resolution_y = 128
    bpy.data.scenes[0].render.resolution_percentage = 100
    #render
    bpy.ops.render.opengl()
    #save image
    img_name = "temp_thumb.png"
    path = os.path.join(directory, img_name)
    bpy.data.images['Render Result'].save_render(path)
    bpy.ops.image.open(filepath = path)
    bpy.data.images[img_name].pack()
    bpy.data.images[img_name].use_fake_user = True
    texture = bpy.data.textures.new("temp_thumb", "IMAGE")
    texture.image = bpy.data.images[img_name]
    texture.use_fake_user = True
    
def create_unique_path(context, directory):

    git = context.window_manager.git
    commit_text = git.commit_text
    
    blendname = bpy.data.filepath[bpy.data.filepath.rfind('\\') + 1:-6]

    isFileExist = True

    number = 1

    while isFileExist:
        
        # Set the filename for the backup
        backup_filename = f"{git.subfolder_path}/{blendname}-{commit_text}-{number}.blend"

        backup_filepath = os.path.join(directory, backup_filename)

        if os.path.exists(backup_filepath):
            number += 1
            isFileExist = True
        else:
            return backup_filepath
        
def delete_unused_data():
    bpy.data.orphans_purge()

def move_objects_to_collection(objects, target_collection_name):
    # Ensure the target collection exists
    if target_collection_name not in bpy.data.collections:
        target_collection = bpy.data.collections.new(target_collection_name)
        bpy.context.scene.collection.children.link(target_collection)
    else:
        target_collection = bpy.data.collections[target_collection_name]

    # Iterate through all objects in the scene
    for obj in objects:
        # Skip objects already in the target collection
        if target_collection_name in [col.name for col in obj.users_collection]:
            continue

        # Remove the object from all other collections
        for col in obj.users_collection:
            col.objects.unlink(obj)
        
        # Add the object to the target collection
        target_collection.objects.link(obj)
    
    return target_collection

def save_backup(context, func, data):
    git = context.window_manager.git

    bpy.ops.wm.save_mainfile()

    # Get the current blend file path
    blend_filepath = bpy.data.filepath
    if not blend_filepath:
        print("Save the .blend file first.")
        return

    # Get the directory of the current blend file
    directory = os.path.dirname(blend_filepath)
    
    # Create path
    if not os.path.exists(directory + "\\" + git.subfolder_path):
        os.makedirs(directory + "\\" + git.subfolder_path)

    backup_filepath = func(context, data, directory)    
    
    delete_unused_data()

    render_preview(context, directory + "\\" + git.subfolder_path)

    # Create a new blend file for the backup
    bpy.ops.wm.save_as_mainfile(filepath=backup_filepath, copy=True)
    
    # Reopen the original blend file
    bpy.ops.wm.open_mainfile(filepath=blend_filepath)

def save_collection_backup(context, collection, directory):

    unique_path = create_unique_path(context, collection.name, directory)

    new_collection_name = 'Backup - ' + collection.name
        
    new_collection = move_objects_to_collection(collection.objects, new_collection_name)

    # Deselect all collections
    for coll in bpy.data.collections:
        coll.hide_viewport = True

    # Select only the target collection
    new_collection.hide_viewport = False
    
    # Remove all collections except the selected one
    for coll in bpy.data.collections:
        if coll != new_collection:
            bpy.data.collections.remove(coll)

    return unique_path

def prepare_selected_objects_backup(context, objects, directory):

    unique_path = create_unique_path(context, directory)

    new_collection_name = 'Backup - ' + objects[0].name

    new_collection = move_objects_to_collection(objects, new_collection_name)

    if len(context.collection.objects) > 0:
        temp_collection_name = 'Temp - ' + objects[0].name
        temp_collection = move_objects_to_collection(context.collection.objects, temp_collection_name)

    # Deselect all collections
    for coll in bpy.data.collections:
        coll.hide_viewport = True

    # Select only the target collection
    new_collection.hide_viewport = False
    
    # Remove all collections except the selected one
    for coll in bpy.data.collections:
        if coll != new_collection:
            bpy.data.collections.remove(coll)

    return unique_path

def save_all_objects_backup(context, objects, directory):

    unique_path = create_unique_path(context, directory)

    return unique_path

def delete_file_by_path(file_path):
    # Check if the file exists before deleting
    if os.path.exists(file_path):
        os.remove(file_path)

def _getChangesObjects(self, context):


    git = context.window_manager.git


    # Unload Libraries
    if len(bpy.data.libraries) > 0:
        prev_library = bpy.data.libraries.get(git.current_state)
        if prev_library:
            bpy.data.libraries.remove(prev_library)

    
    blend_filepath = bpy.data.filepath
    directory = os.path.dirname(blend_filepath)

    blendfile = git.versions_states[git.active_versions_states]

    git.current_state = blendfile.name

    backup_filename = git.subfolder_path + "/" + blendfile.name
    backup_filepath = os.path.join(directory, backup_filename)

    # This will store the names of all objects in the external file
    with bpy.data.libraries.load(backup_filepath, link=True) as (data_from, data_to):
        # Append all objects
        data_to.objects = data_from.objects
        data_to.textures = data_from.textures


    for tex in data_to.textures:
        if tex.name == "temp_thumb":
            git.versions_states[blendfile.name].preview = tex


    git.state_objects.clear()
    # Store actual object references in a Python list
    for obj in data_to.objects:
        obj_ref = git.state_objects.add()

        obj_ref.name = obj.name
        obj_ref.obj = obj

    # Is Preview? 
    if git.preview_mode:
        _previewChanges(self, context)

    git.active_state_objects = 0

def _selectStateObject(self, context):
    
    git = context.window_manager.git
    
    # Select preview object
    if git.temp_col_name in context.scene.collection.children:

        target_col = context.scene.collection.children[git.temp_col_name]
        
        _obj = git.state_objects[git.active_state_objects]

        bpy.ops.object.select_all(action='DESELECT')

        obj = target_col.objects[_obj.name]

        obj.select_set(True)
        context.view_layer.objects.active = obj

    # Datablocks
    git.object_datablocks.clear()

    _obj = git.state_objects[git.active_state_objects].obj

    if _obj:
        obj = git.object_datablocks.add()
        obj.obj = _obj

    if _obj.data:
        mesh = git.object_datablocks.add()
        mesh.mesh = _obj.data

    if _obj.material_slots:
        for mat in _obj.material_slots:
            _mat = git.object_datablocks.add()

            _mat.material = mat.material

    if _obj.animation_data:
        if _obj.animation_data.action:
            action = git.object_datablocks.add()
            action.action = _obj.animation_data.action

def _previewChanges(self, context):
    git = context.window_manager.git

    if len(git.state_objects) == 0:
        self.report({'ERROR'}, f"You have no objects in commit for preview.")
        return {'FINISHED'}


    # Name of the collection in the external file (usually 'Collection' or custom)
    target_collection_name = git.temp_col_name
    target_collection = bpy.data.collections.get(target_collection_name)
    if target_collection:
        bpy.data.collections.remove(target_collection)

    if git.preview_mode:
        # Create a new collection in the current scene
        target_collection = bpy.data.collections.new(target_collection_name)
        bpy.context.scene.collection.children.link(target_collection)


        for ref_obj in git.state_objects:
            obj = ref_obj.obj
            target_collection.objects.link(obj)

        # target_collection.hide_select = True
        target_collection.color_tag = "COLOR_01"

# UI

class BASICLIST_UL_datablocks(bpy.types.UIList):    

#     def filter_items(self, context, data, propname):
#         items = getattr(data, propname)
#         flt_flags = [0] * len(items)
#         flt_neworder = []
        
#         git = context.window_manager.git

#         for idx, item in enumerate(items):
#             if prefix != "":
#                 flt_flags[idx] = self.bitflag_filter_item  # Show item
# #            else: item is hidden (flag remains 0)

#         return flt_flags, flt_neworder
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        ob = data
        
        if item.obj:
            layout.label(text=item.obj.name, icon="OBJECT_DATAMODE")    
            layout.operator(CopyModifiers.bl_idname, text="", icon="MODIFIER")
            layout.operator(CopyConstraints.bl_idname, text="", icon="CONSTRAINT")
            layout.operator(CopyCustomProperties.bl_idname, text="", icon="PRESET_NEW")
            # op = layout.operator(ReassignObject.bl_idname, text="Insert to Active")
            # op.state = "OBJECT"
        if item.mesh:
            layout.label(text=item.mesh.name, icon="MESH_DATA") 
            op = layout.operator(ReassignObject.bl_idname, text="Insert to Active")
            op.state = "MESH"
        if item.material:
            layout.label(text=item.material.name, icon="MATERIAL")    
            op = layout.operator(ReassignObject.bl_idname, text="Insert to Active")
            op.state = "MATERIAL"
        if item.action:
            layout.label(text=item.action.name, icon="ACTION")    
            # op = layout.operator(ReassignObject.bl_idname, text="Insert to Active")
            # op.state = "ACTION"

class BASICLIST_UL_objects(bpy.types.UIList):
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        ob = data

        row = layout.row(align=True)
        if item.name not in context.scene.objects:
            row.alert = True
        row.label(text=item.name)

class BASICLIST_UL_states(bpy.types.UIList):
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        ob = data
        git = context.window_manager.git

        row = layout.row(align=True)
        
        row.label(text=item.name.replace(".blend", ""))

        op = row.operator(OpenFile.bl_idname, text="", icon="FILE_FOLDER")
        op.path = git.subfolder_path + "\\" + item.name
        op = row.operator(DeleteState.bl_idname, text="", icon="TRASH")
        op.path = git.subfolder_path + "\\" + item.name
        

UI_Classes = [
    BASICLIST_UL_datablocks,
    BASICLIST_UL_states,
    BASICLIST_UL_objects
]


# OPERATORS

# Operator for saving collection backup
class SaveCollectionBackup(bpy.types.Operator):
    '''Save selected collection as separate .blend file'''
    bl_idname = "git.save_collection_backup"
    bl_label = "Save Backup"
    bl_options = {'REGISTER', 'UNDO'}
    
    collection_name: bpy.props.StringProperty()
    
    def execute(self, context):
        if bpy.data.is_saved:
            collection = bpy.data.collections.get(self.collection_name)
            if collection:
                save_backup(context, save_collection_backup, collection)
                self.report({'INFO'}, f"Backup saved.")
            else:
                self.report({'ERROR'}, f"Collection not found")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, f"You need to save you .blend file!")
            return {'FINISHED'}
        
# Operator for saving selected objects backup
class SaveSelectedObjectsBackup(bpy.types.Operator):
    '''Save selected objects as separate .blend file'''
    bl_idname = "git.save_selected_objects_backup"
    bl_label = "Save Backup"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        git = context.window_manager.git

        if bpy.data.is_saved:

            if git.commit_selected_only:
                if context.selected_objects:
                    save_backup(context, prepare_selected_objects_backup, context.selected_objects)
                    self.report({'INFO'}, "Backup saved for selected objects")
                else:
                    self.report({'ERROR'}, "No objects selected")
            else:
                save_backup(context, save_all_objects_backup, context.selected_objects)
            
            _getVersionStatesList(self, context)
            _getChangesObjects(self, context)
                
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, f"You need to save you .blend file!")
            return {'FINISHED'}

class OpenFile(bpy.types.Operator):
    bl_idname = "git.open_file_by_os"
    bl_label = "Open File"
    bl_options = {'REGISTER', 'UNDO'}

    path: bpy.props.StringProperty()
           
    def execute(self, context):       
        filepath = bpy.data.filepath
        directory = os.path.dirname(filepath)
               
        os.startfile(os.path.join(directory, self.path))
       
        return {'FINISHED'}
    
class DeleteState(bpy.types.Operator):
    bl_idname = "git.delete_state"
    bl_label = "Delete Commit"
    bl_options = {'REGISTER', 'UNDO'}

    path: bpy.props.StringProperty()
           
    def execute(self, context):       
        git = context.window_manager.git
        filepath = bpy.data.filepath
        directory = os.path.dirname(filepath)

        directory = os.path.join(directory, self.path)

        delete_file_by_path(directory)

        _getVersionStatesList(self, context)

        git.active_versions_states = 0

        git.active_state_objects = 0
       
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

def replace_datablock_references(old_data, new_data):
    # Loop through all ID datablocks in the file
    target_list = None
    if type(new_data) == bpy.types.Mesh:
        target_list = list(bpy.data.objects)
    if type(new_data) == bpy.types.Mesh:
        target_list = list(bpy.data.meshes)
    if type(new_data) == bpy.types.Material:
        target_list = list(bpy.data.materials)
    if type(new_data) == bpy.types.Action:
        target_list = list(bpy.data.actions)

    if target_list == None:
        return target_list

    for id_block in target_list:
        # Check if the datablock has custom properties
        for key, value in id_block.items():
            # Skip built-in properties
            if key.startswith("_"):
                continue

            # Check if the property is a pointer to the old datablock
            if isinstance(value, bpy.types.ID) and value == old_data:
                id_block[key] = new_data
                print(f"Updated custom property '{key}' in {id_block.name}")

        # Also check RNA-defined pointer properties (not just ID properties)
        for prop in id_block.bl_rna.properties:
            if isinstance(prop, bpy.types.PointerProperty):
                try:
                    if getattr(id_block, prop.identifier) == old_data:
                        setattr(id_block, prop.identifier, new_data)
                        print(f"Updated pointer property '{prop.identifier}' in {id_block.name}")
                except Exception:
                    pass  # Some properties may not be settable or may raise errors
                
def _reassign(self, context, source_data, target_data):
    # Define source and target objects

    git = context.window_manager.git

    if git.preview_mode:
        self.report({'ERROR'}, "Your must disable Preview Mode!")

    new_object = target_data.copy()

    # Get the original mesh data-block from the source object
    old_object = source_data
    replace_datablock_references(old_object, new_object)

class ReassignObject(bpy.types.Operator):
    """Insert this data-block into active object"""
    bl_idname = "git.reassign_object"
    bl_label = "Reassign Objects"
    bl_options = {'REGISTER', 'UNDO'}

    state: bpy.props.StringProperty()
           
    def execute(self, context):
        git = context.window_manager.git

        source_obj = context.active_object

        if source_obj:
            
            target_obj = git.state_objects[git.active_state_objects]

            # if self.state == "OBJECT":
            #     _reassign(self, context, source_obj, target_obj.obj)
            if self.state == "MESH":
                _reassign(self, context, source_obj.data, target_obj.obj.data)
            # if self.state == "ACTION":
            #     if not source_obj.animation_data:
            #         self.report({'ERROR'}, "Active object must have animation data or any action!")
            #         return {'FINISHED'}
            #     _reassign(self, context, source_obj.animation_data.action, target_obj.obj.animation_data.action)
            if self.state == "MATERIAL":
                if len(target_obj.obj.material_slots) != len(source_obj.material_slots):
                    self.report({'ERROR'}, "Objects must have same material slots amount!")
                    return {'FINISHED'}
                for i in range(len(source_obj.material_slots)):
                    slot = source_obj.material_slots[i]
                    target_slot = target_obj.obj.material_slots[i]
                    _reassign(self, context, slot.material, target_slot.material)
        else:
            self.report({'ERROR'}, "You have no any active object!")




        return {'FINISHED'}

class ReassignAllObject(bpy.types.Operator):
    """Update all object in scene which name is same in commit state"""
    bl_idname = "git.reassign_all_object"
    bl_label = "Reassign Objects"
    bl_options = {'REGISTER', 'UNDO'}
           
    def execute(self, context):
        git = context.window_manager.git

        objects = context.scene.objects

        for ref_obj in git.state_objects:
            source_obj = objects.get(ref_obj.name)

            if git.batch_selected_only:
                if source_obj:
                    if source_obj in context.selected_objects:
                        target_obj = ref_obj.obj
                        # _reassign(self, context, source_obj, target_obj)
                        _reassign(self, context, source_obj.data, target_obj.data)
                        if len(target_obj.material_slots) != len(source_obj.material_slots):
                            self.report({'INFO'}, "Objects must have same material slots amount!")
                            continue
                        for i in range(len(source_obj.material_slots)):
                            slot = source_obj.material_slots[i]
                            target_slot = target_obj.material_slots[i]
                            _reassign(self, context, slot.material, target_slot.material)
            else:
                if source_obj:
                    target_obj = ref_obj.obj
                    # _reassign(self, context, source_obj, target_obj)
                    _reassign(self, context, source_obj.data, target_obj.data)
                    if len(target_obj.material_slots) != len(source_obj.material_slots):
                        self.report({'INFO'}, "Objects must have same material slots amount!")
                        continue
                    for i in range(len(source_obj.material_slots)):
                        slot = source_obj.material_slots[i]
                        target_slot = target_obj.material_slots[i]
                        _reassign(self, context, slot.material, target_slot.material)
                
        return {'FINISHED'}

class InsertState(bpy.types.Operator):
    """Insert whole commit in scene"""
    bl_idname = "git.insert_state"
    bl_label = "Insert Commit"
    bl_options = {'REGISTER', 'UNDO'}

    path: bpy.props.StringProperty()
            
    def execute(self, context):       
        git = context.window_manager.git

        if len(git.state_objects) == 0:
            self.report({'ERROR'}, f"You have no objects in commit for insert.")
            return {'FINISHED'}

        target_collection_name = git.current_state
        target_collection = bpy.data.collections.get(target_collection_name)
        if target_collection:
            bpy.data.collections.remove(target_collection)

        target_collection = bpy.data.collections.new(target_collection_name)

        context.scene.collection.children.link(target_collection)

        for ref_obj in git.state_objects:
            obj = ref_obj.obj.copy()
            obj.data = ref_obj.obj.data.copy()

            target_collection.objects.link(obj)
        
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


def resolve_datablock(attr, value):
    """Resolve any ID-type to local version by name, or None if not found."""
    if isinstance(value, bpy.types.ID):
        datablock_type = type(value).__name__
        datablock_collection = getattr(bpy.data, datablock_type.lower() + "s", None)
        if datablock_collection:
            local = datablock_collection.get(value.name)
            if local and not local.library:
                return local
            else:
                return None
    return value


def _copy_custom_properties(source, target):
    for key in source.keys():
        if key == "_RNA_UI":
            continue
        value = source[key]
        if isinstance(value, dict):
            # Merge group properties
            if key not in target:
                target[key] = {}
            for subkey, subvalue in value.items():
                target[key][subkey] = subvalue
        else:
            try:
                target[key] = value
            except Exception:
                pass  # Skip if assignment fails

        # Copy UI metadata safely
    if "_RNA_UI" in source:
        if "_RNA_UI" not in target:
            target["_RNA_UI"] = {}
        for key, value in source["_RNA_UI"].items():
            try:
                target["_RNA_UI"][key] = value.copy()
            except Exception:
                pass

class CopyCustomProperties(bpy.types.Operator):
    bl_idname = "git.copy_custom_properties"
    bl_label = "Copy Custom Properties"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        git = context.window_manager.git

        target_obj = context.active_object

        if target_obj:
            
            source_obj = git.state_objects[git.active_state_objects].obj

            _copy_custom_properties(source_obj, target_obj)
        return {'FINISHED'}

def _copy_constraints(source, target):
    for con in source.constraints:
        new_con = target.constraints.new(type=con.type)
        for attr in dir(con):
            if not attr.startswith("_") and not callable(getattr(con, attr)):
                try:
                    value = getattr(con, attr)
                    setattr(new_con, attr, resolve_datablock(attr, value))
                except Exception:
                    pass

class CopyConstraints(bpy.types.Operator):
    bl_idname = "git.copy_constraints"
    bl_label = "Copy Constraints"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        git = context.window_manager.git

        target_obj = context.active_object

        if target_obj:
            
            source_obj = git.state_objects[git.active_state_objects].obj

            _copy_constraints(source_obj, target_obj)
        return {'FINISHED'}
    

def _copy_modifiers(source, target):
    for mod in source.modifiers:
        new_mod = target.modifiers.new(name=mod.name, type=mod.type)
        for attr in dir(mod):
            if not attr.startswith("_") and not callable(getattr(mod, attr)):
                try:
                    value = getattr(mod, attr)
                    setattr(new_mod, attr, resolve_datablock(attr, value))
                    if attr == "node_group":
                        new_mod.node_group.make_local()
                except Exception:
                    pass

class CopyModifiers(bpy.types.Operator):
    bl_idname = "git.copy_modifiers"
    bl_label = "Copy Modifiers"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        git = context.window_manager.git

        target_obj = context.active_object

        if target_obj:
            
            source_obj = git.state_objects[git.active_state_objects].obj

            _copy_modifiers(source_obj, target_obj)
        return {'FINISHED'}


def _getVersionStatesList(self,context):
    git = context.window_manager.git
    # Get the current blend file path
    blend_filepath = bpy.data.filepath
    if not blend_filepath:
        self.report({'ERROR'}, f"You need to save you .blend file!")
        return
    
    directory = os.path.dirname(blend_filepath)

    folder_path = directory + "\\" + git.subfolder_path
    
    # Create path
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    # List all .blend files in the folder
    # blend_files = [f for f in os.listdir(folder_path) if f.endswith(".blend")]
    folder_path = Path(folder_path)
    blend_files = [
        (file, file.stat().st_ctime)
        for file in folder_path.glob("*.blend")
        if file.is_file()
    ]

    # Sort by creation time (oldest to newest)
    blend_files.sort(key=lambda x: x[1])


    git.versions_states.clear()
    for file, ctime in blend_files:
        new_item = git.versions_states.add()

        new_item.name = file.name
        new_item.time = ctime

class GetVersionStatesList(bpy.types.Operator):
    bl_idname = "git.get_states_list"
    bl_label = "Update States List"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        _getVersionStatesList(self, context)
        return {'FINISHED'}
    

OPERATORS_Classes = [
    SaveCollectionBackup,
    SaveSelectedObjectsBackup,
    OpenFile,
    GetVersionStatesList,
    ReassignObject,
    ReassignAllObject,
    DeleteState,
    InsertState,
    CopyModifiers,
    CopyConstraints,
    CopyCustomProperties
]


# MAIN

class ControlVersions(bpy.types.Panel):
    bl_label = "Control Versions"
    bl_idname = "VIEW3D_PT_control_versions"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Script Manager'
    
    def draw_header(self, context):
        """Optional: Draw the header of the panel."""
        self.layout.label(icon='ASSET_MANAGER')  # Example header icon

    def draw(self, context):
        layout = self.layout

        obj = context.active_object

        git = context.window_manager.git
        layout.prop(git, "subfolder_path")

        layout.prop(git, "commit_text")
        layout.operator(SaveSelectedObjectsBackup.bl_idname)


        box = layout.box()

        _row = box.row(align=True)

        _row.prop(git, "commit_selected_only", text="", toggle=True, icon="MOD_ARRAY")
        _row.operator(GetVersionStatesList.bl_idname, text="Update", icon="FILE_REFRESH")
        
        box.template_list("BASICLIST_UL_states", "", git , "versions_states", git, "active_versions_states")

        box = layout.box()

        _row = box.row(align=True)

        _row.prop(git, "batch_selected_only", text="", toggle=True, icon="MOD_ARRAY")

        _row.operator(ReassignAllObject.bl_idname, text="Batch Reassign", icon="PASTEDOWN")

        _row.prop(git, "preview_mode", text="Preview", icon="HIDE_OFF", toggle=True)

        box.operator(InsertState.bl_idname, text="Insert Commit", icon="IMPORT")
        
        current_state = git.versions_states[git.current_state]

        if current_state.preview:
            box.template_preview(git.versions_states[git.current_state].preview)

        box.template_list("BASICLIST_UL_objects", "", git , "state_objects", git, "active_state_objects")

        _row = box.row(align=True)

        # _row.prop(git, "reassign_object", text="", icon="OBJECT_DATAMODE")
        # _row.prop(git, "reassign_mesh", text="", icon="MESH_DATA")

        box.template_list("BASICLIST_UL_datablocks", "", git , "object_datablocks", git, "active_object_datablocks")



MAIN_Classes = [
    ControlVersions
]


bl_info = {
    "name": "Blender Control Version",
    "author": "https://github.com/maqq1e",
    "description": "Easy way manage your project versions.",
    "blender": (4, 5, 0),
    "version": (0, 3, 1),
}

# class GitPreferences(bpy.types.AddonPreferences):
#     bl_idname = __name__

#     subfolder_path: bpy.props.StringProperty()

#     def draw(self, context):
#         layout = self.layout
#         layout.label(text="test")

class GitStates(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(default="")
    time: bpy.props.FloatProperty(default=0.0)
    preview: bpy.props.PointerProperty(type=bpy.types.Texture)

    
class StateObjects(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(default="")
    obj: bpy.props.PointerProperty(type=bpy.types.Object)


# class DataBlocksMaterials(bpy.types.PropertyGroup):
#     name: bpy.props.StringProperty(default="")
#     material: bpy.props.PointerProperty(type=bpy.types.Material)

class DataBlocks(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(default="")
    obj: bpy.props.PointerProperty(type=bpy.types.Object)
    mesh: bpy.props.PointerProperty(type=bpy.types.Mesh)
    material: bpy.props.PointerProperty(type=bpy.types.Material)
    action: bpy.props.PointerProperty(type=bpy.types.Action)


class GitProperties(bpy.types.PropertyGroup):
    # Preferences
    # @property
    # def preferences(self):
    #     # Dynamically access the addon preferences
    #     return bpy.context.preferences.addons[__name__].preferences

    subfolder_path: bpy.props.StringProperty(default=".bgit")

    temp_col_name: bpy.props.StringProperty(default="TEMP_COMMIT_STAGE-DO NOT DELETE MANUALY")

    commit_text: bpy.props.StringProperty(default="Commit Description")

    versions_states: bpy.props.CollectionProperty(type=GitStates)
    current_state: bpy.props.StringProperty(default="")
    active_versions_states: bpy.props.IntProperty(name="Select Commit", default=0, update=_getChangesObjects)

    state_objects: bpy.props.CollectionProperty(type=StateObjects)
    active_state_objects: bpy.props.IntProperty(name="Select Object in Commit what store data-blocks", default=0, update=_selectStateObject)

    object_datablocks: bpy.props.CollectionProperty(type=DataBlocks)
    active_object_datablocks: bpy.props.IntProperty(name="Select data-block", default=0)



    batch_selected_only: bpy.props.BoolProperty(default=True, name="Reassign Selected Only")
    commit_selected_only: bpy.props.BoolProperty(default=True, name="Commit Selected Only")
    
    preview_mode: bpy.props.BoolProperty(default=False, update=_previewChanges, description="Toggle View of Selected Commit")

    reassign_object: bpy.props.BoolProperty(default=False, name="Reassign Object")
    reassign_mesh: bpy.props.BoolProperty(default=True, name="Reassign Mesh")


    
def setProperties():
    
    bpy.types.WindowManager.git = bpy.props.PointerProperty(type=GitProperties)

        
def delProperties():
    
    del bpy.WindowManager.Scene.git


# Initialization Classes
UsesClasses = []
# UsesClasses.append(GitPreferences)
UsesClasses.extend(OPERATORS_Classes)
UsesClasses.extend(MAIN_Classes)
UsesClasses.extend(UI_Classes)
UsesClasses.append(GitStates)
UsesClasses.append(StateObjects)
# UsesClasses.append(DataBlocksMaterials)
UsesClasses.append(DataBlocks)
UsesClasses.append(GitProperties)



# After Load
@bpy.app.handlers.persistent
def after_load(context):
    _getVersionStatesList(None, context)


# Register Classes
def register():

    for useClass in UsesClasses:
        bpy.utils.register_class(useClass)
    
    setProperties()

    bpy.app.handlers.load_post.append(after_load) # Load datas after load blender

def unregister():    
    
    for useClass in UsesClasses:
        bpy.utils.unregister_class(useClass)

    delProperties()

    bpy.app.handlers.load_post.remove(after_load)

# if __name__ == "__main__":
#     register()
