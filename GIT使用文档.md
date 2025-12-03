# Git使用文档

## 一、Git基本概念

Git是一个分布式版本控制系统，用于跟踪文件的变化，协调多人协作开发。

### 核心概念
- **仓库(Repository)**: 包含代码和版本历史的目录
- **工作区(Working Directory)**: 当前编辑的文件目录
- **暂存区(Staging Area)**: 准备提交的文件集合
- **本地仓库(Local Repository)**: 存储在本地的版本历史
- **远程仓库(Remote Repository)**: 存储在服务器上的版本历史
- **分支(Branch)**: 独立的开发线
- **提交(Commit)**: 保存文件变化的快照
- **推送(Push)**: 将本地提交推送到远程仓库
- **拉取(Pull)**: 从远程仓库获取最新代码

## 二、Git安装

### Windows
1. 下载Git for Windows: https://git-scm.com/download/win
2. 运行安装程序，按照默认选项安装
3. 安装完成后，打开Git Bash或Command Prompt验证:
   ```bash
   git --version
   ```

### macOS
1. 使用Homebrew安装:
   ```bash
   brew install git
   ```
2. 或使用Xcode Command Line Tools:
   ```bash
   xcode-select --install
   ```

### Linux
1. Ubuntu/Debian:
   ```bash
   sudo apt-get update
   sudo apt-get install git
   ```
2. CentOS/Fedora:
   ```bash
   sudo yum install git
   ```

## 三、Git配置

### 1. 基本配置
```bash
# 配置用户名
git config --global user.name "Your Name"

# 配置邮箱
git config --global user.email "your.email@example.com"

# 配置默认编辑器
git config --global core.editor "vim"

# 配置差异比较工具
git config --global merge.tool "vimdiff"

# 查看配置
git config --list
```

### 2. SSH密钥配置(推荐用于私有库)
```bash
# 生成SSH密钥对
ssh-keygen -t rsa -b 4096 -C "your.email@example.com"

# 查看公钥
cat ~/.ssh/id_rsa.pub
```

将公钥添加到GitHub: Settings → SSH and GPG keys → New SSH key

## 四、仓库操作

### 1. 克隆远程仓库
```bash
# HTTPS方式
git clone https://github.com/用户名/仓库名.git

# SSH方式(推荐)
git clone git@github.com:用户名/仓库名.git

# 克隆到指定目录
git clone 仓库地址 目录名
```

### 2. 创建本地仓库
```bash
# 在当前目录初始化仓库
git init

# 在指定目录初始化仓库
git init 目录名
```

### 3. 查看仓库状态
```bash
git status
```

## 五、基本工作流程

### 1. 添加文件到暂存区
```bash
# 添加单个文件
git add 文件名

# 添加所有修改的文件
git add .

# 添加指定目录
git add 目录名/
```

### 2. 提交文件到本地仓库
```bash
# 提交暂存区的文件
git commit -m "提交信息"

# 提交所有修改的文件(跳过暂存区)
git commit -am "提交信息"

# 修改最后一次提交信息
git commit --amend -m "新的提交信息"
```

### 3. 推送本地提交到远程仓库
```bash
# 推送到默认远程分支
git push

# 推送到指定远程和分支
git push 远程名 分支名

# 第一次推送新分支
git push -u 远程名 分支名
```

### 4. 从远程仓库拉取代码
```bash
# 拉取最新代码并合并
git pull

# 仅拉取最新代码，不合并
git fetch
```

## 六、分支管理

### 1. 查看分支
```bash
# 查看本地分支
git branch

# 查看远程分支
git branch -r

# 查看所有分支
git branch -a
```

### 2. 创建和切换分支
```bash
# 创建新分支
git branch 分支名

# 创建并切换到新分支
git checkout -b 分支名

# 切换到已有分支
git checkout 分支名
```

### 3. 合并分支
```bash
# 切换到目标分支
git checkout 目标分支

# 合并源分支到目标分支
git merge 源分支
```

### 4. 删除分支
```bash
# 删除本地分支
git branch -d 分支名

# 强制删除本地分支
git branch -D 分支名

# 删除远程分支
git push 远程名 --delete 分支名
```

## 七、远程仓库管理

### 1. 查看远程仓库
```bash
# 查看远程仓库列表
git remote

# 查看远程仓库详细信息
git remote -v
```

### 2. 添加远程仓库
```bash
git remote add 远程名 仓库地址
```

