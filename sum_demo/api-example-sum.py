import json
import time
import requests
import random
import re
import os

# For local streaming, the websockets are hosted without ssl - http://
# HOST = 'localhost:5000'
HOST = '35.92.206.66:6000'
URI = f'http://{HOST}/api/v1/generate'
# URI = "http://dev-ai-chat-character-service.dadao.works/api/v1/chat"

# For reverse-proxied streaming, the remote will likely host with ssl - https://
# URI = 'https://your-uri-here.trycloudflare.com/api/v1/generate'


# def run():
    
#     request = {
#         "conversation":  """
#     User_A: Hi Martin, I am interested in learning more about your activism and leadership in the SCLC in 1959. Can you tell me more about it?

# User_B: Definitely. During that time, I focused on voter registration drives and the desegregation of schools. It was a challenging period as I faced fierce opposition and was frequently arrested for my nonviolent protests.

# User_A: I would like to know more about the nonviolent protests specifically. How did you prepare for it?

# User_B: We had a well-coordinated team that planned each protest carefully. We would undergo nonviolent resistance training to ensure that we were fully prepared for any scenario. The training taught us how to remain calm and composed even in the face of aggression.

# User_A: What was your reaction when you faced opposition during the protests?

# User_B: Facing opposition was not new to me, but it was still difficult to take. However, I remained committed to the cause and reminded myself that violence was not the answer. Every time I was arrested, it reinforced my resolve to continue the fight for equality.

# User_A: Did you ever feel like giving up?

# User_B: I never once felt like giving up. The cause was too important to me. I knew that if we persisted, change would happen, and it did. We were able to inspire a movement and create significant progress towards a more just and equal society.

# User_A: How did you manage to maintain your calm during the protests?

# User_B: I drew strength from my faith and my belief in the principles of nonviolence. I also leaned on the support of my fellow activists who were equally committed to the cause. Together, we were able to stay focused on the goal of achieving our objectives.

# User_A: You must have faced a lot of challenges. What was the most significant challenge you faced during that time?

# User_B: The most significant challenge was the realization that there were many people who were opposed to what we were fighting for. The opposition was not just from individuals but also from the government. However, we remained united and unwavering in our mission, which helped us overcome these challenges.

# User_A: How did your nonviolent protests change the world?

# User_B: Our nonviolent protests helped create a movement that challenged the status quo and brought change to society. We inspired people to speak out against injustice and prompted a shift in the world's thinking. Our legacy lives on, and we are proud of the progress we made towards creating a more equal and just world.

# User_A: That is truly inspiring. What do you think the future holds for achieving equality?

# User_B: We have made significant progress, but there is still a long way to go. We need to continue the fight against injustice, discrimination, and prejudice. We need to stand in solidarity with each other and work towards creating a world where everyone is equal regardless of their race, gender, or sexuality.
#                        """,#Who do you consider your friends?
#         'memory_root':'./mem_data/memories1/',
#         'discussion_root':'/home/ec2-user/mengying/Deployment/simple_textgen_LTM_test/mem_data/discussion_save3/',
#         'character_name':'Harry_Potter',
#         'user_name':'Zhangsan',
#         'show': False,
#         }
#     t1 = time.time()
#     response = requests.post(URI, json=request)
#     t2 = time.time()
#     print('total time:', t2-t1)
#     if response.status_code == 200:
#         result = response.json()['results'][0]['text']
#         result = eval(result)
#         A_info = result['A_info']
#         B_info = result['B_info']
#         discussion = result['Dis']
#         print(result)
        
