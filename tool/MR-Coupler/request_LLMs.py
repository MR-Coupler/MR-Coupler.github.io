import datetime
import os, sys
import time

from util import file_processing,json_processing
import openai

prompt_cache_dir_default = "outputs/requesting_LLMs/"


# setting 
model_symbols = {   
    "WizardCoder-15B-V1.0": "w",
    "gpt-35-turbo": "g3",                       # $0.5/1M tokens(input)
    "gpt-4": "g4",                              # $30/1M tokens(input)
    "gpt-4o": "g4o",                            # $2.5/1M tokens(input)
    "gpt-4o-mini": "g4om",                      # $0.15/1M tokens(input) == ¥1.07/1M tokens(input)
    "o1-mini": "o1m",                            # $0.15/1M tokens(input)
    "o3-mini": "o3m",                           # $1.1/1M tokens(input)
    "o1": "o1",                                 # $15/1M tokens(input)
    "starcoder2-15b-instruct-v0.1": "s2",
    "CodeQwen1.5-7B-Chat": "qw",
    "Meta-Llama-3-8B-Instruct": "ml",
    "deepseek-coder-7b-instruct-v1.5": "dp",
    "deepseek-chat": "dc",                      # ¥0.5/1M tokens(input)     50% off: 00:30~08:30
    "deepseek-reasoner": "dr",                  # ¥1/1M tokens(input)       70% off: 00:30~08:30
    
    "qwen3-coder-flash": "q3cf",                # ¥1/1M tokens(input)
    "qwen3-coder-plus": "q3cp",                 # ¥4/1M tokens(input)
    "qwq-plus": "qwq",                          # ¥1.6/1M tokens(input)
    "claude-3-5-haiku-20241022": "c35h"         # $0.80/1M Token (input), $4.00/1M Token (output)
    
    
}
symbols_model = {   
    "w": "WizardCoder-15B-V1.0",
    "g3": "gpt-35-turbo",
    "g4": "gpt-4",
    "g4o": "gpt-4o",
    "g4om": "gpt-4o-mini",
    "s2": "starcoder2-15b-instruct-v0.1",
    "qw": "CodeQwen1.5-7B-Chat",
    "ml": "Meta-Llama-3-8B-Instruct",
    "dp": "deepseek-coder-7b-instruct-v1.5",
    "dc": "deepseek-chat", # DeepSeek-V3
    "dr": "deepseek-reasoner",
    "qwq": "qwq-plus",
    "q3cf": "qwen3-coder-flash",
    "q3cp": "qwen3-coder-plus",
    "c35h": "claude-3-5-haiku-20241022" # not accessible in China
}

max_tokens = 4096
MaxTimeout=360


def request_deepseekChat(prompt, model="deepseek-chat", promt_id="default", temperature=0, 
                         prompt_results_content_dir=None, system_message="You are a helpful programming assistant", 
                         few_shot_info=[], chat_history=[], include_chat_history=False, return_reasoning_content=False):
    
    # To config
    client = None  # TODO: Initialize your DeepSeek client here

    messages = []
    messages.append({"role": "system", "content": system_message})
    for shot_info in few_shot_info:
        Q = shot_info["Q"]
        A = shot_info["A"]
        messages.append({"role": "user", "content": Q})
        messages.append({"role": "assistant", "content": A})
    if include_chat_history and chat_history: 
        messages.extend(chat_history)
    messages.append({"role": "user", "content": prompt})
    
    if model == "deepseek-chat":
        max_tokens_deepseek = 8192 # max: 8k
    if model == "deepseek-reasoner":
        max_tokens_deepseek = 32000 # max: 64k
  
    response = None
    retries = 3    
    while retries > 0:    
        try: 
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                timeout=MaxTimeout,
                max_tokens=max_tokens_deepseek
            )
            retries = 0
        except Exception as e:    
            if e: 
                print(e)   
                print('LOG, INFO: Timeout error, retrying...')    
                retries -= 1    
                time.sleep(30) # sleep 30 secs    
            else:    
                raise e  
    
    
    content = "" # the content of the response
    reasoning_content = "" # the reasoning of the response
    # Handle the response
    if response:
        # For non-streamed responses, just get the content
        content = response.choices[0].message.content
        if hasattr(response.choices[0].message, 'reasoning_content'):
            reasoning_content = response.choices[0].message.reasoning_content
    else:
        content = "ERROR: No response"

    # Store response
    if prompt_results_content_dir:
        json_processing.write(path=f"{prompt_results_content_dir}/{promt_id}_prompt_messages.md", json_content=messages)
        if content != "ERROR: No response":
            file_processing.write_TXTfile(path=f"{prompt_results_content_dir}/{promt_id}_response_content.md", content=content)
            file_processing.write_TXTfile(path=f"{prompt_results_content_dir}/{promt_id}_reasoning_content.md", content=reasoning_content)
    # BACKUP to default folder
    promt_id_timestamp = f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{model}_{temperature}" 
    dir_promt_id_timestamp = f"{prompt_cache_dir_default}/{promt_id_timestamp}"
    if file_processing.pathExist(dir_promt_id_timestamp) == False:
        file_processing.creatFolder_IfExistPass(dir_promt_id_timestamp)
    json_processing.write(path=f"{dir_promt_id_timestamp}/prompt_messages.md", json_content=messages)
    file_processing.write_TXTfile(path=f"{dir_promt_id_timestamp}/response_content.md", content=content)
    file_processing.write_TXTfile(path=f"{dir_promt_id_timestamp}/reasoning_content.md", content=reasoning_content)
    
    if return_reasoning_content:
        return content, reasoning_content
    else:
        return content