### 3. 修改远程仓库URL
```bash
git remote set-url 远程名 新仓库地址
```

### 4. 删除远程仓库
```bash
git remote remove 远程名
```

## 八、版本回退

### 1. 查看提交历史
```bash
# 查看简洁提交历史
git log --oneline

# 查看详细提交历史
git log

# 查看带图形的提交历史
git log --graph --oneline
```

### 2. 回退到指定版本
```bash
# 回退到指定提交，保留工作区修改
git reset --soft 提交ID

# 回退到指定提交，重置暂存区但保留工作区
git reset --mixed 提交ID

# 回退到指定提交，重置工作区和暂存区
git reset --hard 提交ID
```

### 3. 撤销工作区修改
```bash
# 撤销单个文件修改
git checkout -- 文件名

# 撤销所有工作区修改
git checkout .
```

### 4. 撤销暂存区修改
```bash
# 撤销单个文件的暂存
git reset HEAD 文件名

# 撤销所有暂存
git reset HEAD
```

## 九、解决冲突

当多人修改同一文件的同一部分时，Git会产生冲突。解决步骤：

1. 查看冲突文件:
   ```bash
   git status
   ```

2. 打开冲突文件，手动解决冲突。冲突标记如下:
   ```
   <<<<<<< HEAD
   本地修改内容
   =======
   远程修改内容
   >>>>>>> 分支名
   ```

3. 解决冲突后，添加文件到暂存区:
   ```bash
   git add 冲突文件名
   ```

4. 提交解决冲突:
   ```bash
   git commit -m "解决冲突"
   ```

5. 推送解决后的代码:
   ```bash
   git push
   ```

## 十、私有库注意事项

### 1. 权限管理
- 确保只有授权人员可以访问私有库
- 在GitHub上设置仓库为私有
- 管理协作者权限：Settings → Manage access

### 2. 认证方式
- **HTTPS**: 需要输入用户名和密码(或个人访问令牌)
- **SSH**: 推荐使用SSH密钥认证，更安全方便

### 3. 个人访问令牌(PAT)
如果使用HTTPS方式访问GitHub私有库，需要使用个人访问令牌代替密码:

1. 在GitHub上生成PAT: Settings → Developer settings → Personal access tokens → Generate new token
2. 选择所需的权限(至少需要repo权限)
3. 生成后复制令牌，妥善保存
4. 在Git中使用PAT作为密码

## 十一、常用Git命令速查

| 命令 | 功能 |
|------|------|
| `git init` | 初始化仓库 |
| `git clone` | 克隆仓库 |
| `git status` | 查看状态 |
| `git add` | 添加到暂存区 |
| `git commit` | 提交到本地仓库 |
| `git push` | 推送到远程仓库 |
| `git pull` | 从远程仓库拉取 |
| `git branch` | 管理分支 |
| `git checkout` | 切换分支 |
| `git merge` | 合并分支 |
| `git log` | 查看提交历史 |
| `git reset` | 版本回退 |
| `git remote` | 管理远程仓库 |
| `git diff` | 查看文件差异 |

## 十二、Git工作流程示例

1. 克隆远程仓库:
   ```bash
   git clone git@github.com:tu-MOLO/Web_Cluster_Control_for_ESP_Hi.git
   ```

2. 创建并切换到新分支:
   ```bash
   git checkout -b feature/new-feature
   ```

3. 编辑文件并查看修改:
   ```bash
   git status
   git diff
   ```

4. 添加修改到暂存区:
   ```bash
   git add .
   ```

5. 提交修改到本地仓库:
   ```bash
   git commit -m "添加新功能"
   ```

6. 推送分支到远程仓库:
   ```bash
   git push -u origin feature/new-feature
   ```

7. 合并分支到主分支:
   ```bash
   git checkout main
   git pull origin main
   git merge feature/new-feature
   git push origin main
   ```

8. 删除本地分支:
   ```bash
   git branch -d feature/new-feature
   ```

9. 删除远程分支:
   ```bash
   git push origin --delete feature/new-feature
   ```

## 十三、参考资源

- Git官方文档: https://git-scm.com/doc
- GitHub帮助文档: https://docs.github.com/
- Git教程 - 廖雪峰: https://www.liaoxuefeng.com/wiki/896043488029600
- Git Cheat Sheet: https://education.github.com/git-cheat-sheet-education.pdf

---

希望这个文档能帮助您更好地使用Git进行版本控制和协作开发。如果有任何问题，请随时查阅官方文档或寻求帮助。