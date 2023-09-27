import json
import re
import torch
from pathlib import Path
import numpy as np
import modules.shared as shared
import shutil
import os
import requests
# from modules.utils import get_available_chat_styles
import markdown
# from modules.search_momo import search
import random
import gradio as gr

# Custom chat styles
# chat_styles = {}
# for k in get_available_chat_styles():
#     chat_styles[k] = open(Path(f'css/chat_style-{k}.css'), 'r').read()


def replace_blockquote(m):
    return m.group().replace('\n', '\n> ').replace('\\begin{blockquote}', '').replace('\\end{blockquote}', '')


def convert_to_markdown(string):

    # Blockquote
    pattern = re.compile(r'\\begin{blockquote}(.*?)\\end{blockquote}', re.DOTALL)
    string = pattern.sub(replace_blockquote, string)

    # Code
    string = string.replace('\\begin{code}', '```')
    string = string.replace('\\end{code}', '```')
    string = re.sub(r"(.)```", r"\1\n```", string)

    result = ''
    is_code = False
    for line in string.split('\n'):
        if line.lstrip(' ').startswith('```'):
            is_code = not is_code

        result += line
        if is_code or line.startswith('|'):  # Don't add an extra \n for tables or code
            result += '\n'
        else:
            result += '\n\n'

    if is_code:
        result = result + '```'  # Unfinished code block

    string = result.strip()
    
    return markdown.markdown(string, extensions=['fenced_code', 'tables'])

def generate_cai_chat_html():
    reset_cache=False
    style = 'cai-chat'
    output = f'<style>{chat_styles[style]}</style><div class="chat" id="chat">'

    visible = shared.history['visible']
    name1 = shared.settings['name1']
    name2 = shared.character
    
    current_visible = visible[-1]
    img_me = f'<img src="file/cache/CC.jpeg">'
    img_bot = f'<img src="file/cache/{shared.character.replace(" ", "_")}.png">'
    
    output_name2, model_output = random_text_expression_singlechat(name2, current_visible[1], 0.)
        
    current_output_2 = f"""
              <div class="message">
                <div class="circle-bot">
                  {img_bot}
                </div>
                <div class="text">
                  <div class="username">
                    {name2}
                  </div>
                  <div class="message-body">
                    {output_name2}
                    {convert_to_markdown(model_output)}
                  </div>
                </div>
              </div>
            """
    
    if len(current_visible[0]) != 0:  # don't display empty user messages
        current_output_1 = f"""
                  <div class="message">
                    <div class="circle-you">
                      {img_me}
                    </div>
                    <div class="text">
                      <div class="username">
                        {name1}
                      </div>
                      <div class="message-body">
                        {convert_to_markdown(current_visible[0])}
                      </div>
                    </div>
                  </div>
                """
    else:
        current_output_1 = None
    
    if current_output_1 is not None:
        shared.history_output.append(current_output_1)
    shared.history_output.append(current_output_2)    
    
    shared.history_output.reverse()
    
    for i, _row in enumerate(shared.history_output):
        output += _row
    output += "</div>"
    shared.history_output.reverse()
    
    return output

# def load_prompt(conv):
#     prompt = """The following is a conversation between User_A and User_B. Please help to extract information and summarize opinion on both sides from the following conversation.
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

#     The conversation is as follows:\n[Start of the conversation]
#     """
#     prompt = prompt+conv+"\n[End of the conversation]\n"
#     return prompt

def PreProcess(user_id, another_id, conv): # 先假设每句话的分割符是'\n'
    conv = conv.replace(user_id, 'User_A').replace(another_id, 'User_B')
    conv_ls = conv.strip().split('\n')
    conv_ls = [cv.strip() for cv in conv_ls if cv.strip()!='']
    start,end = 0,0
    res = []
    while end<len(conv_ls):
        start = max(0,end-4)# overlap四句话
        num = random.randint(12,20)
        end = start+num
        res.append({'user_id': user_id, 'another_id': another_id, 'conv': '\n'.join(conv_ls[start:min(end,len(conv_ls))]), 'round': [start,end]})# round:左闭右开.因为是一天一天来的 所以没有记录日期
    
    json.dump(res, open(f'/ai_jfs/mengying/Deployment/sum_demo/mem_data/{user_id}_{another_id}.json','w'))
    return res

