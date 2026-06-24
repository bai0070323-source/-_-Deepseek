# -*- coding: utf-8 -*-
"""
微信聊天记录分析工具 - 优雅界面版 (GUI)
基于 tkinter + ttk，界面更现代，交互更流畅

使用方式：
    python gui.py

依赖：
    pip install openai
"""

import json
import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime
from openai import OpenAI

# ──────────────────────────────────────────────
# 常量配置
# ──────────────────────────────────────────────

DEFAULT_API_KEY = ""
DEFAULT_MODEL = "deepseek-v4-flash"
BASE_URL = "https://api.deepseek.com"

ANALYSIS_DIMENSIONS = [
    ("双方关系", "分析双方的关系定位与亲密度"),
    ("暧昧程度（0~100）", "评估暧昧程度并给出数值"),
    ("谁更主动", "分析聊天的发起方与主动方"),
    ("情绪变化", "分析双方情绪波动曲线"),
    ("双方性格特点", "分析各自的性格特征"),
    ("是否存在冷淡期", "检测是否存在冷淡/疏离期"),
    ("聊天氛围", "分析整体聊天氛围变化"),
    ("关系发展趋势", "预测未来关系走向"),
    ("双方依赖感", "分析彼此依赖程度"),
    ("隐藏情绪", "分析潜台词与隐藏情绪"),
]

COLORS = {
    "bg": "#f4f6f9",
    "card_bg": "#ffffff",
    "fg": "#2c3e50",
    "fg_secondary": "#7f8c8d",
    "primary": "#3498db",
    "primary_dark": "#2980b9",
    "success": "#27ae60",
    "warning": "#f39c12",
    "error": "#e74c3c",
    "border": "#dcdde1",
    "hover_bg": "#ebf5fb",
}


# ──────────────────────────────────────────────
# 工具函数
# ──────────────────────────────────────────────

def truncate_path(path: str, max_len: int = 50) -> str:
    """截断过长路径用于显示"""
    if len(path) <= max_len:
        return path
    half = (max_len - 3) // 2
    return path[:half] + "..." + path[-half:]


def format_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ──────────────────────────────────────────────
# 主界面类
# ──────────────────────────────────────────────

