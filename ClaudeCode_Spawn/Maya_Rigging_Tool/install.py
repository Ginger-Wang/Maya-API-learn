# -*- coding: utf-8 -*-
"""把本文件拖进 Maya 视口即可安装「可变 FK 绑定工具」。

它会做三件事:把当前目录加进本次会话的 ``sys.path``;
在用户的 Maya scripts 目录里写一个 ``variableFK.pth``,让重启后依然能导入;
并在当前 shelf 上放一个按钮。
"""

import os
import sys

SHELF_LABEL = 'VarFK'
SHELF_TOOLTIP = u'可变 FK 绑定工具'
SHELF_COMMAND = '\n'.join([
    'import variableFK',
    'variableFK.show()',
])


def _package_root():
    """本文件所在目录,也就是要加进 sys.path 的那一层。"""
    return os.path.dirname(os.path.abspath(__file__))


def _add_to_path(root):
    if root not in sys.path:
        sys.path.insert(0, root)


def _write_pth(root):
    """在用户 scripts 目录写一个 .pth 文件,让路径在重启后仍然有效。"""
    import maya.cmds as cmds

    scripts_dir = cmds.internalVar(userScriptDir=True)
    if not os.path.isdir(scripts_dir):
        return None
    pth = os.path.join(scripts_dir, 'variableFK.pth')
    with open(pth, 'w') as handle:
        handle.write(root + '\n')
    return pth


def _add_shelf_button():
    """在当前 shelf 上添加按钮(重复安装会先删掉旧的)。"""
    import maya.cmds as cmds
    import maya.mel as mel

    shelf = mel.eval('$tmp = $gShelfTopLevel')
    current = cmds.tabLayout(shelf, query=True, selectTab=True)

    for button in cmds.shelfLayout(current, query=True, childArray=True) or []:
        if cmds.control(button, query=True, docTag=True) == SHELF_TOOLTIP:
            cmds.deleteUI(button)

    cmds.shelfButton(parent=current, label=SHELF_LABEL,
                     annotation=SHELF_TOOLTIP, imageOverlayLabel=SHELF_LABEL,
                     image='kinJoint.png', sourceType='python',
                     command=SHELF_COMMAND, docTag=SHELF_TOOLTIP)
    return current


def onMayaDroppedPythonFile(*_args):     # noqa: N802 —— Maya 规定的回调名
    import maya.cmds as cmds

    root = _package_root()
    _add_to_path(root)
    pth = _write_pth(root)
    shelf = _add_shelf_button()

    import variableFK
    variableFK.show()

    message = [u'可变 FK 绑定工具安装完成。',
               u'路径:{0}'.format(root),
               u'已添加 shelf 按钮到:{0}'.format(shelf)]
    if pth:
        message.append(u'已写入持久化路径:{0}'.format(pth))
    cmds.confirmDialog(title=u'可变 FK 绑定工具', button=[u'确定'],
                       message=u'\n'.join(message))


if __name__ == '__main__':
    onMayaDroppedPythonFile()
