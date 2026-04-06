# 🎯 目标

掌握Python基础语法，能写函数、类、简单逻辑。

🧪 练习任务
写函数(包括检查，更改slot的状态）：
def inspect_slot(slot_id):
    print(f"{slot_id} inspected")

定义类（包括slot和zone)：
class Slot:
    def __init__(self, slot_id, state):
        self.slot_id = slot_id
        self.state = state

创建20个Slot对象并打印状态。

✅完成标准：
建议周末 6 小时拆成 3 次：
Session A（2小时）
跑通 python main.py
看输出日志
理解：Slot/Zone 是什么、dict 存了什么

Session B（2小时）
只改 week1_homework()：
新增一个函数：list_illegal_slots(slots)
新增一个查询：统计每个 Zone 的 free 数量

Session C（2小时）
让程序支持“命令输入”（最简单方式）：
在 main() 最后加：
slot_id = input("Enter slot id: ")
调用 inspect_slot(slots, slot_id)

🎉第1周验收标准（你必须达到）
你能解释：zones 和 slots 两个 dict 里分别是什么
你能自己新增一个查询函数（例如查 illegal slots）
你能让程序根据 input 执行一次 inspect
全程无报错，或者你能定位并修复（常见是拼写/缩进）
