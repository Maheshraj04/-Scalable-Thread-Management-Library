
from task import ThreadPool
from ui import ThreadUI

if __name__ == "__main__":
    print("Logging system initialized")  
    pool = ThreadPool(num_threads=1)
    ThreadUI(pool)
