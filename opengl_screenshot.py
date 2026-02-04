"""
OpenGL 窗口截图工具 - Python实现
基于OP项目的OpenGL截图原理提取

依赖安装:
pip install PyOpenGL PyOpenGL-accelerate Pillow pywin32 numpy
"""

import ctypes
from ctypes import wintypes
import numpy as np
from PIL import Image
import win32gui
import win32con


class OpenGLScreenshot:
    """OpenGL窗口截图类"""

    def __init__(self):
        # 加载OpenGL32.dll
        try:
            self.opengl32 = ctypes.WinDLL('opengl32.dll')
        except OSError:
            raise RuntimeError("无法加载opengl32.dll，请确保系统支持OpenGL")

        # 定义OpenGL函数
        self._setup_gl_functions()

    def _setup_gl_functions(self):
        """设置OpenGL函数签名"""
        # glReadPixels
        self.glReadPixels = self.opengl32.glReadPixels
        self.glReadPixels.argtypes = [
            ctypes.c_int,    # x
            ctypes.c_int,    # y
            ctypes.c_int,    # width
            ctypes.c_int,    # height
            ctypes.c_uint,   # format
            ctypes.c_uint,   # type
            ctypes.c_void_p  # pixels
        ]

        # glPixelStorei
        self.glPixelStorei = self.opengl32.glPixelStorei
        self.glPixelStorei.argtypes = [ctypes.c_uint, ctypes.c_int]

        # glReadBuffer
        self.glReadBuffer = self.opengl32.glReadBuffer
        self.glReadBuffer.argtypes = [ctypes.c_uint]

        # glGetIntegerv
        self.glGetIntegerv = self.opengl32.glGetIntegerv
        self.glGetIntegerv.argtypes = [ctypes.c_uint, ctypes.POINTER(ctypes.c_int)]

    def capture_window(self, hwnd=None, use_front_buffer=True):
        """
        截取OpenGL窗口

        参数:
            hwnd: 窗口句柄，None表示活动窗口
            use_front_buffer: True使用前缓冲区，False使用后缓冲区

        返回:
            PIL.Image对象，失败返回None
        """
        # OpenGL常量定义
        GL_FRONT = 0x0404
        GL_BACK = 0x0405
        GL_BGRA_EXT = 0x80E1
        GL_RGBA = 0x1908
        GL_UNSIGNED_BYTE = 0x1401
        GL_PACK_ALIGNMENT = 0x0D05
        GL_UNPACK_ALIGNMENT = 0x0CF5

        # 获取窗口句柄
        if hwnd is None:
            hwnd = win32gui.GetForegroundWindow()

        if not win32gui.IsWindow(hwnd):
            print(f"错误: 无效的窗口句柄 {hwnd}")
            return None

        # 获取窗口客户区尺寸
        try:
            rect = win32gui.GetClientRect(hwnd)
            width = rect[2] - rect[0]
            height = rect[3] - rect[1]
        except Exception as e:
            print(f"获取窗口尺寸失败: {e}")
            return None

        if width <= 0 or height <= 0:
            print(f"无效的窗口尺寸: {width}x{height}")
            return None

        print(f"窗口尺寸: {width}x{height}")

        try:
            # 设置像素对齐（与OP项目相同）
            self.glPixelStorei(GL_PACK_ALIGNMENT, 1)
            self.glPixelStorei(GL_UNPACK_ALIGNMENT, 1)

            # 选择读取缓冲区
            buffer_type = GL_FRONT if use_front_buffer else GL_BACK
            self.glReadBuffer(buffer_type)

            # 分配内存缓冲区
            buffer_size = width * height * 4  # BGRA = 4字节/像素
            pixel_buffer = (ctypes.c_ubyte * buffer_size)()

            # 读取像素 (与OP项目核心代码一致)
            self.glReadPixels(
                0, 0,           # 起始坐标
                width, height,  # 尺寸
                GL_BGRA_EXT,    # 格式：BGRA
                GL_UNSIGNED_BYTE,
                pixel_buffer
            )

            # 转换为numpy数组
            img_array = np.frombuffer(pixel_buffer, dtype=np.uint8)
            img_array = img_array.reshape((height, width, 4))

            # OpenGL坐标系是下到上，需要垂直翻转
            img_array = np.flipud(img_array)

            # BGRA -> RGBA
            img_array[:, :, [0, 2]] = img_array[:, :, [2, 0]]

            # 创建PIL图像
            img = Image.fromarray(img_array, 'RGBA')

            print(f"截图成功: {width}x{height}")
            return img

        except Exception as e:
            print(f"截图失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def capture_window_by_dc(self, hwnd):
        """
        通过设备上下文截图（备用方案）
        适用于无法直接访问OpenGL上下文的情况
        """
        try:
            # 获取设备上下文
            hdc = win32gui.GetDC(hwnd)
            rect = win32gui.GetClientRect(hwnd)
            width = rect[2] - rect[0]
            height = rect[3] - rect[1]

            # 创建兼容DC和位图
            hdc_mem = ctypes.windll.gdi32.CreateCompatibleDC(hdc)
            hbitmap = ctypes.windll.gdi32.CreateCompatibleBitmap(hdc, width, height)
            ctypes.windll.gdi32.SelectObject(hdc_mem, hbitmap)

            # 拷贝窗口内容
            ctypes.windll.gdi32.BitBlt(
                hdc_mem, 0, 0, width, height,
                hdc, 0, 0, win32con.SRCCOPY
            )

            # 获取位图数据
            bmp_info = ctypes.create_string_buffer(40)
            ctypes.windll.gdi32.GetObjectW(hbitmap, 24, bmp_info)

            # 转换为图像
            bmp_str = ctypes.create_string_buffer(width * height * 4)
            ctypes.windll.gdi32.GetBitmapBits(hbitmap, len(bmp_str), bmp_str)

            img = Image.frombuffer('RGBA', (width, height), bmp_str, 'raw', 'BGRA', 0, 1)

            # 清理资源
            ctypes.windll.gdi32.DeleteObject(hbitmap)
            ctypes.windll.gdi32.DeleteDC(hdc_mem)
            win32gui.ReleaseDC(hwnd, hdc)

            return img

        except Exception as e:
            print(f"DC截图失败: {e}")
            return None


def find_window_by_title(title_keyword):
    """根据标题关键字查找窗口"""
    def callback(hwnd, windows):
        if win32gui.IsWindowVisible(hwnd):
            window_title = win32gui.GetWindowText(hwnd)
            if title_keyword.lower() in window_title.lower():
                windows.append((hwnd, window_title))
        return True

    windows = []
    win32gui.EnumWindows(callback, windows)
    return windows


# ============ 使用示例 ============

if __name__ == "__main__":
    print("OpenGL截图工具 - 基于OP项目提取")
    print("=" * 50)

    # 创建截图对象
    gl_shot = OpenGLScreenshot()

    # 方式1: 截取活动窗口
    print("\n方式1: 截取当前活动窗口...")
    img = gl_shot.capture_window()
    if img:
        img.save("screenshot_active.png")
        print("已保存: screenshot_active.png")
        img.show()

    # 方式2: 根据窗口标题查找并截图
    print("\n方式2: 查找特定窗口...")
    keyword = input("请输入窗口标题关键字 (如'Chrome', 'Game'等): ").strip()

    if keyword:
        windows = find_window_by_title(keyword)

        if windows:
            print(f"\n找到 {len(windows)} 个匹配的窗口:")
            for i, (hwnd, title) in enumerate(windows):
                print(f"  [{i}] HWND={hwnd}, 标题={title}")

            idx = int(input(f"\n选择窗口编号 [0-{len(windows)-1}]: "))
            hwnd = windows[idx][0]

            # 尝试OpenGL截图
            print("\n尝试OpenGL方式截图...")
            img = gl_shot.capture_window(hwnd)

            if img:
                filename = f"screenshot_{hwnd}.png"
                img.save(filename)
                print(f"成功! 已保存: {filename}")
                img.show()
            else:
                # 失败则尝试备用方案
                print("OpenGL截图失败，尝试备用方案...")
                img = gl_shot.capture_window_by_dc(hwnd)
                if img:
                    filename = f"screenshot_{hwnd}_dc.png"
                    img.save(filename)
                    print(f"备用方案成功! 已保存: {filename}")
                    img.show()
        else:
            print("未找到匹配的窗口")

    print("\n" + "=" * 50)
    print("完成!")
