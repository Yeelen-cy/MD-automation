"""
Function: Generate Amber parameter files using tleap for all system folders.
Usage: python md_parm_gen.py
############################################################################ README ############################################################################
# We need at least one folder starting with "system" in the script working path, which contains the pdb file (Receptor structure file).
# If no 'ligprep' folder detected or necessary files missing, treat as apo system.
# For complex system, we need the "ligprep" folder, which contains the following files：
#           (1) ligand strcture file: lig.pdb
#           (2) ligand parameter file: lig.prep and lig.frcmod
############################################################################ README ############################################################################
Author: zhouzhaoyin@simm.ac.cn
Released: 2025-02-26
Updata record: 
  2025-03-17: Unified work path
  2025-03-30: Automatically identify all system folders and process them conditionally + automatically identify protein/complex systems
"""

import os
import sys
import subprocess
import re

def run_tleap(input_file, output_dir):
    """在指定输出目录中执行 tleap，并捕获其输出。
    生成的所有文件（例如 leap.log）将存储在 output_dir 中。
    """
    try:
        subprocess.run(["tleap", "-f", input_file],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       cwd=output_dir)
    except subprocess.CalledProcessError as e:
        print(f"tleap execution failed in {output_dir}: {e}")
        sys.exit(1)

def parse_charge_from_log(log_file):
    """从 leap.log 文件中提取系统电荷。
    搜索类似于：
        Total unperturbed charge:  <value>
    的行，并返回提取的电荷值（float）。
    """
    charge = None
    if not os.path.exists(log_file):
        print("Error: leap.log not found. Please verify tleap execution.")
        sys.exit(1)
    with open(log_file, "r") as log:
        for line in log:
            m = re.search(r'Total unperturbed charge:\s+([-+]?[0-9]*\.?[0-9]+)', line)
            if m:
                charge = float(m.group(1))
                break
    if charge is None:
        print("Error: Failed to parse  charge from leap.log.")
        sys.exit(1)
    return charge

def prepare_protein(base_dir, pdb_filename):
    """处理蛋白质单体体系：
    1. 生成测试 tleap 输入脚本计算蛋白电荷。
    2. 生成完整 tleap 输入脚本，加载蛋白 PDB 文件、保存干体系文件、进行溶剂化和离子添加，
       最后保存溶剂化后的文件。
       
    所有生成的文件均保存在 base_dir/parameters 文件夹下。
    """
    output_dir = os.path.join(base_dir, "parameters")
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成测试脚本以计算电荷
    test_file = os.path.join(output_dir, "tleap_protein_test.in")
    # 因为 parameters 文件夹位于 base_dir 内，所以 PDB 文件路径为 "../<pdb_filename>"
    with open(test_file, "w") as f:
        f.write(
            "source leaprc.protein.ff19SB\n"
            "source leaprc.water.opc\n\n"
            f"pro = loadpdb ../{pdb_filename}\n"
            "charge pro\n"
            "quit\n"
        )
    print(f"[{base_dir}] Running tleap for protein charge test...")
    run_tleap("tleap_protein_test.in", output_dir)
    charge = parse_charge_from_log(os.path.join(output_dir, "leap.log"))
    print(f"[{base_dir}] Detected protein  charge: {charge}")

    # 根据电荷决定添加离子
    ion = None
    nion = 0
    if charge > 0:
        ion = "Cl-"
        nion = int(round(charge))
    elif charge < 0:
        ion = "Na+"
        nion = int(round(-charge))
    if ion and nion > 0:
        print(f"[{base_dir}] Adding {nion} {ion} ions to neutralize the .")
    else:
        print(f"[{base_dir}]  is neutral - no ions required.")

    # 生成完整的 tleap 脚本
    full_file = os.path.join(output_dir, "tleap_protein.in")
    with open(full_file, "w") as f:
        f.write(
            "source leaprc.protein.ff19SB\n"
            "source leaprc.water.opc\n\n"
            f"pro = loadpdb ../{pdb_filename}\n\n"
            "saveamberparm pro pro.prmtop pro.inpcrd\n"
            "savepdb pro pro-dry.pdb\n\n"
            "charge pro\n"
            "solvatebox pro OPCBOX 10\n"
        )
        if ion and nion > 0:
            f.write(f"addionsrand pro {ion} {nion}\n")
            f.write("charge pro\n")
        f.write(
            "\n# Save solvated parameters\n"
            "saveamberparm pro pro-sol.prmtop pro-sol.inpcrd\n"
            "savepdb pro pro-sol.pdb\n"
            "quit\n"
        )
    print(f"[{base_dir}] Processing protein  (solvation and ion addition)...")
    run_tleap("tleap_protein.in", output_dir)
    print(f"[{base_dir}] Protein  processing completed. Generated files in: {output_dir}")
    print(f"  Dry topology: pro.prmtop")
    print(f"  Dry coordinates: pro.inpcrd")
    print(f"  Dry structure: pro-dry.pdb")
    print(f"  Solvated topology: pro-sol.prmtop")
    print(f"  Solvated coordinates: pro-sol.inpcrd")
    print(f"  Solvated structure: pro-sol.pdb")

