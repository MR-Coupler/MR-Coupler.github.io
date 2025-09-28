"""
"""
import json
import multiprocessing
import os, sys
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from util import file_processing,json_processing, java_parser, java_file_processing, config

from bugrevealingmrgen import request_LLMs, running_config
from bugrevealingmrgen.request_GitHub import GitHubIssueFetcher
from bugrevealingmrgen.util import java_file_process_local

from codebleu import calc_codebleu
import re, datetime
import javalang

inputTrans_poj_dir = config.ROOT_DIR
GT_ITrans_w_dir = config.GT_ITRANS_W_DIR
GT_ITrans_wo_dir = config.GT_ITRANS_WO_DIR
benchmark_src_dir = config.BENCHMARK_SRC_DIR

GT_CLASS_SUFFIX = config.GT_CLASS_SUFFIX
HARDCODED_CLASS_SUFFIX = config.HARDCODED_CLASS_SUFFIX
VALID_INPUT_CLASS_SUFFIX = config.VALID_INPUT_CLASS_SUFFIX
FEW_SHOT_BASE_DIR = config.FEW_SHOT_BASE_DIR

codeTransform_control_template_path = f"prompt_templates/codeTransform_control.md"
codeTransform_control_template = file_processing.read_TXTfile(codeTransform_control_template_path)
codeTransform_renaming_template_path = f"prompt_templates/codeTransform_renaming.md"
codeTransform_renaming_template = file_processing.read_TXTfile(codeTransform_renaming_template_path)

mutateMRs_template_path = f"prompt_templates/mutate_MRs.md"
mutateMRs_template = file_processing.read_TXTfile(mutateMRs_template_path)


Template0_path = f"prompt_templates/template0.md"
Template0 = file_processing.read_TXTfile(Template0_path)
Template0_1_path = f"prompt_templates/template0-1.md"
Template0_1 = file_processing.read_TXTfile(Template0_1_path)
Template1_path = f"prompt_templates/template1.md"
Template1 = file_processing.read_TXTfile(Template1_path)
Template1_2_path = f"prompt_templates/template1-2.md"
Template1_2 = file_processing.read_TXTfile(Template1_2_path)
Template2_path = f"prompt_templates/template2.md"
Template2 = file_processing.read_TXTfile(Template2_path)
Template2_2_path = f"prompt_templates/template2-2.md"
Template2_2 = file_processing.read_TXTfile(Template2_2_path)
Template2_1_path = f"prompt_templates/template2-1.md"
Template2_1 = file_processing.read_TXTfile(Template2_1_path)
Template3_path = f"prompt_templates/template3.md"
Template3 = file_processing.read_TXTfile(Template3_path)
Template4_path = f"prompt_templates/template4.md"
Template4 = file_processing.read_TXTfile(Template4_path)
Template5_path = f"prompt_templates/template5.md"
Template5 = file_processing.read_TXTfile(Template5_path)
Templates = {
    "0": Template0,
    "0-1": Template0_1,
    "1": Template1,
    "1-2": Template1_2,
    "2": Template2,
    "2-1": Template2_1,
    "2-2": Template2_2,
    "3": Template3,
    "4": Template4,
    "5": Template5,
    "M": Template2_1,
} 

InputGenTemplate0_path = f"prompt_templates/inputGenTemplate0.md"



