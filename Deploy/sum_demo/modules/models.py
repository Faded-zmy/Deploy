import gc
import json
import os
import re
import time
import zipfile
from pathlib import Path

import numpy as np
import torch
import transformers
from accelerate import infer_auto_device_map, init_empty_weights
from transformers import (AutoConfig, AutoModel, AutoModelForCausalLM,
                          AutoModelForSeq2SeqLM, AutoTokenizer,
                          BitsAndBytesConfig, LlamaTokenizer)

import modules.shared as shared
# from modules import llama_attn_hijack
# from modules.logging_colors import logger



# Some models require special treatment in various parts of the code.
# This function detects those models

def load_base_model(model_path):
    tokenizer = AutoTokenizer.from_pretrained(f"{model_path}/", use_fast=False)
    base_model = AutoModelForCausalLM.from_pretrained(
        f"{model_path}/", torch_dtype=torch.float16
    )
    return base_model,tokenizer


