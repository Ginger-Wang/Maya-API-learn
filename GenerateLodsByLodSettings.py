import unreal
# 指定目录路径
directory_path = "/Game/Art/Character/Animals/test"
# 获取指定目录下的所有资产
asset_data_list = unreal.EditorAssetLibrary.list_assets(directory_path, recursive=True)
# 遍历资产列表，筛选出Skeletal Mesh
skeletal_meshes = []
for asset_data in asset_data_list:
    asset_dataName = unreal.EditorAssetLibrary.load_asset(asset_data)
    # 获取资产路径
    asset_class = asset_dataName.get_class()
    # 判断是否为Skeletal Mesh
    if asset_class.get_fname() == "SkeletalMesh":
        skeletal_meshes.append(asset_dataName)

for skeletal_mesh_actor in skeletal_meshes:
    lod_settings = skeletal_mesh_actor.lod_settings
    # 使用SkeletalMeshLODSettings设置LOD
    # 假设有一个名为"lod_settings"的SkeletalMeshLODSettings对象 /Script/Engine.SkeletalMeshLODSettings'/Game/Art/Character/LODData/Body_LODSettings.Body_LODSettings'
    lod_settings_to_apply = unreal.EditorAssetLibrary.load_asset('/Game/Art/Character/LODData/Animal_LODSettings.Animal_LODSettings')
    skeletal_mesh_actor.lod_settings = lod_settings_to_apply
    lod_groups = lod_settings_to_apply.get_editor_property("lod_groups")
    #重新生成指定数量的LOD "new_lod_count" 5 生成5级LOD  
    unreal.EditorSkeletalMeshLibrary.regenerate_lod(skeletal_mesh_actor, new_lod_count=5)
    # 保存该资产
    unreal.EditorAssetLibrary.save_loaded_asset(skeletal_mesh_actor)
