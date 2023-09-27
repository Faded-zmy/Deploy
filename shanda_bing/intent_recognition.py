import random
from openai_chatcompletion import openai_chatcompletion, openai_chatcompletion_stream

user_intentions = ['news', 'wiki', 'chat']

def intent_recognition(content, chat_history, log, parent=''):
    """
    :param input: Chat history, including the current user's question concatenated at last
    :param llm:
    :param args:
    :return:
    """
    if parent != '':
        content += f"(Cite:'{parent}')"
    prompt = f"""
    The following is the question/command sent by the user to the AI assistant:
    [User's Current Question start]
    {content}
    [User's Current Question end]
    You are an outstanding expert in intent recognition, capable of accurately and precisely identifying users' intentions from user's current question: discuss/chat, searching for news, searching for Wikipedia information. Please analyze user's intention according to the current question, assisting the assistant in making decisions involves either providing direct responses or conducting searches. 
    Requirement:
    1. Output 1 for news, 2 for wiki, 3 for chat.
    2. If the user inquires about the assistant's viewpoint or opinion, the user's intent is to chat. Search should only be conducted when users want to know the latest updates about certain things, acquire detailed information about specific matters.
    3. All of your outputs must be in English.

    The output format should be like:
    Output: xxx
    User's Question: xxx"""
    intent, s_question = 3, ''

    api_id = random.choice([0, 1, 2, 3])
    output = openai_chatcompletion_stream(prompt, api_id, log)
    if output == "" or None:
        return intent, s_question
    print('debug'+'-'*60)
    print('prompt', prompt)
    print('intent_recognition',output)
    print('-'*60)
    output = output.split('\n')

    for text in output:
        if 'output' in text.lower() and ':' in text.lower():
            try:
                intent = int(text.split(':')[1].strip())
            except Exception as e:
                print(e)
                intent = 3
        elif 'user' in text.lower() and 'question' in text.lower() and ':' in text.lower():
            try:
                s_question = text.split(':')[1].strip()
            except Exception as e:
                print(e)
                s_question = ''
    print(f"User intention: {user_intentions[intent-1]}")
    
    return intent, content