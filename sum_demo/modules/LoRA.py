from pathlib import Path

import torch
from peft import PeftModel

# import modules.shared as shared
# from modules.logging_colors import logger

#zmy
def add_lora_to_model(base_model,lora_path):
    lora_model = PeftModel.from_pretrained(
        base_model,
        lora_path,
        torch_dtype=torch.float16,
    )
    model = lora_model.merge_and_unload().cuda()
    return model

