# Function：对齐高斯优化后的原子名称。
# Usage：处理每个ligprep文件夹下的NEWPDB.PDB文件，使用ATOMTYPE.INF文件索引，
#        将NEWPDB.PDB文件中的原子坐标与systemX.sdf文件中的原子坐标对齐，
#        对齐原子名称后生成的文件命名为LIG.PDB，分别储存在每一个ligprep文件夹中。
# Required files:
#            ATOMTYPE.INF
#            NEWPDB.PDB
#            systemX.sdf
# Author: zhuziyu@simm.ac.cn
# Released: 2025-03-30

# 引入需要用到的Python标准库
import os       # 用于文件和目录操作，比如路径拼接、文件遍历等
import re       # 用于正则表达式匹配，处理特定格式的文本
import logging  # 用于打印提示信息和错误信息，让我们了解程序运行状态

# 设置日志输出的格式和等级
# INFO级别表示打印一般信息，格式中只输出消息内容，不带时间等
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# 获取当前运行脚本的目录路径，作为项目的主目录
main_directory = os.getcwd()

# 遍历主目录下的所有文件夹，比如 system1、system2、system3 等
for entry in os.listdir(main_directory):
    system_path = os.path.join(main_directory, entry)  # 拼接成完整路径
    if os.path.isdir(system_path) and entry.startswith("system"):
        # 如果这是一个目录，且名字以"system"开头（即我们关心的文件夹），就处理它
        logging.info(f"🔍 正在处理目录: {system_path}")

        # 在 systemX 文件夹下查找以 .sdf 结尾的文件（通常只有一个，比如 system1.sdf）
        sdf_files = [f for f in os.listdir(system_path) if f.endswith(".sdf")]
        if not sdf_files:
            # 如果没有找到 .sdf 文件，发出警告并跳过这个 system 文件夹
            logging.warning(f"❌ 未找到 .sdf 文件，跳过 {entry}")
            continue  # 跳过当前循环，进入下一个 system

        # 找到的 sdf 文件路径
        sdf_input_path = os.path.join(system_path, sdf_files[0])
        sdf_input_filename = sdf_files[0]  # 文件名仅用于打印提示

        # 找到 ligprep 子目录路径，比如 system1/ligprep/
        ligprep_dir = os.path.join(system_path, "ligprep")

        # 构建 NEWPDB.PDB 和 ATOMTYPE.INF 的完整路径
        pdb_update_path = os.path.join(ligprep_dir, "NEWPDB.PDB")
        inf_file_path = os.path.join(ligprep_dir, "ATOMTYPE.INF")
        output_pdb_file_path = os.path.join(ligprep_dir, "LIG.PDB")  # 输出的新文件

        # 如果两个关键文件没有找到，提示错误并跳过
        if not os.path.exists(pdb_update_path) or not os.path.exists(inf_file_path):
            logging.error(f"❌ 缺少关键文件 (NEWPDB.PDB 或 ATOMTYPE.INF)，跳过 {entry}")
            continue

        # ========== 第一步：读取 SDF 文件中的坐标信息 ==========
        sdf_coordinates = []   # 存储原子的坐标
        sdf_atom_order = []    # 存储原子的元素符号（如 C、N、O 等）

        with open(sdf_input_path, 'r') as f:
            lines = f.readlines()  # 读取所有行
            atom_count = int(lines[3][:3].strip())  # 第4行开头是原子数量
            for line in lines[4:4 + atom_count]:  # 逐个读取原子信息
                parts = line.split()
                x, y, z = parts[0:3]  # 提取坐标 x, y, z
                atom_label = parts[3].strip().upper()  # 提取元素名称（如C、N）
                if atom_label.startswith("H"):
                    continue  # 跳过氢原子
                sdf_coordinates.append([x, y, z])
                sdf_atom_order.append(atom_label)

        print(f"✅ 解析 {sdf_input_filename} 完成，共 {len(sdf_coordinates)} 组坐标（已跳过氢原子）")

        # ========== 第二步：读取 INF 文件中的原子索引信息 ==========
        atom_type_map = {}  # 存储原子名称和它在 SDF 中的编号映射关系
        with open(inf_file_path, 'r') as f:
            for line in f:
                # 匹配格式：[ 1 ] (C)  其中1是编号，C是原子符号
                match = re.search(r'\[\s*(\d+)\s*\]\s*\((\S+)\s*\)', line)
                if match:
                    index, atom_label = match.groups()
                    atom_label = atom_label.strip().upper()
                    if atom_label.startswith("H"):
                        continue  # 跳过氢原子
                    atom_type_map[atom_label] = int(index)

        print(f"✅ 解析 {inf_file_path} 完成")

        # ========== 第三步：读取 PDB 文件并更新坐标 ==========
        updated_pdb_lines = []  # 存储更新后的PDB内容
        with open(pdb_update_path, 'r') as f:
            for line in f:
                if line.startswith("ATOM") or line.startswith("HETATM"):
                    atom_label = line[12:16].strip().upper()  # 提取原子名
                    if atom_label.startswith("H"):
                        continue  # 跳过氢原子
                    if atom_label in atom_type_map:
                        sdf_index = atom_type_map[atom_label] - 1  # 原子编号从1开始，所以要减1
                        if 0 <= sdf_index < len(sdf_coordinates):
                            # 用 SDF 中对应坐标替换掉旧坐标
                            new_x, new_y, new_z = sdf_coordinates[sdf_index]
                            updated_line = (
                                f"{line[:30]}"
                                f"{float(new_x):8.3f}{float(new_y):8.3f}{float(new_z):8.3f}"
                                f"{line[54:]}"
                            )
                            updated_pdb_lines.append(updated_line)
                            continue
                        else:
                            print(f"❌ 错误: {atom_label} 对应的索引 {sdf_index+1} 超出范围")
                    else:
                        print(f"⚠️ 警告: {atom_label} 未在 {inf_file_path} 中找到")

                updated_pdb_lines.append(line)  # 非ATOM/HETATM的行保留原样

        # ========== 第四步：写入新的 PDB 文件 ==========
        with open(output_pdb_file_path, 'w') as f:
            f.writelines(updated_pdb_lines)

        print(f"✅ 处理完成，已保存 {output_pdb_file_path}")

# ========== 所有system文件夹处理完毕 ==========
print("🎉 所有 system 目录处理完毕！")
