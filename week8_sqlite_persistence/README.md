# 一个最小持久化系统

slots 表：存车位当前状态
slot_history 表：存状态变化历史
自动建库
插入 100 个车位
批量更新状态
查询：
全部车位
指定区域空闲车位
指定车位历史记录

这已经不再是 demo 脚本，而是一个真正有“数据底座”的小系统。

## 1. 为什么要拆成 slots 和 slot_history 两张表？

因为“当前状态”和“历史轨迹”不是一回事。
slots：回答“现在是什么状态”
slot_history：回答“它是怎么变成现在这样的”
这和你们未来要积累的“对象-事件-任务-结果”闭环资产是一致的。

## 2. 为什么 update_slot_state() 要同时写历史表？

因为真正有价值的不是 state = RESOLVED 这一个结果，
而是：
从什么状态来
因为什么变更
属于什么事件
什么时候发生
这才有审计价值、复盘价值、规则优化价值。

## 3. 为什么先只建 Slot 表，而不急着建 Zone / Lane 表？

因为你这周的重点是先掌握 ORM 和持久化基础动作，不是一次性把整个世界模型建完。
所以这里采用了一个折中做法：
zone_id
lane_id
先作为字段存进去。
这对初学者更友好，也足够支撑查询。
等第9周再升级成真正的多表关系模型更合适。

## 4. 为什么插入100个 Slot？

因为样本量太小，你感受不到数据库的意义。
100个对象会让你第一次真正感受到：
批量初始化
批量查询
区域过滤
历史管理
这才像一个系统，而不是玩具脚本。

# 你这一周要真正吃透的 4 个 SQLAlchemy 概念

## 1. Base.metadata.create_all(bind=engine)

作用：按你定义的模型自动建表。

这是 ORM 最基本的一步。

## 2. SessionLocal()

作用：拿到数据库会话，相当于这次数据库操作的“上下文”。

你所有增删改查，都是通过 db 来做。

## 3. db.add() + db.commit()

作用：

add()：把对象放进待写入队列
commit()：真正提交到数据库

没有 commit()，数据库里不会真正落地。

## 4. db.query(...)

作用：查询数据。
例如：
db.query(Slot).filter(Slot.zone_id == "Zone-A").all()
这已经是最基础的 ORM 查询能力。

# 本周练习题

## 练习1：查询所有 ILLEGAL 状态车位

在 crud.py 里新增：
def get_illegal_slots(db: Session):
    return db.query(Slot).filter(Slot.state == "ILLEGAL").all()
然后在 main.py 里打印。

## 练习2：查询某个区域的充电车位

新增函数：
def get_free_charging_slots_by_zone(db: Session, zone_id: str):
条件：
zone_id == zone_id
slot_type == "CHARGING"
state == "FREE"
这会帮助你理解“语义属性 + 状态”联合查询。

## 练习3：为历史表增加 operator

例如：
SYSTEM
ROBOT
HUMAN
然后在状态更新时把操作者写进去。
这会让系统更接近真实业务闭环。

## 练习4：实现“重复状态不写历史”

现在代码里已经跳过“相同状态更新”。
你可以自己测试：
update_slot_state(db, "Slot-A-1-01", "OCCUPIED", "重复写入测试")
确认它不会再产生一条没意义的历史。
这一步会让你理解“幂等性”。
