from celery.decorators import task
from celery.registry import tasks
from celery.task import Task

@task(name='add')
def add(x, y):
    return x + y

tasks.register(add)
