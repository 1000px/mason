import tkinter as tk
from tkinter import messagebox
from src.skills.base import BaseSkill
from src.db.story_store import save_story


class StoryCollectorSkill(BaseSkill):
    name = "story_collector"
    description = "打开故事收集窗口，录入故事的标题、作者、标签和正文，保存到数据库。"

    permissions = {
        "network": False,
        "filesystem": False,
        "max_cpu": 0.2,
        "max_memory": 64,
    }

    def execute(self, **kwargs) -> str:
        result = {"saved": False, "title": ""}

        root = tk.Tk()
        root.title("故事收集")
        root.geometry("600x520")
        root.resizable(True, True)

        root.columnconfigure(0, weight=1)
        root.columnconfigure(1, weight=3)

        tk.Label(root, text="标题：").grid(row=0, column=0, sticky="e", padx=(10, 5), pady=(10, 5))
        title_entry = tk.Entry(root, width=50)
        title_entry.grid(row=0, column=1, sticky="ew", padx=(5, 10), pady=(10, 5))

        tk.Label(root, text="作者：").grid(row=1, column=0, sticky="e", padx=(10, 5), pady=5)
        author_entry = tk.Entry(root, width=50)
        author_entry.grid(row=1, column=1, sticky="ew", padx=(5, 10), pady=5)

        tk.Label(root, text="标签：").grid(row=2, column=0, sticky="e", padx=(10, 5), pady=5)
        tags_entry = tk.Entry(root, width=50)
        tags_entry.grid(row=2, column=1, sticky="ew", padx=(5, 10), pady=5)
        tk.Label(root, text="（多个标签用逗号隔开）", fg="gray").grid(
            row=3, column=1, sticky="w", padx=(5, 10)
        )

        tk.Label(root, text="正文：").grid(row=4, column=0, sticky="ne", padx=(10, 5), pady=(10, 5))
        content_text = tk.Text(root, width=50, height=15)
        content_text.grid(row=4, column=1, sticky="nsew", padx=(5, 10), pady=(10, 5))

        root.rowconfigure(4, weight=1)

        def do_save():
            title = title_entry.get().strip()
            author = author_entry.get().strip()
            tags = tags_entry.get().strip()
            content = content_text.get("1.0", "end-1c").strip()

            if not title:
                messagebox.showwarning("提示", "请输入标题。")
                return
            if not author:
                messagebox.showwarning("提示", "请输入作者。")
                return
            if not content:
                messagebox.showwarning("提示", "请输入正文。")
                return

            story_id = save_story(title, author, tags, content)
            if story_id:
                result["saved"] = True
                result["title"] = title
                title_entry.delete(0, "end")
                author_entry.delete(0, "end")
                tags_entry.delete(0, "end")
                content_text.delete("1.0", "end")
                messagebox.showinfo("成功", f"故事「{title}」已保存！")
            else:
                messagebox.showerror("错误", "保存失败，请检查数据库连接。")

        def do_close():
            root.destroy()

        btn_frame = tk.Frame(root)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=(10, 15))

        tk.Button(btn_frame, text="保存", command=do_save, width=12, bg="#4CAF50", fg="white").pack(
            side="left", padx=5
        )
        tk.Button(btn_frame, text="关闭", command=do_close, width=12).pack(side="left", padx=5)

        root.mainloop()

        if result["saved"]:
            return f"✅ 故事「{result['title']}」已成功收集并保存到数据库。"
        else:
            return "📋 故事收集窗口已关闭。"


def create_skill():
    return StoryCollectorSkill()