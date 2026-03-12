import os
import re
import shutil
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from urllib.parse import unquote

# --- 볼트 내 파일 선택을 위한 커스텀 탐색기 클래스 ---
class VaultBrowser(tk.Toplevel):
    def __init__(self, master, vault_path):
        super().__init__(master)
        self.vault_path = os.path.normpath(vault_path)
        self.selected_file = None
        
        self.title(f"볼트 탐색기: {os.path.basename(self.vault_path)}")
        self.geometry("700x500")
        self.attributes('-topmost', True)  # 창을 맨 앞으로 가져옴

        # UI 구성
        self.setup_ui()
        self.load_tree()
        
        # 창이 닫힐 때 처리
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_ui(self):
        label = tk.Label(self, text=f"시작할 마크다운 파일을 선택하세요\n(루트: {self.vault_path})", pady=10)
        label.pack()

        self.tree = ttk.Treeview(self)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        
        scrollbar = ttk.Scrollbar(self.tree, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        btn_frame = tk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=15)
        tk.Button(btn_frame, text="선택 완료", command=self.on_select, width=20, bg="#e1e1e1").pack(side=tk.RIGHT, padx=30)

    def load_tree(self):
        # 최상위 루트 노드
        root_node = self.tree.insert('', 'end', text=os.path.basename(self.vault_path), open=True)
        self.nodes = {self.vault_path: root_node}

        # 하위 구조 스캔
        for root, dirs, files in os.walk(self.vault_path):
            for d in sorted(dirs):
                full_path = os.path.join(root, d)
                parent_path = os.path.dirname(full_path)
                if parent_path in self.nodes:
                    node = self.tree.insert(self.nodes[parent_path], 'end', text=d, open=False)
                    self.nodes[full_path] = node
            
            for f in sorted(files):
                if f.lower().endswith('.md'):
                    full_path = os.path.join(root, f)
                    parent_path = os.path.dirname(full_path)
                    if parent_path in self.nodes:
                        self.tree.insert(self.nodes[parent_path], 'end', text=f, values=(full_path,))

    def on_select(self):
        selected_item = self.tree.selection()
        if selected_item:
            values = self.tree.item(selected_item[0], 'values')
            if values:
                self.selected_file = values[0]
                self.destroy()
            else:
                messagebox.showwarning("알림", "폴더가 아닌 마크다운 파일을 선택해 주세요.")
        else:
            messagebox.showwarning("알림", "파일을 먼저 선택해 주세요.")

    def on_close(self):
        self.selected_file = None
        self.destroy()

# --- 수집 및 병합 로직 (이전과 동일) ---
def collect_and_merge(start_md, vault_path, base_output_path):
    # 결과물을 저장할 dist 폴더 경로 설정
    dist_folder = os.path.join(base_output_path, 'dist')
    asset_folder = os.path.join(dist_folder, 'exported_assets')
    
    # dist 및 하위 폴더 생성
    if not os.path.exists(asset_folder):
        os.makedirs(asset_folder)

    visited_docs = set()
    existing_assets = set(f.lower() for f in os.listdir(asset_folder))
    queue = [os.path.abspath(start_md)]
    ordered_md_contents = []
    asset_count = 0

    print(f"\n[1/3] 볼트 데이터 분석 중...")
    file_db = {}
    for root, dirs, files in os.walk(vault_path):
        for file in files:
            full_path = os.path.normpath(os.path.join(root, file))
            f_low = file.lower()
            name_low = os.path.splitext(f_low)[0]
            if f_low not in file_db: file_db[f_low] = full_path
            if name_low not in file_db or f_low.endswith('.md'):
                file_db[name_low] = full_path

    print(f"[2/3] 문서 분석 및 이미지 수집 중 (대상: {dist_folder})...")
    while queue:
        current_md = queue.pop(0)
        if current_md in visited_docs:
            continue
        
        visited_docs.add(current_md)
        md_name = os.path.basename(current_md)

        try:
            with open(current_md, 'r', encoding='utf-8-sig') as f:
                content = f.read()
                
            ordered_md_contents.append(f"\n\n\n# Document: {md_name}\n\n{content}\n\n---")

            patterns = [r'!\[\[(.*?)\]\]', r'\[\[(.*?)\]\]', r'!\[.*?\]\((.*?)\)', r'\[.*?\]\((.*?)\)']
            links = list(set([item for p in patterns for item in re.findall(p, content)]))

            for link in links:
                clean_link = unquote(link.split('|')[0].split('?')[0].split('#')[0].strip())
                f_name = os.path.basename(clean_link).lower()
                f_no_ext = os.path.splitext(f_name)[0]
                found_path = file_db.get(f_name) or file_db.get(f"{f_name}.md") or file_db.get(f_no_ext)

                if found_path and os.path.exists(found_path):
                    found_name = os.path.basename(found_path)
                    if found_name.lower().endswith('.md'):
                        if found_path not in visited_docs:
                            queue.append(found_path)
                    else:
                        if found_name.lower() not in existing_assets:
                            try:
                                shutil.copy2(found_path, asset_folder)
                                existing_assets.add(found_name.lower())
                                asset_count += 1
                            except: pass
        except Exception: continue

    print(f"[3/3] 통합 문서 생성 중...")
    merge_file_path = os.path.join(dist_folder, "merged_notebook.md")
    with open(merge_file_path, 'w', encoding='utf-8') as outfile:
        outfile.write(f"// Total Merged Documents: {len(visited_docs)}\n")
        outfile.write("".join(ordered_md_contents))

    return asset_count, merge_file_path, len(visited_docs), dist_folder

if __name__ == "__main__":
    output_path = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()

    root = tk.Tk()
    root.withdraw()

    v_dir = filedialog.askdirectory(title="1. 볼트 폴더를 선택하세요")
    if not v_dir:
        sys.exit(1)

    browser = VaultBrowser(root, v_dir)
    root.wait_window(browser)

    if not browser.selected_file:
        sys.exit(1)

    try:
        assets, m_path, docs, final_dist = collect_and_merge(browser.selected_file, v_dir, output_path)

        print(f"\n========================================")
        print(f" [완료] 모든 결과물이 dist 폴더에 저장되었습니다.")
        print(f" - 분석된 문서: {docs}개")
        print(f" - 수집된 이미지: {assets}개")
        print(f" - 위치: {final_dist}")
        print(f"========================================")
    except Exception as e:
        print(f"오류 발생: {e}")
        sys.exit(1)