def generate_prompt_from_profile(input_generator):
    """
        direct_prompt
    """
    Setting = input_generator.Setting
    MTC_FQN = input_generator.MTC_FQN
    MTC_item = input_generator.MTC_item
    index_of_request = input_generator.index_of_request
    Crafted_prompts_dir = input_generator.Crafted_prompts_dir
    target_methods_FQN = input_generator.target_methods_FQN
    target_methods_FQS = input_generator.target_methods_FQS
    prompt = input_generator.prompt_template
    number_of_candidate_per_request = "five" 
    if "number_of_MR_per_request" in Setting and Setting["number_of_MR_per_request"] != "":
        number_of_candidate_per_request = Setting["number_of_MR_per_request"]
    test_file_path =input_generator.path_MTC_version_testclass_file
    test_class_name = test_file_path.split("/")[-1].replace(".java", "")
    MTC_test_method_name = MTC_FQN.split(".")[-1]
    invoked_methods_FQS = input_generator.invoked_methods_FQS.copy()   
    dir_MTCFQN_VERSION_BUGREV = input_generator.dir_MTCFQN_VERSION_BUGREV
    MTC_version_poj_dir = input_generator.MTC_version_poj_dir
    invoked_package_FQN = input_generator.invoked_package_FQN
    
    task_symbol = input_generator.task_symbol
    context_data_for_current_task_symbol = input_generator.context_data_for_current_task_symbol
    
    owner_name = input_generator.owner_name
    poj_name = input_generator.poj_name
    issueID = input_generator.issueID

    pre_revision_evaluation_result_summary = input_generator.pre_revision_evaluation_result_summary
    chat_history = input_generator.chat_history
    compilation_log_content = input_generator.compilation_log_content
    execution_log_content = input_generator.execution_log_content
    
    poj_dir = MTC_version_poj_dir
    
    target_methods_FQS_return_type = {}# key: method_FQS, value: return_type
    
    
    #     invoked_methods_FQS = []
        

    """ get the system message """
    system_message = ""
    flag_is_system_message = False
    for line in prompt.split("\n"):
        if "<SYSTEM MESSAGE: END>" in line:
            flag_is_system_message = False
        if flag_is_system_message:
            system_message += line + "\n"
        if "<SYSTEM MESSAGE: START>" in line:
            flag_is_system_message = True

    """ get: the body of MUT & METHOD CONTEXT """
    # given the poj dir and FQS of the MUT, to get the test file path 
    declarations_of_focal_methods  = []
    skeleton_of_classes = []
    target_CUTs_pathes = []
    target_CUTs_FQNs = []
    method_declaration = ""
    target_methodsFQN_CUTpaths = {}
    # for method_FQS in invoked_methods_FQS:
    # for method_FQS in target_methods_FQS:
    for method_FQS in target_methods_FQN: 
        method_name = method_FQS.split("(")[0].split(".")[-1]
        class_path = java_file_processing.find_class_file_path_by_methodFQS(poj_dir, method_FQS)
        print( f"1 method_name: {method_name}, class_path: {class_path}, poj_dir: {poj_dir} " )
        if class_path== None: 
            class_path = java_file_processing.find_class_file_path_by_methodFQS(MTC_item["poj_dir"], method_FQS)
            print( f"1 method_name: {method_name}, class_path: {class_path}, poj_dir: {MTC_item['poj_dir']} " )
        if class_path==None: continue
        print(f"LOG:method_FQS: {method_FQS} class_path: {class_path}")
        target_methodsFQN_CUTpaths[method_FQS.split("(")[0]] = class_path
        
        # get the body of MUT
        # try1: 
        return_type = "NA"
        method_name_simple = method_name.split(".")[-1]
        method_paras = method_FQS.split("(")[-1].split(")")[0].split(",")
        method_paras_simple = [ ele.split(".")[-1] for ele in method_paras]
        method_signature_formated = f"{return_type}:{method_name_simple}:{','.join(method_paras_simple)}" # "String:setPackages:String"
        print(f"LOG: method_FQS: {method_FQS}, method_signature_formated: {method_signature_formated}, class_path: {class_path}")
        method_declaration = java_file_processing.getMethodBasedOnMethodSignature(class_path, method_signature_formated) 
        # option2: when the method_FQS is the signaure, rather then  method_FQN .... 
        # method_name_simple, parameter_simple_types = java_file_processing.get_simpleMethodName_simpleParameterTypes_from_methodFQS(method_FQS)
        # method_signature_formated = f"{return_type}:{method_name_simple}:{parameter_simple_types}
        print(f"LOG: method_declaration: {method_declaration}")
        # try2: as the backup
        method_declaration = java_parser.get_method_body_or_related_class_field(file_path=class_path, method_name=method_name, function="getMethodsSameName") # DONE: get_method_body_or_related_class_field should include constructor!!!
        
        if len(method_declaration) < 15:
            print(f"LOG: len(method_declaration) < 15: {method_declaration}")
        if method_declaration not in declarations_of_focal_methods:
            declarations_of_focal_methods.append(method_declaration)
        """ get: METHOD CONTEXT """
        # 1. the skeleton of CUT
        class_skeleton = java_file_processing.get_skeleton_of_class(class_path) # option 2, method body is replaced by "..."
        if class_skeleton == None: 
            print(f"LOG: class_skeleton == None: {class_path}, using option 1")
            class_skeleton = java_parser.get_skeleton_of_class(file_path=class_path, function="extractClassSkeleton") # option 1, method body is replaced by "'"
        if class_skeleton not in skeleton_of_classes:
            skeleton_of_classes.append(class_skeleton)
        if file_processing.pathExist(class_path):
            target_CUTs_pathes.append(class_path)
    # based on the target_CUTs_pathes, to get the fully_qualified_names of the classes
    target_CUTs_FQNs = java_file_processing.get_class_fully_qualified_names(target_CUTs_pathes)
    
    """ paired method info """
    # invoked_methods_FQS is paired method info
    similar_MUTb_MTC_code = ""
    if Setting["paired_method_info"]=="":
        # invoked_methods_FQS = invoked_methods_FQS
        pass
    elif Setting["paired_method_info"]=="similarMTC":
        
        all_suggested_methods = []
        FQN_name = method_FQS.split("(")[0].split(".")[-1]
        FQN_prefix = method_FQS.split(f".{FQN_name}")[0]
        if Setting["pair_method_methodology"] in ["S","2","P","2-1"]:
            suggested_methods = []
            suggested_methods = context_data_for_current_task_symbol["suggested_methods"]
            similar_MUTb = context_data_for_current_task_symbol["similar_MUTb"][0] 
            if hasattr(similar_MUTb, "metadata"):
                similar_MUTb_MTC_code = similar_MUTb.metadata["MTC_code"]
            elif isinstance(similar_MUTb, list):
                similar_MUTb = similar_MUTb[0] 
            else:
                print(f"DEBUG: what issimilar_MUTb: {similar_MUTb}")
            
            if "itself" in str(suggested_methods):
                suggested_methods = []
                for ele in target_methods_FQS:
                    if FQN_prefix not in ele: suggested_methods.append(ele)
                    else: suggested_methods.append(ele.replace(f"{FQN_prefix}.", ""))

            all_suggested_methods.extend([ f"{FQN_prefix}.{method}" for method in suggested_methods if FQN_prefix not in method])
            invoked_methods_FQS = list(set(all_suggested_methods))
            print(f"LOG: invoked_methods_FQS: {invoked_methods_FQS}")
        
        # the same setting of 1, but new implementation
        if Setting["pair_method_methodology"] == "1-1":
            pattern_suggested_MUTbs = input_generator.context_data.pattern_suggested_MUTbs
            pattern_suggested_pairMethods = input_generator.context_data.pattern_suggested_pairMethods
            ordered_similar_MUTsB_and_patterns = input_generator.context_data.ordered_similar_MUTsB_and_patterns
            
            for similar_MUTsB_and_pattern in ordered_similar_MUTsB_and_patterns[:5]:
                pattern_type = similar_MUTsB_and_pattern["pattern"]["paired_patterns"][0]["pattern_type"] 
                if pattern_type == 4.3: continue # 4.3: skip
                if pattern_type not in pattern_suggested_pairMethods:
                    print(f"LOG: pattern_type not in pattern_suggested_pairMethods, pattern_type:{pattern_type}, MTC_FQN:{MTC_FQN}")
                    continue
                suggested_methods = pattern_suggested_pairMethods[pattern_type]
                
                all_suggested_methods.extend([ f"{FQN_prefix}.{method}" for method in suggested_methods])
            invoked_methods_FQS = list(set(all_suggested_methods))[:5]
            print(f"LOG: invoked_methods_FQS: {invoked_methods_FQS}")
        
        # methodology: (baseline) 1 MUTa -> 5 * similar MUTsB (with pattern) -> n* suggested methods (for pair) [just get the first 5 suggested methods]
        if Setting["pair_method_methodology"] == "1":
            # if running_config.Setting["paired_method_info"] == "similarMTC":
            from bugrevealingmrgen.MTCDB import query_DB
            for method_FQS in target_methods_FQS:
                if method_FQS.split("(")[0] not in target_methodsFQN_CUTpaths: continue
                
                # get the return type of the method
                return_type = ""
                if method_FQS not in target_methods_FQS_return_type:
                    """ get the precise return type of the method """
                    # option1
                    class_path_, MUT_code, return_type = java_file_processing.get_classPath_methodCode_returnType(method_FQS, poj_dir)
                    
                    target_methods_FQS_return_type[method_FQS] = return_type
                else:
                    return_type = target_methods_FQS_return_type[method_FQS]
                
                path_CUT = target_methodsFQN_CUTpaths[method_FQS.split("(")[0]]
                print(f"LOG: invocation of query_DB.get_suggested_MUTs: return_type method_FQS {return_type} {method_FQS}, MTC_FQN {MTC_FQN}, path_CUT {path_CUT}")
                suggested_methods = query_DB.get_suggested_MUTs(f"{return_type} {method_FQS}", MTC_FQN, path_CUT)
                
                all_suggested_methods.extend([ f"{FQN_prefix}.{method}" for method in suggested_methods])
            invoked_methods_FQS = list(set(all_suggested_methods))[:5] 
            print(f"LOG: invoked_methods_FQS: {invoked_methods_FQS}")
        
        
    else:
        invoked_methods_FQS = []

    """ get <EXISTING TESTS> """
    test_file_content = file_processing.read_TXTfile(test_file_path)
    # delete existing MTC (防止泄题了)
    test_file_content = java_file_processing.remove_test_cases(test_file_path, [MTC_test_method_name])
    # just keep relevant tests, otherwise the information is too dense.
    print(f"LOG: keep_relevant_tests: {target_methods_FQN}, {invoked_methods_FQS}, {test_file_path}")
    # should be target_methods_FQN + paired method info
    # test_file_content = java_file_processing.keep_relevant_tests(test_file_content, list(set(target_methods_FQN + invoked_methods_FQS)))
    test_file_content = keep_relevant_tests(test_file_content, list(set(target_methods_FQN + invoked_methods_FQS)))
    # print(f"LOG: after keep_relevant_tests: {test_file_content}")
    
    
    """ get # <SUGGESTED METHODS> """    
    # invoked_methods_FQS -> invoked_methods_names
    invoked_methods_names = [ ele.split("(")[0].split(".")[-1] for ele in invoked_methods_FQS ]
    invoked_methods_names = list(set(invoked_methods_names)) # remove duplicates
    invoked_methods_signatures = []
    for method_FQS in invoked_methods_FQS:
        for method_name in invoked_methods_names:
            if f".{method_name}(" in method_FQS:
                invoked_methods_signatures.append( f"{method_name}(" + method_FQS.split(f".{method_name}(")[-1])
    invoked_methods_signatures = list(set(invoked_methods_signatures)) # remove duplicates

    declarations_of_invoked_methods = []
    for method_FQS in list(set(invoked_methods_FQS)): # remove duplicates
        method_name = method_FQS.split("(")[0].split(".")[-1]
        class_path = java_file_processing.find_class_file_path_by_methodFQS(poj_dir, method_FQS)
        print( f"2 method_name: {method_name}, class_path: {class_path}, poj_dir: {poj_dir} " )
        if class_path== None:
            class_path = java_file_processing.find_class_file_path_by_methodFQS(MTC_item["poj_dir"], method_FQS)
            print( f"2 method_name: {method_name}, class_path: {class_path}, poj_dir: {MTC_item['poj_dir']} " )
        
        """  get the body of MUT """
        if class_path==None: continue
        # try1: 
        return_type = "NA"
        # method_name_simple = method_name.split(".")[-1]
        # method_paras = method_FQS.split("(")[-1].split(")")[0].split(",")
        # method_paras_simple = [ ele.split(".")[-1] for ele in method_paras]
        # method_signature_formated = f"{return_type}:{method_name_simple}:{','.join(method_paras_simple)}" # "String:setPackages:String"
        method_name_simple, parameter_simple_types = java_file_processing.get_simpleMethodName_simpleParameterTypes_from_methodFQS(method_FQS)
        method_signature_formated = f"{return_type}:{method_name_simple}:{parameter_simple_types}" # "String:setPackages:String"
        print(f"LOG: method_FQS: {method_FQS}, method_signature_formated: {method_signature_formated}, class_path: {class_path}")
        method_declaration = java_file_processing.getMethodBasedOnMethodSignature(class_path, method_signature_formated) 
        # print(f"LOG: method_declaration: {method_declaration}")
        # try2: as the backup
        if method_declaration == "" or method_declaration==None:
            method_declaration = java_parser.get_method_body_or_related_class_field(file_path=class_path, method_name=method_name, function="getMethod") # TODO: get_method_body_or_related_class_field should include constructor!!! 
        if method_declaration not in declarations_of_invoked_methods:
            declarations_of_invoked_methods.append(method_declaration)

    
    """ get: REQUIRED DELIVERABLE """
    genreated_test_class_name = f"{test_class_name}_{MTC_test_method_name}_{task_symbol}_{index_of_request}"
    promt_id = genreated_test_class_name

    """ fine tune the prompt """
    if len(declarations_of_focal_methods)<=1 and  "empty empty() {" in ("\n").join(declarations_of_focal_methods):
        declarations_of_focal_methods = [ f'method name: {ele.split(".")[-1]}' for ele in target_methods_FQN ]
        pass
    if len(declarations_of_invoked_methods)<=1 and "empty empty() {" in ("\n").join(declarations_of_invoked_methods):
        declarations_of_invoked_methods = [ f"* {ele}" for ele in invoked_methods_signatures]
        pass
    
    """ get:  ISSUE INFO"""
    issue_info_dict = GitHubIssueFetcher.get_issue_info(owner_name, poj_name, issueID)
    readable_issue_info = GitHubIssueFetcher.get_readable_issue_titleBodyComments(issue_info_dict)
    issue_info = f"*Title*\n{readable_issue_info['title']}\n\n*Body*\n{readable_issue_info['body']}\n\n*Comments*\n{readable_issue_info['comments']}"
    
    FOCAL_METHOD = ("\n").join(declarations_of_focal_methods)
    SUGGESTED_METHODS = ("\n").join(declarations_of_invoked_methods)
    SUGGESTED_METHODS = SUGGESTED_METHODS.replace(FOCAL_METHOD, "")
    
    """ before replace, do code refactoring """
    if Setting["code_refactoring"] == "RefactorCode":
        prompt_messages_path = f"{input_generator.prompt_code_refactoring_dir}{promt_id}_prompt_messages_SUGGESTED_METHODS.md"
        response_content_path = f"{input_generator.prompt_code_refactoring_dir}{promt_id}_response_content_SUGGESTED_METHODS.md"
        prompt_content = codeTransform_control_template.replace("{Java_Code_for_Refactoring}", SUGGESTED_METHODS)
        if file_processing.pathExist(prompt_messages_path):
            refactored_SUGGESTED_METHODS = file_processing.read_TXTfile(response_content_path)
        else:
            refactored_SUGGESTED_METHODS = request_LLMs.request_deepseekChat(
                prompt= prompt_content,
                model="deepseek-chat",
                temperature=0
            )
            file_processing.write_TXTfile(path = response_content_path, content=refactored_SUGGESTED_METHODS)
        file_processing.write_TXTfile(path = prompt_messages_path, content=prompt_content)
        
        prompt_messages_path = f"{input_generator.prompt_code_refactoring_dir}{promt_id}_prompt_messages_FOCAL_METHOD.md"
        response_content_path = f"{input_generator.prompt_code_refactoring_dir}{promt_id}_response_content_FOCAL_METHOD.md"
        prompt_content2 = codeTransform_control_template.replace("{Java_Code_for_Refactoring}", FOCAL_METHOD)
        if file_processing.pathExist(prompt_messages_path):
            refactored_FOCAL_METHOD = file_processing.read_TXTfile(response_content_path)
        else:
            refactored_FOCAL_METHOD = request_LLMs.request_deepseekChat(
                prompt= prompt_content2,
                model="deepseek-chat",
                temperature=0)
            file_processing.write_TXTfile(path = response_content_path, content=refactored_FOCAL_METHOD)
        file_processing.write_TXTfile(path = prompt_messages_path, content=prompt_content2)
        
        SUGGESTED_METHODS = refactored_SUGGESTED_METHODS
        FOCAL_METHOD = refactored_FOCAL_METHOD

    """ functiona relevance """
    # <FUNCTIONAL REVELANCE>
    context_data_for_current_task_symbol = input_generator.context_data_for_current_task_symbol
    functional_revelance_info = ""
    if context_data_for_current_task_symbol != None:
        pattern_info = context_data_for_current_task_symbol["pattern_info"]
        
        functional_revelance_info = ""
        signature_info = ""
        MethodInvocation_info = ""
        state_access_info = ""
        for feature_name, feature_info in pattern_info.items():
            if "Sig1" in pattern_info.keys():
                feature_info = pattern_info["Sig1"]
                signature_info += f"\t* {feature_info}\n"
                break # don't need other info
            if feature_name == "Sig4.3": continue
            
            if feature_name.startswith("Sig"):
                signature_info += f"\t* {feature_info}\n"
            elif feature_name.startswith("MI"): # MethodInvocation
                MethodInvocation_info += f"\t* {feature_info}\n"
            elif feature_name.startswith("State"):
                state_access_info += f"\t* {feature_info}\n"
        functional_revelance_info += "1. Method Signature – reflects the method’s intention: \n" + signature_info
        functional_revelance_info += "2. Method Invocation  – characterizes functional behavior through invoked functions: \n" + MethodInvocation_info
        functional_revelance_info += "3. State Access/Update – characterizes functional behavior based on accessed or updated class fields or object states: \n" + state_access_info


    """ replace CUT   """
    CUT = ("\n\n").join(skeleton_of_classes)
    EXISTING_TESTS = test_file_content
    
    if len(FOCAL_METHOD.replace("\n", "").strip(" ")) <= 10 or len(FOCAL_METHOD.split("\n")) ==1:
        # give the MUT signature
        sigatures_str = "\n".join([f"* {ele}" for ele in target_methods_FQS])
        FOCAL_METHOD = f"Method signature:\n{sigatures_str}"
    if len(SUGGESTED_METHODS.replace("\n", "").strip(" ")) <= 10 or len(SUGGESTED_METHODS.split("\n")) ==1:
        # give the invoked methods signatures
        sigatures_str = "\n".join([f"* {ele}" for ele in invoked_methods_FQS])
        SUGGESTED_METHODS = f"Method signature:\n{sigatures_str}"
    
    prompt = prompt.replace("<FOCAL METHOD>", FOCAL_METHOD) 
    prompt = prompt.replace(f"# Task Description\n<SYSTEM MESSAGE: START>\n{system_message}<SYSTEM MESSAGE: END>", "")
    prompt = prompt.replace("<N>", number_of_candidate_per_request)
    prompt = prompt.replace("$TestClassName$", genreated_test_class_name)
    prompt = prompt.replace("<METHOD CONTEXT>", CUT)  
    prompt = prompt.replace("<EXISTING TESTS>", EXISTING_TESTS)  
    # <SUGGESTED METHODS>
    # prompt = prompt.replace("<SUGGESTED METHODS>", "* " + ("\n* ").join(invoked_methods_signatures)) 
    prompt = prompt.replace("<SUGGESTED METHODS>", SUGGESTED_METHODS) 
    prompt = prompt.replace("<MR-ENCODED TESTS>", mr_encoded_tests)
    prompt = prompt.replace("<ISSUE INFO>", issue_info)
    prompt = prompt.replace("<FUNCTIONAL RELEVANCE>", functional_revelance_info)


    
    

    """ for self_revise """ # flag_include_chat_history: chat_history already prepared in preparation_for_LLMSelfRevision
    
    if Setting["number_of_revise"] > 0 and pre_revision_evaluation_result_summary == "uncompiled":
        # in case some log too long... it may overflow the prompt.
        if compilation_log_content: compilation_log_content = compilation_log_content[:6000]
    
        prompt = f"The previously generated test classes failed to compile. Below is the compilation log:\n\
            ```\n\
            {compilation_log_content}\n\
            ```\n\
            \nPlease revise the code to fix any compilation errors and provide only the corrected version of the entire test class.\
            "

    elif Setting["number_of_revise"] > 0 and pre_revision_evaluation_result_summary == "non-executable":
        # in case some log too long... it may overflow the prompt.
        if execution_log_content: execution_log_content = execution_log_content[:6000]
        prompt = f"The previously generated test classes failed to execute. Below is the execution log:\n\
            ```\n\
            {execution_log_content}\n\
            ```\n\
            \nPlease revise the code to fix any execution errors and provide only the corrected version of the entire test class.\
            "
            
    """ for applying MRs into more test inputs """
    number_of_tests_per_MR = Setting["number_of_tests_per_MR"]
    prompt_apply_MRs_w_more_inputs = file_processing.read_TXTfile(InputGenTemplate0_path)
    prompt_apply_MRs_w_more_inputs = prompt_apply_MRs_w_more_inputs.replace("<M>", str(number_of_tests_per_MR))
    
    
    """ before replace, do code refactoring: renaming """
    OriginalNames_newNames_dict = {}
    if Setting["code_refactoring"] == "RefactorCode":
        # global names replacement
        prompt_messages_path = f"{input_generator.prompt_code_refactoring_dir}{promt_id}_prompt_messages_names_replacement.md"
        response_content_path = f"{input_generator.prompt_code_refactoring_dir}{promt_id}_response_content_names_replacement.md"
        response_content_path_updated_json = response_content_path.replace(".md","_updated.json")
        prompt_content = codeTransform_renaming_template.replace("{Java_Code_for_Refactoring}", FOCAL_METHOD)
        if file_processing.pathExist(response_content_path_updated_json):
            OriginalNames_newNames_dict = json_processing.read(response_content_path_updated_json)
        else:
            OriginalNames_newNames_dict_str = request_LLMs.request_deepseekChat(
                prompt= prompt_content,
                model="deepseek-chat",
                temperature=0
            )
            OriginalNames_newNames_dict = json.loads(OriginalNames_newNames_dict_str.replace("```json", "").replace("```", ""))
            file_processing.write_TXTfile(path = response_content_path, content=OriginalNames_newNames_dict_str)
        file_processing.write_TXTfile(path = prompt_messages_path, content=prompt_content)
        # update: if key is the substring of another key/value, remove the shorter one
        # also, if the value is the substring of another key/value, remove the shorter one
        items_to_remove = set()
        for original_name, new_name in sorted(list(OriginalNames_newNames_dict.items())):
            for original_name2, new_name2 in sorted(list(OriginalNames_newNames_dict.items())):
                if original_name != original_name2:  # Don't compare with self
                    if original_name in original_name2:
                        items_to_remove.add(original_name)
                    if new_name in new_name2:
                        items_to_remove.add(original_name)
        # Remove items after iteration
        for item in items_to_remove:
            OriginalNames_newNames_dict.pop(item)
        json_processing.write(OriginalNames_newNames_dict, response_content_path_updated_json)
        
        for original_name, new_name in OriginalNames_newNames_dict.items():
            prompt = prompt.replace(original_name, new_name)

    """ write prompt """
    prompt = prompt.strip("\n")
    prompt_path = f"{Crafted_prompts_dir}{genreated_test_class_name}.md"
    system_message_path = prompt_path.replace(".md",".system_message")
    if Setting["Prompt_template"]=="M" and file_processing.pathExist(prompt_path):
        prompt = file_processing.read_TXTfile(prompt_path)
        system_message = file_processing.read_TXTfile(system_message_path)
    else:
        file_processing.write_TXTfile(path = prompt_path, content=prompt)
        file_processing.write_TXTfile(path = system_message_path, content=system_message)
    print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), f"LOG: END, generate_prompt_from_profile: {MTC_item['FQS']}")
    
    """ update input_generator """
    input_generator.prompt_apply_MRs_w_more_inputs = prompt_apply_MRs_w_more_inputs
    input_generator.prompt_system_message = system_message
    input_generator.prompt_path = prompt_path
    input_generator.promt_id = promt_id
    input_generator.promt_content = prompt
    input_generator.genreated_test_class_name = genreated_test_class_name
    input_generator.genreated_test_class_FQN =  f"{invoked_package_FQN}.{genreated_test_class_name}"
    input_generator.target_CUTs_FQNs = target_CUTs_FQNs
    input_generator.target_CUTs_pathes = target_CUTs_pathes
    input_generator.OriginalNames_newNames_dict = OriginalNames_newNames_dict
    
    input_generator.prompt_EXISTING_TESTS = EXISTING_TESTS
    input_generator.prompt_CUT = CUT
    
    input_generator.suggested_methods_FQS = invoked_methods_FQS
    
    


    return input_generator


