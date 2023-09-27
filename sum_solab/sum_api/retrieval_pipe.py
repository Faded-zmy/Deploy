import time
import os
import json
from func_timeout import func_set_timeout
import multiprocessing
import re

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
    return data_ls


def name_map(names):
    user_names=[chr(65+i) for i in range(26)]
    user_name_map={"Socrates":"Socrates"}
    number=0
    for name in names:
        if name not in user_name_map.keys() and name!="Socrates":
            user_name_map[name]="User_"+user_names[number]
            number+=1
    return user_name_map
 

def PreProcess(data, name2letter):
    data_ls = []

    for d in data: #把每句聊天中name和content连起来，如果Name为Socrates，先把这句话summary
        mes_group = []
        for conv in d['conversations']:
            one_mes = ''
            for key, value in conv.items():
                key = name2letter[key]
                #if key=='Socrates':
                #    value = openai_chatcompletion_stream(prompt(value, 'solab'), openai_key)
                one_mes += key+': '+repr(value)+"\n"
            mes_group.append(one_mes)
        data_ls.append(mes_group)
    
    return data_ls




def prompt(data, type):
    print('type', type)
    if type == 'solab': ##对苏格拉底的（一句话）summary
        prompt = f"""Please summarize this sentence in concise language.
        The sentence is:
        {data}"""
            
    elif type == 'conv2sum':
        data = '\n'.join(data)
        # data = '\n'.join(['\n'.join(d) for d in data])
        prompt = f"""You are asked to analyze a conversation between an AI assistant 'Socrates' and some members. 
requirement:
(1) Subjects : Please give subjects they discussed. If multiple topics were discussed, please summarize and present them together as "they discuss topic1,topic2...and topicN"
(2) Participants: Summarize the people involved in the conversation.
(3)Persons role and what they are talk about: Give a brief summary of the role each person played and what they were talking about in no more than 50 words. Show each person's summary only once, do not summarize separately.

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
            s = s+f"SPLIT {i+1}:\n[Start of SPLIT {i+1}]\n{data[i]}\n[End of SPLIT {i+1}]\n"
        prompt = f"""The follow is a segmented summary split of one session. Use one paragraph to summarize what happened in the that session. 
Noticed: 
（1）Each participant should be mentioned in the final summary.The names of them should be bolded in the output. 
（2）In the summary, you need to fuse the sliced summaries instead of continuing to summarize them separately.
The output format must follow this:
        In this session, the discussion mainly revolved around topicx, .... And then talk about topicy,...
        {s}"""

    return prompt
    
def worker(data, sum_type, openai_key, i, q):
    res = openai_chatcompletion_stream(prompt(data, sum_type), openai_key)
    q.put([i,res])

def postprocess(result,letter2name):
    for user_name in letter2name.keys():
        user_name1=letter2name[user_name]
        result=result.replace(" "+user_name+" "," <b>"+user_name1+"</b> ").replace(" "+user_name+","," <b>"+user_name1+"</b>,").replace(" "+user_name+"."," <b>"+user_name1+"</b>.")
    print('debug-result', result)
    pos=result.find(". ")
    result=result[:pos+1]+" \n"+result[pos+2:]
    return result

# @func_set_timeout(LONGEST_TIME) #设置超时
def get_final_result(message, max_token, openai_key, history_sum=''):
    #生成user_name_map,把name映射为User_A\User_B...
    names = []
    for d in message:
        for conv in d['conversations']:
            names.extend(conv.keys())
    if history_sum:
        print('debug', re.findall(r'<b>(.*?)</b>', history_sum))
        names.extend(re.findall(r'<b>(.*?)</b>', history_sum))
    name2letter=name_map(names)
    letter2name={v:k for k,v in name2letter.items()}

    max_token = max_token - 100
    data_ls=PreProcess(message, name2letter)
    data_ls = slice(data_ls, max_token, 'conv')
    print('batch size', len(data_ls))
    res = []

    #多进程对conv切片sum
    q = multiprocessing.Queue()
    processes = []
    for i,dl in enumerate(data_ls):
        p = multiprocessing.Process(target=worker, args=(dl, 'conv2sum', openai_key, i, q))
        processes.append(p)
        p.start()
    
    for p in processes:
        p.join()
    
    res_disordered = [q.get() for j in processes]
    res = ['']*len(res_disordered)
    for r in res_disordered:
        res[r[0]] = r[1]
    
    

    #如果conv2sum只有一个，做一次sum2sum
    if len(res)==1:
        res = [openai_chatcompletion_stream(prompt(res, 'sum2sum'), openai_key)]
    #如果conv2sum有多个，做多次sum2sum
    while len(res)!=1:
        sum_ls = slice(res, max_token, 'sum')
        res = []
        
        q = multiprocessing.Queue()
        processes = []
        for i,sl in enumerate(sum_ls):
            p = multiprocessing.Process(target=worker, args=(sl, 'sum2sum', openai_key, i, q))
            processes.append(p)
            p.start()
        
        for p in processes:
            p.join()
        
        res_disordered = [q.get() for j in processes]
        res = ['']*len(res_disordered)
        for r in res_disordered:
            res[r[0]] = r[1]
        
    if history_sum:
        for name in re.findall(r'<b>(.*?)</b>', history_sum):
            history_sum = history_sum.replace(name, name2letter[name])
        sum_ls = [res[0].replace("In this session",""), history_sum.replace("In this session","")]
        res = openai_chatcompletion_stream(prompt(sum_ls, 'sum2sum'), openai_key)
    res=postprocess(res,letter2name)
    return res
        





    
