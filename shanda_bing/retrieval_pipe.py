import time
import os
import json
from func_timeout import func_set_timeout

from intent_recognition import intent_recognition
from search_docs import search_docs
from sum_output import get_output
from reformat_output import reformat_output

NEWS_TOP_N = 2

LONGEST_TIME = 8

user_intentions = ['news', 'wiki', 'chat']

def PreProcess(data, round_time=5):
    
    # content = data['fullName'] + ': ' + data['content'].replace('@Socrates', '')
    content = data['content'].replace('@Socrates', '')
    chat_history = '\n'.join(data['chatHistory'][-round_time:])
    return content, chat_history


@func_set_timeout(LONGEST_TIME)
def get_final_result(data, mode, log, save_root, cite=False, news_top_n=NEWS_TOP_N, news_only=True):
    save_dic= {}
    if mode == 'news':
        intent = 1
        query = data['fullName']+': '+data['content'].replace('@Socrates', '')
        save_dic['mode'] = 'news'
        save_dic['inputs'] = query
    elif mode == 'wiki':
        intent = 2
        query = data['fullName']+': '+data['content'].replace('@Socrates', '')
        save_dic['mode'] = 'wiki'
        save_dic['inputs'] = query

    elif mode == 'auto':
        content, chat_history = PreProcess(data)
        t1 = time.time()
        intent, query = intent_recognition(content, chat_history, data['parent'])
        save_dic['mode'] = 'auto'
        save_dic['inputs'] = {'content':content, 'chat_history':chat_history, 'parent':data['parent']}
        save_dic['intent_output'] = {'intent': intent, 'query': query}
        t2 = time.time()
        log.info(f'Intent Output IS {intent}')
        log.info(f'Intent Output Needs Time: {t2-t1}')
    t2 = time.time()
    if news_only and intent == 2:
        intent = 3
    docs = search_docs(query, intent, news_top_n)
    t3 = time.time()
    print(f"Search time: {t3-t2}")
    log.info(f'Search Time: {t3-t2}')

    output = get_output(docs, query, intent, news_top_n, log)
    if output == "":
        output = {
            "answer": "",
            "type": None
        }
        return output

    t4 = time.time()
    print(f"Generation time: {t4-t3}")
    log.info(f'Generation Time: {t4-t3}')

    urls = [d['previewUrl'] for d in docs]
    final_output, citations = reformat_output(output, urls, cite)

    if intent == 1 or intent == 2:
        if cite:
            if intent == 1:
                if citations == []:
                    output = {
                        "answer": "",
                        "type": None
                    }
                else:
                    log.info('Successfully retri news!')
                    retri_infos = []
                    for c in citations:
                        retri_infos.append({'previewUrl': docs[c-1]['previewUrl']})

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
                "answer": final_output.replace('[1]','').replace('[2]','').replace('[3]','').replace('[4]','').replace('[5]','').replace(' .', '.'),
                "type": user_intentions[intent-1]
            }
        
   
    else:
        output = {
            "answer": "",
            "type": None
        }
    t5 = time.time()
    print(f"total time: {t5-t2}")
    log.info(f"total time: {t5-t2}")

    save_dic['output'] = output
    folder = save_root+'/'+time.strftime("%Y_%m_%d", time.localtime()) 
    if not os.path.exists(folder):
        os.makedirs(folder)
    
    json.dump(save_dic, open(folder+'/'+data['roomId']+'_'+data['msgId']+'.json', 'w'), indent=4)

    return output