def keep_relevant_tests(test_file_content, target_methods_FQS):
    """
    Filter and keep the most relevant test cases from the test file content.
    
    Args:
        test_file_content (str): Content of the test file
        target_methods_FQS (list): List of fully qualified names of target methods
        
    Returns:
        str: Filtered test file content containing only relevant test cases
    """
    # Extract target method names and parameter types
    target_info = []
    for fqn in target_methods_FQS:
        method_sig = fqn.split("(")[0]
        method_name = method_sig.split(".")[-1]
        param_types = []
        if "(" in fqn and ")" in fqn:
            params = fqn.split("(")[1].split(")")[0]
            if params:
                param_types = [p.split(" ")[0].strip() for p in params.split(",")]
        target_info.append({
            "name": method_name,
            "params": param_types
        })
    
    # Split test file into individual test methods
    lines = test_file_content.split("\n")
    test_methods = []
    current_method = []
    in_method = False
    method_name = ""
    brace_count = 0
    
    for line in lines:
        stripped_line = line.strip()
        # Start of a test method
        if "@Test" in line or (not in_method and "test" in line.lower() and "public" in line.lower() and "void" in line.lower()):
            if current_method and brace_count == 0:
                test_methods.append({"name": method_name, "content": "\n".join(current_method)})
            current_method = []
            in_method = True
            method_name = line if "@Test" not in line else ""
            current_method.append(line)
            if "{" in line:
                brace_count += line.count("{")
        # Inside a method
        elif in_method:
            current_method.append(line)
            if "{" in line:
                brace_count += line.count("{")
            if "}" in line:
                brace_count -= line.count("}")
            if not method_name and "void" in line:
                method_name = line
            # End of method when braces balance
            if brace_count == 0 and stripped_line == "}":
                test_methods.append({"name": method_name, "content": "\n".join(current_method)})
                current_method = []
                in_method = False
                method_name = ""
            
    # Score each test method based on relevance
    scored_methods = []
    for test_method in test_methods:
        score = 0
        content = test_method["content"].lower()
        
        # 1. Check for methods with similar names
        for target in target_info:
            if target["name"].lower() in content:
                score += 3  # High priority for name matches
            # Check for similar names (e.g., testAdd vs add)
            elif any(w for w in content.split() if target["name"].lower() in w):
                score += 2
                
        # 2. Check for parameter type usage
        for target in target_info:
            for param_type in target["params"]:
                param_base = param_type.split(".")[-1].lower()
                if param_base in content:
                    score += 2  # Medium priority for parameter type matches
                    
        # 3. Additional relevance factors
        # Check for assertion patterns
        if "assert" in content:
            score += 1
            
        # Check for error handling
        if "exception" in content or "throws" in content:
            score += 1
            
        # Check for setup/initialization patterns
        if "new " in content:
            score += 1
            
        scored_methods.append((score, test_method["content"]))
    
    # Sort by score and take top N most relevant tests
    scored_methods.sort(reverse=True)
    MAX_TESTS = 5  # Limit to 5 most relevant tests
    
    # If there are no scored methods but there are test methods, include all test methods up to MAX_TESTS
    if not scored_methods and test_methods:
        selected_methods = [method["content"] for method in test_methods[:MAX_TESTS]]
    else:
        selected_methods = [method for score, method in scored_methods[:MAX_TESTS]]
    
    # If no methods were selected but we have test methods, include them all
    if not selected_methods and test_methods:
        selected_methods = [method["content"] for method in test_methods[:MAX_TESTS]]
    
    # Reconstruct file content with selected methods
    # Keep the class structure and imports
    header = []
    class_start = False
    for line in lines:
        if "class" in line and "{" in line:
            class_start = True
            header.append(line)
            break
        header.append(line)
    
    # Add any class-level fields or helper methods that appear before the first test
    class_fields = []
    for line in lines[len(header):]:
        if "@Test" in line:
            break
        if line.strip() and not line.strip().startswith("//"):
            class_fields.append(line)
    
    # Combine everything
    result = "\n".join(header) + "\n"
    if class_fields:
        result += "\n".join(class_fields) + "\n"
    result += "\n".join(selected_methods)
    result += "\n}"  # Close the class
    
    return result