class WeChatAnalysisApp:
    """微信聊天记录分析工具 — 主界面"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("微信聊天记录分析工具")
        self.root.geometry("1020x780")
        self.root.minsize(860, 640)
        self.root.configure(bg=COLORS["bg"])

        # ── 状态变量 ──
        self.chat_path_var = tk.StringVar(value="")
        self.api_key_var = tk.StringVar(value=DEFAULT_API_KEY)
        self.model_var = tk.StringVar(value=DEFAULT_MODEL)
        self.show_api_key = tk.BooleanVar(value=False)
        self.is_running = False
        self.last_result = None

        # 维度开关
        self.dim_vars: dict[str, tk.BooleanVar] = {}
        for name, _ in ANALYSIS_DIMENSIONS:
            self.dim_vars[name] = tk.BooleanVar(value=True)

        # ── 构建界面 ──
        self._build_ui()
        self._center_window()
        self._bind_shortcuts()

    # ──────────────── 界面构建 ────────────────

    def _build_ui(self):
        """构建完整界面"""
        # 外层滚动容器（适配小屏幕）
        outer_frame = ttk.Frame(self.root, padding="20 15")
        outer_frame.pack(fill=tk.BOTH, expand=True)

        # ── 标题栏 ──
        self._build_header(outer_frame)

        # ── 设置卡片 ──
        self._build_settings_card(outer_frame)

        # ── 维度卡片 ──
        self._build_dimension_card(outer_frame)

        # ── 操作按钮区 ──
        self._build_action_bar(outer_frame)

        # ── 结果输出区 ──
        self._build_result_area(outer_frame)

        # ── 底部状态栏 ──
        self._build_footer(outer_frame)

    def _build_header(self, parent):
        """标题行"""
        header = ttk.Frame(parent)
        header.pack(fill=tk.X, pady=(0, 18))

        title = tk.Label(
            header,
            text="💬 微信聊天记录分析",
            font=("Microsoft YaHei", 18, "bold"),
            bg=COLORS["bg"],
            fg=COLORS["fg"],
        )
        title.pack(side=tk.LEFT)

        subtitle = tk.Label(
            header,
            text="基于 DeepSeek AI  ·  上传 JSON 自动分析",
            font=("Microsoft YaHei", 9),
            bg=COLORS["bg"],
            fg=COLORS["fg_secondary"],
        )
        subtitle.pack(side=tk.LEFT, padx=(12, 0), pady=(6, 0))

    def _build_settings_card(self, parent):
        """设置区域（聊天文件 / API Key / 模型）"""
        card = tk.Frame(parent, bg=COLORS["card_bg"], highlightbackground=COLORS["border"],
                        highlightthickness=1, padx=16, pady=14)
        card.pack(fill=tk.X, pady=(0, 14))

        # 标题
        section_title = tk.Label(
            card, text="⚙  设置", font=("Microsoft YaHei", 11, "bold"),
            bg=COLORS["card_bg"], fg=COLORS["fg"],
        )
        section_title.pack(anchor=tk.W, pady=(0, 12))

        # ── 聊天文件 ──
        file_row = tk.Frame(card, bg=COLORS["card_bg"])
        file_row.pack(fill=tk.X, pady=(0, 8))
        tk.Label(file_row, text="聊天文件", width=9, anchor=tk.W,
                 font=("Microsoft YaHei", 10),
                 bg=COLORS["card_bg"], fg=COLORS["fg"]).pack(side=tk.LEFT)
        self.file_entry = tk.Entry(file_row, textvariable=self.chat_path_var,
                                   font=("Microsoft YaHei", 9),
                                   bg="#fafafa", relief="solid", bd=1)
        self.file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.browse_btn = tk.Button(file_row, text="📁 浏览", font=("Microsoft YaHei", 9),
                                    bg=COLORS["primary"], fg="white",
                                    relief="flat", padx=10, cursor="hand2",
                                    activebackground=COLORS["primary_dark"],
                                    command=self._browse_file)
        self.browse_btn.pack(side=tk.RIGHT)

        # ── API Key ──
        api_row = tk.Frame(card, bg=COLORS["card_bg"])
        api_row.pack(fill=tk.X, pady=(0, 8))
        tk.Label(api_row, text="API Key", width=9, anchor=tk.W,
                 font=("Microsoft YaHei", 10),
                 bg=COLORS["card_bg"], fg=COLORS["fg"]).pack(side=tk.LEFT)
        self.api_entry = tk.Entry(api_row, textvariable=self.api_key_var,
                                  font=("Microsoft YaHei", 9),
                                  bg="#fafafa", relief="solid", bd=1,
                                  show="*")
        self.api_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        self.toggle_api_btn = tk.Button(api_row, text="👁", width=3,
                                        font=("Microsoft YaHei", 9),
                                        bg="#ecf0f1", relief="flat",
                                        cursor="hand2",
                                        command=self._toggle_api_visibility)
        self.toggle_api_btn.pack(side=tk.RIGHT, padx=(0, 4))
        self.toggle_api_btn.bind("<Enter>", lambda e: self.toggle_api_btn.configure(bg="#d5dbdb"))
        self.toggle_api_btn.bind("<Leave>", lambda e: self.toggle_api_btn.configure(bg="#ecf0f1"))

        # ── 模型选择 ──
        model_row = tk.Frame(card, bg=COLORS["card_bg"])
        model_row.pack(fill=tk.X)
        tk.Label(model_row, text="AI 模型", width=9, anchor=tk.W,
                 font=("Microsoft YaHei", 10),
                 bg=COLORS["card_bg"], fg=COLORS["fg"]).pack(side=tk.LEFT)
        model_combo = ttk.Combobox(model_row, textvariable=self.model_var,
                                   values=["deepseek-v4-flash", "deepseek-v4-pro"],
                                   state="readonly", width=24)
        model_combo.pack(side=tk.LEFT)
        tk.Label(model_row, text="🌐 api.deepseek.com",
                 font=("Microsoft YaHei", 9),
                 bg=COLORS["card_bg"], fg=COLORS["fg_secondary"]).pack(side=tk.LEFT, padx=(10, 0))

    def _build_dimension_card(self, parent):
        """分析维度选择区"""
        card = tk.Frame(parent, bg=COLORS["card_bg"], highlightbackground=COLORS["border"],
                        highlightthickness=1, padx=16, pady=14)
        card.pack(fill=tk.X, pady=(0, 14))

        # 标题 + 全选/取消
        header_row = tk.Frame(card, bg=COLORS["card_bg"])
        header_row.pack(fill=tk.X, pady=(0, 10))
        tk.Label(header_row, text="📊  分析维度  (点击切换)",
                 font=("Microsoft YaHei", 11, "bold"),
                 bg=COLORS["card_bg"], fg=COLORS["fg"]).pack(side=tk.LEFT)

        btn_frame = tk.Frame(header_row, bg=COLORS["card_bg"])
        btn_frame.pack(side=tk.RIGHT)

        self.select_all_btn = tk.Button(btn_frame, text="✅ 全选",
                                        font=("Microsoft YaHei", 9),
                                        bg="#ecf0f1", relief="flat",
                                        padx=8, cursor="hand2",
                                        command=self._select_all)
        self.select_all_btn.pack(side=tk.LEFT, padx=(0, 4))
        self._style_hover(self.select_all_btn)

        self.deselect_all_btn = tk.Button(btn_frame, text="❌ 取消",
                                          font=("Microsoft YaHei", 9),
                                          bg="#ecf0f1", relief="flat",
                                          padx=8, cursor="hand2",
                                          command=self._deselect_all)
        self.deselect_all_btn.pack(side=tk.LEFT)
        self._style_hover(self.deselect_all_btn)

        # 维度网格
        grid = tk.Frame(card, bg=COLORS["card_bg"])
        grid.pack(fill=tk.X)

        self.dim_items = []  # (var, frame, label)

        for i, (name, desc) in enumerate(ANALYSIS_DIMENSIONS):
            row_idx, col_idx = divmod(i, 2)
            var = self.dim_vars[name]

            item = tk.Frame(grid, bg=COLORS["card_bg"], cursor="hand2",
                            highlightbackground=COLORS["border"],
                            highlightthickness=1, padx=8, pady=4)
            item.grid(row=row_idx, column=col_idx, sticky=tk.EW, pady=3, padx=(0, 15))
            grid.columnconfigure(col_idx, weight=1)

            # 勾选标识
            status_lbl = tk.Label(item, text="✓", width=2,
                                  font=("Microsoft YaHei", 12, "bold"),
                                  bg=COLORS["card_bg"],
                                  fg=COLORS["success"] if var.get() else "#cccccc")
            status_lbl.pack(side=tk.LEFT)

            # 名称
            name_lbl = tk.Label(item, text=name,
                                font=("Microsoft YaHei", 10),
                                bg=COLORS["card_bg"],
                                fg=COLORS["fg"] if var.get() else COLORS["fg_secondary"],
                                anchor=tk.W)
            name_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

            # 描述 tooltip （通过 bind 临时展示）
            def make_toggle(v, s_lbl, n_lbl):
                def toggle(_=None):
                    v.set(not v.get())
                    s_lbl.configure(fg=COLORS["success"] if v.get() else "#cccccc")
                    n_lbl.configure(fg=COLORS["fg"] if v.get() else COLORS["fg_secondary"])
                return toggle

            toggle_fn = make_toggle(var, status_lbl, name_lbl)
            for w in (item, status_lbl, name_lbl):
                w.bind("<Button-1>", toggle_fn)

            # 悬停高亮
            def make_hover(frame):
                def on_enter(e):
                    frame.configure(bg=COLORS["hover_bg"])
                    for c in frame.winfo_children():
                        if isinstance(c, tk.Label):
                            c.configure(bg=COLORS["hover_bg"])
                def on_leave(e):
                    frame.configure(bg=COLORS["card_bg"])
                    for c in frame.winfo_children():
                        if isinstance(c, tk.Label):
                            c.configure(bg=COLORS["card_bg"])
                return on_enter, on_leave

            enter_f, leave_f = make_hover(item)
            for w in (item, status_lbl, name_lbl):
                w.bind("<Enter>", enter_f)
                w.bind("<Leave>", leave_f)

            self.dim_items.append((var, status_lbl, name_lbl))

    def _build_action_bar(self, parent):
        """操作按钮 + 状态"""
        bar = tk.Frame(parent, bg=COLORS["bg"])
        bar.pack(fill=tk.X, pady=(0, 10))

        # 开始按钮
        self.start_btn = tk.Button(
            bar, text="▶  开始分析",
            font=("Microsoft YaHei", 11, "bold"),
            bg=COLORS["primary"], fg="white",
            padx=22, pady=5, relief="flat",
            cursor="hand2", bd=0,
            activebackground=COLORS["primary_dark"],
            command=self._start_analysis,
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 8))
        self.start_btn.bind("<Enter>", lambda e: self.start_btn.configure(bg=COLORS["primary_dark"]))
        self.start_btn.bind("<Leave>", lambda e: self.start_btn.configure(bg=COLORS["primary"]))

        # 保存按钮
        self.save_btn = tk.Button(
            bar, text="💾  保存结果",
            font=("Microsoft YaHei", 10),
            bg="#ecf0f1", fg=COLORS["fg"],
            padx=16, pady=5, relief="flat",
            cursor="hand2", bd=0,
            state=tk.DISABLED,
            command=self._save_result,
        )
        self.save_btn.pack(side=tk.LEFT, padx=(0, 8))
        self._style_hover(self.save_btn)

        # 清空结果按钮
        self.clear_btn = tk.Button(
            bar, text="🗑  清空",
            font=("Microsoft YaHei", 10),
            bg="#ecf0f1", fg=COLORS["fg"],
            padx=12, pady=5, relief="flat",
            cursor="hand2", bd=0,
            command=self._clear_result,
        )
        self.clear_btn.pack(side=tk.LEFT)
        self._style_hover(self.clear_btn)

        # 状态标签
        self.status_var = tk.StringVar(value="就绪 ✅")
        self.status_label = tk.Label(
            bar, textvariable=self.status_var,
            font=("Microsoft YaHei", 10),
            bg=COLORS["bg"], fg=COLORS["fg_secondary"],
        )
        self.status_label.pack(side=tk.RIGHT)

        # 进度条
        self.progress = ttk.Progressbar(bar, mode="indeterminate", length=200)
        self.progress.pack(side=tk.RIGHT, padx=(0, 12))
        self.progress.pack_forget()

    def _build_result_area(self, parent):
        """结果显示区域"""
        # 标签行
        label_row = tk.Frame(parent, bg=COLORS["bg"])
        label_row.pack(fill=tk.X, pady=(0, 5))
        tk.Label(label_row, text="📝  分析结果",
                 font=("Microsoft YaHei", 11, "bold"),
                 bg=COLORS["bg"], fg=COLORS["fg"]).pack(side=tk.LEFT)
        tk.Label(label_row, text="（支持选中文本复制）",
                 font=("Microsoft YaHei", 9),
                 bg=COLORS["bg"], fg=COLORS["fg_secondary"]).pack(side=tk.LEFT, padx=(8, 0))

        # 文本框
        text_container = tk.Frame(parent, bg=COLORS["border"], bd=1)
        text_container.pack(fill=tk.BOTH, expand=True)

        self.result_text = tk.Text(
            text_container,
            wrap=tk.WORD,
            font=("Microsoft YaHei", 10),
            bg="#fafafa",
            fg="#333333",
            padx=14,
            pady=12,
            bd=0,
            relief="flat",
            state=tk.DISABLED,
            selectbackground="#c7e2f7",
            selectforeground="#1a1a1a",
        )
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 滚动条
        scrollbar = tk.Scrollbar(text_container, orient=tk.VERTICAL,
                                 command=self.result_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_text.configure(yscrollcommand=scrollbar.set)

        # 文本标签样式
        self.result_text.tag_configure("title",
                                       font=("Microsoft YaHei", 14, "bold"),
                                       foreground="#2c3e50", spacing1=6, spacing3=4)
        self.result_text.tag_configure("section",
                                       font=("Microsoft YaHei", 11, "bold"),
                                       foreground="#3498db", spacing1=6, spacing3=2)
        self.result_text.tag_configure("content",
                                       font=("Microsoft YaHei", 10),
                                       foreground="#333333", spacing1=2, spacing3=2)
        self.result_text.tag_configure("highlight",
                                       font=("Microsoft YaHei", 10, "bold"),
                                       foreground="#e67e22")
        self.result_text.tag_configure("meta",
                                       font=("Microsoft YaHei", 9),
                                       foreground="#95a5a6")
        self.result_text.tag_configure("error",
                                       font=("Microsoft YaHei", 10, "bold"),
                                       foreground=COLORS["error"])
        self.result_text.tag_configure("success",
                                       font=("Microsoft YaHei", 10),
                                       foreground=COLORS["success"], spacing1=2)

        # 右键菜单
        self._build_context_menu()

    def _build_context_menu(self):
        """文本框右键菜单"""
        self.context_menu = tk.Menu(self.root, tearoff=0, font=("Microsoft YaHei", 9))
        self.context_menu.add_command(label="复制", command=self._copy_selection)
        self.context_menu.add_command(label="全选", command=self._select_all_text)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="清空", command=self._clear_result)

        self.result_text.bind("<Button-3>", self._show_context_menu)
        self.result_text.bind("<Button-2>", self._show_context_menu)  # macOS

    def _build_footer(self, parent):
        """底部状态栏"""
        footer = tk.Frame(parent, bg=COLORS["bg"])
        footer.pack(fill=tk.X, pady=(8, 0))

        tk.Label(footer,
                 text="💡 提示：选择微信导出的 JSON 聊天记录文件，点击「开始分析」即可",
                 font=("Microsoft YaHei", 9),
                 bg=COLORS["bg"],
                 fg=COLORS["fg_secondary"]).pack(side=tk.LEFT)

        # 统计信息（动态更新）
        self.stats_var = tk.StringVar(value="")
        tk.Label(footer,
                 textvariable=self.stats_var,
                 font=("Microsoft YaHei", 9),
                 bg=COLORS["bg"],
                 fg=COLORS["fg_secondary"]).pack(side=tk.RIGHT)

    # ──────────────── 辅助工具 ────────────────

    def _center_window(self):
        """窗口居中"""
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")

    def _bind_shortcuts(self):
        """键盘快捷键"""
        self.root.bind("<Control-o>", lambda e: self._browse_file())
        self.root.bind("<Control-Return>", lambda e: self._start_analysis())
        self.root.bind("<Control-s>", lambda e: self._save_result())
        self.root.bind("<Escape>", lambda e: self._clear_result() if not self.is_running else None)

    def _style_hover(self, btn: tk.Button):
        """为普通按钮添加悬停效果"""
        orig_bg = btn.cget("bg")
        btn.bind("<Enter>", lambda e: btn.configure(bg="#d5dbdb"))
        btn.bind("<Leave>", lambda e: btn.configure(bg=orig_bg))

    def _toggle_api_visibility(self):
        """切换 API Key 明文/密文"""
        if self.show_api_key.get():
            self.api_entry.configure(show="*")
            self.toggle_api_btn.configure(text="👁")
        else:
            self.api_entry.configure(show="")
            self.toggle_api_btn.configure(text="👁‍🗨")
        self.show_api_key.set(not self.show_api_key.get())

    def _browse_file(self):
        """选择聊天 JSON 文件"""
        initial_dir = os.path.dirname(self.chat_path_var.get()) \
            if self.chat_path_var.get() and os.path.exists(os.path.dirname(self.chat_path_var.get())) \
            else "E:/微信聊天分析"
        path = filedialog.askopenfilename(
            title="选择微信聊天记录 JSON 文件",
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")],
            initialdir=initial_dir,
        )
        if path:
            self.chat_path_var.set(path)
            # 更新文件信息
            fname = os.path.basename(path)
            fsize = os.path.getsize(path)
            if fsize < 1024:
                size_str = f"{fsize} B"
            elif fsize < 1024 * 1024:
                size_str = f"{fsize / 1024:.1f} KB"
            else:
                size_str = f"{fsize / 1024 / 1024:.1f} MB"
            self.stats_var.set(f"📄 {fname}  ({size_str})")

    def _select_all(self):
        """全选维度"""
        for var, s_lbl, n_lbl in self.dim_items:
            var.set(True)
            s_lbl.configure(fg=COLORS["success"])
            n_lbl.configure(fg=COLORS["fg"])

    def _deselect_all(self):
        """取消全选维度"""
        for var, s_lbl, n_lbl in self.dim_items:
            var.set(False)
            s_lbl.configure(fg="#cccccc")
            n_lbl.configure(fg=COLORS["fg_secondary"])

    def _clear_result(self):
        """清空结果区"""
        if self.is_running:
            return
        self.result_text.configure(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)
        self.result_text.configure(state=tk.DISABLED)
        self.last_result = None
        self.save_btn.configure(state=tk.DISABLED)
        self.status_var.set("已清空 🧹")
        self.stats_var.set("")

    def _copy_selection(self):
        """复制选中文本"""
        try:
            text = self.result_text.selection_get()
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
        except tk.TclError:
            pass

    def _select_all_text(self):
        """全选结果文本"""
        self.result_text.focus_set()
        self.result_text.tag_add(tk.SEL, "1.0", tk.END)
        self.result_text.mark_set(tk.INSERT, "1.0")
        self.result_text.see(tk.INSERT)
        return "break"

    def _show_context_menu(self, event):
        """显示右键菜单"""
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    # ──────────────── 结果输出 ────────────────

    def _append_result(self, text: str, tag: str = "content"):
        """向结果框追加文本（线程安全）"""
        self.result_text.configure(state=tk.NORMAL)
        self.result_text.insert(tk.END, text, tag)
        self.result_text.see(tk.END)
        self.result_text.configure(state=tk.DISABLED)
        self.root.update_idletasks()

    def _set_status(self, text: str, color: str | None = None):
        """更新状态标签"""
        self.status_var.set(text)
        if color:
            self.status_label.configure(fg=color)
        else:
            self.status_label.configure(fg=COLORS["fg_secondary"])
        self.root.update_idletasks()

    # ──────────────── 核心分析流程 ────────────────

    def _start_analysis(self):
        """启动分析（校验 → 子线程）"""
        if self.is_running:
            return

        # ── 校验 ──
        chat_path = self.chat_path_var.get().strip()
        api_key = self.api_key_var.get().strip()

        if not chat_path:
            messagebox.showwarning("提示", "请先选择聊天文件")
            return
        if not os.path.exists(chat_path):
            messagebox.showwarning("提示", f"文件不存在：\n{chat_path}")
            return
        if not chat_path.lower().endswith(".json"):
            if not messagebox.askyesno("确认", "所选文件不是 .json 格式，是否继续？"):
                return
        if not api_key:
            messagebox.showwarning("提示", "请输入 API Key")
            return

        selected = [n for n, v in self.dim_vars.items() if v.get()]
        if not selected:
            messagebox.showwarning("提示", "请至少选择一个分析维度")
            return

        # ── 锁定 UI ──
        self.is_running = True
        self.start_btn.configure(state=tk.DISABLED, text="⏳ 分析中...", bg="#95a5a6")
        self.save_btn.configure(state=tk.DISABLED)
        self.browse_btn.configure(state=tk.DISABLED)
        self.progress.pack(side=tk.RIGHT, padx=(0, 12))
        self.progress.start(15)
        self._clear_result()

        self._append_result(f"⏰ 分析开始时间：{format_timestamp()}\n\n", "meta")

        # ── 子线程 ──
        t = threading.Thread(
            target=self._run_analysis,
            args=(chat_path, api_key, selected),
            daemon=True,
        )
        t.start()

    def _run_analysis(self, chat_path: str, api_key: str, dimensions: list[str]):
        """执行分析（子线程）"""
        try:
            # ── 1. 读取文件 ──
            self.root.after(0, lambda: self._set_status("📂 正在读取聊天文件...", COLORS["primary"]))
            self._append_result("📂 读取聊天记录文件...\n", "meta")

            with open(chat_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            messages = data.get("messages", [])
            self._append_result(f"✅ 读取成功，共 {len(messages)} 条消息\n\n", "success")

            # ── 2. 拼接聊天文本 + 统计 ──
            self.root.after(0, lambda: self._set_status("📊 正在整理聊天记录...", COLORS["primary"]))
            self._append_result("📊 聊天统计数据\n", "section")

            chat_text = ""
            sender_count: dict[str, int] = {}
            type_count: dict[str, int] = {}
            date_range = set()

            for msg in messages:
                content = msg.get("content", "")
                if not content:
                    continue
                sender = msg.get("senderDisplayName", "未知")
                time = msg.get("formattedTime", "")
                msg_type = msg.get("type", "")

                chat_text += f"[{time}] {sender} ({msg_type}): {content}\n"
                sender_count[sender] = sender_count.get(sender, 0) + 1
                type_count[msg_type] = type_count.get(msg_type, 0) + 1
                if time and len(time) >= 10:
                    date_range.add(time[:10])

            if not chat_text.strip():
                self._append_result("❌ 未识别到有效聊天记录\n", "error")
                self.root.after(0, lambda: self._set_status("❌ 无有效聊天记录", COLORS["error"]))
                self._finish()
                return

            # 显示统计
            for sender, cnt in sorted(sender_count.items(), key=lambda x: -x[1]):
                pct = cnt / sum(sender_count.values()) * 100
                self._append_result(f"  👤 {sender}：{cnt} 条 ({pct:.1f}%)\n", "content")

            if date_range:
                dates = sorted(date_range)
                self._append_result(f"  📅 时间跨度：{dates[0]}  ~  {dates[-1]}  (共 {len(dates)} 天)\n", "content")
            self._append_result(
                f"  💬 消息类型：{', '.join(f'{k}={v}' for k, v in sorted(type_count.items(), key=lambda x: -x[1])[:5])}\n\n",
                "content",
            )

            # ── 3. 构建 Prompt ──
            self.root.after(0, lambda: self._set_status("🤖 正在请求 AI 分析...", COLORS["primary"]))
            self._append_result("🤖 正在向 DeepSeek 发送分析请求...\n\n", "meta")

            dim_instructions = "\n".join(
                f"{i+1}. {name}：{desc}"
                for i, (name, desc) in enumerate(ANALYSIS_DIMENSIONS)
                if name in dimensions
            )

            prompt = f"""你是一位专业的亲密关系分析师，精通心理学与沟通分析。请仔细阅读以下微信聊天记录，并从多个维度进行深度分析。

