#!/usr/bin/env python
"""
分子动力学预平衡自动化脚本
作者：Chaoyue Xia
更新日期：2025-03-04
功能描述：
本脚本用于自动化分子动力学（MD）模拟流程，主要功能包括：
- 多GPU任务调度与负载均衡
- 自动化执行能量最小化（EM）、NVT/NPT平衡阶段
- 支持时间步长（dt）多阶段调整（0.5ps, 1ps, 2ps）
- 错误重试机制（默认3次）
- 任务超时监控与自动恢复
- 详细的日志记录与进度追踪
目录结构要求
project_root/
├── pre_equ.py              # 主脚本
├── system1/               # 体系目录
│   ├── gmx.gro            # 结构文件
│   ├── gmx.top            # 拓扑文件
│   └── mdp/               # 参数文件
│       ├── em.mdp
│       ├── nvt.mdp
│       └── npt.mdp
├── system2/
└── ...
"""

import re
import os
import logging
import time
import shutil
import subprocess
from multiprocessing import Pool, Manager
from datetime import datetime

# 全局配置
CONFIG = {
    'GPU_DEVICES': [0, 1, 2, 3],          # 可用GPU列表
    'MAX_RETRIES': 3,               # 最大重试次数
    'LOG_LEVEL': logging.INFO,      # 日志级别
    'TIME_STEPS': [0.0005, 0.001, 0.002],  # 时间步长 (ps)
    'CHECK_INTERVAL': 300,          # 负载检查间隔(秒)
    'TASK_TIMEOUT': 3600            # 任务超时时间(秒)
}

class TaskManager:
    """任务调度管理器"""
    def __init__(self):
        manager = Manager()
        self.lock = manager.Lock()
        self.task_queue = manager.Queue()
        self.gpu_pool = manager.list(CONFIG['GPU_DEVICES'])
        self.running_tasks = manager.dict()

    def add_system(self, system_dir):
        """添加体系到任务队列"""
        priority = self._calculate_priority(system_dir)
        with self.lock:
            self.task_queue.put((priority, system_dir))
            
    def _calculate_priority(self, system_dir):
        """基于体系大小计算优先级"""
        gro_file = os.path.join(system_dir, 'gmx.gro')
        top_file = os.path.join(system_dir, 'gmx.top')
        return -(os.path.getsize(gro_file) + os.path.getsize(top_file))

    def get_next_task(self):
        """获取下一个任务"""
        with self.lock:
            if not self.task_queue.empty():
                return self.task_queue.get()[1]
            return None

    def assign_gpu(self):
        """分配可用GPU"""
        with self.lock:
            if len(self.gpu_pool) > 0:
                return self.gpu_pool.pop(0)
            return None

    def release_gpu(self, gpu_id):
        """释放GPU资源"""
        with self.lock:
            if gpu_id not in self.gpu_pool:
                self.gpu_pool.append(gpu_id)

    def monitor_load(self):
        """负载监控守护进程"""
        while True:
            time.sleep(CONFIG['CHECK_INTERVAL'])
            with self.lock:
                for gpu in list(self.running_tasks.keys()):
                    start_time, system_dir = self.running_tasks[gpu]
                    if time.time() - start_time > CONFIG['TASK_TIMEOUT']:
                        logging.error(f"任务超时: {system_dir} on GPU{gpu}")
                        self.release_gpu(gpu)
                        del self.running_tasks[gpu]
                        self.add_system(system_dir)

