from tasks import grade_essay
import time
import os

def api_submit_essay():
    user_id = 1001
    essay_text = "Today is a sunny day..."
    
    print(">>> 提交作文批改任务...")
    task = grade_essay.apply_async(
        args=[user_id, essay_text],
        kwargs={"essay_image_url": "https://oss/bucket/xxx.jpg"},
        priority=9 
    )
    
    print(f">>> 作文批改任务已提交，Task ID: {task.id}")
    print(">>> 正在等待任务结果 (按 Ctrl+C 取消)...")
    max_wait_seconds = int(os.getenv("TASK_RESULT_WAIT_SECONDS", "20"))
    start_ts = time.time()
    
    # 轮询获取结果 (仅作测试演示，实际业务通常由前端轮询或WebSocket推送)
    while not task.ready():
        if time.time() - start_ts > max_wait_seconds:
            print(">>> 等待超时：请确认 Celery Worker 已启动，或设置 CELERY_ALWAYS_EAGER=1 做本地同步调试。")
            return
        time.sleep(1)
        
    if task.successful():
        print(">>> 最终结果:", task.result)
    else:
        print(">>> 任务失败:", task.info)

if __name__ == "__main__":
    api_submit_essay()
