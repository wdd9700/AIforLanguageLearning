"""
【MinIO/OSS 分片上传支持大文件实现】

核心作用与业务价值：
1. 突破单次HTTP请求的限制（如 Nginx/网关文件大小限制），允许前端安全、稳定地上传GB级大文件（如高清视频、复杂数据集）。
2. 支持“断点续传”、“多线程并发上传”，如果某一个分片上传失败，前端只需重试该分片，极大提高网络不稳定时的上传成功率。
3. 释放后端服务器的带宽压力：前后端配合，后端仅颁发每次分片的预签名URL（安全通行证），真实文件数据流不经过后端，由前端直传给 MinIO。

基于 boto3 库实现的分片上传全生命周期：
步骤1：初始化分片上传任务（获取 UploadId）
步骤2：服务端批量生成分片的预签名URL（供前端并发上传每一个块）
步骤3：所有块前端上传完毕后，通知服务器合并分片完成文件落地
"""

import os
import boto3
from botocore.config import Config
from typing import List, Dict

import uuid

# ==========================================
# 配置 S3 客户端：支持真实 MinIO 与 Mock 双模式
# ==========================================

# 构造一个模拟 S3 客户端，防止在没有开启 Docker MinIO 服务时报错卡死
class MockS3Client:
    def head_bucket(self, Bucket): pass
    def create_bucket(self, Bucket): pass
    def create_multipart_upload(self, Bucket, Key, ContentType):
        # 伪造一个唯一的上传 ID
        return {'UploadId': str(uuid.uuid4())}
    def generate_presigned_url(self, ClientMethod, Params, ExpiresIn):
        # 伪造一个含有秘钥串的临时 URL
        return f"http://localhost:9000/{Params['Bucket']}/{Params['Key']}?uploadId={Params['UploadId']}&partNumber={Params['PartNumber']}&X-Amz-Signature=mock_signature..."
    def complete_multipart_upload(self, Bucket, Key, UploadId, MultipartUpload):
        # 伪造合并成功后的返回值
        return {'Location': f"http://localhost:9000/{Bucket}/{Key}"}

def build_s3_client():
    use_mock = os.getenv("MINIO_USE_MOCK", "1") == "1"
    if use_mock:
        print("[提示] MINIO_USE_MOCK=1，当前使用 MockS3Client（不会连接真实 MinIO）。")
        return MockS3Client()

    endpoint = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
    access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    region = os.getenv("MINIO_REGION", "us-east-1")

    return boto3.client(
        's3',
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version='s3v4'),
        region_name=region
    )


S3_CLIENT = build_s3_client()

BUCKET_NAME = os.getenv("MINIO_BUCKET", "education-assets")

# 为了本地测试顺利，增加一个主动创建 Bucket 的小逻辑
if isinstance(S3_CLIENT, MockS3Client):
    print("[提示] 使用 Mock 客户端，跳过真实 Bucket 检查与创建。")
else:
    try:
        S3_CLIENT.head_bucket(Bucket=BUCKET_NAME)
    except Exception:
        try:
            S3_CLIENT.create_bucket(Bucket=BUCKET_NAME)
            print(f"--> 已自动创建测试 Bucket: {BUCKET_NAME}")
        except Exception as e:
            print(f"创建 Bucket 失败（如果没开本地 MinIO 会报错）: {e}")

def init_multipart_upload(object_name: str, content_type: str = "application/octet-stream") -> str:
    """
    步骤 1: 告诉 MinIO 要开启一次大文件分片上传任务。
    返回唯一的 UploadId (此次大文件上传过程的唯一事务凭证)
    """
    print(f"[{object_name}] 初始化分片上传任务...")
    
    response = S3_CLIENT.create_multipart_upload(
        Bucket=BUCKET_NAME,
        Key=object_name,
        ContentType=content_type
    )
    
    upload_id = response['UploadId']
    print(f"--> 成功获取 UploadId: {upload_id}")
    return upload_id


