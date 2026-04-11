"""
使用Celery实现作文批改异步任务队列系统

【核心作用与业务价值】
这段代码在项目中扮演着“后台异步任务处理中心”的角色，核心目的是解决耗时操作阻塞系统、保障重要任务优先执行以及容错兜底：

1. 解决全站“卡死”问题（异步非阻塞）
   - 痛点：用户提交作文同步调用大模型批改耗时长，网页假死。
   - 作用：真正的耗时工作交由 Worker 在后台默默执行，前端瞬间返回排队ID，体验丝滑。

2. 实现核心业务的 VIP 通道（优先级与路由控制）
   - 痛点：被大量低优先级任务（如学习报告生成）挤占资源。
   - 作用：配置独立的高优先级队列，保障作文批改开辟VIP特快通道。

3. 铁壁般的重试与防丢机制（高可用容错）
   - 痛点：网络抖动、模型限流、服务器宕机导致任务丢失。
   - 作用：代码级 `self.retry` + 机制级 `task_acks_late=True`，保证任务百分百不丢。

4. 死信队列 (DLQ) 处理（消息最终兜底）
   - 痛点：当某篇作文本身存在系统级致命错误（触发多次重试依然全部失败）时，会无限循环占用队列资源。
   - 作用：配置 RabbitMQ 的 DLX(死信交换机) 和 DLQ(死信队列)，当任务重试次数耗尽后，会自动被打入“死信队列”，交给专门的兜底程序（比如发送钉钉报警、落库保存并让人工介入排查）处理。
"""

# ==========================================
# 1. Celery 配置 (模拟 celery_config.py)
# 用于配置 Broker、Backend，以及队列的路由和优先级策略。
# ==========================================
from kombu import Queue, Exchange

# Broker: RabbitMQ, Backend: Redis
broker_url = 'amqp://guest:guest@localhost:5672//'
result_backend = 'redis://localhost:6379/0'

task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'Asia/Shanghai'

# 按照优先级分为 high_priority, medium_priority, low_priority
# 并为重要队列配置 RabbitMQ 死信队列 (DLQ) 处理失败任务
dlx_exchange = Exchange('dlx_exchange', type='direct')

task_queues = (
    Queue('high_priority', Exchange('high_priority'), routing_key='high.#', 
          queue_arguments={
              'x-max-priority': 10,
              'x-dead-letter-exchange': 'dlx_exchange',        # 绑定死信交换机
              'x-dead-letter-routing-key': 'dead.high.essay'   # 死亡后路由键
          }),
    Queue('medium_priority', Exchange('medium_priority'), routing_key='medium.#', queue_arguments={'x-max-priority': 10}),
    Queue('low_priority', Exchange('low_priority'), routing_key='low.#', queue_arguments={'x-max-priority': 10}),
    
    # 专门用于存储/处理死信的队列
    Queue('dead_letter_queue', dlx_exchange, routing_key='dead.#'),
)

# 路由规则
task_routes = {
    'tasks.grade_essay': {'queue': 'high_priority', 'routing_key': 'high.essay'},
    'tasks.generate_vocab': {'queue': 'medium_priority', 'routing_key': 'medium.vocab'},
    'tasks.build_report': {'queue': 'low_priority', 'routing_key': 'low.report'},
    'tasks.process_dead_letter': {'queue': 'dead_letter_queue', 'routing_key': 'dead.high.essay'},
}

# 开启任务失败重试和可见性超时（防止任务丢失）
task_acks_late = True  
task_reject_on_worker_lost = True 


# ==========================================
# 2. 异步任务定义 (模拟 tasks.py)
# 定义作文批改任务逻辑以及失败重试机制。
# ==========================================
import time
from celery import Celery

app = Celery('education_tasks', broker=broker_url, backend=result_backend)
app.conf.update(
    task_queues=task_queues,
    task_routes=task_routes,
    task_acks_late=task_acks_late,
    task_reject_on_worker_lost=task_reject_on_worker_lost
)

@app.task(name='tasks.grade_essay', bind=True, max_retries=3, default_retry_delay=5)
def grade_essay(self, user_id: int, essay_content: str, essay_image_url: str = None):
    try:
        if essay_image_url:
            # 下载图片等耗时操作
            pass 
            
        time.sleep(3) # 模拟批改调用模型的延迟
        
        result = {
            "user_id": user_id,
            "score": 92,
            "feedback": "文章结构清晰，词汇丰富。"
        }
        return result
        
    except (TimeoutError, ConnectionError) as exc:
        # 当异常重试超过 `max_retries` 限制时，Celery 将不再重试，触发 Reject/Ack 机制
        # 同时 RabbitMQ 的队列由于配置了 dead-letter-exchange 会把这个任务消息打入 dlx_exchange，落入死信队列死角
        print(f"[批改异常] 正在重试，剩余重试次数限制...")
        raise self.retry(exc=exc)
    except Exception as exc:
        print(f"[批改失败] 不可重试异常: {exc}")
        raise

@app.task(name='tasks.process_dead_letter')
def process_dead_letter(message_body):
    """
    单独的 Worker 任务：专门监听 dead_letter_queue 处理死亡任务
    """
    print(f"[🚨 严重告警] 捕获到死信任务，已触发钉钉/邮件告警，请运维人员检查该记录: {message_body}")
    # 发送告警逻辑，并将原始报文落库...


@app.task(name='tasks.generate_vocab')
def generate_vocab(user_id: int):
    return {"user_id": user_id, "vocab_count": 20}


@app.task(name='tasks.build_report')
def build_report(user_id: int):
    return {"user_id": user_id, "report": "weekly-summary"}


# ==========================================
# 3. 业务接口调用 (模拟 main.py)
# 模拟前端API请求中将耗时任务发往异步队列。
# ==========================================
def api_submit_essay():
    user_id = 1001
    essay_text = "Today is a sunny day..."
    
    # 异步发送任务，并设置最高优先级9 (最高10)
    task = grade_essay.apply_async(
        args=[user_id, essay_text],
        kwargs={"essay_image_url": "https://oss/bucket/xxx.jpg"},
        priority=9 
    )
    
    return {"message": "作文已提交批改", "task_id": task.id}