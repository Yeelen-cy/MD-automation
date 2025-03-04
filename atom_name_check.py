# Function：对齐高斯优化后的原子名称。
# Usage：将本文本放在主文件夹下，即可遍历当前文件夹下所有子文件夹，
#        处理每个子文件夹下的NEWPDB.PDB文件，使用ATOMTYPE.INF文件索引，
#        将NEWPDB.PDB文件中的原子坐标与pdb{folder}-lig.pdb文件中的原子坐标对齐，
#        对齐原子名称后生成的文件命名为LIG.PDB，分别储存在每一个子文件夹中。
# Required files:
#            ATOMTYPE.INF
#            NEWPDB.PDB
#            pdb{folder}-lig.pdb
# Author: zhuziyu@simm.ac.cn
# Released: 2025-03-04

import os
import re

# 获取主目录（当前脚本所在的目录）
main_directory = os.path.dirname(os.path.abspath(__file__))

# 遍历所有子文件夹
for folder in os.listdir(main_directory):
    subfolder_path = os.path.join(main_directory, folder)

    # 只处理真正的子文件夹，排除 __pycache__
    if os.path.isdir(subfolder_path) and folder != "__pycache__":
        print(f"🔄 进入 {subfolder_path} 处理数据...")

        # 获取子文件夹名称（用于动态生成 PDB 文件名）
        pdb_input_filename = f"pdb{folder}-lig.pdb"
        pdb_input_path = os.path.join(subfolder_path, pdb_input_filename)
        pdb_update_path = os.path.join(subfolder_path, "NEWPDB.PDB")
        inf_file_path = os.path.join(subfolder_path, "ATOMTYPE.INF")
        output_pdb_file_path = os.path.join(subfolder_path, "LIG.PDB")

        # 确保关键文件存在
        if not os.path.exists(pdb_input_path):
            print(f"❌ 错误: 未找到 {pdb_input_filename}，请检查 {subfolder_path} 目录！")
            continue
        if not os.path.exists(pdb_update_path):
            print(f"❌ 错误: 未找到 NEWPDB.PDB，请检查 {subfolder_path} 目录！")
            continue
        if not os.path.exists(inf_file_path):
            print(f"❌ 错误: 未找到 ATOMTYPE.INF，请检查 {subfolder_path} 目录！")
            continue

        print(f"📄 选定 PDB 输入文件: {pdb_input_filename}")
        print(f"📄 选定 PDB 更新文件: NEWPDB.PDB")

        # 读取新的 PDB 文件，提取坐标
        pdb_coordinates = []
        pdb_atom_order = []

        with open(pdb_input_path, 'r') as f:
            for line in f:
                if line.startswith("ATOM") or line.startswith("HETATM"):
                    atom_label = line[12:16].strip().upper()
                    if atom_label.startswith("H"):
                        continue
                    x, y, z = line[30:38].strip(), line[38:46].strip(), line[46:54].strip()
                    pdb_coordinates.append([x, y, z])
                    pdb_atom_order.append(atom_label)

        print(f"✅ 解析 {pdb_input_filename} 完成，共 {len(pdb_coordinates)} 组坐标（已跳过氢原子）")

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
                        pdb_index = atom_type_map[atom_label] - 1
                        if 0 <= pdb_index < len(pdb_coordinates):
                            new_x, new_y, new_z = pdb_coordinates[pdb_index]
                            updated_line = f"{line[:30]}{float(new_x):8.3f}{float(new_y):8.3f}{float(new_z):8.3f}{line[54:]}"
                            updated_pdb_lines.append(updated_line)
                            continue
                        else:
                            print(f"❌ 错误: {atom_label} 对应的索引 {pdb_index+1} 超出范围")
                    else:
                        print(f"⚠️ 警告: {atom_label} 未在 {inf_file_path} 中找到")

                updated_pdb_lines.append(line)

        # 写入新的 PDB 文件
        with open(output_pdb_file_path, 'w') as f:
            f.writelines(updated_pdb_lines)

        print(f"✅ 处理完成，已保存 {output_pdb_file_path}")

print("🎉 所有子文件夹处理完毕！")
