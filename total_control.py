'''
Function: Master control script for automated molecular dynamics workflow
Usage: python total_control_3.py <0|1> (0 for protein-only, 1 for complex systems)
Author: Chaoyue Xia
Released: 2025-03-30

Description:
This script serves as the central controller for an end-to-end molecular dynamics preparation pipeline. It automatically:

1. Creates required subdirectories (ligprep, parameters, mdp) in each system folder
2. Processes ligand parameters through multiple calculation stages
3. Handles both protein-only and complex system types
4. Validates input files and provides detailed error logging
5. Executes the complete workflow:
   - Ligand parameter calculation (lig_parameter_cal.py)
   - RESP charge calculation (lig_resp_cal.py)
   - Atom name validation (atom_name_check.py)
   - MD parameter generation (md_parm_gen.py)
   - AMBER to GROMACS conversion with restraints (amber_to_gmx-add_restraint.py)
   - Pre-equilibration setup (pre_equ.py)
   
'''

import subprocess
import os
import sys
import logging
from glob import glob

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# 获取项目根目录
project_root = os.path.dirname(os.path.abspath(__file__))

def validate_arguments():
    if len(sys.argv) != 2 or sys.argv[1] not in ["0", "1"]:
        logging.error("Usage: python total_control.py <0|1>")
        sys.exit(1)
    return sys.argv[1]

def prepare_system_directories():
    """
    遍历每个系统目录（匹配 system*），在每个目录下创建所需的子文件夹：
    ligprep、parameters 和 mdp。如果文件夹已存在，则忽略。
    """
    system_dirs = glob(os.path.join(project_root, "system*"))
    if not system_dirs:
        logging.error("No system directories found in the project root.")
        sys.exit(1)
    for system_dir in system_dirs:
        for folder in ["ligprep", "parameters", "mdp"]:
            folder_path = os.path.join(system_dir, folder)
            if not os.path.exists(folder_path):
                os.makedirs(folder_path, exist_ok=True)
                logging.info(f"Created folder: {folder_path}")
            else:
                logging.info(f"Folder already exists: {folder_path}")

def run_script(script_name, args_list):
    script_path = os.path.join(project_root, script_name)
    # 检查脚本是否存在
    if not os.path.exists(script_path):
        logging.error(f"Script {script_name} not found at {script_path}")
        sys.exit(1)
    command = ["python", script_path] + args_list
    logging.info(f"Executing: {' '.join(command)}")
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        logging.error(f"Script {script_name} failed!\nStdout: {result.stdout}\nStderr: {result.stderr}")
        sys.exit(1)
    logging.info(f"{script_name} completed successfully.")

def run_workflow(system_type):
    # 步骤1：运行 lig_parameter_cal.py，处理所有系统中的 SDF 文件
    sdf_files = glob(os.path.join(project_root, "system*", "*.sdf"))
    if not sdf_files:
        logging.error("No SDF files found in system directories.")
        sys.exit(1)
    step1_args = ["-i"] + sdf_files + ["-t", "sdf"]
    run_script("lig_parameter_cal.py", step1_args)
    
    # 步骤2：运行 lig_resp_cal.py，处理所有系统中的 ligprep 目录
    ligprep_dirs = glob(os.path.join(project_root, "system*", "ligprep"))
    if not ligprep_dirs:
        logging.error("No ligprep directories found in system directories.")
        sys.exit(1)
    step2_args = ["-i"] + ligprep_dirs
    run_script("lig_resp_cal.py", step2_args)
    
    # 步骤3：运行 atom_name_check.py，无需额外参数
    run_script("atom_name_check.py", [])
    
    # 步骤4：运行 md_parm_gen.py，传入体系类型参数（0: protein-only; 1: complex）
    run_script("md_parm_gen.py", [system_type])
    
    # 步骤5：运行 amber_to_gmx-add_restraint.py，传入参数 "1"
    run_script("amber_to_gmx-add_restraint.py", ["1"])
    
    # 步骤6：运行 pre_equ.py，无需额外参数
    run_script("pre_equ.py", [])

if __name__ == "__main__":
    system_type = validate_arguments()
    # 预处理：为每个系统目录创建必要的子文件夹
    prepare_system_directories()
    try:
        run_workflow(system_type)
        logging.info("Workflow completed successfully!")
    except Exception as e:
        logging.critical(f"Critical error: {str(e)}")
        sys.exit(1)
