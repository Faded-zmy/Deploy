import os
import warnings
import yaml
import requests

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

import yaml
from PIL import Image

import modules.extensions as extensions_module
from modules import chat, shared, ui#, utils
from modules.extensions import apply_extensions

def create_interface():

    # Defining some variables
    gen_events = []
    title = 'Text generation web UI'


    # css/js strings
    # css = ui.css if not shared.is_chat() else ui.css + ui.chat_css
    # js = ui.main_js if not shared.is_chat() else ui.main_js + ui.chat_js
    css = ui.css + ui.chat_css
    js = ui.main_js + ui.chat_js
    css += apply_extensions('css')
    js += apply_extensions('js')

    with gr.Blocks(css=css, analytics_enabled=False, title=title, theme=ui.theme) as shared.gradio['interface']:
        if Path("notification.mp3").exists():
            shared.gradio['audio_notification'] = gr.Audio(interactive=False, value="notification.mp3", elem_id="audio_notification", visible=False)
            audio_notification_js = "document.querySelector('#audio_notification audio')?.play();"
        else:
            audio_notification_js = ""

        # Create chat mode interface
        # if shared.is_chat():
        shared.input_elements = ui.list_interface_input_elements(chat=True)
        shared.gradio['interface_state'] = gr.State({k: None for k in shared.input_elements})
        shared.gradio['Chat input'] = gr.State()
        # shared.gradio['dummy'] = gr.State()

        with gr.Tab('One Person Sum', elem_id='main'):
            with gr.Column():
                with gr.Row():
                    with gr.Column():
                        shared.gradio['display'] = gr.HTML(label="Output")
                    with gr.Column():
                        # shared.gradio['character_menu'] = gr.Dropdown(choices=["Elon Musk","Socrates","Albert Einstein","Charles Darwin","William Shakespeare","Lionel Messi","Warren Buffett","Stephen Hawking","Donald Trump", "Harry Potter","Sherlock Holmes","Iron Man","Captain America","Dr. Watson","Pikachu","Jay Gatsby","Juliet","Daenerys Targaryen","Spider-Man"],value=shared.character, label='Character', elem_id='character-menu', info='Used in chat and tweet modes.')
                        shared.gradio['user_id'] = gr.Textbox(label='User id',scale=1 ,min_width=100)
                    with gr.Column():
                        shared.gradio['another_id'] = gr.Textbox(label='The other one',scale=1 ,min_width=100)
                        
                with gr.Column():
                    with gr.Column():
                        shared.gradio['textbox'] = gr.Textbox(label='Input',scale=1 ,min_width=100)

                    with gr.Column():
                        shared.gradio['encoder'] = gr.Button('Encode', elem_id='encoder', variant='primary')

                    with gr.Column():
                        shared.gradio['Clear history'] = gr.Button('Clear history')
                        shared.gradio['Clear history-confirm'] = gr.Button('Confirm', variant='stop', visible=False)
                        shared.gradio['Clear history-cancel'] = gr.Button('Cancel', visible=False)

            # with gr.Tab('InsideOut', elem_id='memory'):
            #     with gr.Row():
            #         with gr.Column():
            #             shared.gradio['user_a'] = gr.HTML(label="User A")
            #         with gr.Column():
            #             shared.gradio['user_b'] = gr.HTML(label="User B")
            #         with gr.Column():
            #             shared.gradio['summary'] = gr.HTML(label="Summary")
                         
        # chat mode event handlers
        # if shared.is_chat():
            
        clear_arr = [shared.gradio[k] for k in ['Clear history-confirm', 'Clear history', 'Clear history-cancel']]

        shared.gradio['max_new_tokens'] = 4096
        gen_events.append(shared.gradio['encoder'].click(
            # ui.gather_interface_values, [shared.gradio[k] for k in shared.input_elements], shared.gradio['interface_state']).then(
            lambda x: (x, ''), shared.gradio['textbox'], [shared.gradio['Chat input'], shared.gradio['textbox']], show_progress=False).then(
            chat.summary_encoder, [shared.gradio['user_id'], shared.gradio['Chat input']], None, show_progress=False).then(
            # chat.generate_cai_chat_html, None, shared.gradio['display']).then(
            # # chat.get_insideout_encoder, None, [shared.gradio['user_a'], shared.gradio['user_b'], shared.gradio['summary']]).then(
            lambda: None, None, None, _js=f"() => {{{audio_notification_js}}}")
        )
        

        shared.gradio['Clear history'].click(lambda: [gr.update(visible=True), gr.update(visible=False), gr.update(visible=True)], None, clear_arr)
        shared.gradio['Clear history-cancel'].click(lambda: [gr.update(visible=False), gr.update(visible=True), gr.update(visible=False)], None, clear_arr)
      
        extensions_module.create_extensions_block()
    shared.gradio['interface'].queue()
    auth = None
    if shared.args.listen:
        shared.gradio['interface'].launch(prevent_thread_lock=True, share=shared.args.share, server_name=shared.args.listen_host or '0.0.0.0', server_port=shared.args.listen_port, inbrowser=shared.args.auto_launch, auth=auth)
    else:
        shared.gradio['interface'].launch(prevent_thread_lock=True, share=shared.args.share, server_port=shared.args.listen_port, inbrowser=shared.args.auto_launch, auth=auth)

