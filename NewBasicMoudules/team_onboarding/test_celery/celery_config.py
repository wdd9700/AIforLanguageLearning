import os
from kombu import Queue, Exchange

broker_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/1')
result_backend = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/2')

task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'Asia/Shanghai'

# x-max-priority 只在 RabbitMQ 等 AMQP Broker 下生效。
_queue_args = {'x-max-priority': 10} if broker_url.startswith('amqp://') else {}

task_queues = (
    Queue('high_priority', Exchange('high_priority'), routing_key='high.#',
          queue_arguments=_queue_args),
)

task_routes = {
    'tasks.grade_essay': {'queue': 'high_priority', 'routing_key': 'high.essay'},
}

# 仅在需要本地同步调试时开启：CELERY_ALWAYS_EAGER=1
task_always_eager = os.getenv('CELERY_ALWAYS_EAGER', '0') == '1'
task_eager_propagates = True

task_acks_late = True
task_reject_on_worker_lost = True
