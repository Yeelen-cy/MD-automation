import os
import sys
import logging
import re
import parmed as pmd  # 确保安装了 parmed

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

def amber_to_gmx(prmtop_file, inpcrd_file):
    """
    Convert AMBER parameter and coordinate files to GROMACS format.
    
    Parameters:
        prmtop_file (str): Path to the AMBER prmtop file.
        inpcrd_file (str): Path to the AMBER inpcrd file.
    """

    # 固定 GROMACS 输出文件名
    top_file = "gmx.top"
    gro_file = "gmx.gro"

    # 检查输入文件是否存在
    if not os.path.exists(prmtop_file):
        logging.error(f"AMBER prmtop file not found: {prmtop_file}")
        sys.exit(1)
    if not os.path.exists(inpcrd_file):
        logging.error(f"AMBER inpcrd file not found: {inpcrd_file}")
        sys.exit(1)

    try:
        # 加载 AMBER 参数和坐标文件
        amber = pmd.load_file(prmtop_file, inpcrd_file)

        # 保存为 GROMACS 格式
        amber.save(top_file, format="gromacs")  # 指定 GROMACS 格式
        amber.save(gro_file, format="gro")      # 保存 .gro 坐标文件

        logging.info(f"Files successfully converted to GROMACS format: {top_file}, {gro_file}")
    except Exception as e:
        logging.exception("Error during AMBER to GROMACS conversion")
        sys.exit(1)


def position_restraint():
    """Modify GROMACS topology file to include position restraint."""
    
    top_file = "gmx.top"

    # 如果 gmx.top 不存在，先自动调用 amber_to_gmx()
    if not os.path.exists(top_file):
        logging.info("Converting AMBER parameters to GROMACS format...")
        
        # 假设有默认的 AMBER 文件名
        default_prmtop = "complex.prmtop"
        default_inpcrd = "complex.inpcrd"

        if not os.path.exists(default_prmtop) or not os.path.exists(default_inpcrd):
            logging.error("Default AMBER files not found. Cannot generate gmx.top automatically.")
            sys.exit(1)

        amber_to_gmx(default_prmtop, default_inpcrd)

    # 现在 gmx.top 已经生成，继续执行 position restraint
    posres_protein = "; Include Position restraint file\n#ifdef  POSRES\n#include \"posre1.itp\"\n#endif\n\n"
    posres_mol = "; Include Position restraint file\n#ifdef  POSRES\n#include \"posre2.itp\"\n#endif\n\n"

    with open(top_file, "r") as f:
        lines = f.readlines()

    modified = False
    found_protein = False
    found_ion = False

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if re.match(r'^\s*\[\s*moleculetype\s*\]\s*$', line, re.IGNORECASE):
            if i + 2 < len(lines):
                line1 = lines[i+1].strip()
                line2 = lines[i+2].strip()
                #line3 = lines[i+2].strip()
                
                #if line1 == "MOL" or line2 == "MOL" or line3 == "MOL":
                if line1.split()[0] == "MOL" or line2.split()[0] == "MOL":
                    if not lines[i-1].strip() == posres_protein.strip():  
                        lines.insert(i, posres_protein)
                        found_protein = True
                        modified = True
                        logging.info("Position restraints have been added to the protein molecule.")

                if line1.split()[0] == "Na+" or line2.split()[0] == "Na+" or line1.split()[0] == "Cl-" or line2.split()[0] == "Cl-" :
                    if not lines[i-1].strip() == posres_mol.strip():
                        lines.insert(i, posres_mol)
                        found_ion = True
                        modified = True
                        logging.info("Position restraints have been added to the small molecule.")

        i += 1  

    if not found_protein:
        logging.warning("Protein chain position not found.")

    if not found_ion:
        logging.warning("Small molecule position not found.")

    if modified:
        with open(top_file, "w") as f:
            f.writelines(lines)
        logging.info(f"Position restraints have been added to {top_file}.")
    else:
        logging.info("Could not find the correct position.")


def main():
    """Main execution based on command line argument:
    0: AMBER to GROMACS conversion
    1: Add position restraint
    """
    if len(sys.argv) < 2 or sys.argv[1] not in ["0", "1"]:
        logging.error("Invalid argument. Usage:")
        logging.error("  python new2.py 0 <prmtop> <inpcrd>   # Convert AMBER to GROMACS (auto output names)")
        logging.error("  python new2.py 1                     # Add position restraint")
        sys.exit(1)

    mode = sys.argv[1]
    
    if mode == "0":
        if len(sys.argv) != 4:
            logging.error("Missing arguments for AMBER to GROMACS conversion.")
            logging.error("Usage: python new2.py 0 <prmtop> <inpcrd>")
            sys.exit(1)
        
        prmtop_file = sys.argv[2]
        inpcrd_file = sys.argv[3]

        amber_to_gmx(prmtop_file, inpcrd_file)

    elif mode == "1":
        position_restraint()

if __name__ == "__main__":
    main()