def generate_presigned_urls_for_parts(object_name: str, upload_id: str, part_count: int) -> List[str]:
    """
    步骤 2: 为文件切出的所有包(Part)生成可以临时上传的“预签名URL”。
    前端切好文件块后，使用这些生成的独立URL进行 PUT 直传操作。
    """
    print(f"[{object_name}] 为 {part_count} 个分块生成预签名直传URL...")
    
    presigned_urls = []
    for part_number in range(1, part_count + 1):
        # 利用 Client 生成单个包专用的签发URL
        url = S3_CLIENT.generate_presigned_url(
            ClientMethod='upload_part',
            Params={
                'Bucket': BUCKET_NAME,
                'Key': object_name,
                'UploadId': upload_id,
                'PartNumber': part_number
            },
            ExpiresIn=3600  # 1小时过期机制(符合权限最小化安全原则)
        )
        presigned_urls.append({
            "part_number": part_number,
            "upload_url": url
        })
        
    return presigned_urls


def complete_multipart_upload(object_name: str, upload_id: str, parts_info: List[Dict]):
    """
    步骤 3: 前端反馈所有分片块都上传完成了，指挥 MinIO 后台将所有的快块拼合起来，形成最终的可用大文件。
    注意：parts_info 里面需要包含前端通过预签名URL上传完成后，MinIO返回的 ETag 头部响应信息。
    """
    print(f"[{object_name}] 所有分片就绪，正在触发 MinIO 进行文件合并指令...")
    
    # 格式要求: [{'PartNumber': 1, 'ETag': '"xxxxxx"'}, {'PartNumber': 2, 'ETag': '"yyyyyy"'}]
    response = S3_CLIENT.complete_multipart_upload(
        Bucket=BUCKET_NAME,
        Key=object_name,
        UploadId=upload_id,
        MultipartUpload={
            'Parts': parts_info
        }
    )
    
    print("--> 分片合并成功！最终文件访问地址: ", response.get('Location', f"/{BUCKET_NAME}/{object_name}"))
    return True


# ==========================================
# 模拟业务全流程使用调用
# ==========================================
if __name__ == "__main__":
    file_key = "users/1001/essays/high_res_scan_video.mp4"
    total_parts = 5  # 假设前端计算这是一个50MB的文件，按每片10MB切，一共切了 5 份
    
    try:
        # 1. 先声明一场上传任务
        upload_id = init_multipart_upload(file_key, "video/mp4")
        
        # 2. 为前端批量生成这些切片的临时绿色安全通道 (URL)
        urls_list = generate_presigned_urls_for_parts(file_key, upload_id, total_parts)
        
        print("\n[模拟发给前端的数据] 请前端将分片发送往以下地址：")
        for u in urls_list:
            print(f"分片 {u['part_number']}: {u['upload_url'][:80]}...")
            
        print("\n(假设前端已经顺着上面的URL，用axios的PUT方法把真文件全传进MinIO了...)")
        print("(同时前端传完每一片后，收集到了对应的 ETag 值)")
        
        # 3. 前端完成上传后，将所有分片序号对应的校验码 ETag 原路传回给我们的后端完成组装
        mock_etags_from_frontend = [
            {"PartNumber": 1, "ETag": '"etag_mock_string_1"'},
            {"PartNumber": 2, "ETag": '"etag_mock_string_2"'},
            {"PartNumber": 3, "ETag": '"etag_mock_string_3"'},
            {"PartNumber": 4, "ETag": '"etag_mock_string_4"'},
            {"PartNumber": 5, "ETag": '"etag_mock_string_5"'},
        ]
        
        complete_multipart_upload(file_key, upload_id, mock_etags_from_frontend)
        
    except Exception as e:
        print(f"产生错误, 分片上传失败: {e}")
        # 【进阶处理】: 若果上传到一半用户关网页跑了，可以调用 abort_multipart_upload 杀掉这一批僵尸孤儿碎片
        # boto3.client('s3').abort_multipart_upload(Bucket=BUCKET_NAME, Key=file_key, UploadId=upload_id)
