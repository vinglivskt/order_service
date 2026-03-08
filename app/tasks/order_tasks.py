import time

from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.order_tasks.process_order")
def process_order(order_id: str) -> None:
    time.sleep(2)
    print(f"Order {order_id} processed")