def request_QwQ(prompt, model="qwq-plus", promt_id="default", temperature=0, 
                 prompt_results_content_dir=None, system_message="You are a helpful programming assistant", 
                 few_shot_info=[], chat_history=[], include_chat_history=False, return_reasoning_content=False):

    # TO config: the api key of LLMs
    client = None  # TODO: Initialize your QwQ client here
    
    messages = []
    messages.append({"role": "system", "content": system_message})
    for shot_info in few_shot_info:
        Q = shot_info["Q"]
        A = shot_info["A"]
        messages.append({"role": "user", "content": Q})
        messages.append({"role": "assistant", "content": A})
    if include_chat_history and chat_history: 
        messages.extend(chat_history)
    messages.append({"role": "user", "content": prompt})
    
    
    max_tokens_qwq = 8000 # max: 8k, not setting, becasue don't know
    
    response = None
    retries = 3    
    while retries > 0:    
        try: 
          response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                timeout=MaxTimeout,
                # QwQ 模型仅支持流式输出方式调用
                stream=True
            )
          retries = 0
        except Exception as e:    
         if e: 
             print(e)   
             print('LOG, INGO: Timeout error, retrying...')    
             retries -= 1    
             time.sleep(10) # sleep 10 secs    
         else:    
             raise e  

    reasoning_content = ""  # 定义完整思考过程
    content = ""     # 定义完整回复
    is_answering = False   # 判断是否结束思考过程并开始回复

    # TODO: 处理流式输出 and return content
    for chunk in response:
        # 如果chunk.choices为空，则打印usage
        if not chunk.choices:
            pass
        else:
            delta = chunk.choices[0].delta
            # 打印思考过程
            if hasattr(delta, 'reasoning_content') and delta.reasoning_content != None:
                reasoning_content += delta.reasoning_content
            else:
                # 开始回复
                if delta.content != "" and is_answering is False:
                    is_answering = True
                # 打印回复过程
                content += delta.content

    # Store response
    if prompt_results_content_dir:
        json_processing.write(path=f"{prompt_results_content_dir}/{promt_id}_prompt_messages.md", json_content=messages)
        if content != "ERROR: No response":
            file_processing.write_TXTfile(path=f"{prompt_results_content_dir}/{promt_id}_response_content.md", content=content)
            file_processing.write_TXTfile(path=f"{prompt_results_content_dir}/{promt_id}_reasoning_content.md", content=reasoning_content)
    # BACKUP to default folder
    promt_id_timestamp = f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{model}_{temperature}" 
    dir_promt_id_timestamp = f"{prompt_cache_dir_default}/{promt_id_timestamp}"
    if file_processing.pathExist(dir_promt_id_timestamp) == False:
        file_processing.creatFolder_IfExistPass(dir_promt_id_timestamp)
    json_processing.write(path=f"{dir_promt_id_timestamp}/prompt_messages.md", json_content=messages)
    file_processing.write_TXTfile(path=f"{dir_promt_id_timestamp}/response_content.md", content=content)
    file_processing.write_TXTfile(path=f"{dir_promt_id_timestamp}/reasoning_content.md", content=reasoning_content)
    
    if return_reasoning_content:
        return content, reasoning_content
    else:
        return content
    