class MDExecutor:
    """分子动力学流程执行器"""
    def __init__(self, system_dir, gpu_id):
        self.system_dir = os.path.abspath(system_dir)
        self.gpu_id = gpu_id
        self.logger = self._init_logger()
        os.environ['CUDA_VISIBLE_DEVICES'] = str(gpu_id)

    def _init_logger(self):
        """初始化日志系统"""
        logger = logging.getLogger(os.path.basename(self.system_dir))
        logger.setLevel(CONFIG['LOG_LEVEL'])
        
        # 文件日志
        log_file = os.path.join(self.system_dir, 'simulation.log')
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(
            '[%(asctime)s] %(levelname)s - %(message)s'))
        
        # 控制台日志
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            f'%(name)s [GPU{self.gpu_id}] - %(levelname)s: %(message)s'))
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        return logger

    def run_command(self, command, work_dir):
        """执行命令并记录日志"""
        self.logger.info(f"执行命令: {command}")
        try:
            result = subprocess.run(command, shell=True, check=True,
                                  cwd=work_dir, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, timeout=CONFIG['TASK_TIMEOUT'])
            self.logger.debug(f"命令输出:\n{result.stdout.decode()}")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"命令失败: {e.stderr.decode()}")
            return False
        except Exception as e:
            self.logger.error(f"执行错误: {str(e)}")
            return False

    def modify_mdp(self, mdp_type, cycle=0):
        """修改MDP文件时间步长"""
        src_mdp = os.path.join(self.system_dir, 'mdp', f'{mdp_type}.mdp')
        
        # 生成目录后缀
        dir_suffix = str(cycle) if cycle > 0 else ''
        dest_dir = os.path.join(self.system_dir, f'{mdp_type}{dir_suffix}')
        os.makedirs(dest_dir, exist_ok=True)
        
        # 设置时间步长
        if mdp_type == 'em':
            dt = CONFIG['TIME_STEPS'][0]
        else:
            dt = CONFIG['TIME_STEPS'][cycle-1] if cycle > 0 else CONFIG['TIME_STEPS'][0]
        
        dest_mdp = os.path.join(dest_dir, f'{mdp_type}.mdp')
        shutil.copy(src_mdp, dest_mdp)
        
        # 修改dt参数
        with open(dest_mdp, 'r') as f:
            content = f.read()
        content = re.sub(r'dt\s*=\s*\d+\.?\d*', f'dt = {dt}', content)
        
        with open(dest_mdp, 'w') as f:
            f.write(content)
        
        return dest_mdp

    def run_em(self):
        """能量最小化流程"""
        em_dir = os.path.join(self.system_dir, 'em')
        os.makedirs(em_dir, exist_ok=True)

        cmd = (f"gmx_mpi grompp -f {self.modify_mdp('em')} "  # 使用默认cycle=0
               f"-c {os.path.join(self.system_dir, 'gmx.gro')} "
               f"-r {os.path.join(self.system_dir, 'gmx.gro')} "
               f"-p {os.path.join(self.system_dir, 'gmx.top')} "
               f"-o {os.path.join(em_dir, 'em.tpr')}")

        if not self.run_command(cmd, em_dir):
            return False

        return self.run_command(
            f"gmx_mpi mdrun -v -deffnm {os.path.join(em_dir, 'em')}",
            em_dir
        )

    def run_nvt(self, cycle):
        """NVT平衡"""
        stage_dir = os.path.join(self.system_dir, f'nvt{cycle}')
        prev_dir = os.path.join(self.system_dir, 'em') if cycle == 1 else os.path.join(self.system_dir, f'npt{cycle-1}')
        
        # 生成正确的mdp路径
        self.modify_mdp('nvt', cycle)
        
        cmd = (f"gmx_mpi grompp -f {os.path.join(stage_dir, 'nvt.mdp')} "
               f"-c {os.path.join(prev_dir, f'em.gro' if cycle == 1 else f'npt{cycle-1}.gro')} "
               f"-r {os.path.join(prev_dir, f'em.gro' if cycle == 1 else f'npt{cycle-1}.gro')} "
               f"-p {os.path.join(self.system_dir, 'gmx.top')} "
               f"-o {os.path.join(stage_dir, f'nvt{cycle}.tpr')}")
        
        return self.run_command(cmd, stage_dir) and \
               self.run_command(f"gmx_mpi mdrun -v -deffnm {os.path.join(stage_dir, f'nvt{cycle}')}", stage_dir)

    def run_npt(self, cycle):
        """NPT平衡"""
        stage_dir = os.path.join(self.system_dir, f'npt{cycle}')
        prev_dir = os.path.join(self.system_dir, f'nvt{cycle}')
        
        # 生成正确的mdp路径
        self.modify_mdp('npt', cycle)
        
        cmd = (f"gmx_mpi grompp -f {os.path.join(stage_dir, 'npt.mdp')} "
               f"-c {os.path.join(prev_dir, f'nvt{cycle}.gro')} "
               f"-r {os.path.join(prev_dir, f'nvt{cycle}.gro')} "
               f"-p {os.path.join(self.system_dir, 'gmx.top')} "
               f"-o {os.path.join(stage_dir, f'npt{cycle}.tpr')}")
        
        return self.run_command(cmd, stage_dir) and \
               self.run_command(f"gmx_mpi mdrun -v -deffnm {os.path.join(stage_dir, f'npt{cycle}')}", stage_dir)

    def execute(self):
        """执行完整流程"""
        try:
            self.logger.info("开始处理体系")
            
            # 能量最小化
            if not self.retry_command(self.run_em, '能量最小化'):
                return False
                
            # 三轮NVT/NPT循环
            for cycle in range(1, 4):
                if not self.retry_command(
                    lambda: self.run_nvt(cycle), f'NVT循环{cycle}'
                ) or not self.retry_command(
                    lambda: self.run_npt(cycle), f'NPT循环{cycle}'
                ):
                    return False
            
            self.logger.info("全部流程完成")
            return True
            
        except Exception as e:
            self.logger.error(f"流程异常终止: {str(e)}")
            return False

    def retry_command(self, func, desc, max_retries=CONFIG['MAX_RETRIES']):
        """带重试的执行方法"""
        for attempt in range(1, max_retries+1):
            if func():
                return True
            self.logger.warning(f"{desc} 第{attempt}次重试...")
        self.logger.error(f"{desc} 超过最大重试次数")
        return False

