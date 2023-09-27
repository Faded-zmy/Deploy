import openai
import requests
import tiktoken
import time
import logging
import re 
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread, Lock

HOST_WIKI = '10.10.100.201:7778'
URI_WIKI = f'http://{HOST_WIKI}/api/v1/chat'


HOST_NEWS = '10.10.100.81:7779'
URI_NEWS = f'http://{HOST_NEWS}/api/v1/chat'


MAX_TETRY_TIMES = 5

NEWS_TOP_N = 3
NEWS_TOKEN_LIMIT = {
    5:100,
    4:100,
    3:100,
    2:100,
    1:200
}

user_intentions = ['news', 'wiki', 'chat']



def openai_chatcompletion(prompt, api_id, model_id=0, temperature=0):
    # api_id = 0
    api_key = [
        "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",
        "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",
        "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",
        "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",
    ]
    models=["gpt-3.5-turbo", "gpt-3.5-turbo-16k"]
    openai.api_key = api_key[api_id]
    cn = 0
    enc = tiktoken.get_encoding("cl100k_base")
    print(f"Tokens Of Prompt in {api_id}: {len(enc.encode(prompt))}!")
    if len(enc.encode(prompt)) > 4000:
        print("Tokens > 4k, return directly.")
        return None
    while True:
        output = ""
        try:
            response = openai.ChatCompletion.create(
                # model="gpt-4-0613",
                model=models[model_id],
                # model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                # max_tokens=max_token,
                request_timeout=120,
                timeout=120
            )
            usages = response['usage']

            print("Request cost: {0}".format(usages['total_tokens']))
            output = response['choices'][0]['message']['content']
            break
        except openai.error.OpenAIError as e:
            print(f"error {e} {api_id}")
            logging.warning("Error: {0}. Retrying...".format(e))
            cn += 1
            if cn > 3:
                print(f"Already tried more than {cn} times!")
                break
            time.sleep(18)

    return output



def PreProcess(data):
    
    conv = data['fullName']+': '+data['content'].replace('@Socrates', '')
    conv = '\n'.join(data['chatHistory'])+'\n'+conv
    return conv

def intent_recognition(input, parent=''):
    """
    :param input: Chat history, 包括当前的query（拼在最后）
    :param llm:
    :param args:
    :return:
    """
    if parent != '':
        input += f"(Cite:'{parent}')"
    prompt = f"""
    The following is a conversation between some users and AI assistant Socretes:
    [Start of the conv]
    {input}
    [End of the conv]
    You are an outstanding expert in intent recognition, capable of accurately and precisely identifying users' intentions from conversations: discuss/chat, searching for news, searching for Wikipedia information. Please analyze the last user's intention according to the conversation, assisting the assistant in making decisions involves either providing direct responses or conducting searches. 
    Requirement:
    1. Output 1 for news, 2 for wiki, 3 for chat. 
    2. If the user inquires about the assistant's viewpoint or opinion, and the mentioned topic has been previously mentioned in the preceding text, the user's intent is to chat. Search should only be conducted when users want to know the latest updates about certain things, acquire detailed information about specific matters, and the relevant information has not been previously mentioned in the conversation history.
    3. If the noun referred to in the user's last sentence pertains to the content mentioned earlier, you need to supplement the user's question to make it easier to comprehend and search.
    4. All of your outputs must be in English.

    The output format should be like:
    Output: xxx
    Supplemented Question: xxx"""
    output = openai_chatcompletion(prompt, 1)
    # print('debug'+'-'*60)
    # print('prompt', prompt)
    # print('intent_recognition',output)
    # print('-'*60)
    output = output.split('\n')
    intent, s_question = 3, ''
    for text in output:
        if 'output' in text.lower() and ':' in text.lower():
            try:
                intent = int(text.split(':')[1].strip())
            except Exception as e:
                print(e)
                intent = 3
        elif 'supplemented' in text.lower() and ':' in text.lower():
            try:
                s_question = text.split(':')[1].strip()
            except Exception as e:
                print(e)
                s_question = ''
    print(f"User intention: {user_intentions[intent-1]}")
    return intent, s_question


