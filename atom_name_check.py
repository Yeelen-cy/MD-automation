# Function：对齐高斯优化后的原子名称。
# Usage：处理每个子文件夹下的NEWPDB.PDB文件，使用ATOMTYPE.INF文件索引，
#        将NEWPDB.PDB文件中的原子坐标与input.sdf文件（文件名可修改）中的原子坐标对齐，
#        对齐原子名称后生成的文件命名为LIG.PDB，分别储存在每一个子文件夹中。
# Required files:
#            ATOMTYPE.INF
#            NEWPDB.PDB
#            input.sdf
# Author: zhuziyu@simm.ac.cn
# Released: 2025-03-21

import os
import re
import logging

# 配置日志输出
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# 设定主目录
main_directory = os.getcwd()

# `LRT` 目录存放了需要处理的输入文件
lrt_dir = os.path.join(main_directory, "ligprep", "LRT")
zzy_output_dir = os.path.join(main_directory, "ligprep", "ZZY")

if not os.path.exists(lrt_dir):
    logging.error(f"❌ 未找到 LRT 目录，请检查路径: {lrt_dir}")
    exit(1)

# 遍历 `LRT` 目录，获取 `sdf`、`NEWPDB.PDB` 和 `ATOMTYPE.INF`
for root, dirs, files in os.walk(lrt_dir):
    logging.info(f"🔄 处理目录: {root}")

    # 确定 SDF 文件
    sdf_files = [f for f in files if f.endswith(".sdf")]
    if not sdf_files:
        logging.warning(f"❌ 未找到 .sdf 文件，跳过 {root}")
        continue

    sdf_input_path = os.path.join(root, sdf_files[0])
    pdb_update_path = os.path.join(root, "NEWPDB.PDB")
    inf_file_path = os.path.join(root, "ATOMTYPE.INF")

    if not all(os.path.exists(f) for f in [pdb_update_path, inf_file_path]):
        logging.error(f"❌ 缺少关键文件 (NEWPDB.PDB 或 ATOMTYPE.INF)，跳过 {root}")
        continue

    # 确定输出目录（ZZY）
    relative_path = os.path.relpath(root, lrt_dir)  # 获取相对路径
    output_dir = os.path.join(zzy_output_dir, relative_path)
    os.makedirs(output_dir, exist_ok=True)
    output_pdb_file_path = os.path.join(output_dir, "LIG.PDB")

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
