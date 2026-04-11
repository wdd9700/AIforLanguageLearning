import time
from celery import Celery
import celery_config

app = Celery('education_tasks')
app.config_from_object(celery_config)

@app.task(bind=True, max_retries=3, default_retry_delay=5)
def grade_essay(self, user_id: int, essay_content: str, essay_image_url: str = None):
    try:
        print(f"[开始批改] 正在处理用户 {user_id} 的作文...")
        if essay_image_url:
            print(f"正在从图片URL获取内容: {essay_image_url}")
            
        time.sleep(3) # 模拟批改延迟
        
        result = {
            "user_id": user_id,
            "score": 92,
            "grammar_errors": [],
            "feedback": "文章结构清晰，词汇丰富，但需注意部分时态。"
        }
        
        print(f"[批改完成] 用户 {user_id} 成绩: {result['score']}")
        return result
        
    except Exception as exc:
        print(f"[批改失败] 发生异常: {exc}，准备重试...")
        raise self.retry(exc=exc)
