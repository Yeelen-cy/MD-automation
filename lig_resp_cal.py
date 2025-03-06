##
import os
import subprocess
import argparse
from lig_parameter_cal import Tools

##

"""
Usage: 
    python script_name.py -i <input_directory>

Arguments:
    -i: 根目录路径，表示你希望处理的文件夹路径。如果没有指定，将默认为当前目录。
  
Description:
    该脚本用于处理配体相关的数据，执行以下操作：
    1. 从指定的文件夹中提取 `.log` 文件。
    2. 使用 `antechamber` 和 `parmchk` 工具生成配体的 `.prep` 和 `.frcmod` 文件。
    3. 在处理完毕后，恢复最初的工作目录。

Author:
    hanzijian、luoruitong
    Date: 2025-02-21
"""


class ParaMeterInfo:

    def __init__(self, rootpath='./'):

        self.orgin_path = os.getcwd()
        self.rootpath = rootpath
        os.chdir(self.rootpath)


    def get_lig_information(self, filepath):
        """
        该方法用于获取配体信息，执行以下操作：
        1. 根据输入的文件路径获取相应的文件名和扩展名
        2. 执行 `antechamber` 命令来生成 prep 文件
        3. 执行 `parmchk` 命令来生成 frcmod 文件
        """

        folder, file = os.path.split(filepath)
        os.chdir(folder)
        log_file = os.path.splitext(filepath)[0] + '.log'
        prep_file = os.path.splitext(filepath)[0] + '.prep'
        frcmod_file = os.path.splitext(filepath)[0] + '.frcmod'

        command_antechamber = f'antechamber -i {log_file} -fi gout -o {prep_file} -fo prepi -c resp'
        command_parmchk = f'parmchk2 -i {prep_file} -f prepi -o {frcmod_file} -a y'

        try:
            subprocess.run(command_antechamber, text=True, stdout=subprocess.PIPE, check=True, shell=True)
            subprocess.run(command_parmchk, text=True, stdout=subprocess.PIPE, check=True, shell=True)
        except subprocess.CalledProcessError as e:
            print(f"Error reading {log_file}: {e}")


    def get_log_files(self, filepath=None):
        """
        该方法用于获取所有 `log` 文件并调用 `get_lig_information` 处理每一个文件。
        """
        # 如果未指定文件夹路径，则默认为当前文件夹
        if filepath == None:
            filepath = './'
        # 如果是文件夹路径，则获取该文件夹下的所有 `.log` 文件
        if os.path.isdir(filepath):
            log_list = Tools.get_files(root_filepath=filepath, filetype='log')
        # 否则，将输入路径当做单一的 log 文件
        else:
            log_list = [filepath]
        # 遍历每一个 log 文件，调用 get_lig_information 方法处理
        for log_file in log_list:
            self.get_lig_information(log_file)
        

    def __del__(self):

        os.chdir(self.orgin_path)


if __name__ == '__main__':
    paser = argparse.ArgumentParser()
    paser.add_argument('-i', type=str, default='./')
    args = paser.parse_args()
    myOniom = ParaMeterInfo(args.i)
    myOniom.get_log_files(args.i)


