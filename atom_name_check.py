# Function：对齐高斯优化后的原子名称。
# Usage：将本脚本放在主文件夹下，可遍历当前文件夹下所有子文件夹，
#        处理每个子文件夹下的NEWPDB.PDB文件，使用ATOMTYPE.INF文件索引，
#        将NEWPDB.PDB文件中的原子坐标与input.sdf文件（文件名可修改）中的原子坐标对齐，
#        对齐原子名称后生成的文件命名为LIG.PDB，分别储存在每一个子文件夹中。
# Required files:
#            ATOMTYPE.INF
#            NEWPDB.PDB
#            input.sdf
# Author: zhuziyu@simm.ac.cn
# Released: 2025-03-20

import os
import re

# 获取当前脚本所在的目录，即父文件夹
main_directory = os.getcwd()

# 遍历所有子文件夹，包括更深层级
for root, dirs, files in os.walk(main_directory):
    if root == main_directory:
        continue  # 跳过主目录本身，仅处理子文件夹
    
    print(f"🔄 进入 {root} 处理数据...")

    # 查找当前子文件夹中的第一个 SDF 文件
    sdf_files = [f for f in files if f.endswith(".sdf")]
    sdf_input_filename = sdf_files[0] if sdf_files else None

    if sdf_input_filename is None:
        print(f"❌ 错误: 未找到任何 .sdf 文件，请检查 {root} 目录！")
        continue

    sdf_input_path = os.path.join(root, sdf_input_filename)
    pdb_update_path = os.path.join(root, "NEWPDB.PDB")
    inf_file_path = os.path.join(root, "ATOMTYPE.INF")
    output_pdb_file_path = os.path.join(root, "LIG.PDB")

    # 检查文件存在
    if not os.path.exists(pdb_update_path):
        print(f"❌ 错误: 未找到 NEWPDB.PDB，请检查 {root} 目录！")
        continue
    if not os.path.exists(inf_file_path):
        print(f"❌ 错误: 未找到 ATOMTYPE.INF，请检查 {root} 目录！")
        continue

    print(f"📄 选定 SDF 输入文件: {sdf_input_filename}")
    print(f"📄 选定 PDB 更新文件: NEWPDB.PDB")

    # 读取SDF文件并提取坐标
    sdf_coordinates = []
    sdf_atom_order = []

    with open(sdf_input_path, 'r') as f:
        lines = f.readlines()
        atom_count = int(lines[3][:3].strip())
        for line in lines[4:4 + atom_count]:
            parts = line.split()
            x, y, z = parts[0:3]
            atom_label = parts[3].strip().upper()
            if atom_label.startswith("H"):
                continue
            sdf_coordinates.append([x, y, z])
            sdf_atom_order.append(atom_label)

    print(f"✅ 解析 {sdf_input_filename} 完成，共 {len(sdf_coordinates)} 组坐标（已跳过氢原子）")

    # 读取 INF 文件并构建原子类型到索引的映射
    atom_type_map = {}
    with open(inf_file_path, 'r') as f:
        for line in f:
            match = re.search(r'\[\s*(\d+)\s*\]\s*\((\S+)\s*\)', line)
            if match:
                index, atom_label = match.groups()
                atom_label = atom_label.strip().upper()
                if atom_label.startswith("H"):
                    continue
                atom_type_map[atom_label] = int(index)

    print(f"✅ 解析 {inf_file_path} 完成")

    # 读取 PDB 文件并更新坐标
    updated_pdb_lines = []
    with open(pdb_update_path, 'r') as f:
        for line in f:
            if line.startswith("ATOM") or line.startswith("HETATM"):
                atom_label = line[12:16].strip().upper()
                if atom_label.startswith("H"):
                    continue
                if atom_label in atom_type_map:
                    sdf_index = atom_type_map[atom_label] - 1
                    if 0 <= sdf_index < len(sdf_coordinates):
                        new_x, new_y, new_z = sdf_coordinates[sdf_index]
                        updated_line = f"{line[:30]}{float(new_x):8.3f}{float(new_y):8.3f}{float(new_z):8.3f}{line[54:]}"
                        updated_pdb_lines.append(updated_line)
                        continue
                    else:
                        print(f"❌ 错误: {atom_label} 对应的索引 {sdf_index+1} 超出范围")
                else:
                    print(f"⚠️ 警告: {atom_label} 未在 {inf_file_path} 中找到")

            updated_pdb_lines.append(line)

    # 写入新的 PDB 文件
    with open(output_pdb_file_path, 'w') as f:
        f.writelines(updated_pdb_lines)

    print(f"✅ 处理完成，已保存 {output_pdb_file_path}")

print("🎉 所有子文件夹处理完毕！")