# def get_few_shot_info():
#     # 1. get this MTC
#     pre_processed_MTC_h_code_this = get_pre_processed_MTC_h_code(trans_generator.MTC_item)
#     FQS_testMethos_this = trans_generator.MTC_item['FQS_testMethos']

#     # 2. get all MTCs with GT (w and w/o)
#     """ the base to choose few shot """ 
#     all_GT_MTCs = Profile_GT_MTCs_wo_IT + Profile_GT_MTCs_w_IT
#     pre_processed_MTC_h_code_GTs = {}
#     MTC_item_dicts = {} #FQS_testMethos: MTC id
#     for MTC_item in all_GT_MTCs:
#         if "skip" in MTC_item and MTC_item["skip"] == True: continue
#         FQS_testMethos = MTC_item['FQS_testMethos']
#         if FQS_testMethos == FQS_testMethos_this: continue # avoid select itself
        
#         MTC_item_dicts[FQS_testMethos] = MTC_item
#         # get the code of the MTC
#         pre_processed_MTC_h_code_GT = get_pre_processed_MTC_h_code(MTC_item)
#         pre_processed_MTC_h_code_GTs[FQS_testMethos] = pre_processed_MTC_h_code_GT

#     # 3. get top-n CodeBLEU socres
#     codebleu_scores = {}
#     for FQS_testMethos in pre_processed_MTC_h_code_GTs.keys():
#         pre_processed_MTC_h_code_GT = pre_processed_MTC_h_code_GTs[FQS_testMethos]
#         # CodeBLEU of: pre_processed_MTC_h_code_this , pre_processed_MTC_h_code_GT
#         # codebleu_result = calc_codebleu([pre_processed_MTC_h_code_GT], [pre_processed_MTC_h_code_this], lang="java", weights=(0.25, 0.25, 0.25, 0.25), tokenizer=None)
#         codebleu_result = calc_codebleu([pre_processed_MTC_h_code_GT], [pre_processed_MTC_h_code_this], lang="java")
#         codebleu_score = codebleu_result["codebleu"]
#         codebleu_scores[FQS_testMethos] = codebleu_score
    
