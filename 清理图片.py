import os
import re
import shutil
from pathlib import Path

# ========== 使用相对路径（脚本所在文件夹 = 笔记根目录） ==========
NOTE_ROOT = Path(".")
# ==============================================================

# 校验根目录
note_root_path = NOTE_ROOT.resolve()
if not note_root_path.exists():
    print(f"错误：当前目录不存在！路径：{note_root_path}")
    exit(1)

# 匹配图片链接正则
img_pattern = re.compile(r'!\[.*?\]\((.*?)\)')
used_img_names = set()

print("正在扫描全部Markdown文档，收集已引用图片...")
# 遍历所有md文件
for md_file in note_root_path.rglob("*.md"):
    try:
        content = md_file.read_text(encoding="utf-8")
        matches = img_pattern.findall(content)
        for rel_path in matches:
            # 剔除锚点、URL参数，只保留文件名
            clean_path = rel_path.split("#")[0].split("?")[0]
            img_name = os.path.basename(clean_path)
            if img_name.strip():
                used_img_names.add(img_name)
    except Exception as e:
        print(f"读取失败 {md_file.name}: {str(e)}")

# 创建备份文件夹（自动逐级创建，不会报路径不存在）
del_backup = note_root_path / "deleted_img_backup"
del_backup.mkdir(parents=True, exist_ok=True)
clean_count = 0

print("\n开始检索无引用的冗余图片...")
# 兼容两种图片目录：Typora *.assets + Obsidian attachments
scan_dirs = list(note_root_path.rglob("*.assets")) + list(note_root_path.rglob("attachments"))

for target_dir in scan_dirs:
    if not target_dir.is_dir():
        continue
    for img_file in target_dir.iterdir():
        ext = img_file.suffix.lower()
        # 支持所有常见图片格式
        if ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tiff"):
            if img_file.name not in used_img_names:
                # 处理重名避免覆盖
                target_path = del_backup / img_file.name
                dup_num = 1
                while target_path.exists():
                    target_path = del_backup / f"{img_file.stem}_{dup_num}{img_file.suffix}"
                    dup_num += 1
                shutil.move(str(img_file), str(target_path))
                clean_count += 1
                print(f"已备份冗余图：{img_file.relative_to(note_root_path)}")

# 汇总输出
print(f"\n==================== 执行完成 ====================")
print(f"本次共备份清理无用图片：{clean_count} 张")
print(f"备份存放位置：{del_backup.resolve()}")
print("确认图片无丢失后，可手动删除 deleted_img_backup 文件夹释放空间")