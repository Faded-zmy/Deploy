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

def run(f, message):
    start_time = time.time()
    result1_root = '/ai_jfs/mengying/Deployment/sum_api/case_result/'
    result1 = json.load(open(result1_root+f, 'r'))
    if len(result1['input'])>=5 and result1['time']>=20 and not os.path.exists('./case_result_5r_20s/'+f):
        request = {
            "message": message
        }

        response = httpx.post(URI, json=request, timeout=200)

        if response.status_code == 200:
            end_time = time.time()
            result = response.json()
            
            all = {'input': message, 'output': result, 'time': end_time - start_time, 'result1': result1['output'], 'time1': result1['time']}
            json.dump(all, open('./case_result_5r_20s/'+f, 'w'), indent=4, ensure_ascii=False)
            print(f"{result}\n")

def main():
    num_processes = 1
    processes = []
    root_path = '/ai_jfs/liwei/data_process/solab_data/'

    
    files = os.listdir(root_path)
    prompt_list = []

    for f in tqdm(files, total=len(files)):
        conv = json.load(open(root_path+f, 'r'))
    
        prompt_list.append(conv)
    

    start_time = time.time()
    # for i in range(num_processes):
    for i in range(len(prompt_list)):
        prompt = prompt_list[i]
        f = files[i]
        try:
            run(f,prompt)
        except:
            print(f)
    #     p = Process(target=run, args=[f, prompt])
    #     p.start()
    #     processes.append(p)
    
    # for p in processes:
    #     p.join()
    end_time = time.time()
    print(f"Total time: {end_time - start_time}")
if __name__ == '__main__':
    main()
