import os
import json
import time
import openai
import numpy as np
from tqdm import tqdm

openai.api_key = "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"

prompt_templete={
    "date_of_birth":"Please format the following strings '{info}' in year-month-day format, If there are only years, only months, and only days, then format as 'None', The final output format must follow the format as below: \nOutput:\nYear: xx\nMonth: xx\nDay: xx",
    "classify":["Please classify these words according to their meanings which describe general types/activities of ",",and put similar words into the same category, and use the definition as a keyword for these words.\nThe output dict structure must are as follows:\n{\n'meaning1':[[xxx1,xxx2],[number1,number2]], \n'meaning2':[[xxx1,xxx2,...], [number1,number2,...]], \n...\n'meaning3':[[xxx1,xxx2,...], [number1,number2,...]], \n...}\nThe list of words is as follows:\n"],
    "add":"Determine which of the following keys in the origin dict the word '{key_word}' belongs to, \n1. if True, add 1 to the his corresponding original number.\n2. if not, please create a new keyword definition to describe it, and add to the original dict, meaning as key and word as values: \n[origin dict begin]{origin_dict}[origin dict end]\n\nThe output dict must follow:\n{new_dict}",
    "person_related":["There is a todo list for someone below, please help to analyze which other people and the corresponding relational terms(such as father, mother, good friend, etc.) this todolist is related to and and specific things in to-do list.\n1. Mark 'None' if there is no person or no relational terms. \n2. If the relational terms is not explicitly mentioned, please do not answer imaginatively, just mark 'None'.\n3. specific things cannot contain any person, only the event itself.\ntodo list:\n","\nThe output format follows this dict:\n{\n'thing1':{'relational terms': [relation1/None, relation2/None,...], 'person name': [person1/None, person2/None,...]},\n'thing2':{'relational terms': [relation1/None, relation2/None,...], 'person name': [person1/None, person2/None,...]},\n}"],
    "person_emotion":["The following is the person whom someone admires. Please split the vocabulary into the name and the corresponding relational terms.\n1. indicated by nouns, such as father, mother, good friend, etc.\n2. the smaller the split, the better, If multiple people are implied, it can be disassembled according to common sense\n3. if it does not exist, you can mark it as none.\nwords:\n","\nThe output format follows this dict:\n{\n'relational terms': [xxx1/None,xxx2/None,...], 'person name': [xxx1/None,xxx2/None,...]\n}"]
    }

def store_add(user_info,memory_user_store,Time):
    if user_info not in memory_user_store[0]:
        memory_user_store[0]+=[user_info]
        memory_user_store[1]+=[1]
        memory_user_store[2]+=[Time]
    else:
        memory_user_store[1][memory_user_store[0].index(user_info)]+=1
        memory_user_store[2][memory_user_store[0].index(user_info)]=Time
    return memory_user_store

def store_add_todo(user_info,memory_user_store,Time):
    if isinstance(user_info[0],list):
        user_info[0]=",".join(user_info[0])
    if isinstance(user_info[1],list):
        user_info[1]=",".join(user_info[1])
    
    a1 = user_info[0].lstrip().strip()
    a2 = user_info[1].lstrip().strip()


    memory_user_store[0]+=[a1]
    if a2!="None" and a2!="Unknown":
        memory_user_store[1]+=[a2]
    else:
        memory_user_store[1]+=[""]
    memory_user_store[-1]+=[Time]

#这里可能有两个隐患，就是他连续两次跟我说他要干什么，但是在不同的时间，我会把之前的时间覆盖掉，如果两件事不同且第一件没有做，那就会出现尴尬的情况，比如今天9天提醒我12点吃午饭，然后第二天10点，又让我提醒第二天12点吃午饭，这样就会有问题，最好有准确的时间保存下来，TODO
def store_todo_show(info,save_thing,save_time,Time,delete):
    if info not in save_thing:
        save_thing.append(info)
        save_time.append(Time)
    else:
        save_time[save_thing.index(info)]=Time
    
    #清除一下空的时间和信息
    if delete in save_thing:
    
        delate_i=[]
        for i in range(len(save_thing)):
            if save_thing[i]==delete:
                delate_i.append(i)
        
        for i in delate_i[::-1]:
            del save_thing[i]
            del save_time[i]

def gpt(user_prompt: str, model="gpt-3.5-turbo"):
    for i in range(3):
        try:
            response = openai.ChatCompletion.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant"},
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                temperature=0.2,  # TODO: figure out which temperature is best for evaluation
                max_tokens=1024,
            )
            content = response["choices"][0]["message"]["content"]
            return content
        except Exception as e:
            # print(e)
            time.sleep(10)
    return "error"

