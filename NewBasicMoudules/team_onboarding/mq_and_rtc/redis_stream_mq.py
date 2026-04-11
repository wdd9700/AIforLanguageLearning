"""
【使用 Redis Stream 实现可靠的消息队列】

核心作用与业务价值：
1. 为什么不用 Redis List 或 Pub/Sub？
   - List 没有“消费者组”概念，不支持 ACK（确认机制），一旦弹出发生异常就永远丢失了。
   - Pub/Sub 是“发后即忘”，新上线的消费者收不到历史消息。
2. 为什么用 Redis Stream？
   - 这是 Redis 5.0 专门为消息队列场景推出的数据结构，完美对标 Kafka！
   - 支持【消费者组(Consumer Group)】：一条消息只会被组内的一个 Worker 消费（负载均衡）。
   - 支持【ACK确认机制】和【PEL(待处理列表)】：如果 Worker 崩溃没有 ACK，其他 Worker 可以通过 XCLAIM 抢占这条故障消息重新消费，【保证消息绝对不丢失】。
   - 极其轻量级：如果系统不想引入沉重的 RabbitMQ/Kafka，Redis Stream 是中小型项目最完美的选择。
"""

import redis
import time
import uuid

# ==========================================
# 1. 建立 Redis 连接
# ==========================================
# decode_responses=True 让我们直接获取字符串而不是字节类型
try:
    r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    # 测试连接
    r.ping()
    HAS_REDIS = True
except redis.ConnectionError:
    print("⚠️ 未检测到本地 Redis 服务运行。将打印工作流演示。")
    HAS_REDIS = False

STREAM_KEY = "stream:essay_tasks"
GROUP_NAME = "group:graders"
CONSUMER_NAME = f"worker-{uuid.uuid4().hex[:6]}"
PENDING_IDLE_MS = 30_000


def init_consumer_group():
    """初始化消费者组 (等同于在 Kafka 中创建 Group)"""
    if not HAS_REDIS: return
    try:
        # mkstream=True 表示如果 Stream 不存在则自动创建
        # '$' 表示组从当前最新的消息开始消费 (如果要从头消费用 '0')
        r.xgroup_create(STREAM_KEY, GROUP_NAME, id='0', mkstream=True)
        print(f"--> 成功创建消费者组 [{GROUP_NAME}]")
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP Consumer Group name already exists" in str(e):
            print(f"--> 消费者组 [{GROUP_NAME}] 已存在")
        else:
            raise e

def producer_publish_task(user_id: str, essay_text: str):
    """
    生产者：发布任务到 Stream (等同于往队列塞数据)
    """
    msg_dict = {
        "user_id": user_id,
        "essay_text": essay_text,
        "timestamp": str(time.time())
    }
    
    if HAS_REDIS:
        # XADD: 追加消息到 stream，'*' 表示让 Redis 自动生成唯一的毫秒级 ID
        msg_id = r.xadd(STREAM_KEY, msg_dict, id='*')
        print(f"[生产者] 📮 成功发布作文批改任务! Message ID: {msg_id}")
    else:
        print(f"[生产者] 📮 (Mock) 成功发布作文批改任务! Message ID: 168...-0")


def handle_message(msg_id: str, msg_data: dict):
    """处理单条消息；处理成功后发送 ACK。"""
    print(f"\n[消费者 {CONSUMER_NAME}] 📥 认领了新任务: ID={msg_id}")
    print(f"   => 正在批改用户 {msg_data.get('user_id', 'unknown')} 的作文...")
    try:
        time.sleep(1)  # 模拟批改时间
        # 真实场景可在这里调用模型服务/外部接口。
    except Exception as exc:
        print(f"[消费者 {CONSUMER_NAME}] ❌ 处理失败，暂不 ACK，消息保留在 PEL: {exc}")
        return False

    # XACK: 处理完毕后必须告诉 Redis，这条消息才能从 PEL 中真正销毁。
    r.xack(STREAM_KEY, GROUP_NAME, msg_id)
    print(f"[消费者 {CONSUMER_NAME}] ✅ 批改完成！成功发送 ACK 确认，任务移出 PEL。")
    return True


def recover_stale_pending_messages():
    """
    抢占长时间未 ACK 的挂起消息，避免消息永久滞留在其它消费者的 PEL。
    """
    if not HAS_REDIS:
        return

    try:
        pending_entries = r.xpending_range(
            STREAM_KEY,
            GROUP_NAME,
            '-',
            '+',
            10,
            idle=PENDING_IDLE_MS,
        )
    except TypeError:
        # 兼容不同 redis-py 版本参数签名
        pending_entries = r.xpending_range(STREAM_KEY, GROUP_NAME, '-', '+', 10)
        pending_entries = [
            item for item in pending_entries if item.get('time_since_delivered', 0) >= PENDING_IDLE_MS
        ]

    if not pending_entries:
        return

    print(f"[消费者 {CONSUMER_NAME}] 🔄 检测到 {len(pending_entries)} 条超时挂起消息，准备接管处理...")
    for item in pending_entries:
        msg_id = item['message_id']
        claimed = r.xclaim(
            STREAM_KEY,
            GROUP_NAME,
            CONSUMER_NAME,
            min_idle_time=PENDING_IDLE_MS,
            message_ids=[msg_id],
        )
        if not claimed:
            continue
        claimed_id, claimed_data = claimed[0]
        print(f"[消费者 {CONSUMER_NAME}] 🛠️ 已接管挂起消息: ID={claimed_id}")
        handle_message(claimed_id, claimed_data)


def consumer_process_loop():
    """
    消费者：在一个循环中不断拉取并处理消息
    """
    print(f"\n[消费者 {CONSUMER_NAME}] ⚙️ 启动监听中...")

    if HAS_REDIS:
        recover_stale_pending_messages()
    
    # 获取 2 条消息用于演示
    for i in range(2):
        if not HAS_REDIS:
            print(f"[消费者 {CONSUMER_NAME}] (Mock) 收到消息并处理... [ACK 确认]")
            continue
            
        # XREADGROUP: 按组读取消息
        # count=1 每次拉取1条，block=2000 如果没消息最多阻塞等待2秒
        # streams={STREAM_KEY: '>'} '>' 代表“拉取本组还未被分配给任何人的新消息”
        messages = r.xreadgroup(
            groupname=GROUP_NAME, 
            consumername=CONSUMER_NAME, 
            streams={STREAM_KEY: '>'}, 
            count=1, 
            block=2000
        )
        
        if not messages:
            print(f"[消费者 {CONSUMER_NAME}] 队列空闲，继续等待新任务...")
            continue
            
        # 解析返回的数据结构
        # messages 格式: [['stream:essay_tasks', [('168...', {'user_id': '1', ...})]]]
        _, message_list = messages[0]
        msg_id, msg_data = message_list[0]
        handle_message(msg_id, msg_data)


if __name__ == "__main__":
    print("="*50)
    print(" Redis Stream 高可用消息队列工作流演示")
    print("="*50)
    
    # 1. 建立消费者分组
    init_consumer_group()
    
    # 2. 生产者疯狂发任务
    producer_publish_task("2001", "Today is a good day")
    producer_publish_task("2002", "I love programming")
    
    # 3. 消费者消费任务
    consumer_process_loop()
