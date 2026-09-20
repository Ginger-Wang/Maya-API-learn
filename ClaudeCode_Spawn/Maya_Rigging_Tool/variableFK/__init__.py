# -*- coding: utf-8 -*-
"""Maya 可变 FK(触手)绑定工具包。

在 Maya 里这样用::

    import variableFK
    variableFK.show()          # 打开界面

或者直接脚本化构建::

    import variableFK
    variableFK.build('curve1', prefix='tentacle_', num_controls=4,
                     num_joints=40)
"""

from . import core
from . import ui

build = core.build
show = ui.show

__all__ = ['core', 'ui', 'build', 'show']
__version__ = '1.0.0'


def reload_all():
    """重新导入所有子模块 —— 在 Maya 里反复改代码调试时很方便。"""
    try:
        from importlib import reload as _reload
    except ImportError:                                   # Maya 2019 / py2
        _reload = reload                                  # type: ignore # noqa: F821

    from . import nodes
    _reload(nodes)
    _reload(core)
    _reload(ui)

    global build, show
    build = core.build
    show = ui.show