def save_gpt(data_path,prompt,result):
    with open(os.path.expanduser(data_path), "a") as fout:
        ans_json={
                "question":prompt,
                "output":result
            }
        fout.write(json.dumps(ans_json) + "\n")

def format_birth(info,memory_store,Time,gpt_results_root):
    prompt = prompt_templete["date_of_birth"].format(info=info)
    result = gpt(prompt)
    result = result.split("\n")[-3:]
    result = {i.split(": ")[0]:int(i.split(": ")[1]) for i in result}

    #save to path
    save_gpt(gpt_results_root+"birth.json",prompt,result)
    #跟memory融合,默认只能允许有一个日期存在，如果错误，需要覆盖
    for key in result:
        if result[key]!="None":
            memory_store[0][key]=result[key]
            memory_store[1]=Time
    return memory_store

def format_most_and_last(info,memory_store,memory_user_show,Time):
    #选出现的最多的，以及最新出现的两个值作为memory的搜索
    name = info
    before_name_index = np.argmax(memory_store[1])
    before_name = memory_store[0][before_name_index]
    before_time = memory_store[2][before_name_index]
    memory_user_show=[["most time",before_name,before_time],["last time",name,Time]]

    return memory_user_show

def format_most(memory_store,memory_user_show):
    #选出现的最多的，以及最新出现的两个值作为memory的搜索
    before_name_index = np.argmax(memory_store[1])
    before_name = memory_store[0][before_name_index]
    before_time = memory_store[2][before_name_index]
    memory_user_show=[before_name,before_time]

    return memory_user_show

def format_meaning(info,memory_store,memory_user_show,Time,number,gpt_results_root,cat):
    #现在有个问题是判定是否属于的时候会出问题，有的时候就不属于了，很奇怪
    #先看个数是否超过了5,只有超过5次以后（每天做一次总结），才进行分类等
    if np.sum(memory_store[1])<number:
        return memory_user_show
    #首先判定key值是否属于现在的目录中,并且已经满足条件生成了dict，那就不要调gpt了，直接添加进去,如果是空的，那之后的脚本会让他加进去的
    if info in memory_store[0]:
        for key in memory_user_show:
            if info in memory_user_show[key][0]:
                memory_user_show[key][1][memory_user_show[key][0].index(info)]+=1
                return memory_user_show
        #如果他在这里，但是却不在dict里面，只有两种情况，一种是dict是空，还没往里加，还有种情况是dict不为空，这种是错误的，是因为之前合并的时候出了问题
        
        # return memory_user_show

    #show里面是空的，但是也没满足前面的条件，那就是要把change list换成现在的store了
    if memory_user_show=={}:
        change_list=[[memory_store[0][i],memory_store[1][i]] for i in range(len(memory_store[0]))]
        unchange_dict={}

    else:
        #show里面不是空 ，并且 首先得判定show里面是不是有超过number，有的话，key不能改变了
        change_list=[]
        change_key=[]
        unchange_key=[]
        for key in memory_user_show:
            if np.sum(memory_user_show[key][1])<number:
                change_key.append(key)
            else:
                unchange_key.append(key)
        
        unchange_dict={k:memory_user_show[k][:2] for k in unchange_key}
        for k in change_key:
            change_list+=[[memory_user_show[k][0][i],memory_user_show[k][1][i]] for i in  range(len(memory_user_show[k][0]))]

        #首先对于不能改变的key，我们用加入法，如果新增了key，那么就加入下一轮的重新merge,#只有gpt4可以办到，gpt3.5不太行,试过不相关的，一样的，以及相关的，都可以正常归类
        prompt1=prompt_templete["add"].format(key_word=info,origin_dict=str(unchange_dict),new_dict=str(unchange_dict).replace("],",",...],").replace("}",",...}"))
        # print("*******************|prompt1|*************************")
        # print(prompt1)
        # print(memory_store[0],info)
        results=gpt(prompt1,model="gpt-4")
        try:
            unchange_dict_new=eval("{"+results.split("{")[-1].split("}")[0]+"}")
            save_gpt(gpt_results_root+"add_new.json",prompt1,unchange_dict_new)
        except Exception:
            save_gpt(gpt_results_root+"wrong.json",prompt1,results)
            return memory_user_show

        #如果key新增了，就用原来的加到下一轮
        if list(unchange_dict_new.keys())==list(unchange_dict.keys()):
            unchange_dict=unchange_dict_new
    
    #对于能改变的key，我们总结完以后再加入dict
    change_list.append([info,1])
    change_list=[",".join([str(j) for j in i]) for i in change_list]
    prompt2=prompt_templete["classify"][0]+ cat +prompt_templete["classify"][1] +"\n".join(change_list)
    # print("*******************|prompt2|*************************")
    # print(prompt2)
    results=gpt(prompt2,model="gpt-4")
    
    try:
        new_dict=eval("{"+results.split("{")[-1].split("}")[0]+"}")
        save_gpt(gpt_results_root+"generate_new_key.json",prompt2,new_dict)
    except Exception:
        save_gpt(gpt_results_root+"wrong.json",prompt2,results)
        #把unchange的增加进来即可
        for key in unchange_dict:
            memory_user_show[key]=unchange_dict[key]
        return memory_user_show
    # save_gpt(gpt_results_root+"add_new_key.json",prompt2,new_dict)
    exists_key=[]
    for key in new_dict:
        if key in unchange_dict:
            exists_key.append(key)
            unchange_dict[key][0]+=new_dict[key][0]
            unchange_dict[key][1]+=new_dict[key][1]
    
    for key in exists_key:
        del new_dict[key]

    memory_user_show=dict(unchange_dict, **new_dict)

    return memory_user_show

