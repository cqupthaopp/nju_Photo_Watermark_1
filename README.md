# 图片水印工具

这是一个功能完善的图片水印工具，支持文本水印和图片水印，提供直观的图形界面，可在Ubuntu系统中编译出Windows系统的可执行文件。

## 功能特性

### 文件处理
- **导入图片**：支持单张图片拖拽或通过文件选择器导入，也支持批量导入多张图片或整个文件夹。
- **支持格式**：输入格式包括JPEG, PNG, BMP, TIFF等主流格式，输出格式可选择JPEG或PNG。
- **导出图片**：可指定输出文件夹，提供多种文件命名规则选项（保留原文件名、添加前缀、添加后缀）。
- **图片质量调整**：对于JPEG格式，提供图片质量（压缩率）调节滑块。

### 水印类型
- **文本水印**：支持自定义文本内容、字体、字号、粗体、斜体、颜色和透明度，可添加阴影效果。
- **图片水印**：支持从本地选择图片作为水印，支持带透明通道的PNG图片，可调整大小和透明度。

### 水印布局与样式
- **实时预览**：所有对水印的调整都在主预览窗口中实时显示效果。
- **位置设置**：提供九宫格布局预设位置，也支持通过鼠标拖拽调整水印位置。
- **边距控制**：可设置水印与图片边缘的距离。

### 配置管理
- **水印模板**：可将当前水印设置保存为模板，支持加载、管理和删除模板。
- **自动保存**：程序关闭时自动保存当前设置，下次启动时恢复。

## 安装依赖

### 在Ubuntu系统中

```bash
# 安装Python和pip
sudo apt-get update
sudo apt-get install -y python3 python3-pip

# 安装项目依赖
pip3 install -r requirements.txt
```

### 在Windows系统中

```bash
# 安装项目依赖
pip install -r requirements.txt
```

## 使用方法

### 运行源代码

```bash
python3 watermark_app.py
```

### 从Ubuntu构建Windows可执行文件

```bash
# 安装构建依赖（只需运行一次）
python3 build_windows.py --install-deps

# 构建Windows可执行文件
python3 build_windows.py

# 构建并创建便携版本
python3 build_windows.py --portable

# 清理构建文件
python3 build_windows.py --clean
```

## 项目文件说明

- `watermark_app.py`：主要的图形界面应用程序文件。
- `watermark_exif_date.py`：原始的命令行EXIF日期水印工具。
- `build_windows.py`：在Ubuntu中构建Windows可执行文件的脚本。
- `requirements.txt`：项目依赖列表。

## 使用指南

1. **添加图片**：通过"添加文件"或"添加文件夹"按钮，或者直接拖拽图片到程序窗口。
2. **选择水印类型**：选择文本水印或图片水印。
3. **设置水印参数**：根据需要调整水印的内容、样式、位置等参数。
4. **预览效果**：在预览窗口查看水印效果，可通过拖拽调整水印位置。
5. **导出图片**：点击"导出图片"按钮，选择输出目录，设置输出格式和命名规则。
6. **模板管理**：可将当前设置保存为模板，方便以后使用。

## 注意事项

- **文件安全**：为防止覆盖原图，导出时会提示是否导出到原文件夹。
- **性能考虑**：处理大量图片时，可能会消耗较多系统资源，请耐心等待。
- **字体支持**：程序使用系统已安装的字体，部分特殊字体可能无法正常显示。
- **透明度支持**：PNG格式支持透明通道，可用于创建透明水印效果。

## 构建说明

由于跨平台编译的复杂性，在Linux环境中直接构建Windows可执行文件存在挑战。经过测试，我们发现以下是最可靠的构建方法：

### Windows构建常见问题与解决方案

在Windows系统上构建时，您可能会遇到以下常见问题：

#### 1. 权限错误 (PermissionError: [WinError 5] 拒绝访问)

**问题描述**：构建过程中出现类似以下错误：
```
PermissionError: [WinError 5] 拒绝访问。: 'path\to\watermark_app.exe'
```

**解决方案**：
1. **确保程序未运行**：关闭所有正在运行的PhotoWatermarkTool实例
2. **以管理员身份运行**：右键点击命令提示符，选择"以管理员身份运行"
3. **清理构建文件**：手动删除`build`和`dist`文件夹，然后重新构建
4. **关闭安全软件**：某些安全软件可能会锁定正在构建的文件
5. **使用--distpath参数**：在构建命令中指定一个不同的输出目录
   ```bash
   pyinstaller --onefile --windowed --distpath output_folder watermark_app.py
   ```

### 推荐方法：在Windows系统上直接构建

**这是最简单、最可靠的方法**，适用于大多数用户：

1. 在Windows电脑上安装Python 3.8或更高版本（推荐3.10）
2. 安装项目依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 安装PyInstaller：
   ```bash
   pip install pyinstaller
   ```
4. 构建可执行文件：
   ```bash
   pyinstaller --onefile --windowed watermark_app.py
   ```
5. 构建成功后，Windows可执行文件(`.exe`)将位于`dist`目录中。

### 替代方法1：Ubuntu中使用Wine构建

如果您只能在Ubuntu环境中操作，可以尝试使用Wine构建Windows可执行文件：

1. 安装Wine和相关工具：
   ```bash
   sudo apt-get update && sudo apt-get install -y wine winetricks
   ```
2. 在Wine中安装Python（这是最关键的一步）：
   ```bash
   wine cmd
   # 在Wine命令提示符中执行以下命令
   powershell -Command Invoke-WebRequest -Uri https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe -OutFile python-installer.exe
   python-installer.exe /quiet InstallAllUsers=1 PrependPath=1
   ```
3. 关闭Wine命令提示符，回到Ubuntu终端，在Wine中安装项目依赖：
   ```bash
   wine pip install PyQt5 Pillow>=10.0.0 matplotlib pyinstaller
   ```
4. 在Wine中构建可执行文件：
   ```bash
   wine pyinstaller --onefile --windowed watermark_app.py
   ```

### 替代方法2：使用Docker容器构建

对于高级用户，可以使用包含mingw工具链的Docker容器进行交叉编译：

1. 拉取适合的Docker镜像：
   ```bash
   docker pull dockcross/mingw64
   ```
2. 运行容器并挂载项目目录：
   ```bash
   docker run -it -v $(pwd):/work dockcross/mingw64
   ```
3. 在容器内安装Python和依赖
4. 使用PyInstaller进行交叉编译

### 自动化构建脚本

我们提供了自动化构建脚本，尝试上述方法并提供详细的指导：

```bash
python3 build_windows.py
```

**注意：** 脚本运行后，即使在Ubuntu中直接生成了可执行文件（如`dist/win64/PhotoWatermarkTool`），这通常是Linux格式的ELF文件，而非Windows的.exe文件。

### 构建状态说明

- 如果您在Ubuntu中直接运行PyInstaller，默认会生成Linux可执行文件（ELF格式）
- 要生成真正的Windows可执行文件(.exe)，必须使用Windows系统或正确配置的Wine环境
- 根据系统检测，当前构建生成的是Linux可执行文件，如需Windows版本，请使用推荐的Windows系统直接构建方法

### 便携版本

在Windows系统上构建成功后，可以手动创建便携版本：

1. 创建一个新文件夹（如`PhotoWatermarkTool_Portable`）
2. 将生成的`.exe`文件复制到该文件夹
3. 复制`requirements.txt`和创建一个简单的`README.txt`文件说明使用方法


