## EXIF 日期水印命令行工具

将图片 EXIF 拍摄日期（YYYY-MM-DD）作为文字水印绘制到图片上。

### 安装依赖

```bash
pip install -r requirements.txt
```

### 使用方法

```bash
python watermark_exif_date.py <图片路径或目录> [--font-size 36] [--color "#FFFFFF"] [--position br] [--margin 12] [--font /path/to/font.ttf]
```

- `input_path`: 单个图片文件或包含图片的目录。
- `--font-size`: 字体大小（像素）。默认 36。
- `--color`: 字体颜色（CSS 名称或 `#RRGGBB`）。默认白色。
- `--position`: 水印位置，可选 `tl`(左上)、`tr`(右上)、`bl`(左下)、`br`(右下)、`center`(居中)。默认 `br`。
- `--margin`: 边距像素，默认 12。
- `--font`: 自定义字体文件路径（.ttf/.otf），可选。

### 输出

- 若输入为目录：在该目录下生成子目录 `<目录名>_watermark`，水印后的图片会保存到该目录。
- 若输入为单图：在图片所在目录生成子目录 `<目录名>_watermark`，保存同名文件。

### 注意

- 程序会优先读取 EXIF 的 `DateTimeOriginal`，其次 `DateTimeDigitized`，再次 `DateTime`。
- 如果图片没有 EXIF 日期信息，会跳过并提示。