def search_docs(query, search_type, news_top_n):
    request = {'text': query}
    res = ""
    urls = []
    if search_type == 1: # 如果是news
        # print(f"Searching news: {query}")
        response = requests.post(URI_NEWS, json=request)
        if response.status_code == 200:
            result = response.json()['reponses']
            # print(result)
        # 解析news的返回
        print('debug'+'-'*60)
        print('news_result',result)
        print('len(result)',len(result))
        print('-'*60)
        res_len = len(result)
        res = []
        news_nums = res_len//6

        for i in range(min(news_nums, news_top_n)):
            res.append({'title': result[i], 'text': result[news_nums+i], 'description': result[news_nums*4+i]+' ......', 'previewUrl': result[news_nums*2+i], "imageUrl": result[news_nums*3+i], "domain": 'www.msn.com', "imageWidth": 200, "imageHeight": 200, 'date':result[news_nums*5+i]})
        # res = "\n".join([f"News[{i+1}]:(Title:{result[i]}):{result[i+news_nums]}" for i in range(news_nums)])
        # urls = result[news_nums*2: news_nums*3]

    elif search_type == 2: # 如果是wiki
        # print(f"Searching wiki: {query}")
        response = requests.post(URI_WIKI, json=request)
        if response.status_code == 200:
            result = response.json()['reponses']
            # print(result)
        # 解析wiki的返回
        res = []
        for idx, doc in enumerate(result):
            res.append({'title': doc[1], 'description': doc[0], 'previewUrl': f"https://en.wikipedia.org/wiki/{doc[1].replace(' ', '_')}", "domain": 'www.wikipedia.org'})
            # res += f"Document[{idx+1}]:(Title:{doc[1]}): {doc[0]}" + '\n'
            # urls.append(f"https://en.wikipedia.org/wiki/{doc[1].replace(' ', '_')}")

    return res#, urls


def get_output(docs, query, search_type, news_top_n):
    enc = tiktoken.get_encoding("cl100k_base")
    # print('len', len(docs.split(' ')[0]))
    # print('docs', docs)
    # if len(enc.encode(docs)) > 4000:
    #     # docs = 'News'.join([d[:500] for d in docs.split('News')])
    #     docs = ''
    # print('docs', len(docs))
    if docs == "":
        docs = "None"
    if search_type == 1:
        # if len(enc.encode(docs)) > 4000:
        res = "\n".join([f"News[{i+1}]:(Title:{docs[i]['title']}):{' '.join(docs[i]['text'].split(' ')[0: NEWS_TOKEN_LIMIT[news_top_n]])}" for i in range(min(news_top_n, len(docs)))])
        # else:
        #     res = "\n".join([f"News[{i+1}]:(Title:{docs[i]['title']}):{' '.join(docs[i]['text'].split(' '))}" for i in range(len(docs))])
        prompt = """Instruction: Write an accurate, engaging, and concise answer for the given question using only the provided search results (some of which might be irrelevant) and cite them properly. Use an unbiased and journalistic tone. Always cite for any factual claim. When citing several search results, use [1][2][3]. Cite at most three news in each sentence. If multiple news support the sentence, only cite a minimum sufficient subset of the news.
        Question: 
        {q}
        News: 
        {w}
        Answer:""".format(q=query, w=res)
        # print(prompt)
    elif search_type == 2:
        res = "\n".join([f"Document[{i+1}]:(Title:{docs[i]['title']}):{' '.join(docs[i]['description'].split(' '))}" for i in range(len(docs))])
        prompt = """Instruction: Write an accurate, engaging, and concise answer for the given question using only the provided search results (some of which might be irrelevant) and cite them properly. Use an unbiased and journalistic tone. Always cite for any factual claim. When citing several search results, use [1][2][3]. Cite at least one document and at most three documents in each sentence. If multiple documents support the sentence, only cite a minimum sufficient subset of the documents.
        Question: 
        {q}
        Wiki: 
        {w}
        Answer:""".format(q=query, w=docs)
    else:
        return ""
    # print('debug'+'-'*60)
    # print('prompt',prompt)
    output = openai_chatcompletion(prompt, 0)
    # print('output',output)
    # print('-'*60)

    return output