#TODO 对user的名字需要连接user的信息卡才能获取一些对应，目前都是user_A,目前应该是可以连接到用户的信息卡了，但是还没做，之后再做，因为这不止要接一个人的信息卡，可能还涉及到别的角色的信息卡，只要他认识，他聊过他都可以调取
def format_person_related(info,memory_store,memory_user_show,Time,gpt_results_root):
    #当其属于这里的时候，就说明已经生成过了，那就不生成了
    if info in memory_store[0]:
        return memory_user_show
    
    #不属于的时候是新的词，所以需要重新拆解
    prompt=prompt_templete["person_related"][0]+info[0]+prompt_templete["person_related"][1]
    new_dict=eval("{"+gpt(prompt,model="gpt-4").split("{\n")[-1].split("\n}")[0]+"}")
    # print("*******************|prompt|*************************")
    # print(info[0])
    # print("*******************|output|*************************")
    # print(new_dict)
    save_gpt(gpt_results_root+"person_related.json",prompt,new_dict)

    #主要是增加两个信息点，一个是relation，一个是todo
    for thing in new_dict:
        relational_terms=new_dict[thing]["relational terms"]
        person_names=new_dict[thing]["person name"]

        if len(relational_terms)!=len(person_names):
            print(info[0],thing,new_dict[thing])
            continue
        #{"person_list":[],"relationship_list":[],"todo_list":[]}
        for i in range(len(relational_terms)):
            #没有关系 但是有名字的时候，比较容易，目前暂时不涉及名字的匹配，不同的名字就直接新的位置了，TODO
            if relational_terms[i]=="None" or relational_terms[i]==None:

                #没有他人参与的场景，不涉及跟人融合的情况，只需要往里加就好
                if person_names[i]=="None" or person_names[i]==None:
                    person_name="self"
                    person_relationship="-"
                #知道名字的时候，需要跟名字匹配看是否是用户？,其他人目前还可以不匹配，直接往里加，TODO
                else:
                    person_name=person_names[i].lstrip().strip().title()
                    person_relationship=""
                
                if person_name in memory_user_show["person_list"]:
                    save_thing=memory_user_show["todo_list"][memory_user_show["person_list"].index(person_name)]
                    save_time=memory_user_show["todo_time"][memory_user_show["person_list"].index(person_name)]
                    store_todo_show([thing,info[1]],save_thing,save_time,Time,delete=[])
                else:
                    memory_user_show["person_list"].append(person_name)
                    memory_user_show["relationship_list"].append([person_relationship])
                    memory_user_show["relation_time"].append([Time])
                    memory_user_show["emotion"].append([])
                    memory_user_show["emotion_time"].append([])
                    memory_user_show["todo_list"].append([[thing,info[1]]])
                    memory_user_show["todo_time"].append([Time])

                # save_thing=memory_user_show["todo_list"][memory_user_show["person_list"].index(person_name)]
                # save_time=memory_user_show["todo_time"][memory_user_show["person_list"].index(person_name)]
                # store_todo_show([thing,info[1]],save_thing,save_time,Time)

            #relation不为空的时候，一般说到这种时候，应该是唯一性的指向，只会涉及到更新换代，总不能说我的室友，肯定会说我的室友xx，我的朋友xx，但是我的父母是唯一的，男女朋友是唯一的，不唯一的情况肯定会做出额外的描述
            else:
                #当名字是空的时候，那就是唯一指定，可以进行匹配
                if person_names[i]=="None" or person_names[i]==None:
                    person_name=""
                    person_relationship=relational_terms[i].lstrip().strip().title()
                    exsits_relation=-1

                    for i in range(len(memory_user_show["relationship_list"])):
                        if person_relationship in memory_user_show["relationship_list"][i]:
                            exsits_relation=i
                            break
                    #在原始的路径中
                    if exsits_relation!=-1:
                        memory_user_show["relation_time"][exsits_relation][memory_user_show["relation_time"][exsits_relation].index(person_relationship)]=Time
                        save_thing=memory_user_show["todo_list"][exsits_relation]
                        save_time=memory_user_show["todo_time"][exsits_relation]
                        store_todo_show([thing,info[1]],save_thing,save_time,Time,delete=[])
                    else:
                        memory_user_show["person_list"].append(person_name)
                        memory_user_show["relationship_list"].append([person_relationship])
                        memory_user_show["relation_time"].append([Time])
                        memory_user_show["emotion"].append([])
                        memory_user_show["emotion_time"].append([])
                        memory_user_show["todo_list"].append([[thing,info[1]]])
                        memory_user_show["todo_time"].append([Time])
                #当名字不唯一的时候，需要名字先匹配，要是名字匹配上，relation没匹配上，那就是得新增relation
                else:
                    person_name=person_names[i].lstrip().strip().title()
                    person_relationship=relational_terms[i].lstrip().strip().title()
                    #如果名字可以匹配上，那relation看是否需要加进去
                    if person_name in memory_user_show["person_list"]:
                        #关系不为空的时候，新增关系
                        if person_relationship!="":
                            save_thing=memory_user_show["relationship_list"][memory_user_show["person_list"].index(person_name)]
                            save_time=memory_user_show["relation_time"][memory_user_show["person_list"].index(person_name)]
                            store_todo_show(person_relationship,save_thing,save_time,Time,delete="")
                        # if person_relationship!="" and person_relationship not in memory_user_show["relationship_list"][memory_user_show["person_list"].index(person_name)]:
                        #     memory_user_show["relationship_list"][memory_user_show["person_list"].index(person_name)].append(person_relationship)
                        #     memory_user_show["relation_time"][memory_user_show["person_list"].index(person_name)].append(Time)

                        #新增todo
                        save_thing=memory_user_show["todo_list"][memory_user_show["person_list"].index(person_name)]
                        save_time=memory_user_show["todo_time"][memory_user_show["person_list"].index(person_name)]
                        store_todo_show([thing,info[1]],save_thing,save_time,Time,delete=[])
                    #当名字都无法匹配的时候，直接往里加吧
                    else:
                        memory_user_show["person_list"].append(person_name)
                        memory_user_show["relationship_list"].append([person_relationship])
                        memory_user_show["relation_time"].append([Time])
                        memory_user_show["emotion"].append([])
                        memory_user_show["emotion_time"].append([])
                        memory_user_show["todo_list"].append([[thing,info[1]]])
                        memory_user_show["todo_time"].append([Time])

    return memory_user_show

