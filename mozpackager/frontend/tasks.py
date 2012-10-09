from celery.decorators import task
from celery.registry import tasks
from celery.task import Task

@task(name='add')
def add( x, y):
    print "WHOOHOOO"
    return x + y


class NewTestTask(Task):
    def run(self, **kwargs):
        print 'Called from Class'
tasks.register(NewTestTask)
#tasks.register(add)
