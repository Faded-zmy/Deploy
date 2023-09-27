import ast
import random
import re
import threading
import time
import traceback
import json
import os
import numpy as np
import torch
import transformers

import modules.shared as shared
# from modules.callbacks import (Iteratorize, Stream,
#                                _SentinelTokenStoppingCriteria)
# from modules.extensions import apply_extensions
# from modules.html_generator import generate_4chan_html, generate_basic_html
from modules.merge_info_inference import merge_info_to_origin, makedir
#from extensions.long_term_memory.script import custom_generate_chat_prompt
# from modules.logging_colors import logger
# from modules.models import clear_torch_cache, local_rank

def load_prompt(inputs, prompt_type):
    if prompt_type == 'summary':
        prompt = """The following is a conversation between User_A and User_B. Please help to extract information and summarize opinion on both sides from the following conversation.
        Requirement:
        1. Divide the information into two parts, a description of people and opinions on a topic.
        2. Summarize the conversation into one topic and the opinion of both sides. Give both sides's  way of talking and did he achieve a achievement such as convincing someone, getting a message when discuss the topic using a concise sentence or some words. Give the main topic discussed in the conversation.
        3. For the description of people, construct an information card of both sides.
        4. "Todo" is what people is going to do, "Todo_Time" is corresponding time.
        5. If a certain key's information is not mentioned, fill in it with "None".

        The structure of the information card is as follows:
        {"basic_information": {"Name": xxx, "Gender": xxx, "Date_of_Birth": xxx, "Place_of_Birth": xxx, "Race": xxx, "Nationality": xxx}, "background": {"Educational_Background": xxx, "Occupation": xxx, "Position": xxx, "Achievement": xxx}, "others": {"Personality": xxx, "Hobbies": xxx, "Good_at": xxx, "Not_good_at": xxx, "Topics_of_interest": xxx, "Topics_of_disinterest": xxx, "People_They_Admire": xxx, "People_They_Dislike": xxx, "Todo": xxx, "Todo_Time": xxx}}}

        The output format is as follows:
        User_A's information card: xxx

        User_B's information card: xxx

        Discussions:
        {"Topic": xxx,
        "Summary": xxx,
        "User_A's_opinion": xxx,
        "User_A's_way_of_talking": xxx,
        "User_A's_achievement":xxx,
        "User_B's_opinion": xxx,
        "User_B's_way_of_talking": xxx,
        "User_B's_achievement":xxx,
        "Main_Topic": xxx}

        The conversation is as follows:\n[Start of the conversation]
        """
        prompt = prompt+inputs+'\n[End of the conversation]\n'
    
    elif prompt_type == 'merge_sum':
        print('debug'+'='*60)
        print('inputs',inputs)
        print('debug'+'='*60)

        sum_str = ''
        for i,t in enumerate(inputs):
            sum_str += str(i+1)+'. '+t+'\n'
        prompt = f"""
        The following is some summary of several discussions, please use concise language to merge them into a summary.
        Original Summary:    
        {sum_str}
        The output format is as follows:
        Summary: xxx
        """
    elif prompt_type == 'merge_topic':
        topics = ''
        for i,t in enumerate(inputs):
            topics += str(i+1)+'. '+t+'\n'

        prompt = f"""
        The following are some topics that two people talked about in a day, please merge related topics into one topic and give the merged topic.

        Requirement:
            1. The merged topics are not related to each other

        The topics are:
        [Start of the topics]
        {topics}
        [End of the topics]

        The output format is as follows:
        Merged topic1: xxx
            Original topic: 
                2. xxx
                25. xxx
                ......
        Merged topic2: xxx
        ......
        """
    else:
        print("Please input the correct prompt type in ['summary', 'merge_sum', 'merge_tpoic'] !")
        return

    prompt = shared.vicuna_prompt+"\nHuman: "+prompt+"\nAssistant: \n"
    return prompt




def zmy_encode(prompt):
    inputs = shared.tokenizer([prompt])
    input_ids=torch.as_tensor(inputs.input_ids).cuda()
    skip_echo_len = len(prompt.replace('</s>',''))# - prompt.count("</s>") * 4
    return input_ids,skip_echo_len


def zmy_decode(output_ids, skip_special_tokens=True):
    return shared.tokenizer.decode(output_ids, skip_special_tokens)


