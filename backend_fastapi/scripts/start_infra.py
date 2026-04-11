"""一键启动本地基础设施服务"""

from __future__ import annotations

import subprocess
import sys
import time


def run(cmd: list[str]) -> None:
    print("$ " + " ".join(cmd))
    subprocess.run(cmd, check=True)


def wait_for_postgres(max_wait: int = 60) -> None:
    print("Waiting for PostgreSQL...")
    for i in range(max_wait):
        try:
            import psycopg2

            psycopg2.connect(
                host="localhost",
                port=5432,
                dbname="aifl_db",
                user="aifl_user",
                password="aifl_password",
                connect_timeout=2,
            ).close()
            print("PostgreSQL is ready.")
            return
        except Exception:
            time.sleep(1)
    sys.exit("PostgreSQL did not become ready in time.")


def wait_for_redis(max_wait: int = 30) -> None:
    print("Waiting for Redis...")
    for i in range(max_wait):
            import redis

            try:
                r = redis.Redis(host="localhost", port=6379, socket_connect_timeout=2)
                if r.ping():
                    print("Redis is ready.")
                    return
            except Exception:
                pass
            time.sleep(1)
    sys.exit("Redis did not become ready in time.")


def wait_for_es(max_wait: int = 60) -> None:
    print("Waiting for Elasticsearch...")
    import urllib.request

    for i in range(max_wait):
        try:
            resp = urllib.request.urlopen("http://localhost:9200/_cluster/health", timeout=2)
            if resp.status == 200:
                print("Elasticsearch is ready.")
                return
        except Exception:
            pass
        time.sleep(1)
    sys.exit("Elasticsearch did not become ready in time.")


def wait_for_rabbitmq(max_wait: int = 60) -> None:
    print("Waiting for RabbitMQ...")
    import urllib.request

    for i in range(max_wait):
        try:
            req = urllib.request.Request(
                "http://localhost:15672/api/overview",
                headers={"Authorization": "Basic " + "Z3Vlc3Q6Z3Vlc3Q="},
            )
            resp = urllib.request.urlopen(req, timeout=2)
            if resp.status == 200:
                print("RabbitMQ is ready.")
                return
        except Exception:
            pass
        time.sleep(1)
    sys.exit("RabbitMQ did not become ready in time.")


def wait_for_minio(max_wait: int = 30) -> None:
    print("Waiting for MinIO...")
    import urllib.request

    for i in range(max_wait):
        try:
            resp = urllib.request.urlopen("http://localhost:9000/minio/health/live", timeout=2)
            if resp.status == 200:
                print("MinIO is ready.")
                return
        except Exception:
            pass
        time.sleep(1)
    sys.exit("MinIO did not become ready in time.")


if __name__ == "__main__":
    base_dir = __file__.rsplit("scripts", 1)[0]
    run(["docker", "compose", "-f", f"{base_dir}docker-compose.dev.yml", "up", "-d"])
    run(["docker", "compose", "-f", f"{base_dir}docker-compose.infra.yml", "up", "-d"])
    wait_for_postgres()
    wait_for_redis()
    wait_for_es()
    wait_for_rabbitmq()
    wait_for_minio()
    print("\nAll infrastructure services are up and healthy.")