def format_person_emotion(info,memory_store,memory_user_show,Time,gpt_results_root,emotion):
    if info in memory_store[0]:
        return memory_user_show
    prompt=prompt_templete["person_emotion"][0]+info+prompt_templete["person_emotion"][1]
    new_dict=eval("{"+gpt(prompt,model="gpt-4").split("{\n")[-1].split("\n}")[0]+"}")
    save_gpt(gpt_results_root+"person.json",prompt,new_dict)
    relational_terms=new_dict["relational terms"]
    person_names=new_dict["person name"]
    
    if len(relational_terms)!=len(person_names):
        print(info,new_dict)
        return memory_user_show

    for i in range(len(relational_terms)):
        relationship=relational_terms[i]
        person_name=person_names[i]

        #按名字来,一般不会两个都没有，一般都会有一个的
        if relationship=="None" or relationship==None:
            #如果出现了，可能得看看是什么情况了
            if person_name=="None" or person_name==None:
                print("wrong gpt extract",info)
            else:
                if person_name in memory_user_show["person_list"]:
                    save_thing=memory_user_show["emotion"][memory_user_show["person_list"].index(person_name)]
                    save_time=memory_user_show["emotion_time"][memory_user_show["person_list"].index(person_name)]
                    store_todo_show(emotion,save_thing,save_time,Time,delete="")
                    # save_person_index=memory_user_show["emotion"][memory_user_show["person_list"].index(person_name)]
                    # if emotion not in save_person_index:
                    #     memory_user_show["emotion"][memory_user_show["person_list"].index(person_name)].append(emotion)
                    #     memory_user_show["emotion_time"][memory_user_show["person_list"].index(person_name)].append(Time)
                    # else:
                    #     memory_user_show["emotion_time"][memory_user_show["person_list"].index(person_name)][save_person_index.index(emotion)]=Time

                else:
                    memory_user_show["person_list"].append(person_name)
                    memory_user_show["relationship_list"].append([""])
                    memory_user_show["relation_time"].append([Time])
                    memory_user_show["emotion"].append([emotion])
                    memory_user_show["emotion_time"].append([Time])
                    memory_user_show["todo_list"].append([[]])
                    memory_user_show["todo_time"].append([])
        
        else:
            if person_name in memory_user_show["person_list"]:
                save_thing=memory_user_show["emotion"][memory_user_show["person_list"].index(person_name)]
                save_time=memory_user_show["emotion_time"][memory_user_show["person_list"].index(person_name)]
                store_todo_show(emotion,save_thing,save_time,Time,delete="")
                # save_person_emotion=memory_user_show["emotion"][memory_user_show["person_list"].index(person_name)]
                # if emotion not in save_person_emotion:
                #     memory_user_show["emotion"][memory_user_show["person_list"].index(person_name)].append(emotion)
                #     memory_user_show["emotion_time"][memory_user_show["person_list"].index(person_name)].append(Time)
                # else:
                #     memory_user_show["emotion_time"][memory_user_show["person_list"].index(person_name)][save_person_emotion.index(emotion)]=Time
                #relation 也需要更新
                save_thing=memory_user_show["relationship_list"][memory_user_show["person_list"].index(person_name)]
                save_time=memory_user_show["relation_time"][memory_user_show["person_list"].index(person_name)]
                store_todo_show(relationship,save_thing,save_time,Time,delete="")
                                                                 
                # save_person_relation=memory_user_show["relationship_list"][memory_user_show["person_list"].index(person_name)]
                # if relationship not in save_person_relation:
                #     memory_user_show["relationship_list"][memory_user_show["person_list"].index(person_name)].append(relationship)
                #     memory_user_show["relation_time"][memory_user_show["person_list"].index(person_name)].append(Time)
                # else:
                #     memory_user_show["relation_time"][memory_user_show["person_list"].index(person_name)][save_person_relation.index(emotion)]=Time
            else:
                if person_name=="None" or person_name==None:
                    person_name=""
                exsits_relation=-1
                for i in range(len(memory_user_show["relationship_list"])):
                    if relationship in memory_user_show["relationship_list"][i]:
                        exsits_relation=i

                if exsits_relation==-1:
                    memory_user_show["person_list"].append(person_name)
                    memory_user_show["relationship_list"].append([relationship])
                    memory_user_show["relation_time"].append([Time])
                    memory_user_show["emotion"].append([emotion])
                    memory_user_show["emotion_time"].append([Time])
                    memory_user_show["todo_list"].append([[]])
                    memory_user_show["todo_time"].append([])
                
                else:
                    save_person_emotion=memory_user_show["emotion"][exsits_relation]
                    if emotion not in save_person_emotion:
                        memory_user_show["emotion"][exsits_relation].append(emotion)
                        memory_user_show["emotion_time"][exsits_relation].append(Time)
                    else:
                        memory_user_show["emotion_time"][exsits_relation][save_person_emotion.index(emotion)]=Time

    return memory_user_show

