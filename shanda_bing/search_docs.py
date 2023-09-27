import requests

HOST_WIKI = '10.10.100.201:7778'
URI_WIKI = f'http://{HOST_WIKI}/api/v1/chat'

HOST_NEWS = '10.10.100.201:7778'
URI_NEWS = f'http://{HOST_NEWS}/api/v1/chat'

NEWS_KEY_NUM = 6
WIKI_KEY_NUM = 2

def search_docs(query, search_type, news_top_n):
    request = {'text': query}
    res = ""
    urls = []

    # news
    if search_type == 1:
        response = requests.post(URI_NEWS, json=request)
        if response.status_code == 200:
            result = response.json()['reponses']

        res_len = len(result)
        res = []
        news_nums = res_len // NEWS_KEY_NUM
        for i in range(min(news_nums, news_top_n)):
            res.append({'title': result[i], 'text': result[news_nums+i], 'description': result[news_nums*4+i]+' ......', 'previewUrl': result[news_nums*2+i], "imageUrl": result[news_nums*3+i], "domain": 'www.msn.com', "imageWidth": 200, "imageHeight": 200, 'date':result[news_nums*5+i]})

    # wiki
    elif search_type == 2:
        response = requests.post(URI_WIKI, json=request)
        if response.status_code == 200:
            result = response.json()['reponses']

        # wiki return
        res = []
        # old version
        for idx, doc in enumerate(result):
            res.append({'title': doc[1], 'description': doc[0], 'previewUrl': f"https://en.wikipedia.org/wiki/{doc[1].replace(' ', '_')}", "domain": 'www.wikipedia.org'})
        
        # coming version
        # news_nums = len(result) // WIKI_KEY_NUM
        # for i in range(min(news_nums, news_top_n)):
        #     res.append({'title': result[i], 'text': result[news_nums+i], 'previewUrl': f"https://en.wikipedia.org/wiki/{result[i].replace(' ', '_')}", "domain": 'www.msn.com'})

    return res