"""
【Celery 任务路由 (Routing) 与 优先级 (Priority) 深度配置解析】

核心作用与业务场景：
1. 任务隔离 (路由)：如果你的系统里既有“计算密集的作文批改”，又有“IO密集的发送邮件”，把它们混在一个队列里会导致互相堵塞。让专用的服务器(Worker)只监听专门的队列(高配CPU服务器监听AI批改队列，低配闲置服务器监听发邮件队列)。
2. VIP 插队 (优先级)：在资源紧缺时，即使在同一个队列里，也需要让紧急的任务（如用户正在等结果的请求）比不紧急的任务（如定时报表生成）先执行。

此配置展示了 RabbitMQ 作为 Broker 时：
- 如何划分多条队列 (Queue) 与交换机 (Exchange)
- 如何使用 `x-max-priority` 开启优先级机制
"""

from celery import Celery
from kombu import Queue, Exchange
import os

# ==========================================
# 1. 声明底层队列结构及优先级上限
# ==========================================
# RabbitMQ 支持 1-255 的优先级，但官方建议设置在 1-10 之间以节省内存开销。
queue_args = {'x-max-priority': 10}

task_queues = (
    # 核心高优队列：处理用户实时在线等结果的请求
    Queue('urgent_tasks', Exchange('urgent'), routing_key='urgent.#', queue_arguments=queue_args),
    
    # 常规队列：后台数据清洗、词汇生成等普通任务
    Queue('default_tasks', Exchange('default'), routing_key='default.#', queue_arguments=queue_args),
    
    # 慢速低优先级队列：发送营销邮件、生成月度学习报表等
    Queue('batch_tasks', Exchange('batch'), routing_key='batch.#', queue_arguments=queue_args),
)

# ==========================================
# 2. 动态路由分发规则
# ==========================================
# 把你的 Python 函数强制派发到对应的队列，并绑定特有的路由键
task_routes = {
    # '模块名.函数名': {'目标队列', '路由键'}
    'tasks.grade_realtime_essay': {'queue': 'urgent_tasks', 'routing_key': 'urgent.essay'},
    'tasks.generate_daily_vocab':  {'queue': 'default_tasks', 'routing_key': 'default.vocab'},
    'tasks.send_marketing_emails': {'queue': 'batch_tasks', 'routing_key': 'batch.email'},
}

# ==========================================
# 3. 初始化 Celery 应用配置
# ==========================================
app = Celery('education_router', broker='amqp://guest:guest@localhost:5672//')

DEMO_EAGER = os.getenv('CELERY_DEMO_EAGER', '1') == '1'

app.conf.update(
    task_queues=task_queues,
    task_routes=task_routes,
    task_default_queue='default_tasks',     # 如果有其它没有被路由规则包进来的闲散任务，全进默认队列
    task_default_exchange='default',
    task_default_routing_key='default.any',
    
    # 配置公平分发：
    # 如果不设置 worker_prefetch_multiplier=1，Worker 可能会一次性贪婪地从队列里抓一堆任务囤着慢慢跑。
    # 这样就算某条高优先级任务进来了，也插不了这台机器的队。设置为1能保证 Worker 做完一个再去领下一个高级兵。
    worker_prefetch_multiplier=1,
    
    # 默认用于本地演示；生产环境请设置 CELERY_DEMO_EAGER=0 并启动真实 Worker。
    task_always_eager=DEMO_EAGER,
)

# ==========================================
# 4. 模拟任务逻辑及发布 (生产者投递时指定优先级)
# ==========================================
@app.task(name='tasks.grade_realtime_essay')
def grade_realtime_essay(user_id):
    pass

@app.task(name='tasks.generate_daily_vocab')
def generate_daily_vocab(user_id):
    pass

@app.task(name='tasks.send_marketing_emails')
def send_marketing_emails(user_id):
    pass

if __name__ == '__main__':
    print("="*60)
    if DEMO_EAGER:
        print("[提示] 当前处于 CELERY_DEMO_EAGER=1，本次为本地同步演示模式。")
    else:
        print("[提示] 当前处于 CELERY_DEMO_EAGER=0，需要 RabbitMQ 和 Worker 才会真正异步执行。")
    print("【测试演示】投递不同隔离队列与优先级的任务")
    print("="*60)
    
    # 演示：往高级队列投发任务，虽然它天然已经在 urgent_tasks，也可以进一步赋予极速 priority=10
    task1 = grade_realtime_essay.apply_async(args=[101], priority=10)
    print(f"✅ 已派发[批改]任务至 urgent_tasks 队列，优先级：极高(10)")
    
    # 演示：普通的单词生成任务，优先级为 5
    task2 = generate_daily_vocab.apply_async(args=[102], priority=5)
    print(f"✅ 已派发[词汇]任务至 default_tasks 队列，优先级：中等(5)")
    
    print("\n💡【系统架构师知识拓展：如何在正式环境中启动不同性能的消费者？】")
    print("终端 A (高配AI服务器，只专注处理在线高优批改):")
    print("    celery -A your_project worker -Q urgent_tasks -c 8   # 开8个并发猛处理\n")
    print("终端 B (普通廉价机器，用来兜底其它默认低优先级的杂活):")
    print("    celery -A your_project worker -Q default_tasks,batch_tasks -c 2")
