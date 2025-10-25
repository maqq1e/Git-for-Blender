import bpy
import os

# DEF

def create_unique_path(context, directory):

    props = context.window_manager.git
    commit_text = props.commit_text
    
    blendname = bpy.data.filepath[bpy.data.filepath.rfind('\\') + 1:-6]

    isFileExist = True

    number = 1

    while isFileExist:
        
        # Set the filename for the backup
        backup_filename = f".bgit/{blendname}-{commit_text}-{number}.blend"

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
    bpy.ops.wm.save_mainfile()

    # Get the current blend file path
    blend_filepath = bpy.data.filepath
    if not blend_filepath:
        print("Save the .blend file first.")
        return

    # Get the directory of the current blend file
    directory = os.path.dirname(blend_filepath)
    
    # Create path
    if not os.path.exists(directory + "\\.bgit"):
        os.makedirs(directory + "\\.bgit")

    backup_filepath = func(context, data, directory)    
    
    delete_unused_data()

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

def save_selected_objects_backup(context, objects, directory):

    unique_path = create_unique_path(context, directory)

    new_collection_name = 'Backup - ' + objects[0].name

    new_collection = move_objects_to_collection(objects, new_collection_name)

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

def _getChangesObjects(self, context):

    git = context.window_manager.git

    # Unload Libraries
    if len(bpy.data.libraries) > 0:
        if git.current_state != "":
            prev_library = bpy.data.libraries[git.current_state]
            bpy.data.libraries.remove(prev_library)

    
    blend_filepath = bpy.data.filepath
    directory = os.path.dirname(blend_filepath)

    blendfile = git.versions_states[git.active_versions_states]

    git.current_state = blendfile.name

    backup_filename = f".bgit/" + blendfile.name
    backup_filepath = os.path.join(directory, backup_filename)

    # This will store the names of all objects in the external file
    with bpy.data.libraries.load(backup_filepath, link=False) as (data_from, data_to):
        # Append all objects
        data_to.objects = data_from.objects

    git.state_objects.clear()
    # Store actual object references in a Python list
    for obj in data_to.objects:
        obj_ref = git.state_objects.add()

        obj_ref.name = obj.name
        obj_ref.obj = obj


# UI

class BASICLIST_UL_itemslots(bpy.types.UIList):    

    def filter_items(self, context, data, propname):
        items = getattr(data, propname)
        flt_flags = [0] * len(items)
        flt_neworder = []
        
        prefix = context.view_layer['PREFIX']

        for idx, item in enumerate(items):
            
            if prefix != "":
                if prefix in item.name:
                    flt_flags[idx] = self.bitflag_filter_item  # Show item
#            else: item is hidden (flag remains 0)

        return flt_flags, flt_neworder
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        ob = data
        
        layout.prop(item, "name", text="", emboss=False, icon_value=icon)    

class BASICLIST_UL_itemslots_all(bpy.types.UIList):
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        ob = data
        
        layout.prop(item, "name", text="", emboss=False, icon_value=icon)

class BASICLIST_UL_states(bpy.types.UIList):
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        ob = data
        git = context.window_manager.git

        row = layout.row()
        
        row.label(text=item.name.replace(".blend", ""))

        op = row.operator(OpenFile.bl_idname)
        op.path = git.subfolder_path + "\\" + item.name

UI_Classes = [
    BASICLIST_UL_itemslots,
    BASICLIST_UL_states,
    BASICLIST_UL_itemslots_all
]


# OPERATORS

class MatchBlendFilesOperator(bpy.types.Operator):
    bl_idname = "operators.match_blend_files"
    bl_label = "Find Matching Blend Files"

    def execute(self, context):

        pass
            
        return {'FINISHED'}

# Operator for saving collection backup
class SaveCollectionBackup(bpy.types.Operator):
    '''Save selected collection as separate .blend file'''
    bl_idname = "git.save_collection_backup"
    bl_label = "Save Backup"
    
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
    
    def execute(self, context):
        if bpy.data.is_saved:
            if context.selected_objects:
                save_backup(context, save_selected_objects_backup, context.selected_objects)
                self.report({'INFO'}, "Backup saved for selected objects")
            else:
                self.report({'ERROR'}, "No objects selected")
            return {'FINISHED'}
        else:
            self.report({'ERROR'}, f"You need to save you .blend file!")
            return {'FINISHED'}

class OpenFile(bpy.types.Operator):
    bl_idname = "git.open_file_by_os"
    bl_label = "Open File"

    path: bpy.props.StringProperty()
           
    def execute(self, context):       
        filepath = bpy.data.filepath
        directory = os.path.dirname(filepath)
               
        os.startfile(os.path.join(directory, self.path))
       
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
    blend_files = [f for f in os.listdir(folder_path) if f.endswith(".blend")]


    git.versions_states.clear()
    for file in blend_files:
        new_item = git.versions_states.add()

        new_item.name = file

class GetVersionStatesList(bpy.types.Operator):
    bl_idname = "git.get_states_list"
    bl_label = "Update States List"

    def execute(self, context):
        _getVersionStatesList(self, context)
        return {'FINISHED'}
    

OPERATORS_Classes = [
    MatchBlendFilesOperator,
    SaveCollectionBackup,
    SaveSelectedObjectsBackup,
    OpenFile,
    GetVersionStatesList
]


# MAIN

class MatchBlendFilesPanel(bpy.types.Panel):
    bl_label = "Match Blend Files"
    bl_idname = "VIEW3D_PT_match_blend_files"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Script Manager'

    def draw(self, context):
        layout = self.layout

        obj = context.active_object

        git = context.window_manager.git
        layout.prop(git, "subfolder_path")

        layout.prop(git, "commit_text")
        layout.operator(SaveSelectedObjectsBackup.bl_idname)


        box = layout.box()

        _row = box.row()

        _row.operator(GetVersionStatesList.bl_idname, text="Update", icon="FILE_REFRESH")
        
        box.template_list("BASICLIST_UL_states", "", git , "versions_states", git, "active_versions_states")

        box = layout.box()
        
        box.template_list("BASICLIST_UL_itemslots_all", "", git , "state_objects", git, "active_state_objects")



MAIN_Classes = [
    MatchBlendFilesPanel
]


bl_info = {
    "name": "Blender Control Version",
    "author": "https://github.com/maqq1e",
    "description": "Easy way manage your project versions.",
    "blender": (4, 5, 0),
    "version": (0, 0, 1),
}

# class GitPreferences(bpy.types.AddonPreferences):
#     bl_idname = __name__

#     subfolder_path: bpy.props.StringProperty()

#     def draw(self, context):
#         layout = self.layout
#         layout.label(text="test")

class GitStates(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(default="")

    
class StateObjects(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(default="")
    obj: bpy.props.PointerProperty(type=bpy.types.Object)


class GitProperties(bpy.types.PropertyGroup):
    # Preferences
    # @property
    # def preferences(self):
    #     # Dynamically access the addon preferences
    #     return bpy.context.preferences.addons[__name__].preferences

    subfolder_path: bpy.props.StringProperty(default=".bgit")

    commit_text: bpy.props.StringProperty(default="Commit Description")

    versions_states: bpy.props.CollectionProperty(type=GitStates)
    current_state: bpy.props.StringProperty(default="")
    active_versions_states: bpy.props.IntProperty(default=0, update=_getChangesObjects)

    state_objects: bpy.props.CollectionProperty(type=StateObjects)
    active_state_objects: bpy.props.IntProperty(default=0)


    
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
