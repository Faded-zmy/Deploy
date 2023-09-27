import requests
import time
import json
# For local streaming, the websockets are hosted without ssl - http://
# HOST = '10.10.100.81:9998' #第7台
HOST = '10.10.100.201:9998' #第6台
URI = f'http://{HOST}/api/v1/chat'

# For reverse-proxied streaming, the remote will likely host with ssl - https://
# URI = 'https://your-uri-here.trycloudflare.com/api/v1/generate'
def text_join(retrival_page):
    textstr = 'title='+retrival_page[1]+', text='+retrival_page[0]
    print(textstr)
    return textstr


def run(text, cite=False):
    
    request = {
        'text':text,
        'mode': 'news', #'news', 'auto', 'wiki'
        'cite': cite,
        'top_num': 3
        }

    response = requests.post(URI, json=request)

    if response.status_code == 200:
        res = response.json()
        print(res)
        return res


if __name__ == '__main__':
    # topic = "games shanda Chen Tianqiao"
    t1 = time.time()
    conv1 = {
    "fullName": "A",
    "roomId": "64e2d9b0c71e56597f9f345764d44baa2e497c06de2eac1b",
    "msgId": "64e6023f36c49e3f45c45dd4",
    "content": "@Socrates What are the current news?",
    "parent": "",
    "chatHistory": [
            "A: The weather has been becoming more and more extreme recently.",
            "B: Yes, the issue of global climate change is becoming increasingly urgent. Do you know what new strategies have been adopted recently to address this problem?"
        ]

    }
    conv2 = {
    "fullName": "A",
    "roomId": "64e2d9b0c71e56597f9f345764d44baa2e497c06de2eac1b",
    "msgId": "64e6023f36c49e3f45c45dd4",
    "content": "@Socrates How is artificial intelligence being utilized in the field of medical diagnosis, and what potential drawbacks should be considered?",
    "parent": "",
    "chatHistory": [
            "A: I've been reading a lot about how artificial intelligence is making its way into the field of medical diagnosis.",
            "B: Absolutely, AI has shown promising results in helping doctors with quicker and more accurate diagnoses."
        ]

    }
    conv3 = {
    "fullName": "A",
    "roomId": "64e2d9b0c71e56597f9f345764d44baa2e497c06de2eac1b",
    "msgId": "64e6023f36c49e3f45c45dd4",
    "content": "@Socrates What are the key advancements in renewable energy technology that are contributing to the energy revolution?",
    "parent": "",
    "chatHistory": [
            "A: The shift towards renewable energy sources seems to be gaining momentum.",
            "B: Absolutely, advancements in technology are making it more feasible and cost-effective."
        ]

    }
    conv4 = {
    "fullName": "A",
    "roomId": "64e2d9b0c71e56597f9f345764d44baa2e497c06de2eac1b",
    "msgId": "64e6023f36c49e3f45c45dd4",
    "content": "@Socrates How are governments and financial institutions adapting to the rise of digital currencies and their effects on the traditional financial system?",
    "parent": "",
    "chatHistory": [
            "A: Have you been keeping up with the rise of digital currencies lately?",
            "B: Definitely, it's hard to ignore the impact they're having on the financial landscape.",
            "A: I'm really intrigued by how governments and financial institutions are responding to this digital currency trend and its effects on traditional finance.",
            "B: That's a complex issue. Governments are grappling with regulatory frameworks, some are exploring central bank digital currencies, while others are cautious about potential risks. Financial institutions are considering blockchain technology for more efficient transactions, but concerns about security and stability remain.",
            "A: It's fascinating how this technology is reshaping the entire financial system. I wonder what the future holds.",
            "B: Absolutely, it's an ongoing journey with a lot of uncertainties, but also plenty of potential for positive change."
        ]

    }

    cite = True #False
    try_time = 10
    for conv in [conv1, conv2, conv3, conv4]:
        run(conv, cite)
    t2 = time.time()
    print('total time',t2-t1)
    print('average time', (t2-t1)/try_time)

    # news_topic_ls = [
    #     "Have you heard anything about Japan releasing nuclear wastewater recently?",
    #     "你知道最近日本排放核废水的消息吗？"
    #     # "The prospects and risks of artificial intelligence in medical diagnosis.",
    #     # "The energy revolution driven by renewable energy technology.",
    #     # "The impact and exploration of digital currencies on the traditional financial system."
    #     ]
    # chat_history = [
    #     ["A: 最近环境污染问题越来越严重了","B: 对，不仅是空气，现在大海也在被污染。"],
    #     ["A: Environmental pollution has been getting more serious lately.", "B: Absolutely, it's not just the air, even the oceans are being polluted now."],
    #     ["A: Environmental pollution has been getting more serious lately.","B: 对，不仅是空气，现在大海也在被污染。"]
    # ]
    # cite = True #False
    # res = []
    # for [n,c] in [[0,1], [1,0], [0,2]]:
    #     conv = {
    #         "fullName": "A",
    #         "roomId": "64e2d9b0c71e56597f9f345764d44baa2e497c06de2eac1b",
    #         "msgId": "64e6023f36c49e3f45c45dd4",
    #         "content": news_topic_ls[n],
    #         "parent": "",
    #         "chatHistory": []

    #         }
    #     res_one = run(conv, cite)
    #     res_one['question'] = news_topic_ls[n]
    #     res_one['chat_history'] = chat_history[c]
    #     res.append(res_one)
    # json.dump(res, open('cite.json', 'w'), indent=4)


    # print('total time',t2-t1)
    # python3 llama2_deploy/api_example.py --topic The rise and relevance of upcycling in the modern world. --round_time 30 --character [Harry Potter, Elon Musk]
    # fire.Fire(run)
