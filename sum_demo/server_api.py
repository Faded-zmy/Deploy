import os
import warnings
import yaml
import requests
import argparse

# from modules.logging_colors import logger

os.environ['GRADIO_ANALYTICS_ENABLED'] = 'False'
os.environ['BITSANDBYTES_NOWELCOME'] = '1'
warnings.filterwarnings('ignore', category=UserWarning, message='TypedStorage is deprecated')


# This is a hack to prevent Gradio from phoning home when it gets imported
def my_get(url, **kwargs):
    logger.info('Gradio HTTP request redirected to localhost :)')
    kwargs.setdefault('allow_redirects', True)
    return requests.api.request('get', 'http://127.0.0.1/', **kwargs)


original_get = requests.get
requests.get = my_get
import gradio as gr
requests.get = original_get

import matplotlib
matplotlib.use('Agg')  # This fixes LaTeX rendering on some systems

import importlib
import io
import json
import math
import os
import re
import sys
import time
import traceback
import zipfile
from datetime import datetime
from functools import partial
from pathlib import Path
from threading import Lock

import psutil
import torch
import yaml
from PIL import Image

# import modules.extensions as extensions_module
from modules import shared
# from modules.extensions import apply_extensions
# from modules.html_generator import chat_html_wrapper
from modules.LoRA import add_lora_to_model
from modules.models import load_base_model
# from modules.text_generation import (generate_reply_wrapper,
#                                      get_encoded_length, stop_everything_event)


from extensions.api import script as api_script


if __name__ == "__main__":
    # parser = argparse.ArgumentParser(formatter_class=lambda prog: argparse.HelpFormatter(prog, max_help_position=54))


    # parser.add_argument('--base_model', type=str, default=None, help='the bath model path.')
    # #tweet weight path
    # parser.add_argument('--summary_lora_path', type=str, default=None, help='the summary model lora weight path.')
    # parser.add_argument('--sum_merge_lora_path', type=str, default=None, help='the merge summary model lora weight path.')
    # parser.add_argument('--topic_merge_lora_path', type=str, default=None, help='the merge topic model lora weight path.')

    # args = parser.parse_args()
    
    api_script.setup()
    base_model, shared.tokenizer = load_base_model(shared.args.base_model)
    # delta_weight_path = yaml.safe_load(open('characters/'+s+'.yaml','r', encoding='utf-8').read())['delta_weight_path']
    
    shared.summary_model = add_lora_to_model(base_model,shared.args.summary_lora_path)
    base_model, shared.tokenizer = load_base_model(shared.args.base_model)
    shared.sum_merge_model = add_lora_to_model(base_model,shared.args.sum_merge_lora_path)
    base_model, shared.tokenizer = load_base_model(shared.args.base_model)
    shared.topic_merge_model = add_lora_to_model(base_model,shared.args.topic_merge_lora_path)
    print('Successfully load lora!')

    # base_model, shared.tokenizer = load_base_model(shared.model_name)

    # print('tweet path:',shared.args.tweet_model)
    # print('Successfully load lora!')

    # Force a character to be loaded
    # if shared.is_chat():
        # shared.persistent_interface_state.update({
        #     'mode': shared.settings['mode'],
        #     'character_dw_menu': shared.args.character or shared.settings['character'],
        #     'instruction_template': shared.settings['instruction_template']
        # })

    shared.generation_lock = Lock()
    # Launch the web UI
    # create_interface()
    while True:
        time.sleep(0.5)
        if shared.need_restart:
            shared.need_restart = False
            time.sleep(0.5)
            shared.gradio['interface'].close()
            time.sleep(0.5)
            # create_interface()
    