def summary_encoder(conv):
    prompt = load_prompt(conv, 'summary')
    print('-'*60)
    print('PROMPT',prompt)
    print('-'*60)
    input_ids,skip_echo_len = zmy_encode(prompt)
    output_ids = shared.summary_model.generate(
            torch.as_tensor(input_ids).cuda(),
            do_sample=True,
            temperature=0.7,
            max_new_tokens=4096,
        )
    # outputs = shared.tokenizer.batch_decode(output_ids, skip_special_tokens=True)[0]
    print('ZMY-output_ids',len(output_ids[0]))
    reply = zmy_decode(output_ids[0], skip_special_tokens=True)[skip_echo_len:].strip()#zmy
    print('-'*60)
    print('ZMY-generate-reply',reply)
    print('-'*60)
    return reply

def merge_sum(sum_ls):
    prompt = load_prompt(sum_ls, 'merge_sum')
    print('-'*60)
    print('merge_sum PROMPT',prompt)
    print('-'*60)
    input_ids,skip_echo_len = zmy_encode(prompt)
    output_ids = shared.sum_merge_model.generate(
            torch.as_tensor(input_ids).cuda(),
            do_sample=True,
            temperature=0.7,
            max_new_tokens=4096,
        )
    # outputs = shared.tokenizer.batch_decode(output_ids, skip_special_tokens=True)[0]
    # print('ZMY-output_ids',output_ids)
    reply = zmy_decode(output_ids[0], skip_special_tokens=True)[skip_echo_len:].strip()#zmy
    print('-'*60)
    print('ZMY-generate-reply',reply)
    print('-'*60)
    return reply

def merge_topic(topic_ls):
    prompt = load_prompt(topic_ls, 'merge_topic')
    print('-'*60)
    print('PROMPT',prompt)
    print('-'*60)
    input_ids,skip_echo_len = zmy_encode(prompt)
    output_ids = shared.topic_merge_model.generate(
            torch.as_tensor(input_ids).cuda(),
            do_sample=True,
            temperature=0.7,
            max_new_tokens=4096,
        )
    # outputs = shared.tokenizer.batch_decode(output_ids, skip_special_tokens=True)[0]
    # print('ZMY-output_ids',output_ids)
    reply = zmy_decode(output_ids[0], skip_special_tokens=True)[skip_echo_len:].strip()#zmy
    print('-'*60)
    print('ZMY-generate-reply',reply)
    print('-'*60)
    return reply




def generate_chat_reply(prompt):
    # if 'long_term_memory' in shared.args.extensions:
    #     prompt = custom_generate_chat_prompt(name1, name2, prompt)
    prompt = "A chat between a curious user and an artificial intelligence assistant. The assistant gives helpful, detailed, and polite answers to the user's questions. USER: "+prompt+"\nASSISTANT: "
    # print('ZMY-generate-prompt2',prompt)
    input_ids,skip_echo_len = zmy_encode(prompt)
    # print('ZMY_DEBUG-model-key',shared.model.keys())
    # model = getattr(shared,name2.replace(' ','_'))
    # model = shared.model[name2]
    output_ids = shared.model.generate(
            torch.as_tensor(input_ids).cuda(),
            do_sample=True,
            temperature=0.7,
            max_new_tokens=2048,
        )
    # outputs = shared.tokenizer.batch_decode(output_ids, skip_special_tokens=True)[0]
    # print('ZMY-output_ids',output_ids)
    reply = zmy_decode(output_ids[0], skip_special_tokens=True)[skip_echo_len:].strip()#zmy
    # print('-'*60)
    # print('ZMY-generate-reply',reply)
    # print('-'*60)
    return reply

def TransName(user_name, character_name, info):
    return info.replace('User_A',user_name).replace('User_B',character_name)
    

