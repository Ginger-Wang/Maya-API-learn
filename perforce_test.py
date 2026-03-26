def check_file_in_perforce(p4, file_path):
    """
    判断文件是否存在于Perforce服务器，并返回状态
    :param p4: 已连接的P4对象
    :param file_path: 文件路径（工作区相对路径或绝对路径）
    :return: 'open' 文件已被打开（检出）
             'edit' 文件存在但未检出，可编辑
             'add' 文件不存在，可添加
    """
    try:
        fstat = p4.run("fstat", file_path)
        opened = p4.run("opened", file_path)
        if opened:
            return "open"
        else:
            return "edit"
    except P4Exception as e:
        # 这里假设异常意味着文件不存在
        return "add"

# 使用示例
p4 = P4()
client_value = os.getenv('workSpace_name') # 环境变量中的workspace 名称
if client_value is not None:
    p4.client = client_value
else:
    p4.client = "workSpace_name"
    
p4.port = "Perforce:1666" #p4 服务器IP地址
p4.user = "user_name" #用户名
file_path = "User_file_path"

try:
    p4.connect()       
    action = check_file_in_perforce(p4, file_path)    
    if action == "edit":
        print("文件存在于Perforce服务器上,可以check out 编辑")
    elif action == "add":
        print("文件不存在于Perforce服务器上,可以添加到workspace")
    elif action == "open":
        cmds.warning(f"文件已被打开（已 Checkout）: {file_path}")
    else:
        print("未知状态")
finally:
    p4.disconnect()
