#!/usr/bin/env python3
"""
图片水印工具
一个具有图形界面的图片水印应用程序，支持文本和图片水印，可在Ubuntu编译为Windows可执行文件。
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QFileDialog, QListWidget, QListWidgetItem, QLabel, QSlider,
    QColorDialog, QComboBox, QLineEdit, QGroupBox, QFormLayout, QCheckBox,
    QSpinBox, QMessageBox, QTabWidget, QSplitter, QFrame, QMenu, QAction,
    QInputDialog
)
from PyQt5.QtGui import (
    QPixmap, QImage, QPainter, QColor, QFont, QFontDatabase, QPen,
    QIcon, QDragEnterEvent, QDropEvent, QMouseEvent, QPainterPath
)
from PyQt5.QtCore import Qt, QSize, QPoint, QRect, QUrl, pyqtSignal

from PIL import Image, ImageDraw, ImageFont, ImageColor, ExifTags
import numpy as np


# 支持的图片格式
SUPPORTED_EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.webp'
}

# 预设水印位置
WATERMARK_POSITIONS = {
    'tl': ('左上角', lambda img_w, img_h, w, h, m: (m, m)),
    'tr': ('右上角', lambda img_w, img_h, w, h, m: (img_w - w - m, m)),
    'bl': ('左下角', lambda img_w, img_h, w, h, m: (m, img_h - h - m)),
    'br': ('右下角', lambda img_w, img_h, w, h, m: (img_w - w - m, img_h - h - m)),
    'center': ('居中', lambda img_w, img_h, w, h, m: ((img_w - w) // 2, (img_h - h) // 2))
}

# 配置文件路径
CONFIG_FILE = Path.home() / '.photo_watermark' / 'config.json'
TEMPLATES_DIR = Path.home() / '.photo_watermark' / 'templates'


class DraggableWatermarkLabel(QLabel):
    """可拖拽的水印预览标签"""
    positionChanged = pyqtSignal(int, int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dragging = False
        self.last_pos = QPoint()
        self.setCursor(Qt.OpenHandCursor)
        
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.last_pos = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)
            
    def mouseMoveEvent(self, event: QMouseEvent):
        if self.dragging:
            delta = event.pos() - self.last_pos
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self.last_pos = event.pos()
            self.positionChanged.emit(self.x(), self.y())
            event.accept()
        else:
            super().mouseMoveEvent(event)
            
    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.dragging = False
            self.setCursor(Qt.OpenHandCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class ImageThumbnailItem(QListWidgetItem):
    """图片缩略图列表项"""
    def __init__(self, image_path: Path, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.setSizeHint(QSize(100, 120))
        self.setTextAlignment(Qt.AlignBottom | Qt.AlignHCenter)
        
        # 加载缩略图
        try:
            pixmap = QPixmap(str(image_path))
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    90, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.setIcon(QIcon(scaled_pixmap))
                self.setText(image_path.name)
        except Exception:
            self.setText(f"无法加载: {image_path.name}")


class WatermarkApp(QMainWindow):
    """图片水印应用程序主窗口"""
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.init_config()
        self.load_last_settings()
        
    def init_ui(self):
        """初始化用户界面"""
        # 设置窗口标题和大小
        self.setWindowTitle("图片水印工具")
        self.resize(1200, 800)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 顶部按钮栏
        top_bar_layout = QHBoxLayout()
        
        self.add_files_btn = QPushButton("添加文件")
        self.add_files_btn.clicked.connect(self.add_files)
        top_bar_layout.addWidget(self.add_files_btn)
        
        self.add_folder_btn = QPushButton("添加文件夹")
        self.add_folder_btn.clicked.connect(self.add_folder)
        top_bar_layout.addWidget(self.add_folder_btn)
        
        self.clear_btn = QPushButton("清空列表")
        self.clear_btn.clicked.connect(self.clear_list)
        top_bar_layout.addWidget(self.clear_btn)
        
        top_bar_layout.addStretch()
        
        # 导出按钮
        self.export_btn = QPushButton("导出图片")
        self.export_btn.clicked.connect(self.export_images)
        self.export_btn.setEnabled(False)
        top_bar_layout.addWidget(self.export_btn)
        
        main_layout.addLayout(top_bar_layout)
        
        # 主分割器
        main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(main_splitter)
        
        # 左侧面板 - 图片列表
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        self.image_list = QListWidget()
        self.image_list.setViewMode(QListWidget.IconMode)
        self.image_list.setIconSize(QSize(90, 90))
        self.image_list.setResizeMode(QListWidget.Adjust)
        self.image_list.setMovement(QListWidget.Static)
        self.image_list.setFlow(QListWidget.LeftToRight)
        self.image_list.setWrapping(True)
        self.image_list.setMaximumWidth(300)
        self.image_list.itemClicked.connect(self.on_image_selected)
        left_layout.addWidget(QLabel("已导入图片"))
        left_layout.addWidget(self.image_list)
        
        main_splitter.addWidget(left_panel)
        
        # 右侧面板 - 预览和设置
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # 标签页控件
        tabs = QTabWidget()
        
        # 预览标签页
        preview_tab = QWidget()
        preview_layout = QVBoxLayout(preview_tab)
        
        self.preview_label = QLabel("预览区域")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(400, 300)
        self.preview_label.setStyleSheet("background-color: #f0f0f0;")
        preview_layout.addWidget(self.preview_label)
        
        # 水印预览标签
        self.watermark_preview = DraggableWatermarkLabel(self.preview_label)
        self.watermark_preview.hide()
        self.watermark_preview.positionChanged.connect(self.on_watermark_position_changed)
        
        tabs.addTab(preview_tab, "预览")
        
        # 设置标签页
        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)
        
        # 水印类型选择
        watermark_type_group = QGroupBox("水印类型")
        watermark_type_layout = QHBoxLayout()
        
        self.text_watermark_radio = QCheckBox("文本水印")
        self.text_watermark_radio.setChecked(True)
        self.text_watermark_radio.toggled.connect(self.on_watermark_type_changed)
        watermark_type_layout.addWidget(self.text_watermark_radio)
        
        self.image_watermark_radio = QCheckBox("图片水印")
        self.image_watermark_radio.toggled.connect(self.on_watermark_type_changed)
        watermark_type_layout.addWidget(self.image_watermark_radio)
        
        watermark_type_group.setLayout(watermark_type_layout)
        settings_layout.addWidget(watermark_type_group)
        
        # 文本水印设置
        self.text_watermark_group = QGroupBox("文本水印设置")
        text_watermark_layout = QFormLayout()
        
        # 文本内容
        self.watermark_text_edit = QLineEdit("水印文本")
        self.watermark_text_edit.textChanged.connect(self.update_preview)
        text_watermark_layout.addRow("文本内容:", self.watermark_text_edit)
        
        # 字体选择
        self.font_combo = QComboBox()
        self.font_combo.addItems(sorted(QFontDatabase().families()))
        self.font_combo.currentTextChanged.connect(self.update_preview)
        text_watermark_layout.addRow("字体:", self.font_combo)
        
        # 字体大小
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 120)
        self.font_size_spin.setValue(36)
        self.font_size_spin.valueChanged.connect(self.update_preview)
        text_watermark_layout.addRow("字体大小:", self.font_size_spin)
        
        # 字体样式
        font_style_layout = QHBoxLayout()
        self.bold_check = QCheckBox("粗体")
        self.bold_check.toggled.connect(self.update_preview)
        self.italic_check = QCheckBox("斜体")
        self.italic_check.toggled.connect(self.update_preview)
        font_style_layout.addWidget(self.bold_check)
        font_style_layout.addWidget(self.italic_check)
        text_watermark_layout.addRow("字体样式:", font_style_layout)
        
        # 文本颜色
        self.color_btn = QPushButton("选择颜色")
        self.color_btn.setStyleSheet("background-color: #FFFFFF; color: #000000")
        self.color_btn.clicked.connect(self.choose_color)
        text_watermark_layout.addRow("文本颜色:", self.color_btn)
        
        # 透明度
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self.update_preview)
        text_watermark_layout.addRow("透明度 (%):", self.opacity_slider)
        
        # 阴影效果
        self.shadow_check = QCheckBox("添加阴影")
        self.shadow_check.setChecked(True)
        self.shadow_check.toggled.connect(self.update_preview)
        text_watermark_layout.addRow("阴影效果:", self.shadow_check)
        
        self.text_watermark_group.setLayout(text_watermark_layout)
        settings_layout.addWidget(self.text_watermark_group)
        
        # 图片水印设置
        self.image_watermark_group = QGroupBox("图片水印设置")
        image_watermark_layout = QFormLayout()
        
        # 选择水印图片
        self.watermark_image_path = QLineEdit()
        self.watermark_image_path.setReadOnly(True)
        self.watermark_image_btn = QPushButton("浏览")
        self.watermark_image_btn.clicked.connect(self.choose_watermark_image)
        
        watermark_image_path_layout = QHBoxLayout()
        watermark_image_path_layout.addWidget(self.watermark_image_path)
        watermark_image_path_layout.addWidget(self.watermark_image_btn)
        image_watermark_layout.addRow("水印图片:", watermark_image_path_layout)
        
        # 水印图片大小
        self.watermark_image_size_slider = QSlider(Qt.Horizontal)
        self.watermark_image_size_slider.setRange(10, 100)
        self.watermark_image_size_slider.setValue(50)
        self.watermark_image_size_slider.valueChanged.connect(self.update_preview)
        image_watermark_layout.addRow("水印大小 (%):", self.watermark_image_size_slider)
        
        # 水印图片透明度
        self.watermark_image_opacity_slider = QSlider(Qt.Horizontal)
        self.watermark_image_opacity_slider.setRange(0, 100)
        self.watermark_image_opacity_slider.setValue(100)
        self.watermark_image_opacity_slider.valueChanged.connect(self.update_preview)
        image_watermark_layout.addRow("水印透明度 (%):", self.watermark_image_opacity_slider)
        
        self.image_watermark_group.setLayout(image_watermark_layout)
        self.image_watermark_group.setEnabled(False)
        settings_layout.addWidget(self.image_watermark_group)
        
        # 水印位置设置
        position_group = QGroupBox("水印位置")
        position_layout = QVBoxLayout()
        
        # 预设位置按钮
        positions_layout = QGridLayout()
        for i, (pos_key, (pos_name, _)) in enumerate(WATERMARK_POSITIONS.items()):
            btn = QPushButton(pos_name)
            btn.clicked.connect(lambda checked, pk=pos_key: self.set_watermark_position(pk))
            row, col = divmod(i, 3)
            positions_layout.addWidget(btn, row, col)
        position_layout.addLayout(positions_layout)
        
        # 边距设置
        margin_layout = QHBoxLayout()
        margin_layout.addWidget(QLabel("边距: "))
        self.margin_spin = QSpinBox()
        self.margin_spin.setRange(0, 200)
        self.margin_spin.setValue(12)
        self.margin_spin.valueChanged.connect(self.update_preview)
        margin_layout.addWidget(self.margin_spin)
        margin_layout.addWidget(QLabel("像素"))
        margin_layout.addStretch()
        position_layout.addLayout(margin_layout)
        
        position_group.setLayout(position_layout)
        settings_layout.addWidget(position_group)
        
        # 导出设置
        export_group = QGroupBox("导出设置")
        export_layout = QFormLayout()
        
        # 输出格式
        self.output_format_combo = QComboBox()
        self.output_format_combo.addItems(["JPEG (*.jpg)", "PNG (*.png)"])
        export_layout.addRow("输出格式:", self.output_format_combo)
        
        # JPEG质量
        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setRange(0, 100)
        self.quality_slider.setValue(95)
        export_layout.addRow("图片质量 (%):", self.quality_slider)
        
        # 文件命名规则
        self.keep_name_radio = QCheckBox("保留原文件名")
        self.keep_name_radio.setChecked(True)
        self.add_prefix_radio = QCheckBox("添加前缀")
        self.add_suffix_radio = QCheckBox("添加后缀")
        
        for radio in [self.keep_name_radio, self.add_prefix_radio, self.add_suffix_radio]:
            radio.toggled.connect(self.on_naming_rule_changed)
            export_layout.addRow(radio)
        
        # 前缀/后缀输入框
        self.prefix_edit = QLineEdit("wm_")
        self.prefix_edit.setEnabled(False)
        export_layout.addRow("前缀:", self.prefix_edit)
        
        self.suffix_edit = QLineEdit("_watermarked")
        self.suffix_edit.setEnabled(False)
        export_layout.addRow("后缀:", self.suffix_edit)
        
        export_group.setLayout(export_layout)
        settings_layout.addWidget(export_group)
        
        settings_layout.addStretch()
        tabs.addTab(settings_tab, "设置")
        
        # 模板管理标签页
        template_tab = QWidget()
        template_layout = QVBoxLayout(template_tab)
        
        # 模板列表
        self.template_list = QListWidget()
        template_layout.addWidget(QLabel("已保存模板"))
        template_layout.addWidget(self.template_list)
        
        # 模板按钮
        template_buttons_layout = QHBoxLayout()
        self.save_template_btn = QPushButton("保存当前设置为模板")
        self.save_template_btn.clicked.connect(self.save_template)
        template_buttons_layout.addWidget(self.save_template_btn)
        
        self.load_template_btn = QPushButton("加载选中模板")
        self.load_template_btn.clicked.connect(self.load_template)
        template_buttons_layout.addWidget(self.load_template_btn)
        
        self.delete_template_btn = QPushButton("删除选中模板")
        self.delete_template_btn.clicked.connect(self.delete_template)
        template_buttons_layout.addWidget(self.delete_template_btn)
        
        template_layout.addLayout(template_buttons_layout)
        
        template_layout.addStretch()
        tabs.addTab(template_tab, "模板管理")
        
        right_layout.addWidget(tabs)
        main_splitter.addWidget(right_panel)
        
        # 设置拖放支持
        self.setAcceptDrops(True)
        self.image_list.setAcceptDrops(True)
        self.preview_label.setAcceptDrops(True)
        
        # 加载已保存的模板
        self.load_templates()
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
    def init_config(self):
        """初始化配置文件和模板目录"""
        # 创建配置目录和模板目录
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
        
    def load_last_settings(self):
        """加载上次的设置"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                # 恢复水印类型设置
                if 'watermark_type' in config:
                    self.text_watermark_radio.setChecked(config['watermark_type'] == 'text')
                    self.image_watermark_radio.setChecked(config['watermark_type'] == 'image')
                    self.on_watermark_type_changed()
                    
                # 恢复文本水印设置
                if 'text' in config:
                    text_config = config['text']
                    if 'content' in text_config:
                        self.watermark_text_edit.setText(text_config['content'])
                    if 'font' in text_config:
                        index = self.font_combo.findText(text_config['font'])
                        if index >= 0:
                            self.font_combo.setCurrentIndex(index)
                    if 'font_size' in text_config:
                        self.font_size_spin.setValue(text_config['font_size'])
                    if 'bold' in text_config:
                        self.bold_check.setChecked(text_config['bold'])
                    if 'italic' in text_config:
                        self.italic_check.setChecked(text_config['italic'])
                    if 'color' in text_config:
                        self.current_color = text_config['color']
                        self.color_btn.setStyleSheet(f"background-color: {self.current_color}; color: {'#FFFFFF' if self.is_dark_color(text_config['color']) else '#000000'}")
                    if 'opacity' in text_config:
                        self.opacity_slider.setValue(text_config['opacity'])
                    if 'shadow' in text_config:
                        self.shadow_check.setChecked(text_config['shadow'])
                        
                # 恢复图片水印设置
                if 'image_watermark' in config:
                    img_config = config['image_watermark']
                    if 'path' in img_config:
                        self.watermark_image_path.setText(img_config['path'])
                    if 'size' in img_config:
                        self.watermark_image_size_slider.setValue(img_config['size'])
                    if 'opacity' in img_config:
                        self.watermark_image_opacity_slider.setValue(img_config['opacity'])
                        
                # 恢复位置设置
                if 'position' in config:
                    self.last_position = config['position']
                    if 'margin' in config:
                        self.margin_spin.setValue(config['margin'])
                        
                # 恢复导出设置
                if 'export' in config:
                    export_config = config['export']
                    if 'format' in export_config:
                        index = self.output_format_combo.findText(export_config['format'])
                        if index >= 0:
                            self.output_format_combo.setCurrentIndex(index)
                    if 'quality' in export_config:
                        self.quality_slider.setValue(export_config['quality'])
                    if 'naming_rule' in export_config:
                        rule = export_config['naming_rule']
                        self.keep_name_radio.setChecked(rule == 'keep_name')
                        self.add_prefix_radio.setChecked(rule == 'add_prefix')
                        self.add_suffix_radio.setChecked(rule == 'add_suffix')
                        self.on_naming_rule_changed()
                        if 'prefix' in export_config:
                            self.prefix_edit.setText(export_config['prefix'])
                        if 'suffix' in export_config:
                            self.suffix_edit.setText(export_config['suffix'])
            except Exception as e:
                print(f"加载配置文件失败: {e}")
        else:
            # 默认颜色设置
            self.current_color = '#FFFFFF'
            self.color_btn.setStyleSheet(f"background-color: {self.current_color}; color: #000000")
            self.last_position = 'br'
    
    def save_settings(self):
        """保存当前设置"""
        config = {
            'watermark_type': 'text' if self.text_watermark_radio.isChecked() else 'image',
            'text': {
                'content': self.watermark_text_edit.text(),
                'font': self.font_combo.currentText(),
                'font_size': self.font_size_spin.value(),
                'bold': self.bold_check.isChecked(),
                'italic': self.italic_check.isChecked(),
                'color': self.current_color,
                'opacity': self.opacity_slider.value(),
                'shadow': self.shadow_check.isChecked()
            },
            'image_watermark': {
                'path': self.watermark_image_path.text(),
                'size': self.watermark_image_size_slider.value(),
                'opacity': self.watermark_image_opacity_slider.value()
            },
            'position': self.last_position,
            'margin': self.margin_spin.value(),
            'export': {
                'format': self.output_format_combo.currentText(),
                'quality': self.quality_slider.value(),
                'naming_rule': 'keep_name' if self.keep_name_radio.isChecked() else 
                               'add_prefix' if self.add_prefix_radio.isChecked() else 'add_suffix',
                'prefix': self.prefix_edit.text(),
                'suffix': self.suffix_edit.text()
            }
        }
        
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
    def load_templates(self):
        """加载已保存的模板"""
        self.template_list.clear()
        for template_file in TEMPLATES_DIR.glob('*.json'):
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    template = json.load(f)
                    item = QListWidgetItem(template.get('name', template_file.stem))
                    item.setData(Qt.UserRole, template_file.name)
                    self.template_list.addItem(item)
            except Exception:
                pass
    
    def save_template(self):
        """保存当前设置为模板"""
        template_name, ok = QInputDialog.getText(self, "保存模板", "请输入模板名称:")
        if ok and template_name:
            # 获取当前设置
            config = {
                'name': template_name,
                'watermark_type': 'text' if self.text_watermark_radio.isChecked() else 'image',
                'text': {
                    'content': self.watermark_text_edit.text(),
                    'font': self.font_combo.currentText(),
                    'font_size': self.font_size_spin.value(),
                    'bold': self.bold_check.isChecked(),
                    'italic': self.italic_check.isChecked(),
                    'color': self.current_color,
                    'opacity': self.opacity_slider.value(),
                    'shadow': self.shadow_check.isChecked()
                },
                'image_watermark': {
                    'path': self.watermark_image_path.text(),
                    'size': self.watermark_image_size_slider.value(),
                    'opacity': self.watermark_image_opacity_slider.value()
                },
                'position': self.last_position,
                'margin': self.margin_spin.value()
            }
            
            # 保存模板文件
            template_file = TEMPLATES_DIR / f"{template_name}.json"
            try:
                with open(template_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                self.load_templates()
                QMessageBox.information(self, "成功", f"模板 '{template_name}' 已保存")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存模板失败: {e}")
    
    def load_template(self):
        """加载选中的模板"""
        selected_item = self.template_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "警告", "请先选择一个模板")
            return
        
        template_file = TEMPLATES_DIR / selected_item.data(Qt.UserRole)
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                template = json.load(f)
                
                # 应用模板设置
                if 'watermark_type' in template:
                    self.text_watermark_radio.setChecked(template['watermark_type'] == 'text')
                    self.image_watermark_radio.setChecked(template['watermark_type'] == 'image')
                    self.on_watermark_type_changed()
                    
                if 'text' in template:
                    text_config = template['text']
                    if 'content' in text_config:
                        self.watermark_text_edit.setText(text_config['content'])
                    if 'font' in text_config:
                        index = self.font_combo.findText(text_config['font'])
                        if index >= 0:
                            self.font_combo.setCurrentIndex(index)
                    if 'font_size' in text_config:
                        self.font_size_spin.setValue(text_config['font_size'])
                    if 'bold' in text_config:
                        self.bold_check.setChecked(text_config['bold'])
                    if 'italic' in text_config:
                        self.italic_check.setChecked(text_config['italic'])
                    if 'color' in text_config:
                        self.current_color = text_config['color']
                        self.color_btn.setStyleSheet(f"background-color: {self.current_color}; color: {'#FFFFFF' if self.is_dark_color(text_config['color']) else '#000000'}")
                    if 'opacity' in text_config:
                        self.opacity_slider.setValue(text_config['opacity'])
                    if 'shadow' in text_config:
                        self.shadow_check.setChecked(text_config['shadow'])
                        
                if 'image_watermark' in template:
                    img_config = template['image_watermark']
                    if 'path' in img_config:
                        self.watermark_image_path.setText(img_config['path'])
                    if 'size' in img_config:
                        self.watermark_image_size_slider.setValue(img_config['size'])
                    if 'opacity' in img_config:
                        self.watermark_image_opacity_slider.setValue(img_config['opacity'])
                        
                if 'position' in template:
                    self.last_position = template['position']
                    self.set_watermark_position(self.last_position)
                    if 'margin' in template:
                        self.margin_spin.setValue(template['margin'])
                        
            QMessageBox.information(self, "成功", f"模板 '{template.get('name', template_file.stem)}' 已加载")
            self.update_preview()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载模板失败: {e}")
    
    def delete_template(self):
        """删除选中的模板"""
        selected_item = self.template_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "警告", "请先选择一个模板")
            return
        
        template_name = selected_item.text()
        reply = QMessageBox.question(
            self, "确认", f"确定要删除模板 '{template_name}' 吗?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            template_file = TEMPLATES_DIR / selected_item.data(Qt.UserRole)
            try:
                template_file.unlink()
                self.load_templates()
                QMessageBox.information(self, "成功", f"模板 '{template_name}' 已删除")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除模板失败: {e}")
    
    def is_dark_color(self, color_hex: str) -> bool:
        """判断颜色是否为深色"""
        try:
            r = int(color_hex[1:3], 16)
            g = int(color_hex[3:5], 16)
            b = int(color_hex[5:7], 16)
            # 计算亮度 (0-255)
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            return brightness < 128
        except:
            return False
    
    def add_files(self):
        """添加图片文件"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择图片文件", "", 
            "图片文件 (*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp)"
        )
        
        if files:
            self.add_images_to_list(files)
            
    def add_folder(self):
        """添加文件夹中的图片"""
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹", "")
        
        if folder:
            image_files = []
            for root, _, files in os.walk(folder):
                for file in files:
                    ext = Path(file).suffix.lower()
                    if ext in SUPPORTED_EXTENSIONS:
                        image_files.append(os.path.join(root, file))
            
            if image_files:
                self.add_images_to_list(image_files)
            else:
                QMessageBox.information(self, "提示", "所选文件夹中没有找到支持的图片文件")
    
    def add_images_to_list(self, file_paths: List[str]):
        """将图片添加到列表"""
        for file_path in file_paths:
            path = Path(file_path)
            if path.exists() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
                item = ImageThumbnailItem(path)
                self.image_list.addItem(item)
                
        # 启用导出按钮
        if self.image_list.count() > 0:
            self.export_btn.setEnabled(True)
            # 自动选择第一张图片
            if self.image_list.currentItem() is None:
                self.image_list.setCurrentRow(0)
                self.on_image_selected(self.image_list.currentItem())
                
    def clear_list(self):
        """清空图片列表"""
        self.image_list.clear()
        self.export_btn.setEnabled(False)
        self.preview_label.setText("预览区域")
        self.watermark_preview.hide()
        
    def on_image_selected(self, item: QListWidgetItem):
        """当选中图片时更新预览"""
        if isinstance(item, ImageThumbnailItem):
            self.update_preview()
            
    def on_watermark_type_changed(self):
        """当水印类型改变时更新界面"""
        is_text = self.text_watermark_radio.isChecked()
        self.text_watermark_group.setEnabled(is_text)
        self.image_watermark_group.setEnabled(not is_text)
        self.update_preview()
        
    def on_naming_rule_changed(self):
        """当命名规则改变时更新界面"""
        self.prefix_edit.setEnabled(self.add_prefix_radio.isChecked())
        self.suffix_edit.setEnabled(self.add_suffix_radio.isChecked())
        
    def choose_color(self):
        """选择文本颜色"""
        color = QColorDialog.getColor(QColor(self.current_color), self, "选择文本颜色")
        if color.isValid():
            color_hex = color.name()
            self.current_color = color_hex
            self.color_btn.setStyleSheet(f"background-color: {color_hex}; color: {'#FFFFFF' if self.is_dark_color(color_hex) else '#000000'}")
            self.update_preview()
            
    def choose_watermark_image(self):
        """选择水印图片"""
        file, _ = QFileDialog.getOpenFileName(
            self, "选择水印图片", "", "图片文件 (*.png *.jpg *.jpeg *.bmp)"
        )
        
        if file:
            self.watermark_image_path.setText(file)
            self.update_preview()
            
    def set_watermark_position(self, position_key: str):
        """设置水印位置"""
        self.last_position = position_key
        self.update_preview()
        
    def on_watermark_position_changed(self, x: int, y: int):
        """当水印位置改变时更新"""
        self.last_position = f"custom_{x}_{y}"
        
    def update_preview(self):
        """更新预览"""
        # 检查是否有选中的图片
        current_item = self.image_list.currentItem()
        if not isinstance(current_item, ImageThumbnailItem):
            return
        
        image_path = current_item.image_path
        try:
            # 加载图片
            with Image.open(image_path) as img:
                # 转换为Qt可显示的格式
                img_copy = img.copy()
                if img_copy.mode != 'RGB':
                    img_copy = img_copy.convert('RGB')
                
                # 计算预览大小
                img_width, img_height = img_copy.size
                max_width = 800
                max_height = 600
                scale = min(max_width / img_width, max_height / img_height, 1.0)
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)
                
                # 调整图片大小
                img_copy = img_copy.resize((new_width, new_height), Image.LANCZOS)
                
                # 将PIL图像转换为numpy数组
                img_array = np.array(img_copy)
                
                # 根据图像模式创建QImage
                if img_copy.mode == 'RGBA':
                    q_image = QImage(img_array.data, img_array.shape[1], img_array.shape[0], img_array.shape[1] * 4, QImage.Format_RGBA8888)
                elif img_copy.mode == 'RGB':
                    q_image = QImage(img_array.data, img_array.shape[1], img_array.shape[0], img_array.shape[1] * 3, QImage.Format_RGB888)
                else:
                    # 对于其他模式，先转换为RGB
                    img_copy = img_copy.convert('RGB')
                    img_array = np.array(img_copy)
                    q_image = QImage(img_array.data, img_array.shape[1], img_array.shape[0], img_array.shape[1] * 3, QImage.Format_RGB888)
                
                # 创建QPixmap
                pixmap = QPixmap.fromImage(q_image)
                
                # 设置预览标签
                self.preview_label.setPixmap(pixmap)
                self.preview_label.setFixedSize(new_width, new_height)
                
                # 显示水印预览
                if self.text_watermark_radio.isChecked():
                    self._update_text_watermark_preview(new_width, new_height)
                else:
                    self._update_image_watermark_preview(new_width, new_height)
                    
        except Exception as e:
            self.preview_label.setText(f"无法加载图片: {e}")
            self.watermark_preview.hide()
            
    def _update_text_watermark_preview(self, img_width: int, img_height: int):
        """更新文本水印预览"""
        text = self.watermark_text_edit.text()
        font_name = self.font_combo.currentText()
        font_size = self.font_size_spin.value()
        bold = self.bold_check.isChecked()
        italic = self.italic_check.isChecked()
        opacity = self.opacity_slider.value()
        add_shadow = self.shadow_check.isChecked()
        margin = self.margin_spin.value()
        
        # 创建字体
        font = QFont(font_name, font_size)
        font.setBold(bold)
        font.setItalic(italic)
        
        # 创建文本标签
        self.watermark_preview.setText(text)
        self.watermark_preview.setFont(font)
        
        # 设置文本颜色和透明度
        color = QColor(self.current_color)
        color.setAlpha(int(255 * opacity / 100))
        self.watermark_preview.setStyleSheet(f"color: {color.name()}; background-color: transparent;")
        
        # 自动调整标签大小以适应文本
        self.watermark_preview.adjustSize()
        
        # 设置位置
        wm_width = self.watermark_preview.width()
        wm_height = self.watermark_preview.height()
        
        if self.last_position.startswith('custom_'):
            # 自定义位置
            try:
                _, x, y = self.last_position.split('_')
                x = int(x)
                y = int(y)
                # 确保水印在预览区域内
                x = max(0, min(x, img_width - wm_width))
                y = max(0, min(y, img_height - wm_height))
                self.watermark_preview.move(x, y)
            except:
                # 出错时使用默认位置
                self.last_position = 'br'
                self.set_watermark_position(self.last_position)
        else:
            # 预设位置
            if self.last_position in WATERMARK_POSITIONS:
                _, pos_func = WATERMARK_POSITIONS[self.last_position]
                x, y = pos_func(img_width, img_height, wm_width, wm_height, margin)
                self.watermark_preview.move(x, y)
        
        # 显示水印
        self.watermark_preview.show()
        
    def _update_image_watermark_preview(self, img_width: int, img_height: int):
        """更新图片水印预览"""
        watermark_image_path = self.watermark_image_path.text()
        if not watermark_image_path or not os.path.exists(watermark_image_path):
            self.watermark_preview.hide()
            return
        
        try:
            # 加载水印图片
            with Image.open(watermark_image_path) as wm_img:
                # 计算水印大小
                scale = self.watermark_image_size_slider.value() / 100
                wm_width = int(wm_img.width * scale)
                wm_height = int(wm_img.height * scale)
                
                # 调整水印大小
                wm_img = wm_img.resize((wm_width, wm_height), Image.LANCZOS)
                
                # 设置透明度
                opacity = self.watermark_image_opacity_slider.value()
                if wm_img.mode != 'RGBA':
                    wm_img = wm_img.convert('RGBA')
                
                # 创建新的带透明度的图像
                r, g, b, a = wm_img.split()
                a = a.point(lambda x: int(x * opacity / 100))
                wm_img = Image.merge('RGBA', (r, g, b, a))
                
                # 将PIL图像转换为numpy数组
                img_array = np.array(wm_img)
                
                # 创建RGBA格式的QImage
                q_image = QImage(img_array.data, img_array.shape[1], img_array.shape[0], img_array.shape[1] * 4, QImage.Format_RGBA8888)
                
                # 创建QPixmap
                pixmap = QPixmap.fromImage(q_image)
                
                # 设置水印预览
                self.watermark_preview.setPixmap(pixmap)
                self.watermark_preview.setFixedSize(wm_width, wm_height)
                
                # 设置位置
                margin = self.margin_spin.value()
                
                if self.last_position.startswith('custom_'):
                    # 自定义位置
                    try:
                        _, x, y = self.last_position.split('_')
                        x = int(x)
                        y = int(y)
                        # 确保水印在预览区域内
                        x = max(0, min(x, img_width - wm_width))
                        y = max(0, min(y, img_height - wm_height))
                        self.watermark_preview.move(x, y)
                    except:
                        # 出错时使用默认位置
                        self.last_position = 'br'
                        self.set_watermark_position(self.last_position)
                else:
                    # 预设位置
                    if self.last_position in WATERMARK_POSITIONS:
                        _, pos_func = WATERMARK_POSITIONS[self.last_position]
                        x, y = pos_func(img_width, img_height, wm_width, wm_height, margin)
                        self.watermark_preview.move(x, y)
                
                # 显示水印
                self.watermark_preview.show()
        except Exception:
            self.watermark_preview.hide()
            
    def export_images(self):
        """导出图片"""
        # 选择输出目录
        output_dir = QFileDialog.getExistingDirectory(self, "选择输出目录", "")
        if not output_dir:
            return
        
        # 检查是否与原目录相同
        has_same_dir = False
        for i in range(self.image_list.count()):
            item = self.image_list.item(i)
            if isinstance(item, ImageThumbnailItem):
                original_dir = str(item.image_path.parent)
                if original_dir == output_dir:
                    has_same_dir = True
                    break
        
        if has_same_dir:
            reply = QMessageBox.question(
                self, "警告", "输出目录与部分图片的原目录相同，可能会覆盖原图。是否继续?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        # 导出进度
        total = self.image_list.count()
        success_count = 0
        error_count = 0
        
        for i in range(total):
            # 更新状态栏
            self.statusBar().showMessage(f"正在导出 {i+1}/{total}")
            QApplication.processEvents()
            
            item = self.image_list.item(i)
            if not isinstance(item, ImageThumbnailItem):
                continue
            
            try:
                self._process_and_save_image(item.image_path, output_dir)
                success_count += 1
            except Exception as e:
                print(f"导出失败: {item.image_path} - {e}")
                error_count += 1
        
        # 显示结果
        self.statusBar().showMessage("就绪")
        QMessageBox.information(
            self, "导出完成", 
            f"成功导出 {success_count} 张图片\n" +
            (f"失败 {error_count} 张图片" if error_count > 0 else "")
        )
        
    def _process_and_save_image(self, image_path: Path, output_dir: str):
        """处理并保存图片"""
        with Image.open(image_path) as img:
            # 获取输出文件名
            output_filename = self._get_output_filename(image_path)
            output_path = os.path.join(output_dir, output_filename)
            
            # 应用水印
            watermarked_img = self._apply_watermark(img)
            
            # 保存图片
            if output_filename.lower().endswith('.png'):
                watermarked_img.save(output_path, 'PNG')
            else:
                quality = self.quality_slider.value()
                watermarked_img.save(output_path, 'JPEG', quality=quality)
                
    def _get_output_filename(self, image_path: Path) -> str:
        """获取输出文件名"""
        original_name = image_path.stem
        original_ext = image_path.suffix.lower()
        
        # 根据选择的格式确定输出扩展名
        output_format = self.output_format_combo.currentText()
        if 'PNG' in output_format:
            ext = '.png'
        else:
            ext = '.jpg'
        
        # 根据命名规则生成文件名
        if self.keep_name_radio.isChecked():
            return f"{original_name}{ext}"
        elif self.add_prefix_radio.isChecked():
            prefix = self.prefix_edit.text()
            return f"{prefix}{original_name}{ext}"
        elif self.add_suffix_radio.isChecked():
            suffix = self.suffix_edit.text()
            return f"{original_name}{suffix}{ext}"
        else:
            return f"{original_name}{ext}"
            
    def _apply_watermark(self, img: Image.Image) -> Image.Image:
        """应用水印"""
        # 转换为RGBA以支持透明度
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
            
        width, height = img.size
        
        if self.text_watermark_radio.isChecked():
            # 应用文本水印
            return self._apply_text_watermark(img)
        else:
            # 应用图片水印
            return self._apply_image_watermark(img)
            
    def _apply_text_watermark(self, img: Image.Image) -> Image.Image:
        """应用文本水印"""
        text = self.watermark_text_edit.text()
        font_name = self.font_combo.currentText()
        font_size = self.font_size_spin.value()
        bold = self.bold_check.isChecked()
        italic = self.italic_check.isChecked()
        opacity = self.opacity_slider.value()
        add_shadow = self.shadow_check.isChecked()
        margin = self.margin_spin.value()
        
        # 创建绘制对象
        draw = ImageDraw.Draw(img)
        
        # 加载字体
        try:
            # 尝试加载指定字体
            font = ImageFont.truetype(font_name, font_size)
        except:
            # 回退到默认字体
            try:
                font = ImageFont.load_default()
            except:
                # 作为最后的尝试，使用系统字体
                font = ImageFont.truetype("Arial.ttf", font_size) if os.name == 'nt' else \
                       ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
        
        # 获取文本大小
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # 计算位置
        x, y = self._calculate_watermark_position(
            img.width, img.height, text_width, text_height, margin
        )
        
        # 设置文本颜色和透明度
        try:
            r, g, b = ImageColor.getrgb(self.current_color)
            a = int(255 * opacity / 100)
            text_color = (r, g, b, a)
        except:
            text_color = (255, 255, 255, int(255 * opacity / 100))
        
        # 添加阴影
        if add_shadow:
            shadow_offset = max(1, font_size // 24)
            shadow_color = (0, 0, 0, int(160 * opacity / 100))
            draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=shadow_color)
        
        # 绘制文本
        draw.text((x, y), text, font=font, fill=text_color)
        
        return img
        
    def _apply_image_watermark(self, img: Image.Image) -> Image.Image:
        """应用图片水印"""
        watermark_image_path = self.watermark_image_path.text()
        if not watermark_image_path or not os.path.exists(watermark_image_path):
            return img
        
        with Image.open(watermark_image_path) as wm_img:
            # 计算水印大小
            scale = self.watermark_image_size_slider.value() / 100
            wm_width = int(wm_img.width * scale)
            wm_height = int(wm_img.height * scale)
            
            # 调整水印大小
            wm_img = wm_img.resize((wm_width, wm_height), Image.LANCZOS)
            
            # 设置透明度
            opacity = self.watermark_image_opacity_slider.value()
            if wm_img.mode != 'RGBA':
                wm_img = wm_img.convert('RGBA')
            
            # 创建新的带透明度的图像
            r, g, b, a = wm_img.split()
            a = a.point(lambda x: int(x * opacity / 100))
            wm_img = Image.merge('RGBA', (r, g, b, a))
            
            # 计算位置
            margin = self.margin_spin.value()
            x, y = self._calculate_watermark_position(
                img.width, img.height, wm_width, wm_height, margin
            )
            
            # 创建新图像以避免修改原图
            result = Image.new('RGBA', img.size, (255, 255, 255, 0))
            result.paste(img, (0, 0))
            result.paste(wm_img, (x, y), wm_img)
            
            return result
            
    def _calculate_watermark_position(self, img_width: int, img_height: int, 
                                     wm_width: int, wm_height: int, margin: int) -> Tuple[int, int]:
        """计算水印位置"""
        if self.last_position.startswith('custom_'):
            # 自定义位置 - 需要根据预览比例调整到实际图片尺寸
            try:
                _, preview_x, preview_y = self.last_position.split('_')
                # 获取预览窗口中的图片尺寸
                preview_img_width = self.preview_label.width()
                preview_img_height = self.preview_label.height()
                
                # 计算缩放比例
                scale_x = img_width / preview_img_width
                scale_y = img_height / preview_img_height
                
                # 调整位置到实际图片尺寸
                x = int(int(preview_x) * scale_x)
                y = int(int(preview_y) * scale_y)
                
                # 确保水印在图片范围内
                x = max(0, min(x, img_width - wm_width))
                y = max(0, min(y, img_height - wm_height))
                return x, y
            except:
                # 出错时使用默认位置
                self.last_position = 'br'
        
        # 预设位置
        if self.last_position in WATERMARK_POSITIONS:
            _, pos_func = WATERMARK_POSITIONS[self.last_position]
            return pos_func(img_width, img_height, wm_width, wm_height, margin)
        
        # 默认位置：右下角
        return img_width - wm_width - margin, img_height - wm_height - margin
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖放进入事件处理"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            
    def dropEvent(self, event: QDropEvent):
        """拖放事件处理"""
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isfile(path) and Path(path).suffix.lower() in SUPPORTED_EXTENSIONS:
                files.append(path)
            elif os.path.isdir(path):
                # 处理文件夹
                for root, _, file_names in os.walk(path):
                    for file_name in file_names:
                        ext = Path(file_name).suffix.lower()
                        if ext in SUPPORTED_EXTENSIONS:
                            files.append(os.path.join(root, file_name))
        
        if files:
            self.add_images_to_list(files)
            
    def closeEvent(self, event):
        """窗口关闭事件处理"""
        # 保存当前设置
        self.save_settings()
        event.accept()
        

if __name__ == '__main__':
    # 确保中文显示正常
    import matplotlib
    matplotlib.use('Agg')  # 非交互式后端
    
    app = QApplication(sys.argv)
    window = WatermarkApp()
    window.show()
    sys.exit(app.exec_())