def PostProcess(user_name, character_name, response):
    #转成dic
    my_data = {'A_info':[], 'B_info':[], 'Dis':[], 'org_conv':[]}
    if "User_A's information card:" in response and "User_B's information card:" in response and "Discussions:" in response:
        splitted_data = re.split(f"(User_A's information card|User_B's.*information card|Discussions):", response, flags=re.I)
        # print('splitted_data', splitted_data)
        A_info_card = TransName(user_name, character_name, splitted_data[2].strip().replace(': None',': "None"'))
        # print("A_info_card", A_info_card)
        B_info_card = TransName(user_name, character_name, splitted_data[4].strip().replace(': None',': "None"'))
        Discussions = splitted_data[6].strip().replace(': None',': "None"')
    else:
        response = response.replace("User_A's information card:",'').replace("User_B's information card:",'').replace("Discussions:",'')
        splitted_data = response.strip().split('\n')
        print('-'*60)
        print('splitted_data', splitted_data)
        print('-'*60)
        [A_org_data, B_org_data, Dis_org_data] = [sd for sd in splitted_data if sd != '']
        A_info_card = TransName(user_name, character_name, A_org_data.strip().replace(': None',': "None"'))
        B_info_card = TransName(user_name, character_name, B_org_data.strip().replace(': None',': "None"'))
        Discussions = Dis_org_data.strip().replace(': None',': "None"')
    A_json = eval(A_info_card)
    B_json = eval(B_info_card)
    discussion_json = eval(Discussions)
    
    #压缩key
    key_map = {
        "basic_information": "bi",
        "background": "bg",
        "others": "o",
        "name": "N",
        "gender": "Gd",
        "date_of_birth": "DB",
        "place_of_birth": "PB",
        "race": "R",
        "nationality": "Nat",
        "educational_background": "EB",
        "occupation": "Op",
        "position": "Pos",
        "achievement": "A",
        "personality": "Per",
        "hobbies": "H",
        "good_at": "G",
        "not_good_at": "Ng",
        "topics_of_interest": "Toi",
        "topics_of_disinterest": "Tod",
        "people_they_admire": "PTA",
        "people_they_dislike": "PTD",
        "todo": "Td",
        "todo_time": "TT",
        "topic": "Topic",
        "user_a's_opinion": "User_A's_opinion",
        "user_b's_opinion": "User_B's_opinion",
        "user_a's_way_of_talking": "User_A's_way_of_talking",
        "user_b's_way_of_talking": "User_B's_way_of_talking",
        "summary": "Summary",
        "user_a's_achievement": "user_A's_achievement",
        "user_b's_achievement": "user_B's_achievement"
    }
    A_final = {}
    B_final = {}
    Discussions_final = {}
    for key0 in A_json.keys():
        A_final[key_map[key0.lower().replace(' ','_')]] = {}
        B_final[key_map[key0.lower().replace(' ','_')]] = {}
    for key0 in A_json.keys():
        for key1 in A_json[key0].keys():
            A_final[key_map[key0.lower().replace(' ','_')]][key_map[key1.lower().replace(' ','_')]] = A_json[key0][key1]
            B_final[key_map[key0.lower().replace(' ','_')]][key_map[key1.lower().replace(' ','_')]] = B_json[key0][key1]
    for key in discussion_json.keys():
        Discussions_final[key_map[key.lower().replace(' ','_')]] = TransName(user_name, character_name, discussion_json[key])
    
    my_data['A_info'].append(A_final)
    my_data['B_info'].append(B_final)
    Discussions_final['time'] = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
    my_data['Dis'].append(Discussions_final)
    
    return my_data



def Discussion_add(discussion_root, character_name, user_name, Dis):
    # print('DIs',Dis)
    if not os.path.exists(discussion_root):
        os.makedirs(discussion_root)
    dis_path = discussion_root+'/'+character_name.replace(' ','')+'_'+user_name.replace(' ' ,'')+'.json'
    if os.path.exists(dis_path):
        org_dis = json.load(open(dis_path,'r'))
        org_dis.append(Dis)
    else:
        org_dis = [Dis]
    json.dump(org_dis,open(dis_path,'w'), indent=4)
    return org_dis

# def load_prompt(conv):
#     prompt = """
#     The following is a conversation between User_A and User_B. Please help to extract information and summarize opinion on both sides from the following conversation.
#     Requirement:
#     1. Divide the information into two parts, a description of people and opinions on a topic.
#     2. Summarize the conversation into one topic and the opinion of both sides. Give both sides's  way of talking and did he achieve a achievement such as convincing someone, getting a message when discuss the topic using a concise sentence or some words.
#     3. For the description of people, construct an information card of both sides.
#     4. "Todo" is what people is going to do, "Todo_Time" is corresponding time.
#     5. If a certain key's information is not mentioned, fill in it with "None".

#     The structure of the information card is as follows:
#     {"basic_information": {"Name": xxx, "Gender": xxx, "Date_of_Birth": xxx, "Place_of_Birth": xxx, "Race": xxx, "Nationality": xxx}, "background": {"Educational_Background": xxx, "Occupation": xxx, "Position": xxx, "Achievement": xxx}, "others": {"Personality": xxx, "Hobbies": xxx, "Good_at": xxx, "Not_good_at": xxx, "Topics_of_interest": xxx, "Topics_of_disinterest": xxx, "People_They_Admire": xxx, "People_They_Dislike": xxx, "Todo": xxx, "Todo_Time": xxx}}}

#     The output format is as follows:
#     User_A's information card: xxx

#     User_B's information card: xxx

