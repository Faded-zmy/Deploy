from fastapi import FastAPI
from pydantic import BaseModel
from retrieval_pipe import get_final_result
import func_timeout
import logging
from datetime import datetime
import os

app = FastAPI()

class Item(BaseModel):
    message: list
    max_token: int = 2000
    openai_key: str = ""
    history_sum: str = ''


@app.get("/health")
def read_health():
    return {"status": "OK"}

@app.post("/items/")
def api_output(item: Item):
    message = item.message
    max_token = item.max_token
    openai_key = item.openai_key
    history_sum = item.history_sum

    #日志
    # log = logging.getLogger('news_wiki.bing')
    # log.setLevel('INFO')
    # date = str(datetime.now().date())
    # if not os.path.exists(save_root+'/log/'):
    #     os.makedirs(save_root+'/log/')
    # file_handler = logging.FileHandler(save_root+'/log/'+date+'.log', encoding='utf-8')
    # file_handler.setLevel('INFO')
    # fmt_str = '%(asctime)s %(thread)d %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s'
    # formatter = logging.Formatter(fmt_str)
    # file_handler.setFormatter(formatter)
    # log.addHandler(file_handler)
    
    try:
        print('message', message)
        result = get_final_result(message, max_token, openai_key, history_sum=history_sum)

    except func_timeout.exceptions.FunctionTimedOut:
        result = {
            "answer": "",
            "type": None
        }
        print("Execution has timed out by 8 seconds !!")
        # log.info("Execution has timed out!")
    print(f"{result}\n")
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4321)