def reformat_output(output, urls):
    """
    :param output: llm直接输出的文本
    :param urls: 所有urls
    :return: 格式化后的文本, 真正使用了的url，从1开始
    """
    print(output)
    # 处理不同上标引用同一来源的问题, 如[1, 2, 3, 4], 其中2,3,4其实是相同的链接, 要改为[1, 2, 2, 2]
    replace_symbols = ['Ⅰ', 'II', "III", "IV", "V"]
    for i, url in enumerate(urls):
        output = output.replace(f'[{i+1}]', f'[{urls.index(url)+1}]')
    
    pattern = r'\[(\d+)\]'
    matches = re.findall(pattern, output)
    citation_matches = [int(match) for match in matches] # 匹配
    citation_list= []
    for i in citation_matches: # 绝对去重
        if i not in citation_list:
            citation_list.append(i)
    # 处理不连续的引用， 如[1, 1, 2, 5] -> [1, 1, 2, 3]
    for idx, citation in enumerate(citation_list):
        output = output.replace(f'[{citation}]', f'[{replace_symbols[idx]}]')
    for idx, symbol in enumerate(replace_symbols):
        output = output.replace(f'[{symbol}]', f'[{idx+1}]')
    # print(output)
    # print(urls)
    # print(citation_list)
    # 处理连续引用相同上标问题-单个
    def merge_consecutive_duplicate_references(text):
        references = []
        references_idx = []
        i = 0
        while i < len(text):
            if text[i] == '[':
                left_idx, right_idx = i, i
                for j in range(i+1, len(text)):
                    if not text[j].isdigit() and text[j] not in ['[', ']']:
                        right_idx = j
                        break
                references.append(text[left_idx: right_idx])
                references_idx.append([left_idx, right_idx])
                i = j
                continue
            i += 1
        for i in range(len(references)-1, 0, -1):
            if references[i] == references[i-1]:
                left_index, rigth_index = references_idx[i-1][0], references_idx[i-1][1]
                fill_string = re.sub(r'\d', 'x', text[left_index:rigth_index])
                text = text[0:left_index] + fill_string + text[rigth_index:]
        output = text.replace('[x]', '').replace(' .', '.')
        return output
    output = merge_consecutive_duplicate_references(output)
    # output = output.replace('[x]', '').replace(' .', '.')
    return output, citation_list


def get_final_result(data, mode, cite=False, news_top_n=NEWS_TOP_N):
    
    # print('chat_history',chat_history)
    t2 = time.time()
    if mode == 'news':
        intent = 1
        query = data['fullName']+': '+data['content'].replace('@Socrates', '')
    elif mode == 'wiki':
        intent = 2
        query = data['fullName']+': '+data['content'].replace('@Socrates', '')

    elif mode == 'auto':
        chat_history = PreProcess(data)
        t1 = time.time()
        print('chat_history[-5:]', chat_history[-5:])
        intent, query = intent_recognition(chat_history[-5:], data['parent'])
        t2 = time.time()
        # print(f"Intent recognition time: {t2-t1}")
    # print('debug'+'-'*60)
    # print('intent',intent)
    # print('query',query)
    # print('-'*60)
    docs = search_docs(query, intent, news_top_n)
    t3 = time.time()
    print(f"Search time: {t3-t2}")
    # print('debug'+'-'*60)
    # print('docs',docs)
    # print('-'*60)
    output = get_output(docs, query, intent, news_top_n)
    t4 = time.time()
    print(f"Generation time: {t4-t3}")
    # print('debug'+'-'*60)
    # print('output', output)
    # print('-'*60)
    urls = [d['previewUrl'] for d in docs]
    final_output, citations = reformat_output(output, urls)
    # print('debug'+'-'*60)
    # print('final_output',final_output)
    # print('citations',citations)
    # print('-'*60)
    if intent == 1 or intent == 2:
        if cite:
            if intent == 1:
                retri_infos = []
                for c in citations:
                    retri_infos.append({'title': docs[c-1]['title'], 'description': docs[c-1]['description'], 'previewUrl': docs[c-1]['previewUrl'], "imageUrl": docs[c-1]['imageUrl'], "domain": 'www.msn.com', "imageWidth": 200, "imageHeight": 200, 'date':docs[c-1]['date']})
                output = {
                    "answer": final_output,
                    "type": user_intentions[intent-1],
                    "retri_infos":retri_infos
                }
            else:
                output = {
                    "answer": final_output,
                    "type": user_intentions[intent-1],
                    "retri_infos":[docs[c-1] for c in citations]
                }
        else:
            output = {
                "answer": final_output.replace('[1]','').replace('[2]','').replace('[3]','').replace('[4]','').replace('[5]',''),
                "type": user_intentions[intent-1]
            }
        
   
    else:
        output = {
            "answer": "",
            "type": None
        }
    t5 = time.time()
    print(f"total time: {t5-t2}")
    
    return output

