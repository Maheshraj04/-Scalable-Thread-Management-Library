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

        self.current_task = None          # (priority, fn, args)
        self.progress = 0                 # % based progress 
        self.task_history = []            # Stores completed  tasks

        self.threads = []
        for _ in range(num_threads):
            t = threading.Thread(target=self.worker, daemon=True)
            t.start()
            self.threads.append(t)

    def submit(self, priority, fn, *args):
        self.tasks.put((priority.value, fn, args))

    def get_queue_items(self):
        """Return all pending tasks for UI queue viewer."""
        return list(self.tasks.queue)

    def worker(self):
        while not self.stopped:

            if self.paused:
                time.sleep(0.1)
                continue

            try:
                priority, fn, args = self.tasks.get(timeout=0.2)
            except queue.Empty:
                continue

            start_time = time.time()

            with self.lock:
                self.active_tasks += 1
                self.progress = 0
                self.current_task = (priority, args)

            # --- EXECUTE TASK WITH PROGRESS SIMULATION ---
            try:
                # Task will run normally
                fn(*args)
            except Exception as e:
                print("Task error:", e)

            end_time = time.time()
            duration = round(end_time - start_time, 2)

            with self.lock:
                self.active_tasks -= 1
                self.completed_tasks += 1

                # Save history entry
                self.task_history.append({
                    "value": args[0],
                    "priority": priority,
                    "duration": duration,
                })

                self.current_task = None
                self.progress = 0

            self.tasks.task_done()

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def shutdown(self):
        print("Graceful shutdown initiated...")
        self.stopped = True
        self.tasks.join()
        print("All queued tasks completed. Stopping threads now.")

    def queue_size(self):
        return self.tasks.qsize()