#     # rank based on socre 
#     sorted_MTC_and_CodebleuScores = sorted(codebleu_scores.items(), key=lambda x: x[1], reverse=True) # [('b', 2), ('a', 1)]
#     shot_num = trans_generator.Setting["number_of_shot"]
#     shot_MTCs = sorted_MTC_and_CodebleuScores[:shot_num]
    
#     # get Q and A of each shot MTC
#     few_shot_info = [] # [ {Q:.., A:..} , {Q:.., A:..} ]
#     for FQS_testMethos, codebleu_score in shot_MTCs:
#         MTC_item = MTC_item_dicts[FQS_testMethos]
#         # Q: prompt for this MTC
#         # trans_generator_item = transGenerator(trans_generator.index_of_request, MTC_item)
#         trans_generator_item = type(trans_generator)(trans_generator.index_of_request, MTC_item) # the same as the above constructor
#         print(f"LOG: type: {type(trans_generator_item)}, {trans_generator_item.MTC_item['FQS_testMethos']} ")
#         trans_generator_item = generate_prompt_from_profile(trans_generator_item, task_type="trans_generation")
#         Q = trans_generator_item.promt_content

#         # A: the GT ITrans for this MTC
#         # trans_class_def = get_GT_Trans(trans_generator_item.MTC_item, type="class_definition")
#         # A = f"```java\n{trans_class_def}\n```"
#         A_path = f"{FEW_SHOT_BASE_DIR}{FQS_testMethos}".split("(")[0]
#         A = file_processing.read_TXTfile(A_path)
#         few_shot_info.append({"Q":Q, "A":A})
#         print(f"LOG: FQS_testMethos: {FQS_testMethos}")
#         print(f"LOG: few_shot_info, Q:")
#         print(f"{Q}")
#         print(f"LOG: FQS_testMethos: {FQS_testMethos}")
#         print(f"LOG: few_shot_info, A:")
#         print(f"{A}")
#     trans_generator.few_shot_info = few_shot_info

