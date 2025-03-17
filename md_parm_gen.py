# Function: Generate Amber parameter files using tleap
# Usage: python md_parm_gen.py [system] (0 for protein-only; 1 for complex)
# Required files:
#           (1) Ligand parameter files: lig.prep and lig.frcmod (for mode 1)
#           (2) Ligand structure file: lig.pdb (for mode 1)
#           (3) Protein structure file: pro.pdb (modes 0 and 1)
# Author: zhouzhaoyin@simm.ac.cn
# Released: 2025-02-26
# Updata record: 
# 2025-03-17: Unified work path

import os
import sys
import subprocess
import re

# Define fixed output directory (relative path: system1/parameters)
OUTPUT_DIR = os.path.join("system1", "parameters")
os.makedirs(OUTPUT_DIR, exist_ok=True)

def run_tleap(input_file):
    """Execute tleap in the specified output directory and capture its output.
    
    All generated files (e.g., leap.log) will be created in OUTPUT_DIR.
    """
    try:
        subprocess.run(["tleap", "-f", input_file],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       cwd=OUTPUT_DIR)
    except subprocess.CalledProcessError as e:
        print(f"tleap execution failed: {e}")
        sys.exit(1)

def parse_charge_from_log(log_file):
    """Extract the system charge from leap.log.
    
    This function searches for a line formatted as:
        Total unperturbed charge:  <value>
    and returns the extracted charge as a float.
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
        print("Error: Failed to parse system charge from leap.log.")
        sys.exit(1)
    return charge

def prepare_protein():
    """Process a protein-only system:
    
    1. Generate a test tleap input script to calculate the protein charge.
    2. Create a full tleap input script that:
       - Loads the protein structure (../system1.pdb)
       - Saves the dry parameters (pro.prmtop, pro.inpcrd, pro-dry.pdb)
       - Solvates the system using a 10 Å OPC water box
       - Adds ions for charge neutralization (Cl- for positive charge, Na+ for negative charge)
       - Saves the solvated parameters (pro-sol.* files)
       
    All generated files are saved in OUTPUT_DIR.
    """
    # Generate a test script for charge calculation.
    # Note: The working directory is OUTPUT_DIR, so the protein PDB file path is adjusted.
    test_file = os.path.join(OUTPUT_DIR, "tleap_protein_test.in")
    with open(test_file, "w") as f:
        f.write(
            "source leaprc.protein.ff19SB\n"
            "source leaprc.water.opc\n\n"
            "pro = loadpdb ../system1.pdb\n"  # Adjusted path to the protein PDB file
            "charge pro\n"
            "quit\n"
        )
    print("Running tleap for protein charge test...")
    run_tleap("tleap_protein_test.in")  # File name is relative to OUTPUT_DIR
    charge = parse_charge_from_log(os.path.join(OUTPUT_DIR, "leap.log"))
    print(f"Detected protein system charge: {charge}")

    # Determine ion type and count based on the calculated charge.
    ion = None
    nion = 0
    if charge > 0:
        ion = "Cl-"
        nion = int(round(charge))
    elif charge < 0:
        ion = "Na+"
        nion = int(round(-charge))
    if ion and nion > 0:
        print(f"Adding {nion} {ion} ions to neutralize the system.")
    else:
        print("System is neutral - no ions required.")

    # Generate the full tleap script for processing the protein system.
    full_file = os.path.join(OUTPUT_DIR, "tleap_protein.in")
    with open(full_file, "w") as f:
        f.write(
            "source leaprc.protein.ff19SB\n"
            "source leaprc.water.opc\n\n"
            "pro = loadpdb ../system1.pdb\n\n"  # Adjusted path to the protein PDB file
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

    print("Processing protein system (solvation and ion addition)...")
    run_tleap("tleap_protein.in")
    print("Protein system processing completed. Generated files in:", OUTPUT_DIR)
    print("  Dry topology: pro.prmtop")
    print("  Dry coordinates: pro.inpcrd")
    print("  Dry structure: pro-dry.pdb")
    print("  Solvated topology: pro-sol.prmtop")
    print("  Solvated coordinates: pro-sol.inpcrd")
    print("  Solvated structure: pro-sol.pdb")

def prepare_complex():
    """Process a protein-ligand complex system:
    
    1. Generate a test tleap input script to calculate the complex system charge.
    2. Create a full tleap input script that:
       - Loads protein and ligand parameters.
       - Saves individual components and the combined system.
       - Solvates the complex using a 10 Å OPC water box.
       - Adds ions for charge neutralization.
       - Saves the final parameter files.
       
    All generated files are saved in OUTPUT_DIR.
    """
    # Generate a test script for charge calculation of the complex.
    test_file = os.path.join(OUTPUT_DIR, "tleap_complex_test.in")
    with open(test_file, "w") as f:
        f.write(
            "source leaprc.protein.ff19SB\n"
            "source leaprc.gaff2\n"
            "source leaprc.water.opc\n\n"
            "loadamberparams ../ligprep/lig.frcmod\n"    # Adjusted path to the ligand frcmod file
            "loadamberprep ../ligprep/lig.prep\n\n"       # Adjusted path to the ligand prep file
            "mol = loadpdb ../ligprep/LIG.PDB\n"            # Adjusted path to the ligand PDB file
            "pro = loadpdb ../system1.pdb\n"                # Adjusted path to the protein PDB file
            "com = combine {pro mol}\n\n"
            "charge com\n"
            "quit\n"
        )
    print("Running tleap for complex charge test...")
    run_tleap("tleap_complex_test.in")
    charge = parse_charge_from_log(os.path.join(OUTPUT_DIR, "leap.log"))
    print(f"Detected complex system charge: {charge}")

    # Determine ion type and count based on the calculated charge.
    ion = None
    nion = 0
    if charge > 0:
        ion = "Cl-"
        nion = int(round(charge))
    elif charge < 0:
        ion = "Na+"
        nion = int(round(-charge))
    if ion and nion > 0:
        print(f"Adding {nion} {ion} ions for neutralization.")
    else:
        print("Complex system is neutral - no ions required.")

    # Generate the full tleap script for processing the complex system.
    full_file = os.path.join(OUTPUT_DIR, "tleap_complex.in")
    with open(full_file, "w") as f:
        f.write(
            "source leaprc.protein.ff19SB\n"
            "source leaprc.gaff2\n"
            "source leaprc.water.opc\n\n"
            "loadamberparams ../ligprep/lig.frcmod\n"    # Adjusted path to the ligand frcmod file
            "loadamberprep ../ligprep/lig.prep\n\n"       # Adjusted path to the ligand prep file
            "mol = loadpdb ../ligprep/LIG.PDB\n"            # Adjusted path to the ligand PDB file
            "pro = loadpdb ../system1.pdb\n"                # Adjusted path to the protein PDB file
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
    print("Processing complex system (solvation and ion addition)...")
    run_tleap("tleap_complex.in")
    print("Complex system processing completed. Generated files in:", OUTPUT_DIR)
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

def main():
    """Main execution based on the command line argument:
    
    0: Protein-only system
    1: Protein-ligand complex system
    """
    if len(sys.argv) != 2 or sys.argv[1] not in ["0", "1"]:
        print("Usage: python md_parm_gen.py 0   # Protein-only")
        print("       python md_parm_gen.py 1   # Protein-ligand complex")
        sys.exit(1)

    mode = sys.argv[1]
    if mode == "0":
        prepare_protein()
    elif mode == "1":
        prepare_complex()

if __name__ == "__main__":
    main()