def worker(task_manager):
    """工作进程函数"""
    while True:
        system_dir = task_manager.get_next_task()
        if not system_dir:
            time.sleep(10)
            continue
            
        gpu_id = task_manager.assign_gpu()
        if gpu_id is None:
            task_manager.add_system(system_dir)
            time.sleep(5)
            continue
        
        try:
            # 记录任务开始
            with task_manager.lock:
                task_manager.running_tasks[gpu_id] = (time.time(), system_dir)
            
            # 执行任务
            executor = MDExecutor(system_dir, gpu_id)
            success = executor.execute()
            
            # 处理结果
            if not success:
                logging.error(f"体系处理失败: {system_dir}")
            
        finally:
            # 释放资源
            with task_manager.lock:
                if gpu_id in task_manager.running_tasks:
                    del task_manager.running_tasks[gpu_id]
                task_manager.release_gpu(gpu_id)

def main():
    # 初始化日志
    logging.basicConfig(
        level=CONFIG['LOG_LEVEL'],
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler('master.log'),
            logging.StreamHandler()
        ]
    )
    
    # 发现所有体系
    systems = [d for d in os.listdir() 
              if os.path.isdir(d) and 
              os.path.exists(os.path.join(d, 'gmx.gro')) and
              os.path.exists(os.path.join(d, 'mdp', 'em.mdp'))]
    
    if not systems:
        logging.error("未找到任何有效体系!")
        return
    
    # 初始化任务管理器
    task_manager = TaskManager()
    for sys in systems:
        task_manager.add_system(sys)
    
    # 启动监控进程
    import threading
    monitor_thread = threading.Thread(target=task_manager.monitor_load, daemon=True)
    monitor_thread.start()
    
    # 创建工作进程池
    with Pool(processes=len(CONFIG['GPU_DEVICES'])) as pool:
        for _ in range(len(CONFIG['GPU_DEVICES'])):
            pool.apply_async(worker, (task_manager,))
        pool.close()
        pool.join()

if __name__ == "__main__":
    main()