# def get_final_result(conv):
#     # conv = PreProcess(conv)
#     judge_prompt = load_prompt(conv, 'judge_api')
#     print('-'*60)
#     print('judge_prompt', judge_prompt)
#     print('-'*60)

#     judge_output = openai_chatcompletion(judge_prompt) ##gpt判断调哪个api
#     print('-'*60)
#     print('judge_output', judge_output)
#     print('-'*60)
#     splitted_data = re.split(f"(Output|Translation|Searchable Sentence):", judge_output, flags=re.I)
#     judge_output = {'api_type': splitted_data[2].strip(), 'Translation': splitted_data[4].strip(), 'Searchable_Sentence': splitted_data[6].strip()}
#     print('judge_output', judge_output)
#     URI = {'wiki': 'http://10.10.100.201:7778/api/v1/chat' ,'news':'http://10.10.100.201:7779/api/v1/chat'}
#     if judge_output['api_type'] == '0': #TODO 接入兴康那边的api
#         news = search_news(judge_output['Searchable_Sentence'], URI['news'])
#         org_news = []
#         for i in range(5):
#             org_news.append({'Title':news[i], 'Content':news[5+i], 'Link':news[10+i]})

#         output = {'news':org_news}
#         print("接入news的api......")

#     elif judge_output['api_type'] == '1':
#         print("接入wiki的api......")
#         wiki_doc = search_wiki(judge_output['Searchable_Sentence'], URI['wiki'])
#         print('-'*60)
#         print('wiki_doc', wiki_doc)
#         print('-'*60)
#         output = {'wiki':openai_chatcompletion(load_prompt([wiki_doc, judge_output['Searchable_Sentence']], 'get_wiki_output'))}

#     elif judge_output['api_type'] == '2':
#         output = {'others': ''}
    

#     return output



class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        
        body = json.loads(self.rfile.read(content_length).decode('utf-8'))
        # print(body)
        # res = search(body['text'])
        if body['mode'] in ['news', 'wiki', 'auto']:
            # print('debug'+'-'*60)
            # print('mode',body['mode'])
            # print('-'*60)
            res = get_final_result(body['text'], body['mode'], body['cite'],body['top_num'])
        else: 
            res = {"answer":"Please choose a right mode!!!"}
        # print('debug'+'-'*60)
        # print(res)
        # print('-'*60)
        # response = json.dumps({
        #     'reponses': res
        # })
        response = json.dumps(res)

        self.wfile.write(response.encode('utf-8'))

def _run_server(port: int, share: bool = False):
    address = '0.0.0.0'
    server = ThreadingHTTPServer((address, port), Handler)
    print(f'Starting API at http://{address}:{port}/api')
    server.serve_forever()

def start_server(port: int, share: bool = False):
    Thread(target=_run_server, args=[port, share], daemon=True).start()



    



def main(port=7778, share=False):
    
    global model
    global tokenizer
    global search
    
    
    start_server(port, share)
    generation_lock = Lock()
    while True:
        time.sleep(0.5)

if __name__ == "__main__":
    main(9998)
    # fire.Fire(main_retrival(9999))
    # import gradio
    # interface = gradio.Interface(search, 
    #                                 gradio.inputs.Textbox(lines=1),
    #                             [gradio.outputs.Textbox() for _ in range(10)],
                                
    #                             )

    # interface.launch(inline=True, share=True)
