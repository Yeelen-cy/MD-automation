import os
import argparse
import subprocess

"""
Usage:
    python lig_parameter_cal.py -i <input_directory> -t <file_type>
    python lig_parameter_cal.py -c -i <input_directory>  

Arguments:
    -i  Input directory path (default is current directory './')
        The directory where the input files are located. You can specify the path to any directory.

    -t  File type to filter (default is 'sdf')
        The file extension to filter. For example, use 'gjf', 'sdf', or 'log'. The program will only process files with this extension.

    -c  Check log files for completion status.
        When this flag is provided, the script will scan .log files in the directory and check if they ended successfully.
        
Examples:
    1. Process all .sdf files in the current directory:
       python script.py -i ./ -t sdf

    2. Process all .gjf files in the '/path/to/dir' directory:
       python script.py -i /path/to/dir -t gjf

    3. Check .log files for normal termination:
       python script.py -c

Author:
    luoruitong、hanzijian
    Date: 2025-02-21
"""


class Tools:

    # 用于根据文件类型和过滤条件获取指定目录下的文件列表
    @staticmethod
    def get_files(root_filepath='./', filetype='sdf', file_filter=None):

        filetype = '.' + filetype
        file_path_list = []

        # 如果有文件过滤条件，使用过滤条件筛选文件
        if file_filter:
            if type(file_filter) != list:
                file_filter = [file_filter]
            for root, _, files in os.walk(root_filepath):
                for file in files:
                    if file.endswith(filetype):
                        flag = True
                        for filter in file_filter:
                            if filter not in file:
                                flag = False
                                break
                        if flag:
                            file_path_list.append(os.path.join(root, file))
        else:
            # 如果没有过滤条件，直接筛选指定类型的文件
            for root, _, files in os.walk(root_filepath):
                for file in files:
                    if file.endswith(filetype):
                        file_path_list.append(os.path.join(root, file))
        return file_path_list
    
    # 用于运行 antechamber 生成 .gjf 文件
    @staticmethod
    def run_antechamber(filepath, filetype='sdf'):

        folder, file = os.path.split(filepath)
        os.chdir(folder)

        # 生成输出的 .gjf 文件路径
        gjf_file = os.path.splitext(filepath)[0] + '.gjf'
        i_file = os.path.splitext(filepath)[0]+ '.' +filetype
        charged = Sdffiles.get_charged(filepath=filepath)


        # 构造 antechamber 命令
        command = f'antechamber -i {i_file} -fi {filetype} -o {gjf_file} -fo gcrt -at gaff2 -gn %nproc=4 -gm %mem=4GB -gk "#B3LYP/6-31G* em=gd3bj pop=MK iop(6/33=2,6/42=6) opt" -rn MOL -nc {charged}'
        try:
            result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)    # 执行命令
        except subprocess.CalledProcessError as e:
            print("Error:", e)
            return None
        return gjf_file

class Sdffiles:

    @staticmethod
    def get_charged(filepath):
        with open(filepath, 'r') as file:
            lines = file.readlines()
            for line in lines:
                if line.startswith("M  CHG"):
                    charged_info = line.split()[4]
                    return charged_info
            return "0"


class Logfiles:

    def __init__(self, filepath):

        self.root_filepath = os.getcwd()
        self.log_file_list = Tools.get_files(root_filepath=filepath,filetype='log')
    
    def check_logfiles(self):

        failed_files = []
        continued_files = []
        for log_file in self.log_file_list:
            try:
                with open(log_file, 'r') as file:
                    content = file.read()
                with open(log_file, 'r') as file:
                    last_line = file.readlines()[-1].strip()
                    if 'Error termination' in content:
                        failed_files.append(os.path.basename(log_file) + " failed")
                    elif not last_line.startswith("Normal termination"):
                        continued_files.append(os.path.basename(log_file) + " continued")
                        
            except Exception as e:
                print(f"Error reading {log_file}: {e}")

        if failed_files:
            print("\n".join(failed_files))
        if continued_files:
            print("\n".join(continued_files))
        else:
            print("All files succeed.")



class BatchRun:

    def __init__(self, filepath, filetype):

        self.root_filepath = os.getcwd()
        self.origin_file_list = Tools.get_files(root_filepath=filepath,filetype=filetype)
        self.log_file_list = [os.path.splitext(item)[0] for item in Tools.get_files(root_filepath=filepath,filetype='log')]
        self.origin_file_list_new = []
        self.filetype = filetype
        for item in self.origin_file_list:
            if os.path.splitext(item)[0] not in self.log_file_list:
                self.origin_file_list_new.append(item)
        self.origin_file_list = self.origin_file_list_new

    # 批量提交任务
    def run(self):

        for filepath in self.origin_file_list:
            gjf_file = Tools.run_antechamber(filepath, self.filetype)
            if not gjf_file or not os.path.exists(gjf_file):
                print(f"Skipping {filepath} due to antechamber failed.")
                continue
            folder, file = os.path.split(gjf_file)
            os.chdir(folder)
            # 提交 Gaussian 任务并获取 PID
            process = subprocess.Popen(f'nohup g16 {file} &', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            if process.pid:
                pid = process.pid  # 获取 PID 并去除换行符
                print(f"{file} submitted successfully with PID {pid}")

            os.chdir(self.root_filepath)  # 返回原目录


if __name__=='__main__':

    paser = argparse.ArgumentParser()
    paser.add_argument('-i', type=str, default='./')
    paser.add_argument('-t', type=str, default='sdf')
    paser.add_argument('-c', action='store_true')
    args = paser.parse_args()


    if args.c and args.i:
        checker = Logfiles(args.i)
        checker.check_logfiles()
    elif args.i and args.t:
            myobj = BatchRun(args.i, args.t)
            myobj.run()
    else:
        print("Error: Either specify '-i' and '-t' for processing, or use '-c' and '-i' for log checking.")





