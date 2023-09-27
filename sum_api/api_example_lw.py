import httpx
from multiprocessing import Process
import time
import json
import os
from tqdm import tqdm
# For local streaming, the websockets are hosted without ssl - http://
# HOST = '0.0.0.0:6767'
HOST = '10.10.100.164:6688'
URI = f'http://{HOST}/items/'
# URI = 'https://dev-api.memorylab.works/api/InfoGPT/v1/items/' #测试版本
# URI = 'https://api.memorylab.works/api/InfoGPT/v1/items/' #正式版本


# For reverse-proxied streaming, the remote will likely host with ssl - https://
# URI = 'https://your-uri-here.trycloudflare.com/api/v1/generate'

def run(file, message,hist):
    start_time = time.time()
    request = {
        "message": message,
        "history_sum":hist
    }

    response = httpx.post(URI, json=request, timeout=200)

    if response.status_code == 200:
        end_time = time.time()
        result = response.json()
        all = {'input': message, 'output': result, 'time': end_time - start_time}
        json.dump(all, open('./case_result/'+file, 'w'), indent=4, ensure_ascii=False)
        print(f"{result}\n")

def main():
    num_processes = 1
    processes = []
    hist="In this session, the discussion mainly revolved around the design principles of Milvus and the topic of scalability in next-generation vector databases. UserA initiated the conversation, delving into Milvus's design principles, such as the log-based data approach, duality of table and log, and log persistency. Socrates elaborated on these principles, highlighting their advantages and their alignment with cloud-native design, in response to inquiries from user_B and User_c. In the second part of the session, Socrates emphasized the importance of scalability in next-generation vector databases, discussing factors like distributed processing, high throughput, low latency, load balancing, cloud-native deployment, and cost efficiency, with User A serving as a prompting participant."
    f = '/ai_jfs/liwei/data_process/solab_data/e3918379-341b-7cab-b409-3a0d33e25c2e.json'
    #file = os.listdir(root_path)
    #prompt_list = []

    #for f in tqdm(file, total=len(file)):
    #    conv = json.load(open(root_path+f, 'r'))
    
    #    prompt_list.append(conv)
    start_time = time.time()
    # for i in range(num_processes):
    prompt = json.load(open(f, 'r'))
    run(f.split("/")[-1],prompt,hist)
    #     p = Process(target=run, args=[f, prompt])
    #     p.start()
    #     processes.append(p)
    
    # for p in processes:
    #     p.join()
    end_time = time.time()
    print(f"Total time: {end_time - start_time}")
if __name__ == '__main__':
    main()