def PostProcess(response, process_type):
    #转成dic
    if process_type == 'summary':
        Discussions = response.split('Discussions:\n')[-1].strip().replace(': None',': "None"')
        result = eval(Discussions)
        # Discussions_final['time'] = time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))#TODO 看他们那边的时间怎么给到我们，我们再加上去。 
    elif process_type == 'topic_merge':
        response.replace('Original topics','Original topic')
        splitted_data = re.split(f"(Merged topic.*|Original topic):", response, flags=re.I)
        result = []
        for i in range((len(splitted_data)-1)//4):
            merge_idx = int(splitted_data[4*i+1].replace('Merged topic',''))
            merged_topic = splitted_data[4*i+2].strip()
            org_topics = splitted_data[4*i+4].strip().split('\n')
            org_topics = [{'idx': int(ot.split('.')[0]),'topic':ot} for ot in org_topics]
            result.append({'merge_idx': merge_idx, 'merged_topic':merged_topic, 'org_topics': org_topics})
        

            
    
    return result


def summary_encoder(user_id, another_id, conv):
    summary_URI = 'http://35.167.45.204:7860/api/v1/summary'
    sum_merge_URI = 'http://35.167.45.204:7860/api/v1/sum_merge'
    topic_merge_URI = 'http://35.167.45.204:7860/api/v1/topic_merge'

    # conv = conv.replace(user_id, 'User_A').replace(another_id, 'User_B')

    # 把对话切片分别进行初步encoder
    conv_dic = PreProcess(user_id, another_id, conv)
    # round_sum = []
    for i,cd in enumerate(conv_dic):
        request = {
            "conv": cd['conv'],
        }
        response = requests.post(summary_URI, json=request)

        if response.status_code == 200:
            result = response.json()['results'][0]
            result = PostProcess(user_id, another_id, result)
            conv_dic[i]['round_sum'] = PostProcess(result)
    
    # 把所有的topic分类
    topics = [cv['round_sum']['Main_Topic'] for cv in conv_dic]
    request = {
            "topic_ls": topics,
        }
    response = requests.post(topic_merge_URI, json=request)

    if response.status_code == 200:
        result = response.json()['results'][0]
        merge_topic_result = PostProcess(result,'topic_merge')
    flag = [-1]*len(conv_dic)
    # for i,mt in enumerate(merge_topic_result):

    # 对相邻且同类的summary进行merge
    for mt in merge_topic_result:
        for t in mt['org_topics']:
            flag[t['idx']-1] = mt['merge_idx']
    start,end = 0,0
    merged_result = [] # 只留五个key: 'Merged_topic','Merged_summary','round','user_id','another_id'
    while end<len(flag)-1:
        start = end
        for i in range(start,len(flag)):
            if flag[i] != flag[start]:
                end = i
                break
        sum_ls = [cv['round_sum']['Summary'] for cv in conv_dic[start:end]]
        if len(sum_ls)>1:
            request = {
                    "sum_ls": sum_ls,
                }
            response = requests.post(sum_merge_URI, json=request)
            Merged_summary = response.json()['results'][0]['text']
        else:
            Merged_summary = sum_ls[0]
        merged_result.append({'Merged_topic': merge_topic_result[flag[start]-1]['merged_topic'], 'Merged_summary': Merged_summary, 'round': [conv_dic[start]['round'][0],conv_dic[end]['round'][1]], 'user_id': user_id, 'another_id': another_id})

    # 创建User的文件夹（名字为User的id），把summary(merged)结果存成一个json(名字为another_id)
    user_id = user_id.replace(' ', '_')
    another_id = another_id.replace(' ', '_')
    if not os.path.exists(f'/ai_jfs/mengying/Deployment/sum_demo/mem_data/{user_id}'):
        os.mkdir(f'/ai_jfs/mengying/Deployment/sum_demo/mem_data/{user_id}')
    json.dump(merged_result, open(f'/ai_jfs/mengying/Deployment/sum_demo/mem_data/{user_id}/{another_id}.json','w'), indent=4)
    return merged_result
    
def summary_of_the_day(user_id):
    # 读取user_id文件夹下的所有文件
    user_id = user_id.replace(' ', '_')
    files = os.listdir(f'/ai_jfs/mengying/Deployment/sum_demo/mem_data/{user_id}')
    summary = []
    for file in files:
        summary.extend(json.load(open(f'/ai_jfs/mengying/Deployment/sum_demo/mem_data/{user_id}/{file}', 'r')))
  
    # 把所有的topic分类
    topics = [cv['Merged_topic'] for cv in summary]
    request = {
            "topic_ls": topics,
        }
    response = requests.post(topic_merge_URI, json=request)

    if response.status_code == 200:
        result = response.json()['results'][0]
        merge_topic_result = PostProcess(result,'topic_merge')
  
    # 对同类的summary进行merge

    merged_result = [] # 只留五个key: 'Merged_topic','Merged_summary','round','user_id','another_id'
    for mr in merged_result:
        sum_ls, rounds, another_id = [], [], []
        for t in mr['org_topics']:
            sum_ls.append(summary[t['idx']]['Merged_summary'])
            rounds.append(summary[t['idx']]['round'])
            another_ids.append(summary[t['idx']]['another_id'])

        if len(sum_ls)>1:
            request = {
                    "sum_ls": sum_ls,
                }
            response = requests.post(sum_merge_URI, json=request)
            Merged_summary = response.json()['results'][0]['text']
        else:
            Merged_summary = sum_ls[0]
        merged_result.append({'Merged_topic': merge_topic_result[flag[start]-1]['merged_topic'], 'Merged_summary': Merged_summary, 'round': rounds, 'user_id': user_id, 'another_id': another_ids})
    return result
    




def get_api_chat_result(cha_name, user_name, conv):
    # if shared.character != cha_name:
    #     shared.history = {'internal': [], 'visible': []}
    #     shared.history_output = []
    
    # shared.character = cha_name
    # history = shared.history['visible']
    URI = "http://35.92.206.66:4010/api/v1/chat"
    
    # messages = []
    # for conv in history[-8:]:
    #     messages.append({'role':'user','content':conv[0]})
    #     messages.append({'role': f'{cha_name.lower()}','content':conv[1]})
    # messages.append({'role':'user','content':message})
    conv = conv.replace(user_id, 'User_A').replace(another_id, 'User_B')
    messages = [{'role':'user','content':load_prompt(conv)}]
    request = {
        "messages":  messages, #Who do you consider your friends?
        "mode": "chat",
        "character": f"{cha_name}",
        "context": "A chat between a curious human and an artificial intelligence assistant. The assistant gives helpful, detailed, and polite answers to the human's questions.", 
        "your_name": "User", 
        "regenerate": False, 
        "_continue": False, 
        "stop_at_newline": False, 
        "chat_prompt_size": 4096, 
        "chat_generation_attempts": 1, 
        "max_new_tokens": 250, 
        "do_sample": True, 
        "temperature": 0.7, 
        "top_p": 0.1, 
        "typical_p": 1, 
        "epsilon_cutoff": 0, 
        "eta_cutoff": 0, 
        "repetition_penalty": 1.18, 
        "top_k": 40, 
        "min_length": 0, 
        "no_repeat_ngram_size": 0, 
        "num_beams": 1, 
        "penalty_alpha": 0, 
        "length_penalty": 1, 
        "early_stopping": False, 
        "mirostat_mode": 0, 
        "mirostat_tau": 5, 
        "mirostat_eta": 0.1, 
        "seed": -1, 
        "add_bos_token": True, 
        "truncation_length": 4096, 
        "ban_eos_token": False, 
        "skip_special_tokens": True, 
        "stopping_strings": []
        }
    
    prompt = request['context']
    for mes in request['messages']:
        if mes['role'].lower() == 'user':
            # prompt = prompt+'\nYou: '+mes['content']
            prompt = prompt + '\nUSER_ID10: ' + mes['content']

        elif mes['role'].lower() != 'user':
            chara_name = mes['role'].upper()
            prompt = prompt + f'\n{cha_name}:' + mes['content'] + '</s>'
        
    prompt = prompt + '\n' + request['character'].upper() + ':'
    request['context'] = prompt

    response = requests.post(URI, json=request)

    if response.status_code == 200:
        result = response.json()['results'][0]['history']
        shared.reply = result
    
    shared.history['visible'].append([message, shared.reply])
    
    return 


def get_insideout_encoder():
    
    style = 'cai-chat'
    output = f'<style>{chat_styles[style]}</style><div class="chat" id="chat">'
    info_a = []
    info_b = []
    summary_info = []
    
    period = 7
    first_round = 10
    request = {
        "conversation":  '',
        "memory_root": "/home/ec2-user/mengying/Deployment/simple_textgen_LTM/mem_data/memories/",
        'discussion_root':'/home/ec2-user/mengying/Deployment/simple_textgen_LTM/mem_data/discussion_save2/',
        'character_name': shared.character,
        'user_name': shared.settings['name1'],
        'show': True,
        }
    
    HOST = '35.92.206.66:6000'
    URI = f'http://{HOST}/api/v1/generate'
    # memory inside out
    visible = shared.history['visible']
    chat_rounds = len(visible)
    if chat_rounds == first_round:
        for i, _row in enumerate(visible):
            answer_b = (_row[1].split("\n")[-1]).split(": ")[-1]
            dialog = f"User_A: {_row[0]}\nUser_B: {answer_b}\n"
            request['conversation'] += dialog
    elif chat_rounds > first_round and (chat_rounds - first_round) % period == 0:
        visible_conv = visible[-first_round:]
        for i, _row in enumerate(visible_conv):
            answer_b = (_row[1].split("\n")[-1]).split(": ")[-1]
            dialog = f"User_A: {_row[0]}\nUser_B: {answer_b}\n"
            request['conversation'] += dialog
    else:
        request['conversation'] = None
        
    if request['conversation'] is not None:
        response = requests.post(URI, json=request)
        if response.status_code == 200:
            result = response.json()['results'][0]['text']
            result = eval(result)
            user_a = result['A_info']
            user_b = result['B_info']
            summary = result['Dis'][-1]

            
            for key in user_a['store'].keys():
                info_a.append(key)
                for sub_key in user_a['store'][key].keys():
                    shared.user_a[key][sub_key] = user_a['store'][key][sub_key][0]
                    info_a.append(f"{sub_key}: {str(shared.user_a[key][sub_key])}")
            for key in user_b['store'].keys():
                info_b.append(key)
                for sub_key in user_b['store'][key].keys():
                    shared.user_b[key][sub_key] = user_b['store'][key][sub_key][0]
                    info_b.append(f"{sub_key}: {str(shared.user_b[key][sub_key])}")
            shared.info_a_output = "\n".join(info_a)
            shared.info_b_output = "\n".join(info_b)
            for key in summary.keys():
                if key in shared.summary.keys():
                    shared.summary[key] = summary[key]
                    summary_info.append(f"{key}: {str(shared.summary[key])}")
            shared.summary_output = "\n".join(summary_info)
                
                
    img_b = f'<img src="file/cache/{shared.character}.png">'
    img_a = f'<img src="file/cache/CC.jpeg">'
    output_a = output + f"""
              <div class="message">
                <div class="circle-bot">
                  {img_a}
                </div>
                <div class="text">
                  <div class="username">
                    {shared.settings['name1']}
                  </div>
                  <div class="message-body">
                    {convert_to_markdown(shared.info_a_output)}
                  </div>

            """

    output_b = output + f"""
              <div class="message">
                <div class="circle-bot">
                  {img_b}
                </div>
                <div class="text">
                  <div class="username">
                    {shared.character}
                  </div>
                  <div class="message-body">
                    {convert_to_markdown(shared.info_b_output)}
                  </div>
            """
            
    output_summary = output + f"""
              <div class="message">
                </div>
                <div class="text">
                    <div class="username">
                    {"Summary"}
                  </div>
                  <div class="message-body">
                    {convert_to_markdown(shared.summary_output)}
                  </div>
            """

    return output_a, output_b, output_summary


def get_URI(cha_name):
    cha_ls = json.load(open('./extensions/api/URI_mapping.json','r'))
    URI = cha_ls[cha_name]
    return URI

# room chat
def show_topic(topic):
    reset_cache=False
    style = 'cai-chat'
    output = f'<style>{chat_styles[style]}</style><div class="chat" id="chat">'
    output += f"""
        <div class="message">
        <div class="text">
            <div class="topic">
            {topic}
            </div>
        </div>
        </div>
    """
    return output

def get_api_roomchat_result(speakers, topic, round_times, progress=gr.Progress()):
    speakers_info = {}

    # speakers.append("CC")
    for i in range(len(speakers)):
        speakers_info[f"ID{i}"] = speakers[i]

    if round_times == None:
        round_times = shared.round_times
    else:
        round_times = int(round_times)

    URI = "http://35.92.206.66:3010/api/v1/chat"

    shared.generate_round += 1
    shared.load_times = np.zeros(len(speakers), dtype=np.int32)

    reset_cache = False
    style = 'cai-chat'
    img_me = f'<img src="file/cache/CC.jpeg">'

    name1_ip = "CC"
    message = f"Let's talk about a topic(news) as below: {topic}\n"

    current_output_1 = f"""
                <div class="message">
                <div class="circle-you">
                    {img_me}
                </div>
                <div class="text">
                    <div class="username">
                    {name1_ip}
                    </div>
                    <div class="message-body">
                    {convert_to_markdown(message)}
                    </div>
                </div>
                </div>
            """

    shared.history_output.append(current_output_1)

    current_round = 0
    
    while current_round < round_times:
        last = False
        if current_round == 0:
            ip = speakers[0]

            prompt_start = get_conv_prompt(ip)
            prompt_topic = get_start_prompt(topic)
            prompt_introduction = get_introduction_prompt(speakers_info)
            shared.prompt_inputs[ip] = f"{prompt_start}{prompt_topic}{prompt_introduction}{ip.upper()}:"

            shared.next_ip, out = get_model_output_topic(ip, URI, speakers_info, speakers, last)
            current_round += 1
        else:
            # if current_round == round_times - 1:
            #     last = True
            ip = shared.next_ip

            conversation_before = []

            prompt_start = get_conv_prompt(ip)
            prompt_topic = get_start_prompt(topic)
            prompt_introduction = get_introduction_prompt(speakers_info)

            for conv in shared.history['visible'][-round_times:]:
                ip_before = conv[0]
                model_output = conv[1]
                for n in speakers:
                    if n in model_output and n != ip_before:
                        model_output = model_output.replace(n, f"ID{speakers.index(n)}")
                
                if ip_before == ip:
                    conversation_before.append(f"{ip.upper()}: {model_output}")
                else:
                    ip_idx = speakers.index(ip_before)
                    conversation_before.append(f"USER_ID{ip_idx}: {model_output}")
            
            conv_before = "\n".join(conversation_before)

            shared.prompt_inputs[ip] = f"{prompt_start}{prompt_topic}{prompt_introduction}{conv_before}{ip.upper()}:"

            shared.next_ip, out = get_model_output_topic(ip, URI, speakers_info, speakers, last)
            current_round += 1
        
        output = f'<style>{chat_styles[style]}</style><div class="chat" id="chat">'
        img_ipx = ip.replace(' ', '_')
        img_bot = f'<img src="file/cache/{img_ipx}.png">'

        output_name2 = random_text_expression(ip, out, 0.)
        current_output = f"""
                        <div class="message">
                        <div class="circle-bot">
                            {img_bot}
                        </div>
                        <div class="text">
                            <div class="username">
                                {ip}
                            </div>
                            <div class="message-body">
                                {output_name2}
                                {convert_to_markdown(out)}
                            </div>
                        </div>
                        </div>
                    """
        
        shared.history_output.append(current_output)
        shared.history_output.reverse()
        for i, _row in enumerate(shared.history_output):
            output += _row
        output += "</div>"
        shared.history_output.reverse()
        
        yield output 

def get_api_roomchat_continue(speakers, topic, message, round_times, progress=gr.Progress()):
    speakers_info = {}

    speakers.append("CC")
    for i in range(len(speakers)):
        speakers_info[f"ID{i}"] = speakers[i]

    if round_times == None or round_times == "":
        round_times = shared.round_times
    else:
        round_times = int(round_times)

    URI = "http://35.92.206.66:3010/api/v1/chat"

    shared.generate_round += 1
    shared.load_times = np.zeros(len(speakers), dtype=np.int32)

    reset_cache = False
    style = 'cai-chat'
    img_me = f'<img src="file/cache/CC.jpeg">'

    name1_ip = "CC"
    if len(message) != 0:
        current_output_1 = f"""
                    <div class="message">
                    <div class="circle-you">
                        {img_me}
                    </div>
                    <div class="text">
                        <div class="username">
                        {name1_ip}
                        </div>
                        <div class="message-body">
                        {convert_to_markdown(message)}
                        </div>
                    </div>
                    </div>
                """
        message = f"Actions/Expressions: Raising hand, with a thoughtful expression\nAnswer: {message}\n"

        shared.history_output.append(current_output_1)
        shared.history['visible'].append((name1_ip, message))
        if '@' in message:
            next_ipx = message.split('@')[-1].split(',')[0]
            # check name right in speakers
            for s in next_ipx:
                if not s.isalpha():
                    next_ipx = next_ipx.split(s)[0]
                    break
        
            for n in speakers:
                if next_ipx in n:
                    next_ipx = n
            shared.next_ip = next_ipx
            
        
    current_round = 0
    
    while current_round < round_times:
        last = False
        if current_round == round_times - 1:
            last = True
        ip = shared.next_ip

        conversation_before = []

        prompt_start = get_conv_prompt(ip)
        prompt_topic = get_start_prompt(topic)
        prompt_introduction = get_introduction_prompt(speakers_info)

        for conv in shared.history['visible'][-int(round_times + 6):]:
            ip_before = conv[0]
            model_output = conv[1]
            for n in speakers:
                if n in model_output and n != ip_before:
                    model_output = model_output.replace(n, f"ID{speakers.index(n)}")
            
            if ip_before == ip:
                conversation_before.append(f"{ip.upper()}: {model_output}")
            else:
                ip_idx = speakers.index(ip_before)
                conversation_before.append(f"USER_ID{ip_idx}: {model_output}")
        
        conv_before = "\n".join(conversation_before)

        shared.prompt_inputs[ip] = f"{prompt_start}{prompt_topic}{prompt_introduction}{conv_before}{ip.upper()}:"

        shared.next_ip, out = get_model_output_topic(ip, URI, speakers_info, speakers, last)
        current_round += 1
        
        output = f'<style>{chat_styles[style]}</style><div class="chat" id="chat">'
        img_ipx = ip.replace(' ', '_')
        img_bot = f'<img src="file/cache/{img_ipx}.png">'
        output_name2 = random_text_expression(ip, out, 0.)
        current_output = f"""
                        <div class="message">
                        <div class="circle-bot">
                            {img_bot}
                        </div>
                        <div class="text">
                            <div class="username">
                                {ip}
                            </div>
                            <div class="message-body">
                                {output_name2}
                                {convert_to_markdown(out)}
                            </div>
                        </div>
                        </div>
                    """
        
        shared.history_output.append(current_output)
        shared.history_output.reverse()
        for i, _row in enumerate(shared.history_output):
            output += _row
        output += "</div>"
        shared.history_output.reverse()
        
        yield output 


def get_model_output_topic(ip, URI, speakers_info, speakers, last=False):
    request = request_template(shared.prompt_inputs[ip])
    response = requests.post(URI, json=request)
    if response.status_code == 200:
        shared.prompt_outputs[ip] = response.json()['results'][0]['history']

    shared.record_ip.append(ip)
    shared.history['visible'].append((ip, shared.prompt_outputs[ip]))
    answer_split = shared.prompt_outputs[ip].split('\n')
    actions = answer_split[0].split(': ')[-1]
    answer = answer_split[-1].split(': ')[-1]

    # post processing
    # @ID, @Sherlock, @CC, CC, Sherlock, ID, And @ID, @ID?, (@Sherlock, Sherlock,)
    if "CC" in speakers:
        next_ipx = speakers[0] if speakers.index(ip) == len(speakers) - 2 else speakers[speakers.index(ip) + 1]
    else:
        next_ipx = speakers[0] if speakers.index(ip) == len(speakers) - 1 else speakers[speakers.index(ip) + 1]
    if "ID" in answer:
        for key in speakers_info.keys():
            if key in answer:
                answer = answer.replace(key, speakers_info[key])
                          
    if '@' in answer:                        
        next_ipx = answer.split('@')[-1].split(',')[0]
        # check name right in speakers
        for s in next_ipx:
            if not s.isalpha():
                next_ipx = next_ipx.split(s)[0]
                break
        
        for n in speakers:
            if next_ipx in n:
                next_ipx = n
        
        # check repeat
        repeat_answer = answer.split('@')[-1].split(',')

        if len(repeat_answer) > 1 and repeat_answer[1].strip() in repeat_answer[0]:
            answer = answer.replace('@'+repeat_answer[0]+', ', '')
            answer = answer.replace(repeat_answer[1].strip(), next_ipx)
        else:
            answer = answer.replace('@' + repeat_answer[0], next_ipx)

    else:
        if "?" in answer:
            next_ip = answer.split(".")[-1].split(" ")
            for n in speakers:
                for nip in next_ip:
                    if nip in n:
                        next_ipx = n
        else:
            if speakers.index(ip) == len(speakers) - 1:
                next_ipx = speakers[0]
            else:
                next_ipx = speakers[speakers.index(ip) + 1]
    
    if next_ipx == "CC":
        if "CC" in answer:
            answer = answer.replace(answer.split('.')[-1], '')
        next_ipx = speakers[0]
    
    if next_ipx == ip:
        next_ipx = speakers[0] if speakers.index(ip) == len(speakers) - 2 else speakers[speakers.index(ip) + 1]
    
    # if last:
    #     answer = answer.replace('@' + answer.split('@')[-1], '')
        
    shared.prompt_outputs[ip] = f"Actions/Expressions: {actions}\nAnswer: {answer}"
    print(f"Next character {next_ipx} replied: {shared.prompt_outputs[ip]}")
    return next_ipx, shared.prompt_outputs[ip]
        

def request_template(context=None):
    request = {
        "mode": "chat",
        "context": context, 
        "regenerate": False, 
        "_continue": False, 
        "stop_at_newline": False, 
        "chat_prompt_size": 2048, 
        "chat_generation_attempts": 1, 
        "max_new_tokens": 250, 
        "do_sample": True, 
        "temperature": 0.7, 
        "top_p": 0.1, 
        "typical_p": 1, 
        "epsilon_cutoff": 0, 
        "eta_cutoff": 0, 
        "repetition_penalty": 1.18, 
        "top_k": 40, 
        "min_length": 0, 
        "no_repeat_ngram_size": 0, 
        "num_beams": 1, 
        "penalty_alpha": 0, 
        "length_penalty": 1, 
        "early_stopping": False, 
        "mirostat_mode": 0, 
        "mirostat_tau": 5, 
        "mirostat_eta": 0.1, 
        "seed": -1, 
        "add_bos_token": True, 
        "truncation_length": 2048, 
        "ban_eos_token": False, 
        "skip_special_tokens": True, 
        "stopping_strings": []
        }
    return request

def get_start_prompt(topic):
    prompt2 = f"USER_TOPIC: Let's talk about a topic(news) as below: {topic}\n"
    return prompt2

def get_introduction_prompt(speakers):
    prompt = "Please introduce yourself at first.\n"
    for key in speakers.keys():
        prompt += f"USER_{key}: I'm {speakers[key]}\n"
    return prompt


def get_conv_prompt(name):
    prompt_conv = f"The following is a conversation between character: {name} and other peoples. The character gives a response or comment that matches their personality based on the content of the previous text.\n"
    return prompt_conv

# def random_text_expression_singlechat(ip, answer, threshold = 0.1):
#     answer_split = answer.split('\n')
#     if len(answer_split) > 1:
#         inner_thought = answer_split[0].split(': ')[-1]
#         actions = answer_split[1].split(': ')[-1]
#         answer = answer_split[-1].split(': ')[-1]
#     else:
#         answer = answer_split[0]
#         inner_thought = ""
#         actions = ""
#     model_output = f"Inner thoughts: {inner_thought}\nActions/Expressions: {actions}\nAnswer: {answer}"
#     # possibility threshold of random expression: img or text
#     # random to show expression or text 
#     random_number = random.random()
#     if random_number > threshold:
#             # choose first image
#         img_chat_search = search(ip, actions)[0]
    
#         destination_img_path = os.path.join("cache/cache", img_chat_search.split('/')[-1])
#         shutil.copy(img_chat_search, destination_img_path)

#         img_chat = f'<img src="file/{destination_img_path}">'
#         output_name2 = img_chat
#     else:
#         output_name2 = convert_to_markdown(answer)
#     return output_name2, model_output
    
# def random_text_expression(ip, answer, threshold = 0.1):

#     answer_split = answer.split('\n')
#     actions = answer_split[0].split(': ')[-1]
#     answer = answer_split[-1].split(': ')[-1]


#     # possibility threshold of random expression: img or text
#     # random to show expression or text 
#     random_number = random.random()
#     if random_number > threshold:
#             # choose first image
#         img_chat_search = search(ip, actions)[0]
    
#         destination_img_path = os.path.join("cache/cache", img_chat_search.split('/')[-1])
#         shutil.copy(img_chat_search, destination_img_path)

#         img_chat = f'<img src="file/{destination_img_path}">'
#         output_name2 = img_chat
#     else:
#         output_name2 = convert_to_markdown(answer)

#     return output_name2

def get_available_characters():
    cha_ls = json.load(open('./extensions/api/URI_mapping.json','r')).keys()
    return cha_ls
    
    
    return 








