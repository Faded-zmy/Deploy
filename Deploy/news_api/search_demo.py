import requests
import openai
import tiktoken
import time
import logging
import re
from datetime import datetime

HOST_WIKI = '10.10.100.201:7778'
URI_WIKI = f'http://{HOST_WIKI}/api/v1/chat'


HOST_NEWS = '10.10.100.201:7779'
URI_NEWS = f'http://{HOST_NEWS}/api/v1/chat'
MAX_TETRY_TIMES = 5

NEWS_TOKEN_LIMIT = 50

user_intentions = ['news', 'wiki', 'chat']


def reformat_output(output, urls):
    """
    :param output: llm直接输出的文本
    :param urls: 所有urls
    :return: 格式化后的文本, 真正使用了的url，从1开始
    """
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
    # print(f"Tokens Of Prompt in {api_id}: {len(enc.encode(prompt))}!")
    if len(enc.encode(prompt)) > 15000:
        print("Tokens > 15k, return directly.")
        return None
    while True:
        output = ""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                # max_tokens=max_token,
                request_timeout=120,
                timeout=120
            )
            usages = response['usage']

            # print("Request cost: {0}".format(usages['total_tokens']))
            output = response['choices'][0]['message']['content']
            break
        except openai.error.OpenAIError as e:
            print(f"error {e} {api_id}")
            logging.warning("Error: {0}. Retrying...".format(e))
            cn += 1
            if cn > MAX_TETRY_TIMES:
                print(f"Already tried more than {cn} times!")
                break
            time.sleep(18)
    return output


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
    print(f"User intention: {user_intentions[intent-1]}")
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
        res_len = 15
        news_nums = res_len//3
        res = "\n".join([f"News[{i+1}]:(Title:{result[i]}):{' '.join(result[i+news_nums].split(' ')[0: NEWS_TOKEN_LIMIT])}" for i in range(news_nums)][0:5])
        urls = result[news_nums*2: news_nums*3]

    elif search_type == 2: # 如果是wiki
        print(f"Searching wiki: {query}")
        response = requests.post(URI_WIKI, json=request)
        if response.status_code == 200:
            result = response.json()['reponses']
            # print(result)
        # 解析wiki的返回
        for idx, doc in enumerate(result):
            res += f"Document[{idx+1}]:(Title:{doc[1]}): {doc[0]}" + '\n'
            urls.append(f"https://en.wikipedia.org/wiki/{doc[1].replace(' ', '_')}")

    return res, urls


def get_output(docs, query, search_type):
    enc = tiktoken.get_encoding("cl100k_base")
    if len(enc.encode(docs)) > 14000:
        docs = ' '.join(docs.split(' ')[0:14000])
    if docs == "":
        docs = "None"
    if search_type == 1:
        prompt = """Instruction: Write an accurate, engaging, and concise answer for the given question using only the provided search results (some of which might be irrelevant) and cite them properly. Use an unbiased and journalistic tone. Always cite for any factual claim. When citing several search results, use [1][2][3]. Cite at most three news in each sentence. If multiple news support the sentence, only cite a minimum sufficient subset of the news. If consecutive sentences are quoted from the same source, you only need to cite it once after those sentences.
        Question: 
        {q}
        News: 
        {w}
        Answer:""".format(q=query, w=docs)
        # print(prompt)
    elif search_type == 2:
        prompt = """Instruction: Write an accurate, engaging, and concise answer for the given question using only the provided search results (some of which might be irrelevant) and cite them properly. Use an unbiased and journalistic tone. Always cite for any factual claim. When citing several search results, use [1][2][3]. Cite at least one document and at most three documents in each sentence. If multiple documents support the sentence, only cite a minimum sufficient subset of the documents. If consecutive sentences are quoted from the same source, you only need to cite it once after those sentences.
        Question: 
        {q}
        Wiki: 
        {w}
        Answer:""".format(q=query, w=docs)
    else:
        return ""
    # print(prompt)
    output = openai_chatcompletion(prompt)
    return output


