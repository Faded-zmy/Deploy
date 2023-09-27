import httpx
from multiprocessing import Process
import time
import json
import os
from tqdm import tqdm

HOST = '0.0.0.0:6699'
URI = f'http://{HOST}/items/'


def run(message, openai_key, hist):
    start_time = time.time()
    request = {
        "message": message,
        "openai_key": openai_key,
        "history_sum":hist
    }

    response = httpx.post(URI, json=request, timeout=200)

    if response.status_code == 200:
        end_time = time.time()
        result = response.json()
        print(f"{result}\n")

def main():
 
    hist="In this session, the discussion mainly revolved around alternative recipes for grain-based noodles and how to make delicious rice cakes. <b>Mrs. Puff</b> asked for alternative recipes for grain-based noodles and how to make delicious rice cakes, and <b>Socrates</b> provided <b>Sandy Cheeks</b> with alternative recipes for grain-based noodles and explained how to make delicious rice cakes. Later, <b>Sandy Cheeks</b> expressed confusion about the difference between two things, and <b>Socrates</b> apologized for the previous incorrect answer and provided the correct recipe for sweet rice cake."

    f = '/ai_jfs/mengying/Deployment/sum_api_zmy/3962a0e2-5c2d-1862-5124-3a0cfb1fd560.json'
    prompt = json.load(open(f, 'r'))

    openai_key = "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"

    run(prompt,openai_key,hist)
  
if __name__ == '__main__':
    main()
