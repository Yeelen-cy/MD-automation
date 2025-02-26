# Function: Generate Amber parameter files using tleap
# Usage: python md_parm_gen.py [system] (0 for protein-only; 1 for complex)
# Required files:
#           (1) Ligand parameter files: lig.prep and lig.frcmod (for mode 1)
#           (2) Ligand structure file: lig.pdb (for mode 1)
#           (3) Protein structure file: pro.pdb (modes 0 and 1)
# Author: zhouzhaoyin@simm.ac.cn
# Released: 2025-02-26

import os
import sys
import subprocess
import re

def run_tleap(input_file):
    """Execute tleap with specified input file and capture output.
    Generates leap.log upon completion.
    """
    try:
        subprocess.run(["tleap", "-f", input_file],
                       check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print(f"tleap execution failed: {e}")
        sys.exit(1)

def parse_charge_from_log(log_file):
    """Extract system charge from leap.log.
    Targets lines with format:
      > charge pro
      Total unperturbed charge:  -9.000000
      Total perturbed charge:    -9.000000
      > quit
    Returns the 'Total unperturbed charge' value.
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
    """Process protein-only system:
    1. Generate test script to calculate protein charge for ion neutralization
    2. Create full tleap script to:
       - Load protein structure (pro.pdb)
       - Save dry parameters (pro.prmtop, pro.inpcrd, pro-dry.pdb)
       - Solvate system (10Å OPC water box)
       - Add ions based on charge (Cl- for positive, Na+ for negative)
       - Save solvated parameters (pro-sol.* files)
    """
    # Generate test script for charge calculation
    test_file = "tleap_protein_test.in"
    with open(test_file, "w") as f:
        f.write(
            "source leaprc.protein.ff19SB\n"
            "source leaprc.water.opc\n\n"
            "pro = loadpdb pro.pdb\n"
            "charge pro\n"
            "quit\n"
        )
    print("Running tleap for protein charge test...")
    run_tleap(test_file)
    charge = parse_charge_from_log("leap.log")
    print(f"Detected protein system charge: {charge}")

    # Determine ion type and count
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

    # Generate full protein processing script
    full_file = "tleap_protein.in"
    with open(full_file, "w") as f:
        f.write(
            "source leaprc.protein.ff19SB\n"
            "source leaprc.water.opc\n\n"
            "pro = loadpdb pro.pdb\n\n"
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
    run_tleap(full_file)
    print("Protein system processing completed. Generated files:")
    print("  Dry topology: pro.prmtop")
    print("  Dry coordinates: pro.inpcrd")
    print("  Dry structure: pro-dry.pdb")
    print("  Solvated topology: pro-sol.prmtop")
    print("  Solvated coordinates: pro-sol.inpcrd")
    print("  Solvated structure: pro-sol.pdb")

def prepare_complex():
    """Process protein-ligand complex:
    1. Generate test script for complex charge calculation
    2. Create full tleap script to:
       - Load components (protein, ligand parameters)
       - Save individual components and combined system
       - Solvate complex (10Å OPC water box)
       - Add neutralizing ions
       - Save final parameters
    """
    # Charge test script
    test_file = "tleap_complex_test.in"
    with open(test_file, "w") as f:
        f.write(
            "source leaprc.protein.ff19SB\n"
            "source leaprc.gaff2\n"
            "source leaprc.water.opc\n\n"
            "loadamberparams lig.frcmod\n"
            "loadamberprep lig.prep\n\n"
            "mol = loadpdb lig.pdb\n"
            "pro = loadpdb pro.pdb\n"
            "com = combine {pro mol}\n\n"
            "charge com\n"
            "quit\n"
        )
    print("Running tleap for complex charge test...")
    run_tleap(test_file)
    charge = parse_charge_from_log("leap.log")
    print(f"Detected complex system charge: {charge}")

    # Ion neutralization
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

    # Full complex processing
    full_file = "tleap_complex.in"
    with open(full_file, "w") as f:
        f.write(
            "source leaprc.protein.ff19SB\n"
            "source leaprc.gaff2\n"
            "source leaprc.water.opc\n\n"
            "loadamberparams lig.frcmod\n"
            "loadamberprep lig.prep\n\n"
            "mol = loadpdb lig.pdb\n"
            "pro = loadpdb pro.pdb\n"
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
    run_tleap(full_file)
    print("Complex system processing completed. Generated files:")
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
    """Main execution based on command line argument:
    0: Protein-only system
    1: Protein-ligand complex
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