if __name__ == "__main__":
    # Loading custom settings
    settings_file = None
    # if shared.args.settings is not None and Path(shared.args.settings).exists():
    #     settings_file = Path(shared.args.settings)
    # elif Path('settings.yaml').exists():
    #     settings_file = Path('settings.yaml')
    # elif Path('settings.json').exists():
    #     settings_file = Path('settings.json')

    # if settings_file is not None:
    #     logger.info(f"Loading settings from {settings_file}...")
    #     file_contents = open(settings_file, 'r', encoding='utf-8').read()
    #     new_settings = json.loads(file_contents) if settings_file.suffix == "json" else yaml.safe_load(file_contents)
    #     for item in new_settings:
    #         shared.settings[item] = new_settings[item]

    
    

    # Default extensions
    # extensions_module.available_extensions = utils.get_available_extensions()
    # if shared.is_chat():
    #     for extension in shared.settings['chat_default_extensions']:
    #         shared.args.extensions = shared.args.extensions or []
    #         if extension not in shared.args.extensions:
    #             shared.args.extensions.append(extension)
    # else:
    #     for extension in shared.settings['default_extensions']:
    #         shared.args.extensions = shared.args.extensions or []
    #         if extension not in shared.args.extensions:
    #             shared.args.extensions.append(extension)

    # available_models = utils.get_available_models()

    # Model defined through --model
    # if shared.args.model is not None:
    #     shared.model_name = shared.args.model

    # Only one model is available
    # elif len(available_models) == 1:
    #     shared.model_name = available_models[0]

    # # Select the model from a command-line menu
    # elif shared.args.model_menu:
    #     if len(available_models) == 0:
    #         logger.error('No models are available! Please download at least one.')
    #         sys.exit(0)
    #     else:
    #         print('The following models are available:\n')
    #         for i, model in enumerate(available_models):
    #             print(f'{i+1}. {model}')

    #         print(f'\nWhich one do you want to load? 1-{len(available_models)}\n')
    #         i = int(input()) - 1
    #         print()

    #     shared.model_name = available_models[i]

    # # If any model has been selected, load it
    # if shared.model_name != 'None':
    #     model_settings = get_model_specific_settings(shared.model_name)
    #     shared.settings.update(model_settings)  # hijacking the interface defaults
    #     update_model_parameters(model_settings, initial=True)  # hijacking the command-line arguments


    # Force a character to be loaded
    # if shared.is_chat():
    #     shared.persistent_interface_state.update({
    #         'mode': shared.settings['mode'],
    #         'character_dw_menu': shared.args.character or shared.settings['character'],
    #         'instruction_template': shared.settings['instruction_template']
    #     })

    shared.generation_lock = Lock()
    # Launch the web UI
    create_interface()
    while True:
        time.sleep(0.5)
        if shared.need_restart:
            shared.need_restart = False
            time.sleep(0.5)
            shared.gradio['interface'].close()
            time.sleep(0.5)
            create_interface()
