# Function1: "Converting Amber data to GROMACS data using python"
# Function2: "Add position restraints to the gmx.top file"
# Usage: python amber_to_gmx-add_restraint.py [system] (0 for Convert AMBER to GROMACS; 1 Add position restraint and Generate position restraint file)
# Required files:
#           (1) Amber files: complex.inpcrd, complex.prmtop (for mode 0)
#           (2) GROMACS file: gmx.top (for mode 1)
# Author: 1615326468@qq.com
# Released: 2025-03-18
# Updata record: 2025-03-21: Generate position restraint file and Unified work path




import os
import sys
import logging
import re
import parmed as pmd
import subprocess

# 固定工作目录
work_path = "system1/parameter/PZY"
os.makedirs(work_path, exist_ok=True)

# 设置日志等级为 DEBUG
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")


def amber_to_gmx(prmtop_file, inpcrd_file):
    top_file = os.path.join(work_path, "gmx.top")
    gro_file = os.path.join(work_path, "gmx.gro")

    if not os.path.exists(prmtop_file) or not os.path.exists(inpcrd_file):
        logging.error("AMBER input files missing.")
        sys.exit(1)

    try:
        amber = pmd.load_file(prmtop_file, inpcrd_file)
        amber.save(top_file, format="gromacs")
        amber.save(gro_file, format="gro")
        logging.info(f"Converted: {top_file}, {gro_file}")
    except Exception as e:
        logging.exception("AMBER to GROMACS conversion failed")
        sys.exit(1)


def position_restraint():
    top_file = os.path.join(work_path, "gmx.top")

    if not os.path.exists(top_file):
        logging.info("gmx.top not found. Attempting auto-conversion...")
        default_prmtop = "complex.prmtop"
        default_inpcrd = "complex.inpcrd"
        if not os.path.exists(default_prmtop) or not os.path.exists(default_inpcrd):
            logging.error("Default AMBER files missing.")
            sys.exit(1)
        amber_to_gmx(default_prmtop, default_inpcrd)

    posres_protein = '; Include Position restraint file\n#ifdef  POSRES\n#include "posre1.itp"\n#endif\n\n'
    posres_mol = '; Include Position restraint file\n#ifdef  POSRES\n#include "posre2.itp"\n#endif\n\n'

    with open(top_file, "r") as f:
        lines = f.readlines()

    modified = False
    found_protein = False
    found_ion = False

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if re.match(r'^\[\s*moleculetype\s*\]', line, re.IGNORECASE):
            if i + 2 < len(lines):
                line1 = lines[i+1].strip()
                line2 = lines[i+2].strip()

                if line1.split()[0] == "MOL" or line2.split()[0] == "MOL":
                    if not lines[i-1].strip() == posres_protein.strip():
                        lines.insert(i, posres_protein)
                        found_protein = True
                        modified = True
                        logging.info("Added position restraint to protein.")

                if line1.split()[0] in ["Na+", "Cl-"] or line2.split()[0] in ["Na+", "Cl-"]:
                    if not lines[i-1].strip() == posres_mol.strip():
                        lines.insert(i, posres_mol)
                        found_ion = True
                        modified = True
                        logging.info("Added position restraint to small molecule.")
        i += 1

    if modified:
        with open(top_file, "w") as f:
            f.writelines(lines)
        logging.info(f"Updated: {top_file}")
    else:
        logging.info("No restraints added.")


def generate_position_restraint():
    """Generate posre1.itp (Protein) and posre2.itp (MOL) based on atom counts."""
    gro_file = os.path.join(work_path, "gmx.gro")
    output_itp = os.path.join(work_path, "posre1.itp")
    mol_output_itp = os.path.join(work_path, "posre2.itp")
    mol_atom_count = None

    # Step 1: 查找 Protein 和 MOL 的 group index + atom count
    try:
        process = subprocess.Popen(
            ["gmx_mpi", "genrestr", "-f", gro_file, "-o", os.devnull],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(input="\n")
        output = stdout + stderr

        protein_group = None
        for line in output.splitlines():
            if "Protein" in line and "Group" in line:
                match = re.search(r"Group\s+(\d+)\s+\(\s*Protein", line)
                if match:
                    protein_group = match.group(1)
                    logging.debug(f"Detected Protein group index: {protein_group}")

            if "MOL" in line and "Group" in line:
                match = re.search(r"MOL\)\s+has\s+(\d+)\s+elements", line)
                if match:
                    mol_atom_count = int(match.group(1))
                    logging.debug(f"Detected MOL atom count: {mol_atom_count}")

        if not protein_group:
            logging.warning("Protein group not found, defaulting to 1.")
            protein_group = "1"

    except Exception as e:
        logging.error(f"Failed to parse group info: {e}")
        protein_group = "1"

    # Step 2: 生成 posre1.itp for Protein
    try:
        subprocess.run(
            ["gmx_mpi", "genrestr", "-f", gro_file, "-o", output_itp],
            input=f"{protein_group}\n",
            text=True,
            check=True
        )
        logging.info(f"posre1.itp generated: {output_itp}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to generate posre1.itp: {e}")
        return

    # Step 3: 截取前 N+4 行生成 posre2.itp for MOL
    if mol_atom_count is not None:
        try:
            with open(output_itp, "r") as f:
                lines = f.readlines()

            logging.debug(f"Total lines in posre1.itp: {len(lines)}")
            mol_lines = lines[:mol_atom_count + 4]
            with open(mol_output_itp, "w") as f:
                f.writelines(mol_lines)

            logging.info(f"posre2.itp (small molecule restraints) written: {mol_output_itp}")
            logging.debug(f"Written lines to posre2.itp: {len(mol_lines)}")
        except Exception as e:
            logging.error(f"Failed to generate posre2.itp: {e}")
    else:
        logging.warning("MOL atom count not found; posre2.itp not generated.")


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ["0", "1"]:
        logging.error("Usage:")
        logging.error("  python amber_to_gmx-add_restraint_debug.py 0 <prmtop> <inpcrd>")
        logging.error("  python amber_to_gmx-add_restraint_debug.py 1")
        sys.exit(1)

    mode = sys.argv[1]

    if mode == "0":
        if len(sys.argv) != 4:
            logging.error("Missing arguments: prmtop and inpcrd")
            sys.exit(1)
        prmtop_file = sys.argv[2]
        inpcrd_file = sys.argv[3]
        amber_to_gmx(prmtop_file, inpcrd_file)

    elif mode == "1":
        position_restraint()
        generate_position_restraint()


if __name__ == "__main__":
    main()