#     Discussions:
#     {"Topic": xxx,
#     "Summary": xxx,
#     "User_A's_opinion": xxx,
#     "User_A's_way_of_talking": xxx,
#     "User_A's_achievement":xxx,
#     "User_B's_opinion": xxx,
#     "User_B's_way_of_talking": xxx,
#     "User_B's_achievement":xxx}

#     The conversation is as follows:\n
#     """
#     prompt = prompt+conv
#     return prompt

def dic2dic(dic, category):
    key_map = {
        "bi": "basic_information",
        "bg": "background",
        "o": "others",
        "N": "Name",
        "Gd": "Gender",
        "DB": "Date_of_Birth",
        "PB": "Place_of_Birth",
        "R": "Race",
        "Nat": "Nationality",
        "EB": "Educational_Background",
        "Op": "Occupation",
        "Pos": "Position",
        "A": "Achievement",
        "Per": "Personality",
        "H": "Hobbies",
        "G": "Good_At",
        "Ng": "Not_Good_At",
        "Toi": "Topics_of_Interest",
        "Tod": "Topics_of_Disinterest",
        "PTA": "People_They_Admire",
        "PTD": "People_They_Dislike",
        "Td": "Todo",
        "TT": "Todo_Time",
        "T": "Topic",
        "Ao": "User_A's_Opinion",
        "Bo": "User_B's_Opinion",
        "Aw": "User_A's_Way_of_Talking",
        "Bw": "User_B's_Way_of_Talking",
        "sum": "Summary",
        "Aa": "User_A's_Achievement",
        "Ba": "User_B's_Achievement",
        'time': 'time'
    }
    trans_dic = {}
    if category == "information_card":
        for k in dic.keys():
            sub_dic = {}
            for sk in dic[k].keys():
                sub_dic[key_map[sk]] = dic[k][sk]
            trans_dic[key_map[k]] = sub_dic
    
    elif category == "discussion":
        trans_dic = []
        # print('dic', dic)
        for d in dic:
            tdic = {}
            for k in d.keys():
                tdic[key_map[k]] = d[k]
            trans_dic.append(tdic)
    return trans_dic

def merge_IC(memory_root, discussion_root, character_name, user_name, conversation, show):
    prompt = load_prompt(conversation)
    # t1 = time.time()
    
    reply = generate_chat_reply(prompt)
    print("="*60)
    print('model reply:', reply)
    print("="*60)
    # t2 = time.time()
    # print('model reply need time:', t2-t1)
    # try:
    all_data = PostProcess(user_name, character_name, reply)
    # except Exception as e:
    #     print('error:', e)
        
    gpt_results_root = "/ai_efs/mengying/data/sum/information_card_data/"
    key_map = {
            "basic_information": "bi",
            "background": "bg",
            "others": "o",
            "name": "N",
            "gender": "Gd",
            "date_of_birth": "DB",
            "place_of_birth": "PB",
            "race": "R",
            "nationality": "Nat",
            "educational_background": "EB",
            "occupation": "Op",
            "position": "Pos",
            "achievement": "A",
            "personality": "Per",
            "hobbies": "H",
            "good_at": "G",
            "not_good_at": "Ng",
            "topics_of_interest": "Toi",
            "topics_of_disinterest": "Tod",
            "people_they_admire": "PTA",
            "people_they_dislike": "PTD",
            "todo": "Td",
            "todo_time": "TT",
            "topic": "T",
            "user_a's_opinion": "Ao",
            "user_b's_opinion": "Bo",
            "user_a's_way_of_talking": "Aw",
            "user_b's_way_of_talking": "Bbao bw",
            "summary": "sum",
            "user_a's_achievement": "Aa",
            "user_b's_achievement": "Ba",
            'time': 'time'
        }
    key_map={v:k for k,v in key_map.items()}
    makedir(memory_root,character_name,user_name)
    # t3 = time.time()
    A_info = merge_info_to_origin(all_data['A_info'][0],user_name,character_name,memory_root,gpt_results_root,key_map,show)
    B_info = merge_info_to_origin(all_data['B_info'][0],character_name,user_name,memory_root,gpt_results_root,key_map,show)
    # t4 = time.time()
    # print('merge info need time:', t4-t3)
    Dis = Discussion_add(discussion_root, character_name, user_name, all_data['Dis'][0])
    # Dis = dic2dic(Dis, "discussion")
    
    #TODO 薇姐接入merge代码
    res = {'A_info':A_info,'B_info':B_info,'Dis':Dis}
    # print("RESULT:", res)
    return str(res)
    # except Exception as e:
    #     print('PostProcess ERROR',e) #TODO 输给昌龙哥的dic
    



