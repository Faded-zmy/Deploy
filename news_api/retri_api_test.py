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


HOST_NEWS = '10.10.100.201:7779'
URI_NEWS = f'http://{HOST_NEWS}/api/v1/chat'
MAX_TETRY_TIMES = 5

user_intentions = ['news', 'wiki', 'chat']

def load_prompt(inputs, prompt_type):
    if prompt_type == 'get_wiki_output': #inputs = [query, wiki]
        
        prompt = """Instruction: Write an accurate, engaging, and concise answer for the given question using only the provided search results (some of which might be irrelevant) and cite them properly. Use an unbiased and journalistic tone. Always cite for any factual claim. When citing several search results, use [1][2][3]. Cite at least one document and at most three documents in each sentence. If multiple documents support the sentence, only cite a minimum sufficient subset of the documents.
        If the information in the documents is insufficient to answer the question, or the document is empty, please begin your answer with "I'm sorry, but I couldn't find any relevant information in my knowledge base," and provide your own speculation.
        Question: {q}
        Wiki: {w}
        Answer:""".format(q=inputs[0], w=inputs[1])

    elif prompt_type == 'judge_api': # inputs = conversation
        prompt = f"""Please analyze the intention according to the following conversation with last question and  give a judgement whether you should search the news or wiki or just reply normally without searching. 
        Requirement:
        1. Output 0 for news, 1 for wiki, 2 for normal reply. 
        2. Translate the last question into English if it's not. Then turn the question into a more searchable sentence.

        The format should be like:
        Output: xxx
        Translation: xx
        Searchable Sentence: xxx

        The conversation is as below:
        [Start of the conv]
        {inputs}
        [End of the conv]"""
    return prompt


def openai_chatcompletion(prompt, temperature=0):
    api_id = 0
    api_key = [
        "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",
        "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",
        "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",
        "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",
    ]
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
                model="gpt-3.5-turbo-16k",
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

def search_wiki(query, URI):
    print(f"Searching: {query}")
    request = {'text':query
    }
    response = requests.post(URI, json=request)
    if response.status_code == 200:
        result = response.json()['reponses']
        # print(result)
    res = ""
    for idx, doc in enumerate(result):
        res += f"Document[{idx+1}]:(Title:{doc[1]}): {doc[0]}" + '\n'
    return res

def search_news(query, URI):
    request = {'text':query
        
        }

    response = requests.post(URI, json=request)

    if response.status_code == 200:
        news_response = response.json()['reponses']
        print(news_response)
        return news_response

def PreProcess(data):
    
    conv = data['fullName']+': '+data['content'].replace('@Socrates', '')
    conv = '\n'.join(data['chatHistory'])+'\n'+conv
    return conv

def intent_recognition(input):
    """
    :param input: Chat history, 包括当前的query（拼在最后）
    :param llm:
    :param args:
    :return:
    """
    prompt = f"""
    You are an outstanding expert in intent recognition, capable of accurately and precisely identifying users' intentions from conversations: searching for news, searching for Wikipedia information, or just discuss/chat with you.
    The conversation is as below:
    [Start of the conv]
    {input}
    [End of the conv]
    Please analyze the last user's intention according to the conversation and give a judgement whether you should search the news or wiki or just reply normally without searching. 
    Requirement:
    1. Output 1 for news, 2 for wiki, 3 for chat. 
    2. If the noun referred to in the user's last sentence pertains to the content mentioned earlier, you need to supplement the user's question to make it easier to comprehend and search.
    3. All of your outputs must be in English.

    The output format should be like:
    Output: xxx
    Supplemented Question: xxx"""
    output = openai_chatcompletion(prompt)
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
    # print(f"User intention: {user_intentions[intent-1]}")
    return intent, s_question

def search_docs(query, search_type):
    request = {'text': query}
    res = ""
    urls = []
    if search_type == 1: # 如果是news
        print(f"Searching news: {query}")
        response = requests.post(URI_NEWS, json=request)
        if response.status_code == 200:
            result = response.json()['reponses']
            # print(result)
        # 解析news的返回
        print('debug'+'-'*60)
        print('news_result',result)
        print('-'*60)
        res_len = len(result)
        res = []
        news_nums = res_len//4
        for i in range(news_nums):
            res.append({'title': result[i], 'description': result[news_nums*4+i], 'previewUrl': result[news_nums*8+i], "imageUrl": result[news_nums*12+i], "domain": 'www.msn.com', "imageWidth": 200, "imageHeight": 200})
        # res = "\n".join([f"News[{i+1}]:(Title:{result[i]}):{result[i+news_nums]}" for i in range(news_nums)])
        # urls = result[news_nums*2: news_nums*3]

    elif search_type == 2: # 如果是wiki
        print(f"Searching wiki: {query}")
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


