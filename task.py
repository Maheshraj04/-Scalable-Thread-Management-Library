import threading
import queue
import time
from enum import Enum


class TaskPriority(Enum):
    HIGH = 1
    MEDIUM = 2
    LOW = 3


class ThreadPool:
    def __init__(self, num_threads=6):
        self.tasks = queue.PriorityQueue()
        self.num_threads = num_threads

        self.lock = threading.Lock()
        self.paused = False
        self.stopped = False

        self.completed_tasks = 0
        self.active_tasks = 0

        # Track current running task
        self.current_task = None

        self.threads = []
        for _ in range(num_threads):
            t = threading.Thread(target=self.worker, daemon=True)
            t.start()
            self.threads.append(t)

    def submit(self, priority, fn, *args):
        self.tasks.put((priority.value, fn, args))

    def worker(self):
        while True:

            if self.stopped and self.tasks.empty():
                break

            if self.paused:
                time.sleep(0.1)
                continue

            try:
                priority, fn, args = self.tasks.get(timeout=0.2)
            except queue.Empty:
                continue

            # Track current running task
            self.current_task = (priority, args)

            with self.lock:
                self.active_tasks += 1

            try:
                fn(*args)
            except Exception as e:
                print("Task error:", e)

            with self.lock:
                self.active_tasks -= 1
                self.completed_tasks += 1

            # Clear current task
            self.current_task = None

            self.tasks.task_done()

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def shutdown(self):
        print("Graceful shutdown initiated...")
        self.stopped = True
        self.tasks.join()
        print("All queued tasks completed. Stopping threads now...")

    def queue_size(self):
        return self.tasks.qsize()

    # NEW FUNCTION → Used by UI to show pending queue
    def get_queue_items(self):
        return list(self.tasks.queue)
