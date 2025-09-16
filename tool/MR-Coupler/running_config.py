
import time
from bugrevealingmrgen.request_LLMs import model_symbols, symbols_model

""" run tool config: latest """
Setting = { # revise=0
    "taskset": "all" , # reproduced bugs, 
    "targetCUTv": "latest", # "BUGGY": buggy&fixed, "latest": latest version
    "Pit": False,
    "only2MI": True, # True: only subjects where 2 MI invovled
    "afterCF": False, # True: only subjects after CF date
    "date": "250821", #
    "model": f"{symbols_model['dr']}",  # q3cf, dr, dc, g4om             q3cp, qwq
    "Prompt_template":"5", # 0, 1 , 1-2, 2, 2-1, 4: one-by-one only paired method, M: manually crafted prompt (default 2-1), when baseline: 0/1,  "commentFaultyCode": False
    
    "number_of_revise": 0, # must run 0 first, and then, 1 2 3
    "number_of_tests_per_MR": 1, # 1: when number_of_revise=0, or 10: when number_of_revise>0 (the last version)
    "commentFaultyCode": False, # default: True -> post_processing,
    
    "number_of_MR_per_request": "three", # by default: "five", or "one"
    "number_of_request": 3,
    "number_of_shot":0,
    "temperature": 0.2,
    
    "paired_method_info": "similarMTC", # “”: ground truth, similarMTC: similar MTCs
    "pair_method_methodology": "P", # 1-1, "S"/"2": one-by-one MR (similar MTC driven), "P"/"2-1": one-by-one MR (pattern driven driven)
    "strong_pattern_only_flag": False, # or False # only suggest methods from strong patterns
    "RAG_similar_MUTs": False, # to save running time, when similar MUTs' MTCs are not used, disable it 
    "code_refactoring": "", # by default "". other "RefactorCode" == True
    "mutateMRs": "", # by default "". other "mutateMRs" == True
    
    "result_collect": True, 
    "MRValidation": True,
    "parallel": False,
    "one_by_one": False, 
    "overwritePreviousPIT": False, # default: False, to save time
    "overwritePreviousMRScout": False, # default: False, to save time
    "UseGroundTruthMTCclass":False,   # default: False, just used to reproduce GT MTC
    "overwritePreviousPromptResults":False,
    "overwritePreviousEvaluationResults":True,
    "task_type": "direct_prompt", # direct_prompt: used for folder_name in the original poj.
    "timeout": 200, # for MRScout to run

    "MRScout": True, # 
    "MRScout_plus": True, # 
    "skipCompileIfExist": False, 
    "skipExecuteIfExist": False, 
    "parallel_size": 30, # default: 18, peek: 35  .... # qwq too slow, may just 100 ... 
    "index_of_request": 0,
}


OUTPUT_DIR ='outputs/'
all_evaluation_result_of_generated_MRs_function_path = f"{OUTPUT_DIR}generated_MRs/validation_generated_MRs_{Setting['date']}_{Setting['model']}_T{Setting['Prompt_template']}_Shot{Setting['number_of_shot']}_Request{Setting['number_of_request']}_Temprature{Setting['temperature']}_Rev{Setting['number_of_revise']}_Version{Setting['targetCUTv']}_Tests{Setting['number_of_tests_per_MR']}_commentFaultyCode{Setting['commentFaultyCode']}_{Setting['code_refactoring']}_{Setting['mutateMRs']}_pairedMethod{Setting['paired_method_info']}{Setting['pair_method_methodology']}_afterCF{Setting['afterCF']}_MRValidation{Setting['MRValidation']}.json"

if Setting.get("no-revision-ablation",False) == True:
    all_evaluation_result_of_generated_MRs_function_path = all_evaluation_result_of_generated_MRs_function_path.replace(".json", "_no-revision-ablation.json")
