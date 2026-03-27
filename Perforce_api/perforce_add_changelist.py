from P4 import P4, P4Exception

def create_perforce_changelist(p4,description="New changelist from Maya 2025"):
    try:
        p4.connect()        
        # 获取一个空的 change 模板（Change: new）
        change = p4.fetch_change()
        change._description = description   # 设置描述        
        # 可选：添加其他字段
        # change._client = p4.client
        
        # 保存（会创建编号的 pending changelist）
        result = p4.save_change(change)        
        # result 通常返回 ['Change XXX created.']
        if result:
            changelist_num = result[0].split()[1]
            print(f"成功创建 Perforce Changelist: {changelist_num}")
            return changelist_num
        return None        
    except P4Exception as erro:
        print(f"Perforce 错误:{erro}")
        return None
    finally:
        p4.disconnect()

       
p4 = P4()
client_value = os.getenv('user_workspace_name')
if client_value is not None:
    p4.client = client_value
else:
    p4.client = "user_workspace_name"
   
p4.port = "Perforce:1666"        # 如果需要指定服务器
p4.user = "userName"
file_path = "add_to_Perfoce_filepath/test.txt"

num = create_perforce_changelist(p4,description="New changelist from Maya 2025")
try:
    p4.connect()
    p4.run("add" ,"-c",str(num),file_path)
except P4Exception as err:
    print(err)
finally:
    p4.disconnect()    
    

"""
Reference :
https://help.perforce.com/helix-core/server-apps/cmdref/current/Content/CmdRef/commands.html
"""
