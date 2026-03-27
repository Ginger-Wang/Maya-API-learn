from maya import cmds, mel

def cloth_to_bones_ui():
    if cmds.window("clothToBonesUI", exists=True):
        cmds.deleteUI("clothToBonesUI")

    window = cmds.window("clothToBonesUI", 
                         title="布料顶点动画 → 骨骼动画 (Maya 2025)",
                         widthHeight=(340, 200), sizeable=True)

    cmds.columnLayout(adjustableColumn=True, rowSpacing=12, columnAlign='center')

    num_slider = cmds.intSliderGrp(label="骨骼数量 (推荐 3-15)", 
                                   field=True, 
                                   minValue=2, 
                                   maxValue=50, 
                                   value=5, 
                                   step=1, 
                                   columnWidth=[(1, 130)])

    cmds.button(label="执行转换", 
                height=45, 
                command=lambda x: execute_conversion(
                    cmds.intSliderGrp(num_slider, q=True, value=True)))

    cmds.text(label="使用说明：\n"
                    "1. 选中带顶点动画的布料网格（nCloth 等驱动）\n"
                    "2. 调整骨骼数量后点击按钮\n"
                    "3. 转换后可删除原 nCloth，只保留 SkinCluster",
              align='left', wordWrap=True)

    cmds.showWindow(window)


def execute_conversion(num_bones):
    # 获取选中物体
    sel = cmds.ls(sl=True, type='transform')
    if not sel:
        cmds.warning("请先选中一个带顶点动画的网格物体！")
        return

    mesh = sel[0]

    # 获取 shape
    shapes = cmds.listRelatives(mesh, s=True, ni=True)
    if not shapes or cmds.objectType(shapes[0]) != 'mesh':
        cmds.warning("选中的不是网格物体！")
        return

    shape = shapes[0]

    # 切换到动画起始帧作为绑定姿势
    start_frame = cmds.playbackOptions(q=True, animationStartTime=True)
    cmds.currentTime(start_frame, update=True)

    # 获取顶点数量
    num_vtx = cmds.polyEvaluate(mesh, vertex=True)
    if num_vtx < num_bones * 2:
        cmds.warning(f"顶点数量 ({num_vtx}) 太少，无法创建 {num_bones} 根骨骼！")
        return

    # 获取包围盒，自动判断最长轴
    bbox = cmds.xform(mesh, q=True, bb=True, ws=True)
    dx = bbox[3] - bbox[0]
    dy = bbox[4] - bbox[1]
    dz = bbox[5] - bbox[2]
    axis_ranges = [dx, dy, dz]
    axis_idx = axis_ranges.index(max(axis_ranges))  # 0=X, 1=Y, 2=Z

    axis_name = 'XYZ'[axis_idx]
    print(f"自动检测最长轴: {axis_name} 轴，将沿此轴创建骨骼链")

    # 获取所有顶点在绑定姿势的世界坐标（仅取主轴坐标用于排序）
    vtx_data = []
    for i in range(num_vtx):
        pos = cmds.pointPosition(f"{mesh}.vtx[{i}]", world=True)
        coord = pos[axis_idx]
        vtx_data.append((coord, i, pos))

    # 按主轴排序
    vtx_data.sort(key=lambda x: x[0])

    # 均匀采样骨骼位置（避免首尾过于集中）
    selected_vtx_ids = []
    bind_positions = []
    for k in range(num_bones):
        idx = int(k * (len(vtx_data) - 1) / (num_bones - 1)) if num_bones > 1 else len(vtx_data) // 2
        data = vtx_data[idx]
        selected_vtx_ids.append(data[1])
        bind_positions.append(data[2])

    # 创建骨骼链
    cmds.select(clear=True)
    joint_list = []
    for i, pos in enumerate(bind_positions):
        jnt = cmds.joint(p=pos, name=f"{mesh}_clothBone_{i+1:03d}", radius=0.5)
        cmds.select(clear=True)
        joint_list.append(jnt)

    # 设置骨骼链方向（方便后续蒙皮和动画）
    if joint_list:
        cmds.joint(joint_list[0], edit=True, orientJoint='xyz', 
                   secondaryAxisOrient='yup', children=True, zeroScaleOrient=True)

    # 创建 Point on Poly Constraint（让骨骼跟随顶点动画）
    constraints = []
    for i in range(num_bones):
        vtx = f"{mesh}.vtx[{selected_vtx_ids[i]}]"
        # 直接使用 cmds.pointOnPolyConstraint（更稳定）
        cmds.select(vtx, joint_list[i], )
        constraint = cmds.pointOnPolyConstraint(maintainOffset=False)[0]
        constraints.append(constraint)

    print(f"已创建 {num_bones} 根骨骼和对应的 Point on Poly Constraint")

    # 获取动画范围并烘焙
    min_time = cmds.playbackOptions(q=True, min=True)
    max_time = cmds.playbackOptions(q=True, max=True)

    cmds.bakeResults(joint_list,
                     time=(min_time, max_time),
                     sampleBy=1,
                     attribute=['translateX', 'translateY', 'translateZ',
                                'rotateX', 'rotateY', 'rotateZ'],
                     simulation=True,
                     controlPoints=False,
                     shape=False)

    # 【关键】删除临时约束节点
    if constraints:
        cmds.delete(constraints)
        print(f"已删除 {len(constraints)} 个 Point on Poly Constraint 节点")

    # 创建 Skin Cluster
    skin_cluster = cmds.skinCluster(joint_list, mesh, 
                                    toSelectedBones=True, 
                                    maximumInfluences=4, 
                                    obeyMaxInfluences=True,
                                    name=f"{mesh}_clothBones_Skin")[0]

    print(f"SkinCluster 已创建: {skin_cluster}")

    # 收尾
    cmds.select(joint_list[0])
    cmds.viewFit(joint_list[0])

    print("✅ 转换完成！")


# 启动 UI
cloth_to_bones_ui()