def prepare_complex(base_dir, pdb_filename):
    """处理蛋白-配体复合体系：
    1. 生成测试 tleap 输入脚本计算复合体系电荷。
    2. 生成完整 tleap 脚本，加载蛋白和配体参数、保存各组分及复合体系，
       进行溶剂化和离子添加，最后保存生成的 Amber 参数文件。
       
    所有生成的文件均保存在 base_dir/parameters 文件夹下。
    """
    output_dir = os.path.join(base_dir, "parameters")
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成测试脚本以计算电荷
    test_file = os.path.join(output_dir, "tleap_complex_test.in")
    with open(test_file, "w") as f:
        f.write(
            "source leaprc.protein.ff19SB\n"
            "source leaprc.gaff2\n"
            "source leaprc.water.opc\n\n"
            "loadamberparams ../ligprep/lig.frcmod\n"    # ligand frcmod
            "loadamberprep ../ligprep/lig.prep\n\n"       # ligand prep
            "mol = loadpdb ../ligprep/LIG.PDB\n"            # ligand PDB
            f"pro = loadpdb ../{pdb_filename}\n"            # protein PDB
            "com = combine {pro mol}\n\n"
            "charge com\n"
            "quit\n"
        )
    print(f"[{base_dir}] Running tleap for complex charge test...")
    run_tleap("tleap_complex_test.in", output_dir)
    charge = parse_charge_from_log(os.path.join(output_dir, "leap.log"))
    print(f"[{base_dir}] Detected complex  charge: {charge}")

    # 根据电荷决定添加离子
    ion = None
    nion = 0
    if charge > 0:
        ion = "Cl-"
        nion = int(round(charge))
    elif charge < 0:
        ion = "Na+"
        nion = int(round(-charge))
    if ion and nion > 0:
        print(f"[{base_dir}] Adding {nion} {ion} ions for neutralization.")
    else:
        print(f"[{base_dir}] Complex system is neutral - no ions required.")

    # 生成完整的 tleap 脚本
    full_file = os.path.join(output_dir, "tleap_complex.in")
    with open(full_file, "w") as f:
        f.write(
            "source leaprc.protein.ff19SB\n"
            "source leaprc.gaff2\n"
            "source leaprc.water.opc\n\n"
            "loadamberparams ../ligprep/lig.frcmod\n"    # ligand frcmod
            "loadamberprep ../ligprep/lig.prep\n\n"       # ligand prep
            "mol = loadpdb ../ligprep/LIG.PDB\n"            # ligand PDB
            f"pro = loadpdb ../{pdb_filename}\n"            # protein PDB
            "com = combine {pro mol}\n\n"
            "saveamberparm pro pro.prmtop pro.inpcrd\n"
            "saveamberparm mol lig.prmtop lig.inpcrd\n"
            "saveamberparm com native.prmtop native.inpcrd\n"
            "savepdb com com-dry.pdb\n\n"
            "charge com\n"
            "solvatebox com OPCBOX 10\n"
        )
        if ion and nion > 0:
            f.write(f"addionsrand com {ion} {nion}\n")
            f.write("charge com\n")
        f.write(
            "\nsaveamberparm com complex.prmtop complex.inpcrd\n"
            "savepdb com com.pdb\n"
            "quit\n"
        )
    print(f"[{base_dir}] Processing complex system (solvation and ion addition)...")
    run_tleap("tleap_complex.in", output_dir)
    print(f"[{base_dir}] Complex system processing completed. Generated files in: {output_dir}")
    print("  Protein topology: pro.prmtop")
    print("  Protein coordinates: pro.inpcrd")
    print("  Ligand topology: lig.prmtop")
    print("  Ligand coordinates: lig.inpcrd")
    print("  Dry complex structure: com-dry.pdb")
    print("  Native complex topology: native.prmtop")
    print("  Native coordinates: native.inpcrd")
    print("  Solvated topology: complex.prmtop")
    print("  Solvated coordinates: complex.inpcrd")
    print("  Solvated structure: com.pdb")

def process_system(system_dir):
    """
    检查 system_dir 文件夹是否满足处理条件：
    1. 在 system_dir 根目录下找到一个 PDB 文件（排除 ligprep 文件夹中的文件）
    2. 如果 system_dir 下存在 ligprep 子文件夹，并且其中包含 lig.frcmod, lig.prep 和 LIG.PDB，
       则认为是复合体系；否则为蛋白质单体体系。
    根据检测结果调用相应的处理函数。
    """
    # 查找根目录下的 pdb 文件（排除文件夹）
    pdb_files = [f for f in os.listdir(system_dir)
                 if f.lower().endswith(".pdb") and os.path.isfile(os.path.join(system_dir, f))]
    if not pdb_files:
        print(f"[{system_dir}] 未找到 PDB 文件，跳过该文件夹。")
        return
    # 这里取第一个 pdb 文件作为蛋白质结构文件
    pdb_filename = pdb_files[0]
    
    ligprep_dir = os.path.join(system_dir, "ligprep")
    is_complex = False
    if os.path.isdir(ligprep_dir):
        required_files = {"lig.frcmod", "lig.prep", "LIG.PDB"}
        available = set(os.listdir(ligprep_dir))
        if required_files.issubset(available):
            is_complex = True

    print(f"[{system_dir}] 检测到 PDB 文件：{pdb_filename}")
    if is_complex:
        print(f"[{system_dir}] 检测到完整的 ligprep 文件夹，按照蛋白-配体复合体系处理。")
        prepare_complex(system_dir, pdb_filename)
    else:
        print(f"[{system_dir}] 未检测到 ligprep 或缺失必要文件，按照蛋白质单体体系处理。")
        prepare_protein(system_dir, pdb_filename)

def main():
    """自动扫描当前目录下所有以 'system' 开头的文件夹，并对满足条件的文件夹进行处理。"""
    base_path = os.getcwd()
    dirs = [d for d in os.listdir(base_path) if os.path.isdir(d) and d.startswith("system")]
    if not dirs:
        print("未找到以 'system' 开头的文件夹。")
        sys.exit(1)
    
    for d in dirs:
        system_dir = os.path.join(base_path, d)
        process_system(system_dir)

if __name__ == "__main__":
    main()
