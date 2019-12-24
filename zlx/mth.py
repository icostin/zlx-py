# multithreading helper
import threading
from collections import namedtuple
from zlx.utils import dmsg

QUEUED = 0
RUNNING = 1
COMPLETE = 2
FAILED = 3
CANCELLED = 4
CANCELED = CANCELLED

#* worker_job ***************************************************************
class worker_job:
    __slots__ = 'manager func result error state_'.split()
    def __init__ (job, manager, func):
        job.manager = manager
        job.func = func
        job.state_ = QUEUED
    def wait (job):
        return job.manager._wait(job)
    def cancel (job):
        '''returns the job state:
        * RUNNING: (cannot cancel it it is running)
        * COMPLETE: already ran and returned value
        * FAILED: already ran and returned exception
        * CANCELLED: successfully cancelled the job
        '''
        return job.manager._cancel(job)
    def get_state (job):
        return job.manager.get_job_state(job)


#* worker_manager ***********************************************************
class worker_manager:

# worker_manager.__init__()
    def __init__ (manager, init_worker_count = 4, max_worker_count = 16):
        manager.workers_ = []
        manager.up_ = True
        manager.lock_ = threading.Lock()
        manager.cond_ = threading.Condition(manager.lock_)
        manager.queue_ = []
        for i in range(init_worker_count):
            manager._add_worker()

# worker_manager.get_job_state()
    def get_job_state (manager, job):
        with manager.lock_:
            return job.state_

# worker_manager.queue()
    def queue (manager, work_func):
        with manager.lock_:
            job = worker_job(manager, work_func)
            manager.queue_.append(job)
            dmsg('queued job {}', job)
            manager.cond_.notify()
        return job

# worker_manager.shutdown()
    def shutdown (manager):
        with manager.lock_:
            if not manager.up_: return
            manager.up_ = False
            dmsg('notifying workers to exit...')
            manager.cond_.notify_all()
        for w in manager.workers_:
            w.join()
        dmsg('done shutting down')

# worker_manager.__del__()
    def __del__ (manager):
        '''
        cleanly shut down when all references to this object are lost
        '''
        manager.shutdown()

# worker_manager._add_worker()
    def _add_worker (manager):
        with manager.lock_:
            worker_id = len(manager.workers_)
            dmsg('adding worker {}...', worker_id)
            w = threading.Thread(
                    target = manager._worker,
                    kwargs = dict(worker_id = worker_id))
            manager.workers_.append(w)
        w.start()

# worker_manager._worker()
    def _worker (manager, worker_id):
        dmsg('worker {} starting...', worker_id)
        with manager.lock_:
            while manager.up_:
                while manager.queue_:
                    job = manager.queue_.pop(0)
                    dmsg('worker {} executing job {}', worker_id, job)
                    manager._exec_while_locked(job)
                manager.cond_.wait()
                dmsg('worker {} awake', worker_id)
            dmsg('worker {} exiting...', worker_id)

# worker_manager._exec_while_locked()
    def _exec_while_locked (manager, job):
        job.state_ = RUNNING
        manager.lock_.release()
        try:
            job.result = job.func()
            state = COMPLETE
        except Exception as e:
            state = FAILED
            job.error = e
        manager.lock_.acquire()
        job.state_ = state
        manager.cond_.notify_all()

# worker_manager._wait()
    def _wait (manager, job):
        with manager.lock_:
            assert job.manager == manager
            while job.state_ in (QUEUED, RUNNING):
                manager.cond_.wait()
            return job.state_

# worker_manager._cancel()
    def _cancel (manager, job):
        with manager.lock_:
            if job.state_ == QUEUED:
                manager.queue_.remove(job)
                job.state_ = CANCELLED
                manager.cond_.notify_all()
            return job.state_

# class worker_manager - end

#* self_test ****************************************************************
def boom ():
    raise RuntimeError("boom")

def slow_func ():
    import time
    for i in range(10):
        time.sleep(i * 0.001)

def self_test ():
    import time
    dmsg('running zlx.mth.self_test()...')
    try:
        wm = worker_manager(
                init_worker_count = 2,
                max_worker_count = 4)

        j123 = wm.queue(lambda: 123)
        jboom = wm.queue(boom)

        j123.wait()
        dmsg('j123: {}', j123.get_state())
        assert j123.get_state() == COMPLETE
        assert j123.result == 123
        dmsg('* complete simple job: passed')

        jboom.wait()
        assert jboom.get_state() == FAILED
        assert isinstance(jboom.error, RuntimeError)
        dmsg('* raise exception job: passed')

        while True:
            j = wm.queue(lambda: 234)
            if j.cancel() == CANCELLED: break
        dmsg('* cancelling job: passed')

        while True:
            j = wm.queue(slow_func)
            s = QUEUED
            while s == QUEUED:
                s = j.get_state()
                dmsg('state = {}', s)
                time.sleep(0.001)
            s = j.cancel()
            dmsg('cancelling running job: {}', s)
            if s == RUNNING:
                j.wait()
                break
        dmsg('* attempt to cancel running job: passed')

    finally:
        wm.shutdown()
    return