def get_output(docs, query, search_type):
    enc = tiktoken.get_encoding("cl100k_base")
    # print('len', len(docs.split(' ')[0]))
    # print('docs', docs)
    if len(enc.encode(docs)) > 4000:
        docs = 'News'.join([d[:500] for d in docs.split('News')])
    # print('docs', len(docs))
    if docs == "":
        docs = "None"
    if search_type == 1:
        res = "\n".join([f"News[{i+1}]:(Title:{docs[i]['title']}):{docs[i]['description']}" for i in range(len(docs))])
        prompt = """Instruction: Write an accurate, engaging, and concise answer for the given question using only the provided search results (some of which might be irrelevant) and cite them properly. Use an unbiased and journalistic tone. Always cite for any factual claim. When citing several search results, use [1][2][3]. Cite at most three news in each sentence. If multiple news support the sentence, only cite a minimum sufficient subset of the news.
        Question: 
        {q}
        News: 
        {w}
        Answer:""".format(q=query, w=res)
        # print(prompt)
    elif search_type == 2:
        res = "\n".join([f"Wiki[{i+1}]:(Title:{docs[i]['title']}):{docs[i]['description']}" for i in range(len(docs))])

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
    output = openai_chatcompletion(prompt)
    # print('output',output)
    print('-'*60)

    return output


def reformat_output(output, urls):
    """
    :param output: llm直接输出的文本
    :param urls: 所有urls
    :return: 格式化后的文本 +"\n\n" + 真正引用的urls
    """
    pattern = r'\[(\d+)\]'
    # print('debug'+'-'*60)
    # print('output',output)
    # print('-'*60)
    matches = re.findall(pattern, output)
    citation_list = set([int(match) for match in matches])
    final_urls = []
    # print(output)
    # print(output, urls)
    # print(citation_list)
    for idx, citation in enumerate(citation_list):
        output = output.replace(f'[{citation}]', f'[{idx + 1}]')
        if urls[citation-1] not in final_urls:
            final_urls.append(urls[citation-1])
    output += '\n\n' + '\n'.join(final_urls)
    return output, citation_list


def get_final_result(chat_history, cite=False):
    chat_history = PreProcess(chat_history)
    print('chat_history',chat_history)
    intent, query = intent_recognition(chat_history)
    print('debug'+'-'*60)
    print('intent',intent)
    print('query',query)
    print('-'*60)
    # docs = search_docs(query, intent)
    # output = get_output(docs, query, intent)
    if intent == 1 and cite:
        output = {
            "answer": "Recently, Donald Trump has been facing legal troubles and is set to surrender to authorities in Georgia on charges related to his alleged efforts to overturn the 2020 election [1]. Trump's surrender follows a presidential debate among his rivals for the 2024 Republican nomination, where he remains the leading candidate despite his legal issues [1]. This surrender is part of the fourth criminal case against Trump since March, making him the first former president in U.S. history to be indicted [1]. Trump has denied any wrongdoing and has characterized the charges as politically motivated [1]. Along with Trump, his lawyer Rudy Giuliani and other high-profile defendants have also turned themselves in on charges related to election subversion in Georgia [2][5].",
            "type": "news",
            "retri_infos":[
                {
                    "title": "title", 
                    "description": "description", 
                    "previewUrl": "previewUrl", 
                    "imageUrl": "None", 
                    "domain": "domain", 
                    "imageWidth": 200, 
                    "imageHeight": 200
                }, 
                {
                    "title": "title", 
                    "description": "description", 
                    "previewUrl": "previewUrl", 
                    "imageUrl": "imageUrl", 
                    "domain": "domain", 
                    "imageWidth": 200, 
                    "imageHeight": 200
                }, 
                {
                    "title": "title", 
                    "description": "description", 
                    "previewUrl": "previewUrl", 
                    "imageUrl": "imageUrl", 
                    "domain": "domain", 
                    "imageWidth": 200, 
                    "imageHeight": 200
                }, 
                {
                    "title": "title", 
                    "description": "description", 
                    "previewUrl": "previewUrl", 
                    "imageUrl": "imageUrl", 
                    "domain": "domain", 
                    "imageWidth": 200, 
                    "imageHeight": 200
                }
            ],
        }
    elif intent == 1 and not cite:
        output = {
            "answer": "Recently, Donald Trump has been facing legal troubles and is set to surrender to authorities in Georgia on charges related to his alleged efforts to overturn the 2020 election. Trump's surrender follows a presidential debate among his rivals for the 2024 Republican nomination, where he remains the leading candidate despite his legal issues. This surrender is part of the fourth criminal case against Trump since March, making him the first former president in U.S. history to be indicted. Trump has denied any wrongdoing and has characterized the charges as politically motivated. Along with Trump, his lawyer Rudy Giuliani and other high-profile defendants have also turned themselves in on charges related to election subversion in Georgia.",
            "type": "news"
        }
    else:
        output = {
            "answer": "",
            "type": None
        }

    # final_output, citations = reformat_output(output, urls)
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
        print(body)
        time.sleep(8)
        # res = search(body['text'])
        res = get_final_result(body['text'])
        print(res)
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
    main(9999)
    # fire.Fire(main_retrival(9999))
    # import gradio
    # interface = gradio.Interface(search, 
    #                                 gradio.inputs.Textbox(lines=1),
    #                             [gradio.outputs.Textbox() for _ in range(10)],
                                
    #                             )

    # interface.launch(inline=True, share=True)
