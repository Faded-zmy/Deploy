import tiktoken
from openai_chatcompletion import openai_chatcompletion, openai_chatcompletion_stream
import random

NEWS_TOKEN_LIMIT = {
    5:100,
    4:100,
    3:75,
    2:100,
    1:200
}

def get_output(docs, query, search_type, news_top_n, log):
    enc = tiktoken.get_encoding("cl100k_base")

    if docs == "":
        docs = "None"
    if search_type == 1:

        res = "\n".join([f"News[{i+1}]:(Title:{docs[i]['title']}):{' '.join(docs[i]['text'].split(' ')[0: NEWS_TOKEN_LIMIT[news_top_n]])}" for i in range(min(news_top_n, len(docs)))])

        prompt = """Instruction: Write an accurate, engaging, and concise answer for the given question using only the provided search news (some of which might be irrelevant) and cite them properly. Use an unbiased and journalistic tone. Always cite for any factual claim. When citing several search results, use [1][2][3]. Cite at most three news in each sentence. If multiple news support the sentence, only cite a minimum sufficient subset of the news. If the search news are not enough to answer, please reply with "None".  \n[User's Question start]\n{q}\n[User's Question end]\n[News start]\n{w}\n[News end]\nIf the user query recent/latest news, then all news is relevant.The answer needs to be within 100 words. \nAnswer:""".format(q=query, w=res)

    elif search_type == 2:
        res = "\n".join([f"Document[{i+1}]:(Title:{docs[i]['title']}):{' '.join(docs[i]['description'].split(' '))}" for i in range(len(docs))])
        prompt = """Instruction: Write an accurate, engaging, and concise answer for the given question using only the provided search results (some of which might be irrelevant) and cite them properly. Use an unbiased and journalistic tone. Always cite for any factual claim. When citing several search results, use [1][2][3]. Cite at least one document and at most three documents in each sentence. If multiple documents support the sentence, only cite a minimum sufficient subset of the documents. If the search results and the question are completely unrelated, please reply with "None".
        Question: 
        {q}
        Wiki: 
        {w}
        Answer:""".format(q=query, w=docs)
    else:
        return ""

    api_id = random.choice([2, 4])
    output = openai_chatcompletion_stream(prompt, api_id, log)
    if "None" in output:
        log.info("No Relevant News in database!")
        print(f"There is no relevant news: {query}")
    if output == "" or "None" in output or output is None:
        output = ""
    return output