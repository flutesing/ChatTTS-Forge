import threading
import torch
from modules.ChatTTS import ChatTTS
from modules import config
from modules.devices import devices

import logging
import gc

logger = logging.getLogger(__name__)

chat_tts = None
lock = threading.Lock()


def load_chat_tts_in_thread():
    global chat_tts
    if chat_tts:
        return

    logger.info("Loading ChatTTS models")
    chat_tts = ChatTTS.Chat()
    chat_tts.load_models(
        compile=config.runtime_env_vars.compile,
        source="local",
        local_path="./models/ChatTTS",
        device=devices.device,
        dtype=devices.dtype,
        dtype_vocos=devices.dtype_vocos,
        dtype_dvae=devices.dtype_dvae,
        dtype_gpt=devices.dtype_gpt,
        dtype_decoder=devices.dtype_decoder,
    )

    devices.torch_gc()
    logger.info("ChatTTS models loaded")


def initialize_chat_tts():
    with lock:
        if chat_tts is None:
            model_thread = threading.Thread(target=load_chat_tts_in_thread)
            model_thread.start()
            model_thread.join()


def load_chat_tts():
    if chat_tts is None:
        initialize_chat_tts()
    if chat_tts is None:
        raise Exception("Failed to load ChatTTS models")
    return chat_tts


def unload_chat_tts():
    logging.info("Unloading ChatTTS models")
    global chat_tts

    if chat_tts:
        for model_name, model in chat_tts.pretrain_models.items():
            if isinstance(model, torch.nn.Module):
                model.cpu()
                del model
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    gc.collect()
    chat_tts = None
    logger.info("ChatTTS models unloaded")


def reload_chat_tts():
    logging.info("Reloading ChatTTS models")
    unload_chat_tts()
    instance = load_chat_tts()
    logger.info("ChatTTS models reloaded")
    return instance