#     # for MTC_item in all_GT_MTCs: # for manually construct few shot base
#     #     # Q: prompt for this MTC
#     #     trans_generator_item = transGenerator(trans_generator.index_of_request, MTC_item)
#     #     trans_generator_item = generate_Inputs_with_LLMs.generate_prompt_from_profile(trans_generator_item, task_type="trans_generation")
#     #     Q = trans_generator_item.promt_content

#     #     # A: the GT ITrans for this MTC
#     #     trans_class_def = generate_Inputs_with_LLMs.get_GT_Trans(trans_generator_item.MTC_item, type="class_definition")
#     #     A = f"```java\n{trans_class_def}\n```"
#     #     FQS_testMethos = MTC_item['FQS_testMethos']
#     #     print(f"LOG: FQS_testMethos: {FQS_testMethos}")
#     #     print(f"LOG: few_shot_info, Q:")
#     #     print(f"{Q}")
#     #     print(f"LOG: FQS_testMethos: {FQS_testMethos}")
#     #     print(f"LOG: few_shot_info, A:")
#     #     print(f"{A}")
    
#     # store
#     prompt_path = trans_generator.prompt_path
#     few_shot_info_path = prompt_path.replace(".md",".few_shot_info.json")
#     # print(f"LOG: few_shot_info_path: {few_shot_info_path}")
#     json_processing.write(json_content=few_shot_info, path=few_shot_info_path)
#     trans_generator.few_shot_info_path = few_shot_info_path

