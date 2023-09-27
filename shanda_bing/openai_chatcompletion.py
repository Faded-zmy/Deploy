import openai
import tiktoken

def openai_chatcompletion(prompt, api_id, log, model_id=0, temperature=0):
    # api_id = 2, 4 plus
    api_key = [
        "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",
        "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",
        "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",
        "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",
        "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",
    ]
    models=["gpt-3.5-turbo", "gpt-3.5-turbo-16k"]
    openai.api_key = api_key[api_id]

    enc = tiktoken.get_encoding("cl100k_base")
    print(f"Tokens Of Prompt in {api_id}: {len(enc.encode(prompt))}!")
    if len(enc.encode(prompt)) > 4000:
        print("Tokens > 4k, return directly.")
        return ""
    while True:
        output = ""
        try:
            response = openai.ChatCompletion.create(
                model=models[model_id],
                messages=[
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                request_timeout=120,
                timeout=120
            )
            usages = response['usage']

            print("Request cost: {0}".format(usages['total_tokens']))
            output = response['choices'][0]['message']['content']
            print(f"API Prompt: {prompt}\nAPI Result: {output}\n")
            break
        except openai.error.OpenAIError as e:
            print(f"error {e} {api_id}")
            print("Error: {0}. Retrying...".format(e))
            log.info('OpenAI API RETRY!')
            return output

    return output


def openai_chatcompletion_stream(prompt, api_id, log, model_id=0, temperature=0):
    # api_id = 2, 4 plus
    api_key = [
        "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",
        "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",
        "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",
        "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",
        "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",
    ]
    models=["gpt-3.5-turbo", "gpt-3.5-turbo-16k"]
    openai.api_key = api_key[api_id]

    enc = tiktoken.get_encoding("cl100k_base")
    print(f"Tokens Of Prompt in {api_id}: {len(enc.encode(prompt))}!")
    if len(enc.encode(prompt)) > 4000:
        print("Tokens > 4k, return directly.")
        return ""
    while True:
        output = ""
        try:
            response = openai.ChatCompletion.create(
                model=models[model_id],
                messages=[
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
                request_timeout=3,
                stream=True
            )
            stream_messagees = ""
            for chunk in response:
                delta = chunk["choices"][0]["delta"]
                if "content" in delta: # calculate the time delay of the event
                    stream_message = delta["content"]
                    stream_messagees += stream_message
                    # print(f"Message received: {chunk_time:.2f} seconds after request: {stream_message}")  # print the delay and text
            output = stream_messagees
            print("Request cost: {0}".format(len(enc.encode(output))))
            print(f"API Prompt: {prompt}\nAPI Result: {output}\n")
            break
        except openai.error.OpenAIError as e:
            print(f"error {e} {api_id}")
            print("Error: {0}. Retrying...".format(e))
            log.info('OpenAI API RETRY!')
            return output

    return output
