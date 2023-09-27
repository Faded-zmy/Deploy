import time
import os
import json
from func_timeout import func_set_timeout

# from intent_recognition import intent_recognition
# from search_docs import search_docs
# from sum_output import get_output
# from reformat_output import reformat_output
import tiktoken
from openai_chatcompletion import openai_chatcompletion_stream

SUM_ROUND = 20
OVERLAP_ROUND = 2
LONGEST_TIME = 100

def slice(data, max_token, type): #TODO 这里的max_token要减掉prompt的token数
    if type=='conv':
        token_num = 0
        enc = tiktoken.get_encoding("cl100k_base")
        data_ls,tmp_ls = [],[]
        for d in data:
            tmp_token = 0
            for conv in d:
                if len(enc.encode(conv)) > max_token//2:
                    conv = enc.decode(enc.encode(conv)[:max_token//2])
                tmp_token += len(enc.encode(conv))
            
            if token_num+tmp_token < max_token:
                tmp_ls.extend(d)
                token_num += tmp_token
            else:
                data_ls.append(tmp_ls)
                tmp_ls = d
                token_num = tmp_token
                
        if tmp_ls:
            data_ls.append(tmp_ls)


    elif type=='sum':
        token_num = 0
        enc = tiktoken.get_encoding("cl100k_base")
        data_ls,tmp_ls = [],[]
        for d in data:
            token_num += len(enc.encode(d))
            if len(enc.encode(d)) > max_token:
                d = enc.decode(enc.encode(d)[:max_token])
            if token_num < max_token:
                tmp_ls.append(d)
            else:
                data_ls.append(tmp_ls)
                tmp_ls = [d]
                
        if tmp_ls:
            data_ls.append(tmp_ls)
    print('data_ls', data_ls, len(data_ls))
    return data_ls

def PreProcess(data):
    data_ls = []
    for d in data: #把每句聊天中name和content连起来，如果Name为Socrates，先把这句话summary
        mes_group = []
        for conv in d['conversations']:
            one_mes = ''
            for key, value in conv.items():
                #if key=='Socrates':
                #    value = openai_chatcompletion_stream(prompt(value, 'solab'), openai_key)
                one_mes += key+': '+repr(value)+"\n"
            mes_group.append(one_mes)
        data_ls.append(mes_group)
    print('data_ls', data_ls, len(data_ls))
    return data_ls




def prompt(data, type):
    print('type', type)
    if type == 'solab': ##对苏格拉底的（一句话）summary
        prompt = f"""Please summarize this sentence in concise language.
        The sentence is:
        {data}"""
            
    elif type == 'conv2sum':
        print('data', len(data[0]))
        data = '\n'.join(data)
        # data = '\n'.join(['\n'.join(d) for d in data])
        prompt = f"""You are asked to analyze a conversation between an AI assistant 'Socrates' and some members. 
requirement:
(1) Subjects : Please give subjects they discussed. If multiple topics were discussed, please summarize and present them together as "they discuss topic1,topic2...and topicN"
(2) Participants: Summarize the people involved in the conversation.
(3)Persons role and what they are talk about: Give a brief summary of the role each person played and what they were talking about  in no more than 50 words. A single person's talking is only displayed once. If he speaks in multiple rounds of conversations, please summarize his talking together.

The format must as below:
       1.  Subjects: they discuss topic1,topic2...and topicN
       2. Participants: xxx1,xxx2,xxx3
       4.Persons role and what they are talk about:
            xx1--role1: what1
            xx2--role2: what2
            Socrates--role3:what3
        ...
           xxN--roleN: whatN

        The origin conversation is:
        [Start of the conversation]
        {data}
        [End of the conversation]"""
    
    elif type == 'sum2sum':
        s = ''
        for i in range(len(data)):
            s = s+f"SUMMARIZATION {i+1}:\n[Start of SUMMARIZATION {i+1}]\n{data[i]}\n[End of SUMMARIZATION {i+1}]\n"
        prompt = f"""The follow is a segmented summary of a conversation. Use one paragraph to summarize what happened in the above conversation.Summarize in one paragraph what happened in the above conversation.\nrequirement: The names of participants in the conversation are bolded in the summary.

        {s}"""

    print('prompt', prompt)
    return prompt
    



@func_set_timeout(LONGEST_TIME)
def get_final_result(message, max_token, openai_key, merge=False, history_sum=''):
    data_ls = slice(PreProcess(message), max_token, 'conv')
    print('batch size', len(data_ls))
    res = []
    for dl in data_ls:
        res.append(openai_chatcompletion_stream(prompt(dl, 'conv2sum'), openai_key))
        print('res', res)
    while len(res)!=1:
        print('res', res)
        sum_ls = slice(res, max_token, 'sum')
        res = []
        for sl in sum_ls:
            res.append(openai_chatcompletion_stream(prompt(sl, 'sum2sum'), openai_key))
    if merge:
        sum_ls = [res[0], history_sum]
        res = openai_chatcompletion_stream(prompt(sum_ls, 'sum2sum'), openai_key)
    return res
        





    
