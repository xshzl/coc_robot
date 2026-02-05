"""
任务元数据定义模块

用于解耦任务、数据库、UI的核心抽象层
"""
from dataclasses import dataclass, field
from typing import Any, List, Type, get_type_hints
from enum import Enum


class 参数类型(Enum):
    """支持的参数类型"""
    整数 = "int"
    布尔 = "bool"
    字符串 = "str"
    浮点数 = "float"
    字符串列表 = "list[str]"
    整数列表 = "list[int]"


class UI控件类型(Enum):
    """UI控件类型"""
    自动 = "auto"  # 根据参数类型自动选择
    输入框 = "entry"
    滑块 = "slider"
    复选框 = "checkbox"
    下拉框 = "combobox"
    多选框 = "listbox"


@dataclass
class 任务参数定义:
    """任务参数的元数据"""
    参数名: str  # 参数键名
    参数类型: Type  # Python类型：int, bool, str, float, List[str]等
    默认值: Any = None
    描述: str = ""  # 用户可读描述
    UI控件: UI控件类型 = UI控件类型.自动

    # UI控件专用属性
    最小值: int | float | None = None  # 用于滑块/输入框
    最大值: int | float | None = None
    候选项: List[Any] = field(default_factory=list)  # 用于下拉框/多选框


@dataclass
class 任务状态定义:
    """任务需要持久化的状态字段"""
    状态名: str
    状态类型: Type
    默认值: Any = None
    描述: str = ""


@dataclass
class 任务元数据:
    """任务的完整元数据"""
    任务名称: str  # 任务类名
    显示名称: str  # UI显示用的友好名称
    描述: str = ""  # 任务功能说明

    # 参数定义
    参数列表: List[任务参数定义] = field(default_factory=list)

    # 状态定义
    状态列表: List[任务状态定义] = field(default_factory=list)

    # 依赖关系
    前置任务: List[str] = field(default_factory=list)  # 必须先执行的任务
    互斥任务: List[str] = field(default_factory=list)  # 不能同时执行的任务

    # 执行控制
    是否启用: bool = True
    默认启用: bool = True


def 任务元数据装饰器(
    显示名称: str,
    描述: str = "",
    前置任务: List[str] = None,
    互斥任务: List[str] = None,
    默认启用: bool = True
):
    """
    装饰器：为任务类自动生成元数据

    用法：
    @任务元数据装饰器(
        显示名称="升级城墙",
        描述="自动升级所有可升级的城墙",
        前置任务=["更新主世界账号资源状态"]
    )
    class 升级城墙(基础任务):
        # 参数定义（使用类型注解）
        开启刷墙: bool = False
        刷墙起始金币: int = 100000

        # 状态定义（使用 __状态__ 标记）
        class 状态:
            已升级城墙数量: int = 0
            上次升级时间: float = 0.0
    """
    def 装饰(任务类):
        # 解析参数定义（从类属性的类型注解中提取）
        参数列表 = []
        状态列表 = []

        类型提示 = get_type_hints(任务类)
        for 属性名, 类型 in 类型提示.items():
            if 属性名.startswith('_'):
                continue

            默认值 = getattr(任务类, 属性名, None)
            参数列表.append(任务参数定义(
                参数名=属性名,
                参数类型=类型,
                默认值=默认值,
                描述=f"{属性名}参数"
            ))

        # 解析状态定义（从内部 状态 类中提取）
        if hasattr(任务类, '状态'):
            状态类 = getattr(任务类, '状态')
            状态类型提示 = get_type_hints(状态类)
            for 状态名, 类型 in 状态类型提示.items():
                默认值 = getattr(状态类, 状态名, None)
                状态列表.append(任务状态定义(
                    状态名=状态名,
                    状态类型=类型,
                    默认值=默认值
                ))

        # 创建元数据对象
        元数据 = 任务元数据(
            任务名称=任务类.__name__,
            显示名称=显示名称,
            描述=描述,
            参数列表=参数列表,
            状态列表=状态列表,
            前置任务=前置任务 or [],
            互斥任务=互斥任务 or [],
            默认启用=默认启用
        )

        # 附加到类
        任务类.元数据 = 元数据
        return 任务类

    return 装饰


# ===== 示例用法 =====
if __name__ == "__main__":
    from 任务流程.基础任务框架 import 基础任务

    @任务元数据装饰器(
        显示名称="升级城墙",
        描述="自动升级所有可升级的城墙",
        前置任务=["更新主世界账号资源状态"]
    )
    class 升级城墙示例(基础任务):
        # 参数定义（通过类型注解）
        开启刷墙: bool = False
        刷墙起始金币: int = 100000
        刷墙起始圣水: int = 100000

        # 状态定义
        class 状态:
            已升级城墙数量: int = 0
            上次升级时间: float = 0.0
            上次升级位置: str = ""

        def 执行(self) -> bool:
            # 使用 self.参数 访问参数
            # 使用 self.状态 访问状态
            # 使用 self.保存状态() 保存状态
            pass

    # 打印生成的元数据
    print(f"任务名称：{升级城墙示例.元数据.任务名称}")
    print(f"显示名称：{升级城墙示例.元数据.显示名称}")
    print(f"参数列表：")
    for 参数 in 升级城墙示例.元数据.参数列表:
        print(f"  - {参数.参数名}: {参数.参数类型} = {参数.默认值}")
    print(f"状态列表：")
    for 状态 in 升级城墙示例.元数据.状态列表:
        print(f"  - {状态.状态名}: {状态.状态类型} = {状态.默认值}")
