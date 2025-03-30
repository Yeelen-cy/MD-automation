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
│   └── mdp/          # Auto-created for MD parameter files
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

2. **RESP Charge Calculation** (`lig_resp_cal.py`)
   - Charge calculation
   - Parameter generation

3. **Atom Name Validation** (`atom_name_check.py`)
   - Ligand atom name check

4. **MD Parameter Generation** (`md_parm_gen.py`)
   - Generates amber field parameters for the system
   - Different handling for protein-only vs. complex systems

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
```

### 2. RESP Charge Calculation
```bash
python script_name.py -i <input_directory>
```

### 3. Atom Name Validation
```bash
python atom_name_check.py
```

### 4. MD Parameter Generation
```bash
python md_parm_gen.py [0|1]
# 0 for protein-only, 1 for complex
```

### 5. AMBER to GROMACS Conversion
```bash
python amber_to_gmx-add_restraint.py [system] (0 for Convert AMBER to GROMACS; 1 Add position restraint and Generate position restraint file)
```

### 6. Pre-Equilibration Setup
```bash
python pre_equ.py
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
