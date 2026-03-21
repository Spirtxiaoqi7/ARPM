#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GUI聊天客户端 - 替代命令行交互
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import requests
import threading
import json
from datetime import datetime

class ChatClient:
    def __init__(self, root):
        self.root = root
        self.root.title("RAG智能聊天")
        self.root.geometry("600x700")
        self.root.configure(bg="#f0f0f0")

        # API配置（根据实际服务地址调整）
        self.api_url = "http://127.0.0.1:8003/chat"
        self.chat_history = []

        self.create_widgets()

    def create_widgets(self):
        """创建界面组件"""
        # 标题栏
        title_frame = tk.Frame(self.root, bg="#2c3e50", height=50)
        title_frame.pack(fill="x", side="top")

        title_label = tk.Label(
            title_frame,
            text="💬 RAG智能助手",
            font=("微软雅黑", 16, "bold"),
            bg="#2c3e50",
            fg="white"
        )
        title_label.pack(pady=10)

        # 聊天显示区域
        chat_frame = tk.Frame(self.root, bg="#ffffff", bd=2, relief="sunken")
        chat_frame.pack(padx=10, pady=10, fill="both", expand=True)

        self.chat_display = scrolledtext.ScrolledText(
            chat_frame,
            bg="#f9f9f9",
            fg="#333333",
            font=("微软雅黑", 11),
            wrap="word",
            state="disabled"
        )
        self.chat_display.pack(fill="both", expand=True, padx=5, pady=5)

        # 配置标签样式
        self.chat_display.tag_config("user", foreground="#0066cc", font=("微软雅黑", 11, "bold"))
        self.chat_display.tag_config("ai", foreground="#009933", font=("微软雅黑", 11, "bold"))
        self.chat_display.tag_config("system", foreground="#999999", font=("微软雅黑", 9, "italic"))

        # 输入区域
        input_frame = tk.Frame(self.root, bg="#f0f0f0")
        input_frame.pack(padx=10, pady=10, fill="x")

        # 输入框
        self.input_text = tk.Text(
            input_frame,
            height=4,
            font=("微软雅黑", 11),
            bg="white",
            fg="#333333",
            relief="solid",
            bd=1
        )
        self.input_text.pack(side="left", fill="both", expand=True, padx=(0, 10))
        self.input_text.bind("<Control-Return>", self.send_message)

        # 发送按钮
        send_button = tk.Button(
            input_frame,
            text="发送\n(Send)",
            command=self.send_message,
            font=("微软雅黑", 10, "bold"),
            bg="#3498db",
            fg="white",
            width=12,
            height=4,
            cursor="hand2",
            relief="raised"
        )
        send_button.pack(side="right")

        # 状态栏
        status_frame = tk.Frame(self.root, bg="#e0e0e0", height=30)
        status_frame.pack(fill="x", side="bottom")

        self.status_label = tk.Label(
            status_frame,
            text="🟢 就绪",
            font=("微软雅黑", 9),
            bg="#e0e0e0",
            fg="#0066cc"
        )
        self.status_label.pack(side="left", padx=10, pady=5)

        self.clear_button = tk.Button(
            status_frame,
            text="🗑️ 清空对话",
            command=self.clear_chat,
            font=("微软雅黑", 8),
            bg="#e74c3c",
            fg="white",
            cursor="hand2",
            relief="flat"
        )
        self.clear_button.pack(side="right", padx=10, pady=5)

        # 显示欢迎消息
        self.add_system_message("欢迎使用RAG智能助手！\n在下方输入框输入问题，点击发送或按Ctrl+Enter发送消息。")

    def add_user_message(self, message):
        """添加用户消息"""
        self.chat_display.config(state="normal")
        self.chat_display.insert("end", f"\n👤 你 ({datetime.now().strftime('%H:%M')}):\n", "user")
        self.chat_display.insert("end", f"{message}\n")
        self.chat_display.config(state="disabled")
        self.chat_display.see("end")

    def add_ai_message(self, message):
        """添加AI消息"""
        self.chat_display.config(state="normal")
        self.chat_display.insert("end", f"\n🤖 助手 ({datetime.now().strftime('%H:%M')}):\n", "ai")
        self.chat_display.insert("end", f"{message}\n")
        self.chat_display.config(state="disabled")
        self.chat_display.see("end")

    def add_system_message(self, message):
        """添加系统消息"""
        self.chat_display.config(state="normal")
        self.chat_display.insert("end", f"\n📌 系统:\n", "system")
        self.chat_display.insert("end", f"{message}\n")
        self.chat_display.config(state="disabled")
        self.chat_display.see("end")

    def send_message(self, event=None):
        """发送消息"""
        message = self.input_text.get("1.0", "end-1c").strip()

        if not message:
            return

        # 清空输入框
        self.input_text.delete("1.0", "end")

        # 显示用户消息
        self.add_user_message(message)

        # 禁用发送按钮
        self.root.after(0, lambda: self.status_label.config(text="🔄 思考中...", fg="#f39c12"))

        # 在新线程中发送请求
        threading.Thread(target=self._send_request, args=(message,), daemon=True).start()

    def _send_request(self, message):
        """发送API请求"""
        try:
            # 尝试调用API
            response = requests.post(
                self.api_url,
                json={"message": message},
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                ai_message = result.get("response", result.get("answer", "抱歉，没有收到回复"))
                self.root.after(0, lambda: self.add_ai_message(ai_message))
            else:
                error_msg = f"API错误: {response.status_code}"
                self.root.after(0, lambda: self.add_system_message(error_msg))

        except requests.exceptions.ConnectionError:
            # 如果API不可用，使用模拟回复
            self.root.after(0, lambda: self._simulate_response(message))
        except Exception as e:
            error_msg = f"发生错误: {str(e)}"
            self.root.after(0, lambda: self.add_system_message(error_msg))

        finally:
            # 恢复状态
            self.root.after(0, lambda: self.status_label.config(text="🟢 就绪", fg="#0066cc"))

    def _simulate_response(self, message):
        """模拟AI回复（当API不可用时）"""
        responses = [
            f"你说：{message}\n\n（提示：API服务未连接，请确保RAG服务已启动）",
            "这是一个模拟回复。请确保后端RAG服务（端口8003/8004）正在运行。",
            "我无法连接到RAG服务。请检查服务是否已启动。"
        ]
        import random
        response = random.choice(responses)
        self.add_ai_message(response)

    def clear_chat(self):
        """清空对话"""
        if messagebox.askyesno("确认", "确定要清空所有对话记录吗？"):
            self.chat_display.config(state="normal")
            self.chat_display.delete("1.0", "end")
            self.chat_display.config(state="disabled")
            self.add_system_message("对话已清空")

def main():
    root = tk.Tk()
    app = ChatClient(root)
    root.mainloop()

if __name__ == "__main__":
    main()