def get_store_new(user_info,memory_user_store,memory_user_show,gpt_results_root,key_map,show=False):
    Time= time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))

    key_propress_list=[
        ["bi",["N"],"format_most_and_last_"], #name
        ["bi",["Gd"],"format_most_and_last_"], #gender
        ["bi",["DB"],"format_birth_"], #data_of_birth
        ["bi",["PB"],"format_most_"], #place_of_birth
        ["bi",["R"],"format_most_"], #race
        ["bi",["Nat"],"format_most_"], #nationality 
        ["bg",["EB"],""], #educational_background 还没想到用什么方法
        ["bg",["Op","Pos"],"format_meaning_",10], #position and occupation
        ["bg",["A"],""], #achivement也还没想到用什么方法
        ["o",["Per"],"format_meaning_",10], #personality
        ["o",["H"],"format_meaning_",10], #hobbies
        ["o",["G"],"format_meaning_",10], #good_at
        ["o",["Ng"],"format_meaning_",10], #not_good_at
        ["o",["Toi"],"format_meaning_",10], #topics_of_interest
        ["o",["Tod"],"format_meaning_",10], #topics_of_disinterest
        # ["o",["PTA"],"format_person_"], #people_they_admire
        # ["o",["PTD"],"format_person_"], #people_they_dislike
        # ["o",["Td", "TT"],"format_person_related_"], #todo_time and todo
                        ]

    # key_propress_list=[
    #     ["o",["PTA"],"format_person_"], #people_they_admire
    #     ["o",["PTD"],"format_person_"], #people_they_dislike
    #     ["o",["Td", "TT"],"format_person_related_"], #todo_time and todo
    #                     ]
    
    for format_info in key_propress_list:
    
        key1=format_info[0]
        trans_key1=key_map[key1]
        
        if trans_key1 not in memory_user_store:
            memory_user_store[trans_key1]={}
            memory_user_show[trans_key1]={}

        method=format_info[2]
        
        key2s=format_info[1]
        trans_key2=key_map[key2s[0]]

        #换到relationship里面
        for key2 in key2s:
            #直接添加的操作
            if user_info[key1][key2]=="None" or user_info[key1][key2]=="Unknown": continue

            if trans_key2 not in memory_user_store[trans_key1]:
                memory_user_store[trans_key1][trans_key2]=[[],[],[]]

            #format meaning 要后面才加
            if method not in ["format_meaning_","format_person_","format_person_related_"] and key2!="Td":
                store_add(user_info[key1][key2],memory_user_store[trans_key1][trans_key2],Time)
            
            if show==True:
                if method=="format_birth_":
                    if trans_key2 not in memory_user_show[trans_key1]:
                        memory_user_show[trans_key1][trans_key2]=[{"Year":"","Month":"","Day":""},""]
                    memory_user_show[trans_key1][trans_key2]=format_birth(user_info[key1][key2],memory_user_show[trans_key1][trans_key2],Time,gpt_results_root)

                if method=="format_most_and_last_":
                    if trans_key2 not in memory_user_show[trans_key1]:
                        memory_user_show[trans_key1][trans_key2]=[]
                    memory_user_show[trans_key1][trans_key2]=format_most_and_last(user_info[key1][key2],memory_user_store[trans_key1][trans_key2],memory_user_show[trans_key1][trans_key2],Time)

                if method=="format_meaning_":
                    thre=format_info[3]
                    if trans_key2 not in memory_user_show[trans_key1]:
                        memory_user_show[trans_key1][trans_key2]={}
                    if isinstance(user_info[key1][key2],str):
                        user_info[key1][key2]=user_info[key1][key2].split(",")  
                    for a in user_info[key1][key2]:
                        a = a.lstrip().strip().title()
                        memory_user_show[trans_key1][trans_key2]=format_meaning(
                            a,
                            memory_user_store[trans_key1][trans_key2],
                            memory_user_show[trans_key1][trans_key2],
                            Time,
                            thre,
                            gpt_results_root,
                            trans_key2.lower())
                
                #已跑通，效果正常，但是可能还需要加时间等东西
                if method=="format_person_related_":
                    trans_key2_new = "relationship"
                    if trans_key2_new not in memory_user_show[trans_key1]:
                        memory_user_show[trans_key1][trans_key2_new]={"person_list":["self"],"relationship_list":[["-"]],"relation_time":[["-"]],"emotion":[["-"]],"emotion_time":[["-"]],"todo_list":[[]],"todo_time":[[]]}
                    memory_user_show[trans_key1][trans_key2_new]=format_person_related([user_info[key1][key2],user_info[key1][key2s[1]]],memory_user_store[trans_key1][trans_key2],memory_user_show[trans_key1][trans_key2_new],Time,gpt_results_root)
                    store_add_todo([user_info[key1][key2],user_info[key1][key2s[1]]],memory_user_store[trans_key1][trans_key2],Time)
                    break
                
                #关系还得加上时间，不然要是关系变化了怎么办呢？
                if method=="format_person_":
                    trans_key2_new = "relationship"
                    emotion=trans_key2.split("_")[-1].lstrip().strip().title()
                    if isinstance(user_info[key1][key2],str):
                        user_info[key1][key2]=user_info[key1][key2].split(",")
                    if trans_key2_new not in memory_user_show[trans_key1]:
                        memory_user_show[trans_key1][trans_key2_new]={"person_list":["self"],"relationship_list":[["-"]],"relation_time":[["-"]],"emotion":[["-"]],"emotion_time":[["-"]],"todo_list":[[]],"todo_time":[[]]}
                    for a in user_info[key1][key2]:
                        a = a.lstrip().strip().title()
                        memory_user_show[trans_key1][trans_key2_new]=format_person_emotion(a,memory_user_store[trans_key1][trans_key2],memory_user_show[trans_key1][trans_key2_new],Time,gpt_results_root,emotion)


            if method in ["format_meaning_","format_person_","format_person_related_"] and key2!="Td":
                if isinstance(user_info[key1][key2],str):
                    user_info[key1][key2]=user_info[key1][key2].split(",")  
                for a in user_info[key1][key2]:
                    a = a.lstrip().strip().title()   
                    store_add(a,memory_user_store[trans_key1][trans_key2],Time)
            ##如果是todo的话，需要跟time merge
            if key2=="Td":
                store_add_todo([user_info[key1][key2],user_info[key1][key2s[1]]],memory_user_store[trans_key1][trans_key2],Time)

    return memory_user_store,memory_user_show

