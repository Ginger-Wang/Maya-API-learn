import os

UE_PROJECT_ROOT = "../../../test"
UE_CONTENT_PYTHON = "content/python/"
UE_TOOL_PYTHON = "tools/python/unrealscripts/"


def ue_project_root():
    return os.path.realpath(os.path.join(os.getcwd(), UE_PROJECT_ROOT))


def ue_content_python_path():
    return os.path.join(ue_project_root(), UE_CONTENT_PYTHON)


def ue_tool_python_path():
    return os.path.join(ue_project_root(), UE_TOOL_PYTHON)


def qt_icon_path():
    return os.path.join(ue_tool_python_path(), 'QtUtil/Icons/')


def current_working_directory():
    return os.getcwd()