#     return trans_generator




def get_alternative_input_classes_w_examples(input_generator):
    """
    Get alternative input classes for the given MTC item.

    * the parameter of MUT, -> find the `implementation` or sub/parent/sibling classes -> find the invocation example tests in the project

    Args:
        input_generator: The input generator instance
        MTC_item: The MTC item to process
        
    Returns:
        dict: Dictionary of alternative input classes with examples
    """
    alternative_input_classes_w_examples = {}

    methodsFQS_classPaths = input_generator.methodsFQS_classPath
    target_methods_FQS = input_generator.target_methods_FQS
    MTC_item_forVerionCheckout = input_generator.MTC_item
    poj_dir = MTC_item_forVerionCheckout["poj_dir"]

    if len(target_methods_FQS) == 0:
        print("LOG: No target methods found, returning empty alternative input classes.")
        return alternative_input_classes_w_examples
    method_FQS = target_methods_FQS[0] # take the first one
    class_path = methodsFQS_classPaths.get(method_FQS, False)
    if not class_path: 
        return alternative_input_classes_w_examples # no class path found, return empty dict


    # get the classes of parameters
    parameters_FQN = method_FQS.split("(")[1].split(")")[0].split(",")
    # class_path = java_file_processing.find_class_file_path_by_methodFQS(MTC_item_forVerionCheckout["poj_dir"], methodsFQS)

    try:
        for parameter_FQN in parameters_FQN:
            param_class_path = java_file_processing.find_class_file_path_by_methodFQS(poj_dir, parameter_FQN)
            if class_path is None: continue

            # Analyze if the parameter class is abstract/interface
            class_content = file_processing.read_TXTfile(param_class_path)
            is_abstract = "abstract class" in class_content
            is_interface = "interface " in class_content and "class " not in class_content.split("interface ")[0].split("\n")[-1]
            
            alternative_classes = {}
            if is_abstract or is_interface:
                print(f"LOG: Found {'abstract class' if is_abstract else 'interface'}: {parameter_FQN} in {method_FQS}")
            poj_dir_to_search = ("/").join(class_path.split("/")[:-2])  # to shorten the search space ...
            # Find implementations/subclasses in the project
            alternative_classes = find_implementations_or_subclasses(poj_dir_to_search, parameter_FQN, is_interface)

            # Find usage examples for each alternative class
            for alt_class in alternative_classes:
                examples = find_usage_examples(poj_dir, alt_class)
                if examples:
                    if parameter_FQN not in alternative_input_classes_w_examples:
                        alternative_input_classes_w_examples[parameter_FQN] = {}
                    alternative_input_classes_w_examples[parameter_FQN][alt_class] = examples

    except Exception as e:
        print(f"LOG: Error in get_alternative_input_classes: {str(e)}")
        
    print(f"LOG: Found {len(alternative_input_classes_w_examples)} alternative input classes")
    return alternative_input_classes_w_examples