def get_store(user_info,memory_user_store):
    Time= time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))
    for key in user_info:
        key_trans=key_map[key]
        if key_trans not in memory_user_store:
            memory_user_store[key_trans]={}
        for key2 in user_info[key]:
            key2_trans=key_map[key2]
            #todo he todo time 应该是一起的
            if key2_trans=="todo_time" or key2_trans=="todo":continue

            if key2_trans not in memory_user_store[key_trans]:
                memory_user_store[key_trans][key2_trans]=[[],[],[]]
                
            
            if user_info[key][key2]!="None" and user_info[key][key2]!="Unknown":
                if isinstance(user_info[key][key2],str):
                    user_info[key][key2]=user_info[key][key2].split(",")  
                for a in user_info[key][key2]:
                    a = a.lstrip().strip().title()
                    if a not in memory_user_store[key_trans][key2_trans][0]:
                        memory_user_store[key_trans][key2_trans][0]+=[a]
                        memory_user_store[key_trans][key2_trans][-1]+=[1]
                        memory_user_store[key_trans][key2_trans][-2]+=[Time]
                    else:
                        # print(memory_user_store[key_trans][key2_trans][0].index(a))
                        memory_user_store[key_trans][key2_trans][-1][memory_user_store[key_trans][key2_trans][0].index(a)]+=1
                        memory_user_store[key_trans][key2_trans][-2][memory_user_store[key_trans][key2_trans][0].index(a)]=Time
    key="o"
    key_trans=key_map[key]
    key2_trans="todo_time"

    if key2_trans not in memory_user_store[key_trans]:
        memory_user_store[key_trans][key2_trans]=[[],[],[]]
    
    # print(key,A_info[key])
    if A_info[key]["Td"]!="None":
        if isinstance(A_info[key]["Td"],list):
            A_info[key]["Td"]=",".join(A_info[key]["Td"])
        if isinstance(A_info[key]["TT"],list):
            A_info[key]["TT"]=",".join(A_info[key]["TT"])
        
        a1 = A_info[key]["Td"].lstrip().strip()
        a2= A_info[key]["TT"].lstrip().strip()
        memory_user_store[key_trans][key2_trans][0]+=[a1]
        memory_user_store[key_trans][key2_trans][1]+=[a2]
        memory_user_store[key_trans][key2_trans][-1]+=[Time]

    return memory_user_store

