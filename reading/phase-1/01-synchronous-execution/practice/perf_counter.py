import time
import requests

url = "https://httpbin.org/delay/2"

start_time = time.perf_counter()
response = requests.get(url)
elapsed_time = time.perf_counter() - start_time

print(f"Elapsed time: {elapsed_time:.4f} seconds")
