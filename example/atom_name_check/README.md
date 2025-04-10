### 输入：lig_parm-gen部分优化的结果，MD-automation/example/lig_parm-gen/system13/下三个文件
###              NEVPDB.PDB
###              ATOMTYPE.INF
###             systemX.sdf
### 此脚本的输出：LIG.PDB
### 此脚本的功能：处理每个ligprep文件夹下的NEWPDB.PDB文件，使用ATOMTYPE.INF文件索引，
###             将NEWPDB.PDB文件中的原子坐标与systemX.sdf文件中的原子坐标对齐，
###              对齐原子名称后生成的文件命名为LIG.PDB，分别储存在每一个ligprep文件夹中。
### 使用方法：将此脚本放在systemX文件夹下，python atom_name_check.py