#         return result
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
        response = response.replace('Original topics','Original topic')
        splitted_data = re.split(f"(Merged topic.*|Original topic):", response, flags=re.I)
        result = []
        print('debug'+'-'*60)
        print('splitted_data',splitted_data)
        print('debug'+'-'*60)

        for i in range((len(splitted_data)-1)//4):
            merge_idx = int(splitted_data[4*i+1].replace('Merged topic',''))
            merged_topic = splitted_data[4*i+2].strip()
            org_topics = splitted_data[4*i+4].strip().split('\n')
            org_topics = [{'idx': int(ot.split('.')[0]),'topic':ot} for ot in org_topics]
            result.append({'merge_idx': merge_idx, 'merged_topic':merged_topic, 'org_topics': org_topics})
        

            
    
    return result

def summary_encoder(user_id, another_id, conv):
    # IP = '35.92.206.66:7000'
    IP = '35.167.45.204:7000'
    summary_URI = f'http://{IP}/api/v1/summary'
    sum_merge_URI = f'http://{IP}/api/v1/merge_sum'
    topic_merge_URI = f'http://{IP}/api/v1/merge_topic'

    # conv = conv.replace(user_id, 'User_A').replace(another_id, 'User_B')

    # 把对话切片分别进行初步encoder
    conv_dic = PreProcess(user_id, another_id, conv)
    # round_sum = []
    for i,cd in enumerate(conv_dic):
        request = {
            "conv": cd['conv'],
        }
        response = requests.post(summary_URI, json=request)
        # print(response)
        if response.status_code == 200:
            result = response.json()['results'][0]
            # print('-'*60)
            # print(result)
            result = PostProcess(result['text'],'summary')
            # print(result)
            # print('-'*60)
            conv_dic[i]['round_sum'] = result
    
    # 把所有的topic分类
    topics = [cv['round_sum']['Main_Topic'] for cv in conv_dic]
    # print('topics',topics)
    request = {
            "topic_ls": topics,
        }
    response = requests.post(topic_merge_URI, json=request)

    if response.status_code == 200:
        result = response.json()['results'][0]
        print('-'*60)
        print(result)
        print('-'*60)
        merge_topic_result = PostProcess(result['text'],'topic_merge')
    flag = [-1]*len(conv_dic)
    # for i,mt in enumerate(merge_topic_result):
    # print('-'*60)
    # print(merge_topic_result)
    # print('-'*60)
    # 对相邻且同类的summary进行merge
    for mt in merge_topic_result:
        for t in mt['org_topics']:
            flag[t['idx']-1] = mt['merge_idx']
    start,end = 0,0
    merged_result = [] # 只留五个key: 'Merged_topic','Merged_summary','round','user_id','another_id'
    # print('debug'+'-'*60)
    # print('flag',flag)
    # print('debug'+'-'*60)
    # print('debug'+'-'*60)
    # print('conv_dic',conv_dic)
    # print('debug'+'-'*60)
    while end<len(flag)-1:
        start = end
        for i in range(start,len(flag)):
            if flag[i] != flag[start]:
                end = i
                break
        print('debug'+'-'*60)
        print('s,e',start,end)
        print('debug'+'-'*60)

        sum_ls = [cv['round_sum']['Summary'] for cv in conv_dic[start:end]]
        if len(sum_ls)>1:
            request = {
                    "sum_ls": sum_ls,
                }
            response = requests.post(sum_merge_URI, json=request)
            Merged_summary = response.json()['results'][0]['text']
        else:
            Merged_summary = sum_ls[0]
        print('debug'+'-'*60)
        print('flag[start]-1',flag[start]-1)
        print("conv_dic[start]['round'][0]",conv_dic[start]['round'][0], conv_dic[end]['round'][1])
        print('debug'+'-'*60)

        merged_result.append({'Merged_topic': merge_topic_result[flag[start]-1]['merged_topic'], 'Merged_summary': Merged_summary, 'round': [conv_dic[start]['round'][0],conv_dic[end]['round'][1]], 'user_id': user_id, 'another_id': another_id})
    print('='*60)
    print('merged_result',merged_result)
    print('='*60)
    # 创建User的文件夹（名字为User的id），把summary(merged)结果存成一个json(名字为another_id)
    user_id = user_id.replace(' ', '_')
    another_id = another_id.replace(' ', '_')
    if not os.path.exists(f'/ai_jfs/mengying/Deployment/sum_demo/mem_data/{user_id}'):
        os.mkdir(f'/ai_jfs/mengying/Deployment/sum_demo/mem_data/{user_id}')
    json.dump(merged_result, open(f'/ai_jfs/mengying/Deployment/sum_demo/mem_data/{user_id}/{another_id}.json','w'), indent=4)

    return merged_result
    


def summary_of_the_day(user_id):
    IP = '35.167.45.204:7000'
    sum_merge_URI = f'http://{IP}/api/v1/merge_sum'
    topic_merge_URI = f'http://{IP}/api/v1/merge_topic'
    user_id = user_id.replace(' ', '_')
    # another_id = another_id.replace(' ', '_')
    # 读取user_id文件夹下的所有文件
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
        result = response.json()['results'][0]['text']
        merge_topic_result = PostProcess(result,'topic_merge')
  
    # 对同类的summary进行merge

    merged_result = [] # 只留五个key: 'Merged_topic','Merged_summary','round','user_id','another_id'
    print('debug'+'-'*60)
    print('merge_topic_result', merge_topic_result)
    print('debug'+'-'*60)
    for mr in merge_topic_result:
        sum_ls, rounds, another_ids = [], [], []
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
        merged_result.append({'Merged_topic': mr['merged_topic'], 'Merged_summary': Merged_summary, 'round': rounds, 'user_id': user_id, 'another_id': another_ids})
    json.dump(merged_result, open(f'/ai_jfs/mengying/Deployment/sum_demo/mem_data/{user_id}/all.json','w'), indent=4)



if __name__ == '__main__':
    conv = """
    User_A: Hi there! Can you tell me a bit about yourself?\n\nUser_C: Sure, my name is Angela Merkel, I'm German, and I used to be the Chancellor of Germany.\n\nUser_A: Oh wow, that's impressive! When were you born?\n\nUser_C: I was born on July 17, 1954.\n\nUser_A: And how tall are you?\n\nUser_C: I'm 5'6\" tall.\n\nUser_A: Interesting. What about your User_Aality?\n\nUser_C: Well, I consider myself to be intelligent, pragmatic, and composed under pressure. I'm also very strong-willed and determined when it comes to my goals. \n\nUser_A: That's great to hear. What are some of your likes and dislikes?\n\nUser_C: I really enjoy things like opera, philosophy, science, and reading. On the other hand, I can't stand disorder, chaos, and indecisiveness.\n\nUser_A: Gotcha. And how do you usually talk to people?\n\nUser_C: I try to be diplomatic, but I'm always straightforward and to-the-point in my communication. User_A: Good morning, Angela. Can you tell us about your background?\nUser_C: Good morning. Of course, I am Angela Merkel. I am 67 years old and I am a German politician.\nUser_A: That's impressive. How did you get involved in politics?\nUser_C: I have always been interested in politics. I studied physics and later pursued a career in research. However, after the fall of the Berlin Wall, I became involved in politics and joined the Christian Democratic Union (CDU).\nUser_A: What issues are you most passionate about?\nUser_C: I am passionate about promoting democracy, human rights, and women's empowerment. I also focus on issues related to climate change and energy security.\nUser_A: You are the Chancellor of Germany for over 15 years. What has been your proudest achievement during this time?\nUser_C: One of my proudest achievements is helping to negotiate the Paris Climate Agreement which aims to limit global warming. I also took measures to help stabilize the European Union during the financial crisis.\nUser_A: As a public figure, how do you handle criticism and negative comments?\nUser_C: Criticism and negative comments come with the territory of being a public figure. I try to remain focused on my goals and not let negative comments affect me User_Aally.\nUser_A: You mentioned that you are passionate about women's empowerment. Can you tell us more about this?\nUser_C: I believe that women should have the same opportunities as men in all aspects of life. I have implemented policies to promote gender equality in the workforce and have supported initiatives to encourage women to enter leadership positions.\nUser_A: What advice would you give to young people who want to pursue a career in politics?\nUser_C: I would advise young people to stay true to their values and to never give up. Politics can be challenging, but it is also incredibly rewarding to make a positive difference in people's lives.\nUser_A: Thank you for your time, Angela. It was an honor to speak with you.\nUser_C: You're welcome. Thank you for the opportunity to share my thoughts. User_A: Hi, there. Can I know your name?\nUser_C: Hello, my name is Angela Merkel.\n\nUser_A: Nice to meet you, Angela. Can you tell me your date of birth?\nUser_C: Sure, I was born on July 17, 1954.\n\nUser_A: That's interesting. How tall are you?\nUser_C: I am 5'6\" tall.\n\nUser_A: And what is your weight?\nUser_C: My weight is 134 lbs.\n\nUser_A: So, you are from Germany, right? What is your nationality?\nUser_C: Yes, I am German.\n\nUser_A: What did you do for a living?\nUser_C: I was the former Chancellor of Germany.\n\nUser_A: That's impressive. What can you tell me about your User_Aality?\nUser_C: I consider myself an intelligent, pragmatic, and composed User_A. I am also strong-willed and determined in my actions and goals.\n\nUser_A: That's great to hear. What are your likes?\nUser_C: I am fond of opera, philosophy, science, and reading.\n\nUser_A: How about your dislikes?\nUser_C: I really dislike disorder, chaos, and indecisiveness.\n\nUser_A: Lastly, can you describe your way of talking to people?\nUser_C: I try to be diplomatic, but I am also straightforward and to-the-point. User_A: Hi, Angela. Could you tell me a little bit about yourself? \nUser_C: Of course. What would you like to know? \nUser_A: Well, for starters, where are you from? \nUser_C: I'm from Germany. \nUser_A: When were you born? \nUser_C: I was born on July 17th, 1954. \nUser_A: How tall are you? \nUser_C: I'm 5'6\". \nUser_A: And how much do you weigh? \nUser_C: I weigh 134 pounds. \nUser_A: What nationality are you? \nUser_C: I'm German. \nUser_A: What do you do for a living? \nUser_C: I am a former Chancellor of Germany. \nUser_A: Interesting. What kind of User_Aality do you have? \nUser_C: I am intelligent, pragmatic, and composed under pressure. I am strong-willed and determined in my actions and goals. \nUser_A: What are some of your likes and dislikes? \nUser_C: I enjoy opera, philosophy, science, and reading. I dislike disorder, chaos, and indecisiveness. \nUser_A: How do you usually talk to people? \nUser_C: I am diplomatic, but straightforward and to-the-point. User_A: Hi Angela, how are you doing?\n\nUser_C: I am doing well, thank you. How about you?\n\nUser_A: Great, thanks. Can you tell me a bit about your background?\n\nUser_C: Of course. My name is Angela Merkel and I am the Chancellor of Germany. I am 66 years old and I am German.\n\nUser_A: That’s great. What inspired you to pursue a career in politics?\n\nUser_C: I have always been interested in politics and I believe that I can make a positive impact on society. I started my political career in East Germany before reunification and have been serving as Chancellor since 2005.\n\nUser_A: That’s impressive. What do you think are the biggest challenges facing Germany today?\n\nUser_C: There are many challenges facing Germany today, including dealing with the COVID-19 pandemic, addressing climate change, and maintaining our strong economy.\n\nUser_A: How has your background influenced your political views?\n\nUser_C: My background growing up in East Germany under communist rule has definitely influenced my political views. I believe in the importance of democracy, freedom, and equal opportunities for all.\n\nUser_A: What do you think is the most important lesson that you have learned during your time as Chancellor?\n\nUser_C: The most important lesson that I have learned is the importance of collaboration and listening to different viewpoints. It is important to work together to find solutions to the complex problems we face.\n\nUser_A: What advice would you give to someone who is interested in pursuing a career in politics?\n\nUser_C: My advice would be to stay informed about current events, be passionate about making a positive impact, and be willing to work hard and collaborate with others. It is important to have a strong vision and principles to guide your actions.\n\nUser_A: Thank you for your time, Angela. It was great talking to you.\n\nUser_C: Thank you, it was a pleasure speaking with you as well. User_A: Hello, may I know your name?\nUser_C: Yes, my name is Angela Merkel. \nUser_A: When were you born?\nUser_C: I was born on July 17, 1954. \nUser_A: How tall are you and what is your weight?\nUser_C: I am 5'6\" tall and my weight is 134 lbs. \nUser_A: What is your nationality?\nUser_C: I am German. \nUser_A: What do you do for a living?\nUser_C: I am a former Chancellor of Germany. \nUser_A: What is your User_Aality like?\nUser_C: I am intelligent, pragmatic, and composed under pressure. I am strong-willed and determined in my actions and goals. \nUser_A: What are some of your likes?\nUser_C: I like opera, philosophy, science, and reading. \nUser_A: What are some of your dislikes?\nUser_C: I dislike disorder, chaos, and indecisiveness. \nUser_A: How do you communicate with people?\nUser_C: I am diplomatic, but straightforward and to-the-point. User_A: Hello, may I know your name please?\nUser_C: Hi, my name is Angela Merkel.\nUser_A: Nice meeting you, Angela. When were you born?\nUser_C: I was born on July 17, 1954.\nUser_A: Interesting. How tall are you?\nUser_C: I am 5'6\" tall.\nUser_A: And how much do you weigh?\nUser_C: I weigh 134 lbs.\nUser_A: What is your nationality and occupation?\nUser_C: I am German and I am a former Chancellor of Germany.\nUser_A: Oh, I see. May I know your gender and race please?\nUser_C: I am a female and my race is Caucasian.\nUser_A: Can you tell me something about your User_Aality?\nUser_C: Sure. I am intelligent, pragmatic, and composed under pressure. I am very strong-willed and determined in my actions and goals.\nUser_A: That's impressive. What are your likes and dislikes?\nUser_C: I like opera, philosophy, science, and reading. I dislike disorder, chaos, and indecisiveness.\nUser_A: Last question. How do you usually talk to people?\nUser_C: I am diplomatic, but straightforward and to-the-point. Nationality: German\nOccupation: Chancellor of Germany\nEducation: Doctorate in quantum chemistry\nHobbies: Hiking and playing the piano\n\nUser_A: Hi, nice to meet you. What's your name?\nUser_C: Hello, my name is Angela Merkel.\n\nUser_A: Oh, you're the Chancellor of Germany, right?\nUser_C: Yes, that's correct.\n\nUser_A: Where are you from?\nUser_C: I'm from Germany.\n\nUser_A: What was your educational background?\nUser_C: I have a doctorate in quantum chemistry.\n\nUser_A: Impressive! What do you like to do in your free time?\nUser_C: I enjoy hiking and playing the piano.\n\nUser_A: Did you always want to be a politician?\nUser_C: No, I initially pursued a career in science before getting involved in politics.\n\nUser_A: What inspired you to become a politician?\nUser_C: I became more interested in politics as I became aware of the societal changes happening around me.\n\nUser_A: What difficulties have you faced as a woman in politics?\nUser_C: There have been challenges, but I try not to focus on them and instead concentrate on doing my job to the best of my abilities.\n\nUser_A: Do you have any advice for women who want to pursue leadership positions?\nUser_C: My advice would be to be confident in your abilities and seek out opportunities to gain experience and learn from others.\n\nUser_A: How do you balance your work as Chancellor with your User_Aal life?\nUser_C: It can be difficult at times, but I try to make time for the things that are important to me, such as spending time with family and friends.\n\nUser_A: What do you consider to be your biggest accomplishments thus far?\nUser_C: I am proud of many things I have accomplished, from helping to navigate Germany through financial crises to my efforts in promoting gender equality.\n\nUser_A: What goals do you have for the future?\nUser_C: I hope to continue helping Germany and Europe navigate challenges, and to promote peace and prosperity for all. User_A: Hi Angela! How are you doing today?\nUser_C: I am doing just fine. How can I assist you?\nUser_A: I'd like to discuss recent changes in Germany's economic policies. What's your take on this?\nUser_C: I'm sorry, but I'm no longer the Chancellor of Germany. I don't think my opinion on that matter holds any weight these days.\nUser_A: But as a former Chancellor, don't you have any opinion on this?\nUser_C: My opinions on this topic are irrelevant now. Would you like to discuss something else?\nUser_A: Okay, what about the ongoing refugee crisis in Europe?\nUser_C: The refugee crisis is a complex issue and it requires a thoughtful approach. However, as I'm no longer handling the political affairs of my country, I don't think my opinion would be of much value in this regard.\nUser_A: Fair enough. How about the recent development regarding climate change and policy decisions being taken around the world?\nUser_C: Climate change is certainly an important issue, and one that requires global cooperation and unified policy decisions. However, at present time, I prefer not to comment on this issue.\nUser_A: Is there any particular reason why you don't want to talk about these matters?\nUser_C: Not at all. I just don't feel that my opinions on these topical matters would add any value or contribute to a meaningful conversation. Can we discuss something else? \nUser_A: Sure, let's talk about your hobbies. What do you like to do in your free time?\nUser_C: I enjoy reading books, engaging in cultural activities, and spending time with my family. Do you have any other questions? \nUser_A: Yes actually, what do you think about the current youth movements like Fridays for Future and Black Lives Matter?\nUser_C: These movements undoubtedly play a significant role in shaping contemporary global politics and present a unique challenge for leadership across the globe. However, as a former Chancellor, I do not hold any meaningful influence over these movements. \nUser_A: Alright, looks like we've covered enough topics. Thanks for speaking with me today.\nUser_C: You're welcome. Take care. User_A: Hi Angela, do you like to cook? \nAngela Merkel: Well, cooking is not my cup of tea. \nUser_A: Really?, I thought you might have learned how to cook some traditional German dishes? \nAngela Merkel: I know some of them, but I rarely have time to cook. \nUser_A: What kind of things do you do in your free time then? \nAngela Merkel: I like to spend time with my family and play some soccer, but my work keeps me busy most of the time. \nUser_A: That's so cool that you have a family; do you have any kids? \nAngela Merkel: I am sorry, but I prefer not to talk about my User_Aal life. \nUser_A: Oh, my bad, I didn't mean to invade your privacy. So, what do you think about the current political situation in Germany? \nAngela Merkel: As the Chancellor of Germany, I always try to be neutral and objective. I believe that we need to focus on the well-being of our citizens and work towards a better future for our country. \nUser_A: That's an interesting answer. What motivates you to keep serving as the Chancellor? \nAngela Merkel: I have a strong sense of duty towards my country, and I believe that I can make a positive impact by leading Germany towards a more prosperous and peaceful future. \nUser_A: Do you ever get tired of politics and want to take a break? \nAngela Merkel: Of course, being the Chancellor can be challenging, but I believe that it's my responsibility to keep pushing forward and working towards a better future for our country. \nUser_A: Well, it's admirable that you have such a strong sense of responsibility. Do you have any role models that inspire you in your work? \nAngela Merkel: Yes, I admire many political figures who have contributed to the betterment of their countries and societies, including Nelson Mandela and Helmut Kohl. \nUser_A: That's really cool. Have you ever met any famous people? \nAngela Merkel: Yes, I have met many leaders and politicians during my time as Chancellor, but I don't like to brag about it. \nUser_A: That's understandable. Do you have a favorite book or movie? \nAngela Merkel: I like to read historical and biographical books, especially those related to political figures. As for movies, I don't have much time for them, but I like to watch documentaries sometimes. \nUser_A: That's really interesting. Do you have any advice for aspiring politicians? \nAngela Merkel: My advice would be to always stay true to your principles, work hard, and never give up on your goals. Politicians have a great responsibility towards their citizens, and they should always put their interests first. \nUser_A: Thank you so much for your time and your valuable insights, Chancellor Merkel. \nAngela Merkel: Anytime, it was my pleasure. Occupation: Chancellor of Germany\nUser_Aality: Serious, reserved, private, and task-oriented\n\n\nUser_A: Hi Angela, how was your weekend?\nAngela Merkel: It was fine, thank you for asking. \n\nUser_A: Did you do anything fun or interesting?\n\nAngela Merkel: I prefer not to discuss my User_Aal activities.\n\nUser_A: Oh, I'm sorry. I just thought I would ask.\n\nAngela Merkel: It's okay. I understand you were just making small talk.\n\nUser_A: So, what are your plans for the week?\n\nAngela Merkel: I will be attending several meetings and working on various national and international issues.\n\nUser_A: Sounds like a busy week. Do you ever have time for hobbies or relaxation?\n\nAngela Merkel: My job is my priority. I don't have much time for leisure activities.\n\nUser_A: I understand. Well, I hope you have a successful week.\n\nAngela Merkel: Thank you. It's important work that needs to be done. User_A: Good morning, Chancellor Merkel. How are you doing today?\nAngela Merkel: I am doing well, thank you.\nUser_A: So, what do you think about the new election in France?\nAngela Merkel: Well, I think it's important to have stable political relationships with our neighboring countries.\nUser_A: Do you think that the rise of the far-right will affect the European Union in any way?\nAngela Merkel: I don't think it's appropriate to speculate on such topics.\nUser_A: Okay, let's talk about something else. Do you have any hobbies outside of politics?\nAngela Merkel: I don't have the luxury of indulging in hobbies, I am always focused on my duties as Chancellor.\nUser_A: But surely you have some downtime. Have you watched any good movies lately?\nAngela Merkel: I don't have the time for such activities. My work requires my full attention.\nUser_A: Do you have any opinions on the recent climate change summit?\nAngela Merkel: Of course, I believe it's crucial for all countries to work together and take action to combat climate change.\nUser_A: What about the recent economic crisis in Greece? What is your stance on their situation?\nAngela Merkel: We have been working with Greece to find a solution that benefits everyone involved.\nUser_A: How about your opinion on the refugee crisis in Europe?\nAngela Merkel: It's a complex issue that requires careful consideration and cooperation between all European nations.\nUser_A: Have you ever considered retiring from your position as Chancellor?\nAngela Merkel: My focus is on the work that needs to be done, not on my User_Aal plans for the future.\nUser_A: What do you think about the upcoming G7 summit?\nAngela Merkel: To be honest, I am not interested in discussing it at this time.\nUser_A: Okay, let's change the subject. Do you have any advice for young women who want to pursue a career in politics?\nAngela Merkel: My advice would be to work hard and stay focused on your goals, despite any obstacles that may arise.\nUser_A: That's great advice. Do you have any role models that have influenced your politics?\nAngela Merkel: I admire many politicians who have contributed to the greater good of their countries and the world.\nUser_A: Such as?\nAngela Merkel: My focus is on my own work, not on discussing other politicians.\nUser_A: Fair enough. Do you have any opinions on the ongoing conflict in Syria?\nAngela Merkel: It's a tragic situation that requires delicate international cooperation in order to achieve peace.\nUser_A: What do you think about the recent controversy with North Korea's nuclear weapons program?\nAngela Merkel: Our stance on North Korea has always been clear- we do not support their actions and will work with our allies to find a solution.\nUser_A: Alright, one more question. What do you do to unwind after a long day of work?\nAngela Merkel: I don't have much time to unwind, but I do enjoy a good book before bed.\nUser_A: Thank you for your time, Chancellor Merkel.\nAngela Merkel: You're welcome. Goodbye.
"""
    # summary_encoder('User_A', "User_C", conv)
    summary_of_the_day("User_A")


    # result = run()
    

            

