import os
import re
import shutil
import sys
import tkinter as tk
from tkinter import filedialog
from urllib.parse import unquote

def collect_recursively(start_md, vault_path, target_folder):
    visited_docs = set()  # 문서 중복 분석 방지
    # 이미 대상 폴더에 존재하는 파일 리스트 (시작 시 스캔하여 속도 최적화)
    existing_files = set(f.lower() for f in os.listdir(target_folder))
    
    queue = [os.path.abspath(start_md)]
    copy_count = 0
    skip_count = 0

    # 1. 볼트 내 모든 파일 인덱싱
    print(f"\n[1/3] 볼트 스캔 및 인덱싱 중...")
    file_db = {}
    for root, dirs, files in os.walk(vault_path):
        for file in files:
            full_path = os.path.normpath(os.path.join(root, file))
            f_low = file.lower()
            name_low = os.path.splitext(f_low)[0]
            if f_low not in file_db: file_db[f_low] = full_path
            if name_low not in file_db or f_low.endswith('.md'):
                file_db[name_low] = full_path

    print(f"[2/3] 재귀적 링크 분석 및 효율적 복사 시작...")
    
    while queue:
        current_md = queue.pop(0)
        if current_md in visited_docs:
            continue
        
        visited_docs.add(current_md)
        md_name = os.path.basename(current_md)
        
        # 마크다운 파일 복사 (이미 있으면 스킵)
        if md_name.lower() not in existing_files:
            try:
                shutil.copy2(current_md, target_folder)
                existing_files.add(md_name.lower())
                copy_count += 1
                print(f" -> 수집: {md_name}")
            except: pass
        else:
            skip_count += 1

        try:
            with open(current_md, 'r', encoding='utf-8-sig') as f:
                content = f.read()
        except: continue

        patterns = [r'!\[\[(.*?)\]\]', r'\[\[(.*?)\]\]', r'!\[.*?\]\((.*?)\)', r'\[.*?\]\((.*?)\)']
        links = list(set([item for p in patterns for item in re.findall(p, content)]))

        for link in links:
            clean_link = unquote(link.split('|')[0].split('?')[0].split('#')[0].strip())
            f_name = os.path.basename(clean_link).lower()
            f_no_ext = os.path.splitext(f_name)[0]

            found_path = None
            if f_name in file_db: found_path = file_db[f_name]
            elif f"{f_name}.md" in file_db: found_path = file_db[f"{f_name}.md"]
            elif f_no_ext in file_db: found_path = file_db[f_no_ext]

            if found_path and os.path.exists(found_path):
                found_name = os.path.basename(found_path)
                
                # 마크다운이면 대기열 추가
                if found_name.lower().endswith('.md'):
                    if found_path not in visited_docs:
                        queue.append(found_path)
                
                # 리소스 복사 (이미 대상 폴더에 있으면 무조건 스킵)
                if found_name.lower() not in existing_files:
                    try:
                        shutil.copy2(found_path, target_folder)
                        existing_files.add(found_name.lower())
                        copy_count += 1
                        # print(f"    * 리소스 추가: {found_name}")
                    except: pass
                else:
                    skip_count += 1
    
    return copy_count, skip_count

if __name__ == "__main__":
    output_base_path = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    target_folder = os.path.join(output_base_path, 'exported_assets')

    if not os.path.exists(target_folder):
        os.makedirs(target_folder)

    root = tk.Tk()
    root.withdraw()

    vault_dir = filedialog.askdirectory(title="1. 볼트 폴더를 선택하세요")
    if not vault_dir: sys.exit(1)

    md_file = filedialog.askopenfilename(
        title="2. 분석을 시작할 마크다운 파일을 선택하세요",
        initialdir=vault_dir,
        filetypes=[("Markdown files", "*.md")]
    )
    if not md_file: sys.exit(1)

    final_count, skipped = collect_recursively(md_file, vault_dir, target_folder)

    print(f"\n[3/3] 모든 작업 완료!")
    print(f" - 신규 복사: {final_count}개")
    print(f" - 중복 스킵: {skipped}개")
    print(f" - 최종 위치: {target_folder}")
    print("\n아무 키나 누르면 종료됩니다...")
    os.system("pause > nul")