def find_object_subclasses_and_examples(test_class_file, parameter_FQN):
    """
    Find subclasses of Object and their usage examples in test files.
    
    Args:
        test_class_file (str): Path to the test class file
        parameter_FQN (str): Fully qualified name of the parameter
        
    Returns:
        dict: Dictionary mapping class FQNs to their usage examples
              Format: {class_fqn: [method_code1, method_code2, ...]}
    """
    class_and_examples = {}
    
    if "object" in parameter_FQN.lower():
        # that means the parameter is Object, so we need to find the subclasses of Object
        
        """
        1. identify all classes defined in this test class file
        2. for each class, find this test class's tests/functions which create such class as examples
        """
        
        defined_classes = java_file_process_local.get_defined_classes(test_class_file)
        creation_examples = java_file_process_local.get_creation_examples(test_class_file, defined_classes)
        for class_name, examples in creation_examples.items():
            class_and_examples[class_name] = examples[:1] # may just take the first one
        
    return class_and_examples


def find_implementations_or_subclasses(poj_dir, class_fqn, is_interface):
    """Find implementations (for interfaces) or subclasses (for abstract classes)"""
    alternative_classes = {
        "from_interface": [],
        "from_abstract_class": [],
        "from_parent_class": []
    }
    class_simple_name_given = class_fqn.split(".")[-1]
    
    try:
        # Search for Java files in the project
        java_files = []
        for root, dirs, files in os.walk(poj_dir):
            for file in files:
                if file.endswith(".java"):
                    java_files.append(os.path.join(root, file))
        
        for java_file in java_files:
            try:
                content = file_processing.read_TXTfile(java_file)
                if class_simple_name_given not in content: continue  # Skip the class itself

                package_FQN = ""
                class_declaration_stmt = ""
                for line in content.splitlines():
                    if line.strip().startswith("package "):
                        package_FQN = line.split()[1].strip(";")
                    if line.strip().startswith("public class "):
                        class_declaration_stmt = line.strip()
                class_simple_name = java_file.split("/")[-1].replace(".java", "")
                class_FQN = f"{package_FQN}.{class_simple_name}"

                if class_simple_name == class_simple_name_given: continue
                
                # Look for implementations or extensions
                if is_interface:
                    # Look for "implements ClassName" or "implements package.ClassName"
                    if f"implements" in class_declaration_stmt and f"{class_simple_name}" in class_declaration_stmt:
                        alternative_classes["from_interface"].append(class_FQN)
                else:
                    # Look for "extends ClassName" or "extends package.ClassName"
                    if f"extends" in class_declaration_stmt or f"{class_simple_name}" in class_declaration_stmt:
                        class_FQN = f"{package_FQN}.{class_simple_name}"
                        alternative_classes["from_parent_class"].append(class_FQN)

            except Exception as e:
                print(f"LOG: Error reading file {java_file}: {str(e)}")
                continue
                
    except Exception as e:
        print(f"LOG: Error finding implementations/subclasses: {str(e)}")
        
    return list(set(alternative_classes))  # Remove duplicates


def find_usage_examples(poj_dir, class_fqn):
    """Find usage examples of a class in test files"""
    examples = {}
    
    try:
        class_simple_name = class_fqn.split(".")[-1]
        
        # Search for test files
        test_files = []
        for root, dirs, files in os.walk(poj_dir):
            for file in files:
                if file.endswith("Test.java") and class_simple_name in file.lower():
                    test_files.append(os.path.join(root, file))
        
        for test_file in test_files:
            try:
                content = file_processing.read_TXTfile(test_file)

                # Look for instantiation or usage patterns
                if f"new {class_simple_name}" in content:
                    
                    # get each method in this class, if f"new {class_simple_name}" in, get the code of this method. and store into examples.append({code}})
                    tree = javalang.parse.parse(content)
                    # For each class and its methods in the test file
                    for _, cls in tree.filter(javalang.tree.ClassDeclaration):
                        for method in cls.methods:
                            code_of_method = method.to_string()
                            if f"new {class_simple_name}" in code_of_method:
                                if class_fqn not in examples:
                                    examples[class_fqn] = []
                                examples[class_fqn].append(code_of_method)
                                print(f"LOG: Found usage example in {test_file} for {class_fqn}")

                if len(examples) > 1: break
            except Exception as e:
                print(f"LOG: Error reading test file {test_file}: {str(e)}")
                continue
                
    except Exception as e:
        print(f"LOG: Error finding usage examples: {str(e)}")
        
    return examples


if __name__ == "__main__":
    test_class_file = "projects/example-project/src/test/java/org/example/rules/core/RuleProxyTest.java"
    parameter_FQN = "java.lang.Object"
    examples = find_object_subclasses_and_examples(test_class_file, parameter_FQN)
    print(examples)