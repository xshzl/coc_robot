"""
日志面板模块 - 日志显示和管理功能
"""
import queue
import time
import tkinter as tk
from tkinter import ttk, scrolledtext
from typing import Callable, Optional


class 日志面板(ttk.Frame):
    """日志显示面板"""

    def __init__(self, 父容器, 日志队列: queue.Queue, 获取当前机器人回调: Callable):
        """
        初始化日志面板
        :param 父容器: 父容器控件
        :param 日志队列: 日志消息队列
        :param 获取当前机器人回调: 获取当前选中机器人的回调函数
        """
        super().__init__(父容器)
        self.日志队列 = 日志队列
        self.获取当前机器人 = 获取当前机器人回调

        self.日志缓存时间戳 = {}  # 记录每个机器人的最新日志时间戳
        self.日志缓存内容 = {}    # 记录日志内容缓存
        self._最近日志级别 = "正常"
        self._最近日志文本 = ""

        self._创建界面()
        self._定时刷新日志()

    def _创建界面(self):
        """创建日志显示区域"""
        self.日志文本框 = scrolledtext.ScrolledText(
            self, wrap=tk.WORD, font=('Consolas', 11)
        )
        self.日志文本框.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def _定时刷新日志(self):
        """定时从队列获取日志并刷新显示"""
        try:
            日志消息 = self.日志队列.get_nowait()

            当前机器人 = self.获取当前机器人()
            机器人ID = 日志消息.get("机器人ID")

            if 当前机器人 and 机器人ID == 当前机器人.机器人标志:
                # 记录最近收到的级别，供着色使用
                self._最近日志级别 = 日志消息.get("级别", "正常")
                self._最近日志文本 = 日志消息.get("内容", "")
                self.更新日志显示()
        except queue.Empty:
            pass
        finally:
            # 无论是否异常，都安排下一次调用
            self.after(200, self._定时刷新日志)

    def 更新日志显示(self):
        """刷新日志内容"""
        当前机器人 = self.获取当前机器人()

        if 当前机器人 is None:
            模拟日志 = [
                f"[{time.strftime('%H:%M:%S')}] 系统状态正常",
                f"[{time.strftime('%H:%M:%S')}] 欢迎使用脚本，具体使用步骤如下:",
                f"[{time.strftime('%H:%M:%S')}] 1.在模拟器中安装部落冲突并登录你的账号，确保进入主世界。",
                f"[{time.strftime('%H:%M:%S')}] 2.模拟器分辨率设置宽800，高600，dpi160",
                f"[{time.strftime('%H:%M:%S')}] 3.部落冲突中设置配兵,目前支持所有普通兵种,超级兵种支持超级野蛮人以及超级哥布林",
                f"[{time.strftime('%H:%M:%S')}] 4.打开游戏后",
                f"[{time.strftime('%H:%M:%S')}] 5.先在左边选中需要启动的账号,点击'启动'按钮运行脚本",
                f"[{time.strftime('%H:%M:%S')}] 6.或者在右边配置页面新建机器人再启动"
            ]
        else:
            机器人标志 = 当前机器人.机器人标志
            # 获取上次记录时间戳
            上次时间 = self.日志缓存时间戳.get(机器人标志, 0)
            日志列表 = 当前机器人.数据库.查询日志历史(机器人标志, 起始时间=上次时间 + 0.00001)

            if 日志列表:
                # 更新缓存时间戳为最新日志时间
                最新时间 = max(项.记录时间 for 项 in 日志列表)
                self.日志缓存时间戳[机器人标志] = 最新时间

            # 将缓存日志追加起来
            self.日志缓存内容.setdefault(机器人标志, []).extend(日志列表)

            全部日志 = self.日志缓存内容[机器人标志]
            全部日志.sort(key=lambda 日志: 日志.记录时间)

            模拟日志 = [
                f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(项.记录时间))}  {项.日志内容}"
                for 项 in 全部日志
            ]

        # 记录滚动条位置
        当前视图 = self.日志文本框.yview()

        self.日志文本框.configure(state='normal')
        self.日志文本框.delete(1.0, tk.END)

        # 配置文本颜色 tag
        self.日志文本框.tag_configure('正常', foreground="#1f2937")
        self.日志文本框.tag_configure('警告', foreground="#b45309")
        self.日志文本框.tag_configure('错误', foreground="#b91c1c")

        # 将日志按"前缀"粗略推断级别
        def 推断级别(文本: str) -> str:
            if 文本.strip().startswith("[错误]"):
                return "错误"
            if 文本.strip().startswith("[警告]"):
                return "警告"
            return "正常"

        for log in 模拟日志[-500:]:
            级别 = 推断级别(log)
            self.日志文本框.insert(tk.END, log + '\n', 级别)

        # 最近一条实时日志（如果有）以结构化级别覆盖显示尾部颜色
        if hasattr(self, "_最近日志文本"):
            级别 = getattr(self, "_最近日志级别", "正常")
            self.日志文本框.insert(tk.END, '', '正常')

        self.日志文本框.configure(state='disabled')

        # 判断用户是否在底部
        if 当前视图[1] > 0.95:
            self.日志文本框.see(tk.END)
        else:
            self.日志文本框.yview_moveto(当前视图[0])

    def 记录操作日志(self, 内容: str):
        """插入操作日志行"""
        self.日志文本框.configure(state='normal')
        self.日志文本框.insert(tk.END, f"[操作] {内容}\n")
        self.日志文本框.configure(state='disabled')
        self.日志文本框.see(tk.END)

    def 通知机器人切换(self):
        """选中机器人变化时强制刷新"""
        self.更新日志显示()
