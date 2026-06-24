# -*- coding: utf-8 -*-
"""
聊天记录分析 - 可视化界面
基于 tkinter，无需额外安装依赖
"""
import json
import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

from openai import OpenAI


# 常量配置
DEFAULT_API_KEY = ""#在这里填入你的deepseek api
DEFAULT_MODEL = "deepseek-v4-flash"
DEFAULT_CHAT_PATH = r""
BASE_URL = "https://api.deepseek.com"

ANALYSIS_DIMENSIONS = [
    ("双方关系", "分析双方的关系定位"),
    ("暧昧程度（0~100）", "评估暧昧程度数值"),
    ("谁更主动", "分析聊天的发起方和主动方"),
    ("情绪变化", "分析情绪波动曲线"),
    ("双方性格特点", "分析双方的性格特征"),
    ("是否存在冷淡期", "检测冷淡期"),
    ("聊天氛围", "分析整体聊天氛围"),
    ("关系发展趋势", "预测关系走向"),
    ("双方依赖感", "分析依赖程度"),
    ("是否存在隐藏情绪", "分析潜台词和隐藏情绪"),
]

COLORS = {
    "bg": "#f5f5f0",
    "fg": "#2d2d2d",
    "primary": "#4a90d9",
    "primary_hover": "#357abd",
    "success": "#27ae60",
    "card_bg": "#ffffff",
    "card_border": "#e0e0e0",
    "text_secondary": "#666666",
    "error": "#e74c3c",
    "selected_bg": "#e8f0fe",
}


# ========== 工具函数 ==========
def truncate_path(path: str, max_len: int = 50) -> str:
    """截断过长的路径显示"""
    if len(path) <= max_len:
        return path
    half = (max_len - 3) // 2
    return path[:half] + "..." + path[-half:]


class AnalysisGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("微信聊天记录分析工具")
        self.root.geometry("1000x750")
        self.root.minsize(800, 600)

        # 设置图标（如果有）
        try:
            self.root.iconbitmap(default="")
        except Exception:
            pass

        # 设置样式
        self.setup_styles()

        # 变量
        self.chat_path_var = tk.StringVar(value=DEFAULT_CHAT_PATH)
        self.api_key_var = tk.StringVar(value=DEFAULT_API_KEY)
        self.model_var = tk.StringVar(value=DEFAULT_MODEL)
        self.dimension_vars = {
            name: tk.BooleanVar(value=True)
            for name, _ in ANALYSIS_DIMENSIONS
        }
        self.api_key_visible = tk.BooleanVar(value=False)
        self.is_running = False

        # 构建界面
        self.build_ui()

        # 居中显示
        self.center_window()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        # 通用配置
        style.configure("TFrame", background=COLORS["bg"])
        style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["fg"],
                        font=("Microsoft YaHei", 10))
        style.configure("Card.TFrame", background=COLORS["card_bg"],
                        relief="solid", borderwidth=1)
        style.configure("Header.TLabel", font=("Microsoft YaHei", 16, "bold"),
                        background=COLORS["bg"], foreground=COLORS["fg"])
        style.configure("Section.TLabel", font=("Microsoft YaHei", 11, "bold"),
                        background=COLORS["card_bg"], foreground=COLORS["fg"])
        style.configure("Small.TLabel", font=("Microsoft YaHei", 9),
                        background=COLORS["card_bg"], foreground=COLORS["text_secondary"])
        style.configure("Success.TLabel", foreground=COLORS["success"])
        style.configure("Error.TLabel", foreground=COLORS["error"])
        style.configure("Primary.TButton", font=("Microsoft YaHei", 10, "bold"))

        # Button
        style.configure("Accent.TButton", font=("Microsoft YaHei", 10, "bold"),
                        background=COLORS["primary"], foreground="white",
                        borderwidth=0, focuscolor="none", relief="flat")
        style.map("Accent.TButton",
                  background=[("active", COLORS["primary_hover"]),
                              ("disabled", "#cccccc")],
                  foreground=[("disabled", "#888888")])

        # Checkbutton
        style.configure("Dim.TCheckbutton", font=("Microsoft YaHei", 10),
                        background=COLORS["card_bg"])

        # Entry
        style.configure("TEntry", font=("Microsoft YaHei", 10),
                        fieldbackground="white", borderwidth=1)

        # Combobox
        style.configure("TCombobox", font=("Microsoft YaHei", 10))

        # Progressbar
        style.configure("TProgressbar", background=COLORS["primary"],
                        troughcolor="#e0e0e0", borderwidth=0, thickness=20)

    def build_ui(self):
        # ========== 主容器 ==========
        main_frame = ttk.Frame(self.root, padding="20 15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ========== 标题 ==========
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(title_frame, text="微信聊天记录分析",
                  style="Header.TLabel").pack(side=tk.LEFT)
        ttk.Label(title_frame, text="  —  基于 DeepSeek AI",
                  font=("Microsoft YaHei", 10),
                  foreground=COLORS["text_secondary"],
                  background=COLORS["bg"]).pack(side=tk.LEFT, padx=(5, 0))

        # ========== 设置区域（卡片） ==========
        settings_card = ttk.Frame(main_frame, style="Card.TFrame", padding="15")
        settings_card.pack(fill=tk.X, pady=(0, 12))

        ttk.Label(settings_card, text="⚙ 设置",
                  style="Section.TLabel").pack(anchor=tk.W, pady=(0, 10))

        # 聊天文件选择
        file_frame = ttk.Frame(settings_card)
        file_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(file_frame, text="聊天文件：", width=10,
                  background=COLORS["card_bg"]).pack(side=tk.LEFT)
        self.file_entry = ttk.Entry(file_frame, textvariable=self.chat_path_var,
                                     font=("Microsoft YaHei", 9))
        self.file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        ttk.Button(file_frame, text="浏览...",
                   command=self.browse_file).pack(side=tk.RIGHT)

        # API Key
        api_frame = ttk.Frame(settings_card)
        api_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(api_frame, text="API Key：", width=10,
                  background=COLORS["card_bg"]).pack(side=tk.LEFT)
        self.api_entry = ttk.Entry(api_frame, textvariable=self.api_key_var,
                                    font=("Microsoft YaHei", 9), show="*")
        self.api_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.toggle_btn = ttk.Button(api_frame, text="👁",
                                      width=3, command=self.toggle_api_key)
        self.toggle_btn.pack(side=tk.RIGHT, padx=(0, 4))

        # 模型选择 + 基础信息
        model_frame = ttk.Frame(settings_card)
        model_frame.pack(fill=tk.X)
        ttk.Label(model_frame, text="AI 模型：", width=10,
                  background=COLORS["card_bg"]).pack(side=tk.LEFT)
        model_combo = ttk.Combobox(model_frame, textvariable=self.model_var,
                                    values=["deepseek-v4-flash", "deepseek-v4-pro"],
                                    state="readonly", width=22)
        model_combo.pack(side=tk.LEFT)
        ttk.Label(model_frame, text="API: api.deepseek.com",
                  style="Small.TLabel").pack(side=tk.LEFT, padx=(10, 0))

        # ========== 分析维度（卡片） ==========
        dim_card = ttk.Frame(main_frame, style="Card.TFrame", padding="15")
        dim_card.pack(fill=tk.X, pady=(0, 12))

        # 维度标题 + 全选/取消
        dim_header = ttk.Frame(dim_card)
        dim_header.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(dim_header, text="📊 分析维度  (点击切换 ✓/✗)",
                  style="Section.TLabel").pack(side=tk.LEFT)
        ttk.Button(dim_header, text="全选",
                   command=self.select_all_dims, width=6).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(dim_header, text="取消",
                   command=self.deselect_all_dims, width=6).pack(side=tk.RIGHT)

        # 维度网格 — 打钩样式
        dim_grid = ttk.Frame(dim_card)
        dim_grid.pack(fill=tk.X)
        self.dim_widgets = []
        for i, (name, desc) in enumerate(ANALYSIS_DIMENSIONS):
            row, col = divmod(i, 2)
            item_frame = tk.Frame(dim_grid, bg=COLORS["card_bg"], cursor="hand2",
                                  relief="flat", bd=1)
            item_frame.grid(row=row, column=col, sticky=tk.EW, pady=3, padx=(0, 20))

            # ✓ 标记
            tick_lbl = tk.Label(item_frame, text="✓", width=3,
                                 font=("Microsoft YaHei", 11, "bold"),
                                 bg=COLORS["card_bg"],
                                 fg=COLORS["success"] if self.dimension_vars[name].get() else "#cccccc")
            tick_lbl.pack(side=tk.LEFT)

            # 维度名称
            name_lbl = tk.Label(item_frame, text=name,
                                 font=("Microsoft YaHei", 10),
                                 bg=COLORS["card_bg"], fg=COLORS["fg"],
                                 anchor=tk.W)
            name_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

            # 绑定点击事件
            var = self.dimension_vars[name]
            def make_handler(v, t, n):
                def handler(event=None):
                    v.set(not v.get())
                    if v.get():
                        t.config(fg=COLORS["success"])
                        n.config(fg=COLORS["fg"])
                    else:
                        t.config(fg="#cccccc")
                        n.config(fg=COLORS["text_secondary"])
                return handler

            handler = make_handler(var, tick_lbl, name_lbl)
            for widget in (item_frame, tick_lbl, name_lbl):
                widget.bind("<Button-1>", handler, add="+")

            self.dim_widgets.append((var, tick_lbl, name_lbl, handler))

            # 鼠标悬停高亮
            def make_hl(f):
                def on_enter(e):
                    f.config(bg="#f0f4ff")
                    for w in f.winfo_children():
                        if isinstance(w, tk.Label):
                            w.config(bg="#f0f4ff")
                def on_leave(e):
                    f.config(bg=COLORS["card_bg"])
                    for w in f.winfo_children():
                        if isinstance(w, tk.Label):
                            w.config(bg=COLORS["card_bg"])
                return on_enter, on_leave

            enter_h, leave_h = make_hl(item_frame)
            for widget in (item_frame, tick_lbl, name_lbl):
                widget.bind("<Enter>", enter_h, add="+")
                widget.bind("<Leave>", leave_h, add="+")

        # ========== 操作按钮 ==========
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))

        self.start_btn = tk.Button(
            btn_frame, text="▶ 开始分析", font=("Microsoft YaHei", 11, "bold"),
            bg=COLORS["primary"], fg="white", padx=20, pady=4,
            activebackground=COLORS["primary_hover"], activeforeground="white",
            bd=0, cursor="hand2", command=self.start_analysis
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.save_btn = tk.Button(
            btn_frame, text="💾 保存结果", font=("Microsoft YaHei", 10),
            bg="#ecf0f1", fg=COLORS["fg"], padx=15, pady=4,
            activebackground="#d5dbdb", bd=0, cursor="hand2",
            state=tk.DISABLED, command=self.save_result
        )
        self.save_btn.pack(side=tk.LEFT)

        # 状态标签
        self.status_label = ttk.Label(btn_frame, text="就绪",
                                       foreground=COLORS["text_secondary"])
        self.status_label.pack(side=tk.RIGHT)

        # ========== 进度条 ==========
        self.progress = ttk.Progressbar(main_frame, mode="indeterminate")
        self.progress.pack(fill=tk.X, pady=(0, 10))
        self.progress.pack_forget()  # 初始隐藏

        # ========== 结果区域 ==========
        result_label_frame = ttk.Frame(main_frame)
        result_label_frame.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(result_label_frame, text="📝 分析结果",
                  font=("Microsoft YaHei", 11, "bold"),
                  background=COLORS["bg"]).pack(side=tk.LEFT)

        # 结果文本框
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)

        self.result_text = scrolledtext.ScrolledText(
            text_frame, wrap=tk.WORD,
            font=("Microsoft YaHei", 10),
            bg="#fafafa", fg="#333333",
            bd=1, relief="solid",
            padx=12, pady=12,
            state=tk.DISABLED
        )
        self.result_text.pack(fill=tk.BOTH, expand=True)

        # 配置结果文本框的标签样式
        self.result_text.tag_config("title",
                                     font=("Microsoft YaHei", 13, "bold"),
                                     foreground="#2c3e50", spacing1=8, spacing3=4)
        self.result_text.tag_config("section",
                                     font=("Microsoft YaHei", 11, "bold"),
                                     foreground="#4a90d9", spacing1=6, spacing3=2)
        self.result_text.tag_config("content",
                                     font=("Microsoft YaHei", 10),
                                     foreground="#333333", spacing1=2, spacing3=2)
        self.result_text.tag_config("highlight",
                                     font=("Microsoft YaHei", 10, "bold"),
                                     foreground="#e67e22")
        self.result_text.tag_config("meta",
                                     font=("Microsoft YaHei", 9),
                                     foreground="#999999")
        self.result_text.tag_config("error",
                                     font=("Microsoft YaHei", 10),
                                     foreground=COLORS["error"])

        # ========== 底部状态栏 ==========
        footer = ttk.Frame(main_frame)
        footer.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(footer, text="💡 提示：分析过程使用 DeepSeek API，请确保网络连接正常",
                  font=("Microsoft YaHei", 9),
                  foreground=COLORS["text_secondary"],
                  background=COLORS["bg"]).pack(side=tk.LEFT)

    def create_tooltip(self, widget, text):
        """为组件创建悬停提示"""
        tooltip = None

        def show(event):
            nonlocal tooltip
            if tooltip:
                return
            x = event.x_root + 15
            y = event.y_root + 10
            tooltip = tk.Toplevel(widget)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{x}+{y}")
            label = tk.Label(tooltip, text=text, justify=tk.LEFT,
                              background="#ffffcc", foreground="#333333",
                              font=("Microsoft YaHei", 9),
                              relief="solid", borderwidth=1,
                              padx=6, pady=3)
            label.pack()

        def hide(event):
            nonlocal tooltip
            if tooltip:
                tooltip.destroy()
                tooltip = None

        widget.bind("<Enter>", show, add="+")
        widget.bind("<Leave>", hide, add="+")

    def center_window(self):
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"+{x}+{y}")

    def toggle_api_key(self):
        """切换 API Key 的可见性"""
        if self.api_key_visible.get():
            self.api_entry.config(show="*")
            self.toggle_btn.config(text="👁")
        else:
            self.api_entry.config(show="")
            self.toggle_btn.config(text="👁‍🗨")
        self.api_key_visible.set(not self.api_key_visible.get())

    def browse_file(self):
        """选择聊天文件"""
        path = filedialog.askopenfilename(
            title="选择微信聊天记录 JSON 文件",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=os.path.dirname(self.chat_path_var.get())
            if os.path.exists(os.path.dirname(self.chat_path_var.get()))
            else "E:/微信聊天分析"
        )
        if path:
            self.chat_path_var.set(path)

    def select_all_dims(self):
        for var, tick_lbl, name_lbl, _ in self.dim_widgets:
            var.set(True)
            tick_lbl.config(fg=COLORS["success"])
            name_lbl.config(fg=COLORS["fg"])

    def deselect_all_dims(self):
        for var, tick_lbl, name_lbl, _ in self.dim_widgets:
            var.set(False)
            tick_lbl.config(fg="#cccccc")
            name_lbl.config(fg=COLORS["text_secondary"])

    # 核心分析逻辑

    def append_result(self, text, tag="content"):
        """向结果文本框追加内容"""
        self.result_text.config(state=tk.NORMAL)
        self.result_text.insert(tk.END, text, tag)
        self.result_text.see(tk.END)
        self.result_text.config(state=tk.DISABLED)
        self.root.update_idletasks()

    def set_status(self, text, color=None):
        """更新状态标签"""
        self.status_label.config(text=text)
        if color:
            self.status_label.config(foreground=color)
        else:
            self.status_label.config(foreground=COLORS["text_secondary"])
        self.root.update_idletasks()

    def start_analysis(self):
        """开始分析（在子线程中执行）"""
        if self.is_running:
            return

        # 验证输入
        chat_path = self.chat_path_var.get().strip()
        api_key = self.api_key_var.get().strip()

        if not chat_path:
            messagebox.showwarning("提示", "请选择聊天文件")
            return
        if not os.path.exists(chat_path):
            messagebox.showwarning("提示", f"文件不存在：{chat_path}")
            return
        if not api_key:
            messagebox.showwarning("提示", "请输入 API Key")
            return

        # 检查是否选择了分析维度
        selected_dims = [name for name, var in self.dimension_vars.items() if var.get()]
        if not selected_dims:
            messagebox.showwarning("提示", "请至少选择一个分析维度")
            return

        # 准备 UI 状态
        self.is_running = True
        self.start_btn.config(state=tk.DISABLED, text="⏳ 分析中...")
        self.save_btn.config(state=tk.DISABLED)
        self.progress.pack(fill=tk.X, pady=(0, 10))
        self.progress.start(10)
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)
        self.result_text.config(state=tk.DISABLED)

        # 在子线程中执行分析
        thread = threading.Thread(
            target=self.run_analysis,
            args=(chat_path, api_key, selected_dims),
            daemon=True
        )
        thread.start()

    def run_analysis(self, chat_path, api_key, selected_dims):
        """执行分析（子线程）"""
        try:
            # 1. 读取聊天文件
            self.set_status("正在读取聊天文件...", COLORS["primary"])
            self.append_result("📂 读取聊天文件...\n", "meta")

            with open(chat_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            chat_data = data["messages"]
            self.append_result(f"✅ 成功读取 {len(chat_data)} 条聊天记录\n\n", "meta")

            # 2. 拼接聊天文本
            chat_text = ""
            sender_count = {}
            for msg in chat_data:
                content = msg.get("content", "")
                if not content:
                    continue
                sender = msg.get("senderDisplayName", "未知")
                time = msg.get("formattedTime", "")
                msg_type = msg.get("type", "")
                chat_text += f"[{time}] {sender} ({msg_type}): {content}\n"
                sender_count[sender] = sender_count.get(sender, 0) + 1

            if not chat_text.strip():
                self.append_result("❌ 未识别到有效的聊天记录\n", "error")
                self.set_status("分析失败：无有效聊天记录", COLORS["error"])
                self.finish_analysis()
                return

            # 显示基本统计
            self.append_result("📊 聊天统计\n", "section")
            for s, cnt in sorted(sender_count.items(), key=lambda x: -x[1]):
                self.append_result(f"  • {s}：{cnt} 条消息\n", "content")
            self.append_result(f"\n")

            # 3. 构建 Prompt
            dim_instructions = "\n".join(
                f"{i+1}. {name}" for i, name in enumerate(selected_dims)
            )
            prompt = f"""请你作为专业的关系分析AI，分析以下微信聊天记录。

请详细分析以下方面：
{dim_instructions}

聊天记录：
{chat_text}
"""
            self.set_status("正在发送给 DeepSeek 分析...", COLORS["primary"])
            self.append_result("🤖 正在请求 DeepSeek AI 分析...\n", "meta")

            # 4. 调用 API
            client = OpenAI(
                api_key=api_key,
                base_url=BASE_URL
            )

            response = client.chat.completions.create(
                model=self.model_var.get(),
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                stream=False
            )

            result = response.choices[0].message.content

            # 5. 显示结果
            self.set_status("分析完成", COLORS["success"])
            self.append_result("=" * 50 + "\n", "section")
            self.append_result("📋 分析报告\n", "title")
            self.append_result("=" * 50 + "\n\n", "section")

            # 分段显示结果（按换行分割，识别小标题）
            for line in result.split("\n"):
                line = line.strip()
                if not line:
                    self.append_result("\n")
                elif any(line.startswith(f"{i}.") for i in range(1, 11)):
                    self.append_result(line + "\n", "section")
                elif line.startswith("**") and line.endswith("**"):
                    self.append_result(line.strip("*") + "\n", "highlight")
                else:
                    self.append_result(line + "\n", "content")

            # 保存结果供导出
            self.last_result = result

            self.set_status("✅ 分析完成", COLORS["success"])
            self.append_result("\n\n" + "=" * 50 + "\n", "meta")
            self.append_result("💾 点击「保存结果」可将报告导出为文本文件\n", "meta")

            self.root.after(0, lambda: self.save_btn.config(state=tk.NORMAL))

        except Exception as e:
            error_msg = str(e)
            self.append_result(f"\n❌ 分析出错：{error_msg}\n", "error")
            self.set_status("❌ 分析出错", COLORS["error"])
            self.last_result = None
        finally:
            self.finish_analysis()

    def finish_analysis(self):
        """分析完成后的清理"""
        self.root.after(0, self._finish_ui)

    def _finish_ui(self):
        self.is_running = False
        self.start_btn.config(state=tk.NORMAL, text="▶ 开始分析")
        self.progress.stop()
        self.progress.pack_forget()

    def save_result(self):
        """保存分析结果到文件"""
        if not hasattr(self, "last_result") or not self.last_result:
            messagebox.showinfo("提示", "没有可保存的分析结果")
            return

        # 默认文件名
        default_name = "分析结果_" + os.path.splitext(
            os.path.basename(self.chat_path_var.get())
        )[0] + ".txt"
        default_dir = os.path.dirname(self.chat_path_var.get())

        path = filedialog.asksaveasfilename(
            title="保存分析结果",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialdir=default_dir,
            initialfile=default_name,
            defaultextension=".txt"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self.last_result)
                messagebox.showinfo("保存成功", f"结果已保存至：\n{path}")
            except Exception as e:
                messagebox.showerror("保存失败", f"无法保存文件：\n{str(e)}")


# 启动
def main():
    root = tk.Tk()
    app = AnalysisGUI(root)
    root.mainloop()
    
if __name__ == "__main__":
    main()