def get_show(user_info,memory_user_show):
    return memory_user_show

def merge_info_to_origin(user_info,character_name,user_name,memory_root,gpt_results_root,key_map,show=False):
    print('SHOW:',show)
    memory_user=json.load(open(memory_root+"{user_name}/{character_name}_info_card.json".format(user_name=user_name,character_name=character_name),"r")) #这个是展示在外面的形
    memory_user_store=memory_user["store"]
    memory_user_show=memory_user["show"]
    memory_user_store, memory_user_show = get_store_new(user_info,memory_user_store,memory_user_show,gpt_results_root,key_map,show=show)

    with open(memory_root+"/{user_name}/{character_name}_info_card.json".format(user_name=user_name,character_name=character_name),"w") as f:
        json.dump(memory_user,f,indent=4)

    return memory_user

def makedir(memory_root,character_name,user_name):
    if not os.path.exists(memory_root+"/{character_name}/".format(character_name=character_name)):
        os.makedirs(memory_root+"/{character_name}/".format(character_name=character_name))
    if not os.path.exists(memory_root+"/{character_name}/{user_name}_info_card.json".format(character_name=character_name, user_name=user_name)):
        with open(memory_root+"/{character_name}/{user_name}_info_card.json".format(character_name=character_name, user_name=user_name),"w") as f:
            json.dump({"store":{},"show":{}},f,indent=4)

    if not os.path.exists(memory_root+"/{user_name}/".format(user_name=user_name)):
        os.makedirs(memory_root+"/{user_name}/".format(user_name=user_name))
    if not os.path.exists(memory_root+"/{user_name}/{character_name}_info_card.json".format(user_name=user_name,character_name=character_name)):
        with open(memory_root+"/{user_name}/{character_name}_info_card.json".format(user_name=user_name,character_name=character_name),"w") as f:
            json.dump({"store":{},"show":{}},f,indent=4)