## 分析要求
请对以下维度逐一展开分析，每项分析不少于 50 字，结合聊天记录中的具体例子说明：

{dim_instructions}

## 聊天记录
{chat_text}

## 输出格式要求
- 按编号逐条分析，每个维度用 "**维度名称**" 作为小标题
- 最后给出一个 100 字左右的「综合总结」
- 语言专业但温暖，避免绝对化判断
"""

            # ── 4. 调用 API ──
            client = OpenAI(api_key=api_key, base_url=BASE_URL)

            response = client.chat.completions.create(
                model=self.model_var.get(),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=4096,
                stream=False,
            )

            result = response.choices[0].message.content

            if not result or not result.strip():
                raise ValueError("AI 返回了空结果，请重试")

            # ── 5. 展示结果 ──
            self._append_result("=" * 56 + "\n", "section")
            self._append_result("📋  分析报告\n", "title")
            self._append_result("=" * 56 + "\n\n", "section")

            for line in result.split("\n"):
                line = line.strip()
                if not line:
                    self._append_result("\n")
                elif any(line.startswith(f"{i}.") for i in range(1, 11)):
                    self._append_result(line + "\n", "section")
                elif line.startswith("**") and line.endswith("**"):
                    self._append_result(line.strip("*") + "\n", "highlight")
                elif line.startswith("#"):
                    self._append_result(line.lstrip("#").strip() + "\n", "title")
                else:
                    self._append_result(line + "\n", "content")

            self.last_result = result

            # ── 完成 ──
            self._append_result("\n" + "─" * 56 + "\n", "meta")
            self._append_result(f"✅ 分析完成  |  {format_timestamp()}\n", "success")
            self._append_result("💾 点击「保存结果」导出为文本文件\n", "meta")

            self.root.after(0, lambda: self.save_btn.configure(state=tk.NORMAL))
            self.root.after(0, lambda: self._set_status("✅ 分析完成", COLORS["success"]))

        except json.JSONDecodeError:
            self._append_result("\n❌ 文件格式错误：不是有效的 JSON 文件\n", "error")
            self.root.after(0, lambda: self._set_status("❌ JSON 解析失败", COLORS["error"]))
            self.last_result = None

        except ImportError:
            self._append_result("\n❌ 缺少依赖库，请执行：pip install openai\n", "error")
            self.root.after(0, lambda: self._set_status("❌ 缺少依赖", COLORS["error"]))
            self.last_result = None

        except Exception as e:
            err = str(e)
            self._append_result(f"\n❌ 分析出错：{err}\n", "error")
            self.root.after(0, lambda: self._set_status("❌ 分析出错", COLORS["error"]))
            self.last_result = None

        finally:
            self.root.after(0, self._finish)

    def _finish(self):
        """分析结束后的 UI 还原"""
        self.is_running = False
        self.start_btn.configure(state=tk.NORMAL, text="▶  开始分析", bg=COLORS["primary"])
        self.browse_btn.configure(state=tk.NORMAL)
        self.progress.stop()
        self.progress.pack_forget()

    def _save_result(self):
        """保存结果到文本文件"""
        if not self.last_result:
            messagebox.showinfo("提示", "没有可保存的分析结果")
            return

        chat_file = self.chat_path_var.get()
        base_name = os.path.splitext(os.path.basename(chat_file))[0] if chat_file else "聊天记录"
        default_name = f"分析报告_{base_name}.txt"
        default_dir = os.path.dirname(chat_file) if chat_file else "."

        path = filedialog.asksaveasfilename(
            title="保存分析报告",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")],
            initialdir=default_dir,
            initialfile=default_name,
            defaultextension=".txt",
        )
        if not path:
            return

        try:
            # 加上元信息头
            header = (
                f"微信聊天记录分析报告\n"
                f"{'=' * 50}\n"
                f"生成时间：{format_timestamp()}\n"
                f"源文件：{chat_file}\n"
                f"AI 模型：{self.model_var.get()}\n"
                f"{'=' * 50}\n\n"
            )
            with open(path, "w", encoding="utf-8") as f:
                f.write(header + self.last_result)
            messagebox.showinfo("保存成功", f"报告已保存至：\n{path}")
        except Exception as e:
            messagebox.showerror("保存失败", f"无法保存文件：\n{str(e)}")


# ──────────────────────────────────────────────
# 入口
# ──────────────────────────────────────────────

def main():
    root = tk.Tk()
    app = WeChatAnalysisApp(root)

    # 允许拖拽文件（简单版：通过参数支持）
    if len(os.sys.argv) > 1:
        arg = os.sys.argv[1]
        if os.path.isfile(arg) and arg.lower().endswith(".json"):
            app.chat_path_var.set(os.path.abspath(arg))

    root.mainloop()


if __name__ == "__main__":
    main()