# not accessible in China
import anthropic # type: ignore
def request_Claude(prompt, model="claude-3-5-haiku-20241022", promt_id="default", temperature=0, 
                 prompt_results_content_dir=None, system_message="You are a helpful programming assistant", 
                 few_shot_info=[], chat_history=[], include_chat_history=False, return_reasoning_content=False):
    client = anthropic.Anthropic(
        # defaults to os.environ.get("ANTHROPIC_API_KEY")
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
    )
    messages = []
    messages.append({"role": "system", "content": system_message})
    for shot_info in few_shot_info:
        Q = shot_info["Q"]
        A = shot_info["A"]
        messages.append({"role": "user", "content": Q})
        messages.append({"role": "assistant", "content": A})
    if include_chat_history and chat_history: 
        messages.extend(chat_history)
    messages.append({"role": "user", "content": prompt})
  
    response = None
    retries = 3    
    while retries > 0:    
        try: 
            response = client.messages.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens
            )
            retries = 0
        except Exception as e:    
            if e: 
                print(e)   
                print('LOG, INFO: Timeout error, retrying...')    
                retries -= 1    
                time.sleep(30) # sleep 30 secs    
            else:    
                raise e  
    
    
    content = "" # the content of the response
    reasoning_content = "" # the reasoning of the response
    # Handle the response
    if response:
        # For non-streamed responses, just get the content
        content = response.choices[0].message.content
        if hasattr(response.choices[0].message, 'reasoning_content'):
            reasoning_content = response.choices[0].message.reasoning_content
    else:
        content = "ERROR: No response"

    # Store response
    if prompt_results_content_dir:
        json_processing.write(path=f"{prompt_results_content_dir}/{promt_id}_prompt_messages.md", json_content=messages)
        if content != "ERROR: No response":
            file_processing.write_TXTfile(path=f"{prompt_results_content_dir}/{promt_id}_response_content.md", content=content)
            file_processing.write_TXTfile(path=f"{prompt_results_content_dir}/{promt_id}_reasoning_content.md", content=reasoning_content)
    # BACKUP to default folder
    promt_id_timestamp = f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{model}_{temperature}" 
    dir_promt_id_timestamp = f"{prompt_cache_dir_default}/{promt_id_timestamp}"
    if file_processing.pathExist(dir_promt_id_timestamp) == False:
        file_processing.creatFolder_IfExistPass(dir_promt_id_timestamp)
    json_processing.write(path=f"{dir_promt_id_timestamp}/prompt_messages.md", json_content=messages)
    file_processing.write_TXTfile(path=f"{dir_promt_id_timestamp}/response_content.md", content=content)
    file_processing.write_TXTfile(path=f"{dir_promt_id_timestamp}/reasoning_content.md", content=reasoning_content)
    
    if return_reasoning_content:
        return content, reasoning_content
    else:
        return content

def extract_generated_ITrans_class(response_content, promt_id,prompt_generated_ITrans_dir=""):
    code_lines = []
    code_flag = False
    codes = []
    code=[]
    for line in response_content.split("\n"):
      if code_flag==False and line.strip().startswith("```"):
        code_flag = True
        continue
      if code_flag==True and line.strip().startswith("```"):
         code_flag = False
         code = ("\n").join(code_lines)
         codes.append(code)
         code=[]
         code_lines = []
      if code_flag:
        code_lines.append(line)
    

    class_code = ""
    for code in codes:
       if f"class {promt_id}" in code:
          class_code = code
          break
    
    file_processing.write_TXTfile(path = f"{prompt_generated_ITrans_dir}{promt_id}.java", content=class_code)

    return code


def extract_generated_inputs_blocks(response_content):
    code_lines = []
    code_flag = False
    codes = []
    code=[]
    for line in response_content.split("\n"):
      if code_flag==False and line.strip().startswith("```"):
        code_flag = True
        continue
      if code_flag==True and line.strip().startswith("```"):
         code_flag = False
         code = ("\n").join(code_lines)
         codes.append(code)
         code=[]
         code_lines = []
      if code_flag:
        code_lines.append(line)
    return codes

  
def extract_generated_one_inputs_block(response_content):
    code_lines = []
    code_flag = False
    codes = []
    code=[]
    for line in response_content.split("\n"):
      if code_flag==False and line.strip().startswith("```"):
        code_flag = True
        continue
      if code_flag==True and line.strip().startswith("```"):
         code_flag = False
         code = ("\n").join(code_lines)
         codes.append(code)
         code=[]
         code_lines = []
      if code_flag:
        code_lines.append(line)

    return code



def request_LLMs_main(prompt, model, promt_id, temperature, prompt_results_content_dir, system_message, few_shot_info, chat_history, flag_include_chat_history, return_reasoning_content):
    """
    Main function to route requests to appropriate LLM handlers based on model type.
    
    Returns:
        - A tuple (response_content, reasoning_content) if return_reasoning_content is True and supported
        - Just response_content otherwise
    """
    response_content = None
    reasoning_content = None
    if "deepseek-chat" in model.lower():
        response_content = request_deepseekChat(prompt, model, promt_id, temperature, prompt_results_content_dir, system_message, few_shot_info, chat_history, flag_include_chat_history)   
    elif "deepseek-reasoner" in model.lower():
        response_content, reasoning_content = request_deepseekChat(prompt, model, promt_id, temperature, prompt_results_content_dir, system_message, few_shot_info, chat_history, flag_include_chat_history, return_reasoning_content)        
    elif "qwq-plus" in model.lower():
        response_content, reasoning_content = request_QwQ(prompt, model, promt_id, temperature, prompt_results_content_dir, system_message, few_shot_info, chat_history, flag_include_chat_history, return_reasoning_content)    
    elif "qwen3-coder-plus" in model.lower():
        response_content, reasoning_content = request_QwQ(prompt, model, promt_id, temperature, prompt_results_content_dir, system_message, few_shot_info, chat_history, flag_include_chat_history, return_reasoning_content) 
    elif "qwen3-coder-flash" in model.lower():
        response_content, reasoning_content = request_QwQ(prompt, model, promt_id, temperature, prompt_results_content_dir, system_message, few_shot_info, chat_history, flag_include_chat_history, return_reasoning_content) 
    if return_reasoning_content:    
        return response_content, reasoning_content
    else:
        return response_content






