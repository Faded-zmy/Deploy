retri_URI = 'http://10.10.100.201:9999/api/v1/chat'
import requests
def run(text):
    
    request = {'text':text
        
        }

    response = requests.post(retri_URI, json=request)

    if response.status_code == 200:
        res = response.json()#['reponses']
        show_res = 'News:\n'
        if res.keys() == {'news'}:
            for i in range(5):
                show_res+=str(i+1)+'.\n'+"Title: "+res['news'][i]['Title']+'\n'+"Content: "+res['news'][i]['Content']+'\n'+"Link: "+res['news'][i]['Link']+'\n'
            res = show_res
        # print(res)
        return res

import gradio
interface = gradio.Interface(run, gradio.inputs.Textbox(lines=1), gradio.outputs.Textbox())
# interface = gradio.Interface(run, 
#                                 gradio.inputs.Textbox(lines=1),
#                             [gradio.outputs.Textbox() for _ in range(10)],
                            
#                             )

interface.launch(inline=True, share=True)