def main(chat_history):
    repeat_times = 1
    time1 = time.time()
    intent, query = intent_recognition(chat_history)
    time2 = time.time()
    docs, urls = search_docs(query, intent)
    time3 = time.time()
    for i in range(repeat_times):
        output = get_output(docs, query, intent)
    print(output)
    time4 = time.time()
    final_output, citations = reformat_output(output, urls)
    time5 = time.time()
    print(f"Intent cost:{time2-time1}")
    print(f"Search cost:{time3-time2}")
    print(f"GPT cost:{(time4-time3)/repeat_times}")
    print(f"Format cost:{time5-time4}")
    # print(citations)
    # print(urls)
    return final_output


if __name__ == "__main__":
    # sample:
    # example = "Recently, Donald Trump has been facing legal troubles and is set to surrender to authorities in Georgia on charges related to his alleged efforts to overturn the 2020 election [1]. Trump's surrender follows a presidential debate among his rivals for the 2024 Republican nomination, where he remains the leading candidate despite his legal issues [1]. This surrender is part of the fourth criminal case against Trump since March, making him the first former president in U.S. history to be indicted [1]. Trump has denied any wrongdoing and has characterized the charges as politically motivated [1]. Along with Trump, his lawyer Rudy Giuliani and other high-profile defendants have also turned themselves in on charges related to election subversion in Georgia [2][5]."
    # urls = ['https://www.msn.com/en-us/news/politics/trump-set-to-surrender-at-georgia-jail-on-charges-that-he-sought-to-overturn-2020-election/ar-AA1fHgk0', 'https://www.msn.com/en-us/news/politics/giuliani-turns-himself-in-on-georgia-2020-election-charges-after-bond-is-set-at-150000/ar-AA1fFmIm', 'https://www.msn.com/en-us/news/world/it-manager-implicates-trump-in-classified-files-case/ar-AA1fDVWq', 'https://www.msn.com/en-us/news/politics/former-trump-lawyers-rudy-giuliani-sidney-powell-and-jenna-ellis-surrender-in-election-subversion-case/ar-AA1fF06I', 'https://www.msn.com/en-us/news/politics/giuliani-turns-himself-in-on-georgia-2020-election-charges-after-bond-is-set-at-150000/ar-AA1fFd5w']
    # example_reformat_output = "Recently, Donald Trump has been facing legal troubles and is set to surrender to authorities in Georgia on charges related to his alleged efforts to overturn the 2020 election. Trump's surrender follows a presidential debate among his rivals for the 2024 Republican nomination, where he remains the leading candidate despite his legal issues. This surrender is part of the fourth criminal case against Trump since March, making him the first former president in U.S. history to be indicted. Trump has denied any wrongdoing and has characterized the charges as politically motivated [1]. Along with Trump, his lawyer Rudy Giuliani and other high-profile defendants have also turned themselves in on charges related to election subversion in Georgia [2][3]."
    # answer, citations = reformat_output(example, urls)
    # if answer == example_reformat_output:
    #     print("************************************测试例子1通过************************************")
    # else:
    #     print("************************************测试例子1失败************************************")
    #     print(example)
    #     print("********************************************************************************")
    #     print(answer)
    #     print(citations)


    # example = "Donald Trump, born in 1946, comes from a European background. His paternal grandfather, Frederick Trump, immigrated to the United States from Germany in 1885 [1]. Trump's father's side of the family originated from the German village of Kallstadt in the Palatinate, while his mother's side comes from the Outer Hebrides in Scotland [1]. Trump's career includes various ventures, including real estate and television. He amassed a fortune and became a successful businessman [1]. His eldest son, Donald Trump Jr., is an American businessman and former reality television personality [2]. He campaigned for his father's presidential campaign and has been involved in promoting various conspiracy theories [2]. Trump Jr. currently works with his brother Eric in overseeing their father's assets during his presidency [4]. Eric Trump, another son of Donald Trump, was a key advisor, fundraiser, and campaign surrogate during his father's successful run for the presidency [3]. He attended his father's inauguration in 2017 [5]."
    # urls = ['https://en.wikipedia.org/wiki/Donald_Trump', 'https://en.wikipedia.org/wiki/Donald_Trump_Jr.', 'https://en.wikipedia.org/wiki/Eric_Trump', 'https://en.wikipedia.org/wiki/Donald_Trump_Jr.', 'https://en.wikipedia.org/wiki/Eric_Trump']
    # example_reformat_output = "Donald Trump, born in 1946, comes from a European background. His paternal grandfather, Frederick Trump, immigrated to the United States from Germany in 1885. Trump's father's side of the family originated from the German village of Kallstadt in the Palatinate, while his mother's side comes from the Outer Hebrides in Scotland. Trump's career includes various ventures, including real estate and television. He amassed a fortune and became a successful businessman [1]. His eldest son, Donald Trump Jr., is an American businessman and former reality television personality. He campaigned for his father's presidential campaign and has been involved in promoting various conspiracy theories. Trump Jr. currently works with his brother Eric in overseeing their father's assets during his presidency [2]. Eric Trump, another son of Donald Trump, was a key advisor, fundraiser, and campaign surrogate during his father's successful run for the presidency. He attended his father's inauguration in 2017 [3]."
    # answer, citations = reformat_output(example, urls)
    # if answer == example_reformat_output:
    #     print("************************************测试例子2通过************************************")
    # else:
    #     print("************************************测试例子2失败************************************")
    #     print(example)
    #     print("********************************************************************************")
    #     print(answer)
    #     print(citations)

    # example = "The concerns and controversies surrounding Japan's discharge of nuclear wastewater from the Fukushima Daiichi nuclear power plant into the Pacific Ocean are primarily centered around potential damage to the reputation of seafood, political and diplomatic issues, and the long-term impact of low-dose radioactivity [1][2][3]. Japanese fisher groups, as well as groups in China and South Korea, have opposed the plan due to fears of further damage to the reputation of their seafood, making it a political and diplomatic issue [1][2]. However, the Japanese government and Tokyo Electric Power Company (TEPCO) argue that the water must be released to make room for the plant's decommissioning and to prevent accidental leaks. They claim that the treatment and dilution process will make the wastewater safer than international standards and that its environmental impact will be negligibly small [1][2]. Nonetheless, some scientists argue that the long-term impact of the remaining low-dose radioactivity in the water needs attention [1][2]. The release of the treated radioactive water into the Pacific Ocean marks a milestone in the plant's battle with the growing radioactive water stockpile that has hampered the removal of toxic melted debris from the reactors [1][3]. The water is collected and partly recycled as cooling water after treatment, with the rest stored in tanks that are already filled to 98% of their capacity. These tanks need to be freed up to build new facilities for the decommissioning process [1][3]. Prime Minister Fumio Kishida has emphasized the necessity of the release and stated that it cannot be postponed [1][3]. The release of the water began with the least radioactive water to ensure safety, and final preparations for the release included dilution with seawater and sampling to ensure safety [1][3]. The International Atomic Energy Agency (IAEA) has been monitoring the discharge and has confirmed that it is being carried out in accordance with IAEA safety standards [2][4]."
    # urls = ['https://www.msn.com/en-us/news/world/japan-begins-release-of-radioactive-wastewater-from-fukushima-nuclear-plant-into-pacific-ocean/ar-AA1fHzyE', 'https://www.msn.com/en-us/news/world/japans-fukushima-nuclear-plant-begins-releasing-treated-radioactive-wastewater-into-the-sea/ar-AA1fGXUy', 'https://www.msn.com/en-us/news/world/the-fukushima-nuclear-plant-begins-releasing-radioactive-wastewater-into-the-sea/ar-AA1fGXUy', 'https://www.msn.com/en-us/news/world/the-fukushima-nuclear-plant-begins-releasing-treated-radioactive-wastewater-into-the-sea/ar-AA1fGXUy', 'https://www.msn.com/en-us/news/world/japan-begins-releasing-treated-fukushima-water-into-pacific/ar-AA1fHZLY']
    # example_reformat_output = "The concerns and controversies surrounding Japan's discharge of nuclear wastewater from the Fukushima Daiichi nuclear power plant into the Pacific Ocean are primarily centered around potential damage to the reputation of seafood, political and diplomatic issues, and the long-term impact of low-dose radioactivity [1][2][3]. Japanese fisher groups, as well as groups in China and South Korea, have opposed the plan due to fears of further damage to the reputation of their seafood, making it a political and diplomatic issue. However, the Japanese government and Tokyo Electric Power Company (TEPCO) argue that the water must be released to make room for the plant's decommissioning and to prevent accidental leaks. They claim that the treatment and dilution process will make the wastewater safer than international standards and that its environmental impact will be negligibly small. Nonetheless, some scientists argue that the long-term impact of the remaining low-dose radioactivity in the water needs attention [1][2]. The release of the treated radioactive water into the Pacific Ocean marks a milestone in the plant's battle with the growing radioactive water stockpile that has hampered the removal of toxic melted debris from the reactors. The water is collected and partly recycled as cooling water after treatment, with the rest stored in tanks that are already filled to 98% of their capacity. These tanks need to be freed up to build new facilities for the decommissioning process. Prime Minister Fumio Kishida has emphasized the necessity of the release and stated that it cannot be postponed. The release of the water began with the least radioactive water to ensure safety, and final preparations for the release included dilution with seawater and sampling to ensure safety [1][3]. The International Atomic Energy Agency (IAEA) has been monitoring the discharge and has confirmed that it is being carried out in accordance with IAEA safety standards [2][4]."
    # answer, citations = reformat_output(example, urls)
    # if answer == example_reformat_output:
    #     print("************************************测试例子3通过************************************")
    # else:
    #     print("************************************测试例子3失败************************************")
    #     print(example)
    #     print("********************************************************************************")
    #     print(answer)
    #     print(citations)

    example = "Recently, Japan has begun releasing treated radioactive water from the Fukushima Daiichi nuclear power plant into the Pacific Ocean [1][2][5]. This decision has sparked controversy and raised concerns among neighboring countries, such as South Korea, about the safety of seafood consumption [3][4]."

    chat_history = [
        "Li Feng: Hello!",
        "Socrates: Hello! How can I assist you today?",
        "Li Feng: Who are you?",
        "Socrates: I'm an artificial intelligence assistant, designed to help answer questions, provide information, and assist with various tasks. How can I help you today?",
        "Li Feng: What's been going on with Trump recently? I heard he turned himself in.",
        "Socrates: Recently, Donald Trump has been facing legal troubles and is set to surrender to authorities in Georgia on charges related to his alleged efforts to overturn the 2020 election [1]. Trump's surrender follows the indictment of his lawyer, Rudy Giuliani, and 17 others on similar charges [2]. These charges stem from accusations that Trump and his allies participated in a conspiracy to subvert the will of the voters after he lost to Joe Biden in the election [2]. Trump has denied any wrongdoing and has characterized the investigation as politically motivated [1].",
        "Li Feng: Tell me more about him.",
        "Socrates: The latest news about Donald Trump is that he skipped the first Republican presidential debate in Milwaukee and instead appeared in a pre-recorded interview with Tucker Carlson on X, the website formerly known as Twitter. Trump criticized his rivals, calling former Arkansas Gov. Asa Hutchinson and former New Jersey Gov. Chris Christie 'nasty' and stating that they shouldn't be running for president. Trump's decision to skip the debate was influenced by his ongoing feud with Fox News Channel, which was hosting the debate. He also cited his large lead in the polls as a reason for not appearing on the debate stage with the other candidates [1]. Trump's absence from the debate was notable, and the other candidates had the opportunity to make their case for the party's nomination. The debate was moderated by Fox News hosts Bret Baier and Martha MacCallum, and each candidate was given time to answer questions and respond to follow-up questions and comments [2]. Former President Donald Trump is facing indictments in four jurisdictions and is expected to surrender himself at the Fulton County Jail in Georgia on Thursday [2][3]. Despite the legal problems he is facing, Trump continues to lead the Republican field by a wide margin in the polls [4].",
        "Li Feng: How do you evaluate him?"

    ]

    # chat_history_2 = [
    #     "Chang long: Who are you?",
    #     "Socrates: I'm an artificial intelligence assistant, designed to help answer questions, provide information, and assist with various tasks. How can I help you today?",
    #     "Chang long: What's been going on with Trump recently? I heard he turned himself in.",
    #     "Socrates: Recently, Donald Trump has been facing legal troubles and is set to surrender to authorities in Georgia on charges related to his alleged efforts to overturn the 2020 election [1]. Trump's surrender follows the indictment of his lawyer, Rudy Giuliani, and 17 others on similar charges [2]. These charges stem from accusations that Trump and his allies participated in a conspiracy to subvert the will of the voters after he lost to Joe Biden in the election [2]. Trump has denied any wrongdoing and has characterized the investigation as politically motivated [1].",
    #     "Li Feng: Tell me more about him.(Cite:'Chang long: What's been going on with Trump recently? I heard he turned himself in.')"
    # ]
    # input = "\n".join(chat_history[0:9])
    # input = """
    # Lifeng: How do you comment on Japan's discharge of nuclear wastewater?
    # Socrates: Japan has begun releasing treated radioactive water from the Fukushima Daiichi nuclear power plant into the Pacific Ocean [1][2][3]. This move has sparked controversy and opposition from Japanese fisher groups, as well as concerns from China and South Korea [1][2]. However, the Japanese government and Tokyo Electric Power Company (TEPCO) argue that the water must be released to make room for the plant's decommissioning and to prevent accidental leaks [1][2]. They claim that the treatment and dilution process will make the wastewater safer than international standards and that its environmental impact will be negligibly small [1][2]. Nonetheless, some scientists believe that the long-term impact of the low-dose radioactivity remaining in the water should be given attention [1][2]. The release of this water marks a milestone in the ongoing battle to address the growing radioactive water stockpile at the Fukushima plant, which has hindered the removal of toxic melted debris from the reactors [1][2]. The water is being released in batches, starting with the least radioactive water to ensure safety, and is being discharged into the ocean through an undersea tunnel [1][2]. The water is collected and partly recycled as cooling water after treatment, while the rest is stored in tanks that are already nearly full [1][2]. These tanks need to be emptied to make way for new facilities required for the decommissioning process [1][2]. Prime Minister Fumio Kishida has emphasized the importance of this release and stated that it cannot be postponed [1]. The International Atomic Energy Agency (IAEA) has approved Japan's plan and has experts on-site to ensure that the discharge is carried out in accordance with safety standards [2][3].
    # Lifeng: What do you think about this?
    # """
    chatHistory= [
            "Yan TIFOSI: 当前时间是2027年7月23日23点56分36秒，请问今天星期几，属于哪各生肖年",
            "Socrates: 根据您提供的时间，我无法确定今天的确切星期几和生肖年份，因为我的知识截止日期是2021年9月，我无法获取到2027年的日期信息。要确定今天是星期几和属于哪个生肖年，您可以使用计算工具或者查看当前日期的日历。通常，您可以在手机、电脑或墙上的日历上找到这些信息。",
            "Yan TIFOSI: 当前时间是2027年7月23日23点56分36秒，请问今天星期几，属于哪个生肖年",
            "Socrates: 根据您提供的日期和时间，2027年7月23日是星期六，属于中国农历的生肖年份则需要根据具体日期来计算，但根据我截止到2021年9月的知识，您可以使用农历工具来确定这一信息。 2027年的农历生肖年份是兔年。",
            "Yan TIFOSI: 最近日本发生了什么事？"
    ]
    input = "\n".join(chatHistory)
    print(input)
    print(main(input))