# if __name__=="__main__":
#     data_root = "/ai_efs/kortex_data/data/origin_data/info_card/characters_dialogue_20230621_gpu2/"
    
#     memory_root=memory_root+"/"
#     # gpt_results_root="/ai_efs/kortex_data/information_card_data/"
#     gpt_results_root="./information_card_data/"
#     if not os.path.exists(gpt_results_root):
#         os.makedirs(gpt_results_root)
#     #假设现在是用户和虚拟人聊天，那对于用户和虚拟人来说是有两套存储系统的
#     key_map = {
#             "basic_information": "bi",
#             "background": "bg",
#             "others": "o",
#             "name": "N",
#             "gender": "Gd",
#             "date_of_birth": "DB",
#             "place_of_birth": "PB",
#             "race": "R",
#             "nationality": "Nat",
#             "educational_background": "EB",
#             "occupation": "Op",
#             "position": "Pos",
#             "achievement": "A",
#             "personality": "Per",
#             "hobbies": "H",
#             "good_at": "G",
#             "not_good_at": "Ng",
#             "topics_of_interest": "Toi",
#             "topics_of_disinterest": "Tod",
#             "people_they_admire": "PTA",
#             "people_they_dislike": "PTD",
#             "todo": "Td",
#             "todo_time": "TT",
#             "topic": "T",
#             "user_a's_opinion": "Ao",
#             "user_b's_opinion": "Bo",
#             "user_a's_way_of_talking": "Aw",
#             "user_b's_way_of_talking": "Bbao bw",
#             "summary": "sum",
#             "user_a's_achievement": "Aa",
#             "user_b's_achievement": "Ba"
#         }

#     character_name="SpongeBob_SquarePants"
#     user_name="userid_1234"
#     makedir(character_name,user_name)        

#     key_map={v:k for k,v in key_map.items()}

#     info_jsons = os.listdir(data_root)
    
#     number=0

#     for info_json in tqdm(info_jsons):
#         if character_name not in info_json:continue
#         number+=1
#         info = json.load(open(data_root+info_json))
#         A_infos = info["A_info"]
#         B_infos = info["B_info"]
#         Diss = info["Dis"]
#         org_convs = info["org_conv"]
#         for i in range(len(org_convs)):
#             org_conv = org_convs[i]
#             if org_conv=="":continue
#             A_info = A_infos[i]
#             B_info = B_infos[i]
#             Dis = Diss[i]
            
#             #当固定轮次给我信息的时候，我会调用以下代码
#             memory_user=merge_info_to_origin(B_info,character_name,user_name,memory_root,gpt_results_root,show=True)
#             memory_character=merge_info_to_origin(A_info,user_name,character_name,memory_root,gpt_results_root,show=False)
            
#             # os.system("clear")
#             # # print(memory_user["show"]["basic_information"])
#             # print(memory_user["store"]["basic_information"])
#             # time.sleep(1)

if __name__=="__main__":
    #memory储存路径,这个到时候让昌龙改，目前可以只存在本
    memory_root=memory_root+"/"
    character_name="SpongeBob_SquarePants"
    user_name="userid_1234"
    makedir(character_name,user_name)

    #gpt生成结果储存路径，这个可以存到本地
    gpt_results_root="./information_card_data/"
    if not os.path.exists(gpt_results_root):
        os.makedirs(gpt_results_root)

    #新来的information card 梦颖改成自己模型出来的结果
    data_root = "/ai_efs/kortex_data/data/origin_data/info_card/characters_dialogue_20230621_gpu2/"
    info_json = "SpongeBob_SquarePants_relationship_12.json"
    info=json.load(data_root+info_json)

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
            "user_b's_achievement": "Ba"
        }
    key_map={v:k for k,v in key_map.items()}

    A_infos = info["A_info"][0]
    B_infos = info["B_info"][0]
    Diss = info["Dis"][0]
    org_convs = info["org_conv"][0]

    if org_convs!="":
        memory_user=merge_info_to_origin(B_infos,character_name,user_name,memory_root,gpt_results_root,key_map,show=True)
        memory_character=merge_info_to_origin(A_infos,user_name,character_name,memory_root,gpt_results_root,key_map,show=True)





    
