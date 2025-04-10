# Molecular Dynamics Workflow Automation - README

## Overview
This automated workflow handles the complete preparation process for molecular dynamics simulations, including ligand parameterization, system setup, and pre-equilibration. The `total_control.py` script serves as the master controller for the entire pipeline.

## System Requirements

## Directory Structure
The workflow expects the following structure:
```
project_root/
├── total_control.py
├── lig_parameter_cal.py
├── lig_resp_cal.py
├── atom_name_check.py
├── md_parm_gen.py
├── amber_to_gmx-add_restraint.py
├── pre_equ.py
├── system1/          # System folder 1
├── system2/          # System folder 2
│   ├── system2.sdf   # Original Ligand File
│   ├── system1.pdb   # Initial Protein
│   ├── ligprep/      # Auto-created for ligand prep files
│   ├── parameters/   # Auto-created for parameter files
│   └── mdp/          # Users need to prepare the required parameter files in advance
└── ...               # Additional system folders
```

## Quick Start
1. Place your system folders (named `system*`) in the project root
2. For each system, place your input files:
   - Protein structure file (`.pdb`)
   - Ligand structure file (`.sdf`) if working with complexes
3. Run the master control script:
   ```bash
   python total_control.py <0|1>
   ```
   Where:
   - `0` for protein-only systems
   - `1` for protein-ligand complex systems

## Workflow Steps
The complete workflow executes these steps in order:

1. **Ligand Parameter Calculation** (`lig_parameter_cal.py`)
   - Processes all .sdf files in system directories
   - Generates initial ligand parameters
   - Submits Gaussian jobs in batch

2. **RESP Charge Calculation** (`lig_resp_cal.py`)
   - Charge calculation
   - Parameter generation

3. **Atom Name Validation** (`atom_name_check.py`)
   - Ligand atom name check

4. **MD Parameter Generation** (`md_parm_gen.py`)
   - Generates amber field parameters for the system
   - Automatically identifying protein or complex systems （depends on whether all files for the ligand exist）

5. **AMBER to GROMACS Conversion** (`amber_to_gmx-add_restraint.py`)
   - Converts parameters to GROMACS format
   - Adds necessary restraints

6. **Pre-Equilibration Setup** (`pre_equ.py`)
   - Prepares files for system equilibration
   - Generates necessary input files for MD runs

## Running Individual Components
Each step can be run independently if needed:

### 1. Ligand Parameter Calculation
```bash
python lig_parameter_cal.py -i <input_directory> -t <file_type>
# Processes files and Submits Gaussian jobs
python lig_parameter_cal.py -c -i <input_directory>
# Monitors Gaussian jobs

# Input file:
  Ligand structure file: XXX.sdf/mol/pdb
  We need at least one folder starting with "system" in the script working path, which contains the SDF, MOL, or PDB file (Ligand structure file).
  Gaussian jobs can be submitted using the first command, and the terminal will display the PID of each submitted job. After submission, the second command can be used to monitor the status of these jobs.
  If any jobs fail, we can check the error messages and re-run the first command. It will automatically resubmit the corresponding Gaussian .gjf files that do not have associated .log files.
 
# Output file:
In the "ligprep" folder, you will get:
  Guassian input file: XXX.gjf
  Guassian output file: XXX.log
```

### 2. RESP Charge Calculation
```bash
python script_name.py -i <input_directory>

# Input file:
  Guassian output file: XXX.log (a successful job ends with "Normal termination" at the end of the file)

# Output file:
   (1) ligand strcture file: lig.pdb
   (2) ligand parameter file: lig.prep and lig.frcmod
```

### 3. Atom Name Validation
```bash
python atom_name_check.py

# Input file:
  Ligand structure file: XXX.sdf
  The file generated in the previous step:NEWPDB.PDB
  The file generated in the previous step contains the atomic mapping relationships：ATOMTYPE.INF

# Output files：
  The file containing the correct atomic coordinate information:LIG.PDB
```

### 4. MD Parameter Generation
```bash
python md_parm_gen.py
# Input file:
We need at least one folder starting with "system" in the script working path, which contains the pdb file (Receptor structure file).
If no 'ligprep' folder detected or necessary files missing, treat as apo system.
For complex system, we need the "ligprep" folder, which contains the following files：
          (1) ligand strcture file: lig.pdb
          (2) ligand parameter file: lig.prep and lig.frcmod

# Output file:
For apo system, you will get:
  Dry topology: pro.prmtop
  Dry coordinates: pro.inpcrd
  Dry structure: pro-dry.pdb
  Solvated topology: pro-sol.prmtop
  Solvated coordinates: pro-sol.inpcrd
  Solvated structure: pro-sol.pdb

For complex system, you will get:
  Protein topology: pro.prmtop
  Protein coordinates: pro.inpcrd
  Ligand topology: lig.prmtop
  Ligand coordinates: lig.inpcrd
  Dry complex structure: com-dry.pdb
  Native complex topology: native.prmtop
  Native coordinates: native.inpcrd
  Solvated topology: complex.prmtop
  Solvated coordinates: complex.inpcrd
  Solvated structure: com.pdb
```

### 5. AMBER to GROMACS Conversion
```bash
python amber_to_gmx-add_restraint.py [system] (0 for Convert AMBER to GROMACS; 1 Add position restraint and Generate position restraint file)
```

### 6. Pre-Equilibration Setup
```bash
python pre_equ.py

# Required Files
Before running the script, ensure that the necessary input files are properly placed in the correct directories.
1. MD Parameter Files (MDP)
The required .mdp parameter files must be sourced from:
example/pre-equ/system/mdp
These files contain essential settings for the equilibration process.
2. Input Structure and Topology Files
Each system must have the following files stored in the parameters directory:
gmx.top: The topology file describing the molecular system.
gmx.gro: The initial coordinate file for the system.
.itp: The position restraints file to stabilize the system during equilibration.
```

## Input File Requirements
- **Protein files**: PDB format
- **Ligand files**: SDF format (for complexes)
- Ensure all input files are placed in their respective system folders before running

## Output Files
The workflow generates:
- Ligand parameter files in `ligprep/`
- Force field parameters in `parameters/`
- MD configuration files in `mdp/`


## Troubleshooting
1. **No system directories found**:
   - Ensure your system folders are named `system*` and are in the project root

2. **Missing SDF files**:
   - For complex systems, each system folder must contain at least one `.sdf` file

3. **Script failures**:
   - Check the log output for specific error messages
   - Ensure all required software ( GROMACS) is properly installed

## Logging
The script generates detailed logs showing:
- Each step's execution status
- Any errors encountered
- Successful completion messages

## Best Practices
1. Always validate your input files before running the workflow
2. For new ligands, verify the RESP charges manually
3. Check the restraint files before proceeding with production runs
4. Monitor disk space as temporary files can be large

## Support
For issues or questions, please contact the authors

## Version
Release: 2025-03-30
