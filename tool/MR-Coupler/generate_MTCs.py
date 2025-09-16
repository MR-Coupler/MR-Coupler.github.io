"""
自动解析profile，填充prompt template, 生成prompt
"""
from collections import OrderedDict
import datetime
import multiprocessing
import random
import os, sys
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from CyUtil import file_processing,json_processing, java_parser, compile_java_poj, java_test, config, java_file_processing, PIT # type: ignore

from bugrevealingmrgen import request_LLMs, parse_LLMs_response, construct_prompt, running_config
from bugrevealingmrgen.util import MR_method_pattern, MR_method_feature

import json

from bugrevealingmrgen.util import MR_Scout_plus, MR_similarity, run_major
from bugrevealingmrgen.construct_prompt import Templates
from bugrevealingmrgen.request_LLMs import model_symbols, symbols_model
from bugrevealingmrgen import taskset
import re
from  filelock import FileLock
file_lock = FileLock(f"file.lock")

DIR_DATA = config.DIR_DATA
BUGREV_CACHE_DIR = f"{DIR_DATA}BugRev/cache/"
BUGREV_CACHE_COMMIT_INFO_DIR = f"{DIR_DATA}BugRev/cache/commit_info/"
BUGREV_CACHE_GENERATED_MR_DIR = f"{DIR_DATA}BugRev/cache/generateMRs/"
BUGREV_CACHE_GITHUB_ISSUE_DIR = f"{DIR_DATA}BugRev/cache/github_issue/"
BUGREV_EXPERIMENTAL_POJS_BUGAFIX_DIR = DIR_DATA.replace("/ssddata1/" , "/ssddata/") + "BugRev/projects_bugAfix/"  # only special dir, becasue of the space limitation

PATH_MTCFQN_VERSION_TESTCLASS_COMPILATION = f"{BUGREV_EXPERIMENTAL_POJS_BUGAFIX_DIR}/%s/%s/BugRev/testClass_compilation.json"
DIR_MTCFQN_VERSION_BUGREV = f"{BUGREV_EXPERIMENTAL_POJS_BUGAFIX_DIR}/%s/%s/BugRev/"

PATH_BUGREV_FILE_DATE = DIR_DATA + "BugRev/projects/%s/AutoMR/file_date.json" 

CACHE_GENERATED_CONTENT_DIR = BUGREV_CACHE_GENERATED_MR_DIR
OUTPUT_DIR ='outputs/'
path_reproduced_bugs_metainfo = "projects_reproducedBugs/meta_info.json"
reproduced_bugs_metainfo = json_processing.read(path_reproduced_bugs_metainfo)["bugs"]

path_identified_MTCs = "MTidentifier_result_example.json"
identified_MTCs = json_processing.read(path_identified_MTCs)
identified_MTCs_dict = { ele["FQS_testMethos"].replace("()",""):ele for ele in identified_MTCs["MR_items"] if "FQS_testMethos" in ele} 

path_collect_MTC = "Collected_result_example.json"
collected_MTCs = json_processing.read(path_collect_MTC)
collected_MTCs_dict = { ele["FQS"].replace("()",""):ele for ele in collected_MTCs["MTC_metadatas"]}
MTC_commit_issue_dict = { ele["FQS"].replace("()",""): ele["Commit&issueIDs"] for ele in collected_MTCs["MTC_metadatas"]}

path_checkout_exe_results = "checkout_exe_results_example.json"
checkout_exe_results = json_processing.read(path_checkout_exe_results)
path_additional_checkout_exe_results = "additional_checkout_exe_results_example.json"
additional_checkout_exe_results = json_processing.read(path_additional_checkout_exe_results)
checkout_exe_results["items"].update(additional_checkout_exe_results["items"])
checkout_exe_results["detailed_lists"]["latest_runable"].update(additional_checkout_exe_results["detailed_lists"]["latest_runable"])
checkout_exe_results_sccpu4 = json_processing.read("checkout_exe_results_backup_example.json")

all_MTC_checkout_exe_items_info = json_processing.read("checkout_exe_results_reformatted_example.json")

Junit4_STATEMENT = "import org.junit.Test;\nimport static org.junit.Assert.*;"
Junit5_STATEMENT = "import org.junit.jupiter.api.Test;\nimport static org.junit.jupiter.api.Assertions.*;"

Setting = running_config.Setting
all_evaluation_result_of_generated_MRs_function_path = running_config.all_evaluation_result_of_generated_MRs_function_path

MTC_FQN_list = []
MTC_FQN_skip_list = [
    "com.fasterxml.jackson.databind.PropertyNameTest.testMerging", # latest file does not exist
    "org.tikv.common.TiConfigurationTest.testGrpcIdleTimeoutValue", # GT is not correct
    "com.clearspring.analytics.stream.cardinality.TestHyperLogLogPlus.testMergeSelf", # GT is not correct
    "org.threeten.extra.TestYearWeek.test_carry", # may not MTC
    "org.dyn4j.world.AbstractCollisionWorldTest.convexCast", # GT is not correct
    "org.apache.iotdb.db.storageengine.dataregion.compaction.CompactionTaskManagerTest.testSizeTieredCompactionStatus", # may not MTC
    "org.robovm.compiler.config.ConfigTest.testMergeConfigsFromClasspath", # GT may not correct
    "org.apache.rocketmq.tieredstore.core.MessageStoreTopicFilterTest.filterTopicTest", # may not MTC
    "org.eclipse.angus.mail.util.logging.DurationFilterTest.testCountExceedsRecords", # may not MTC
]
switch = True  # refinement: add dependency
def init():
    global MTC_FQN_list, Setting, all_evaluation_result_of_generated_MRs_function_path
    
    """ define Setting """
    
    """ define taskset """
    if Setting["targetCUTv"] == "latest":
        for MTC_FQN in checkout_exe_results["detailed_lists"]["latest_pass"].keys():
            if MTC_FQN not in identified_MTCs_dict: continue

            MTC_FQN_list.append(MTC_FQN)
        
        path_MTC_FQN_list_random = "tasks_latestV_MTC_FQN_list_random.json"
        if file_processing.pathExist(path_MTC_FQN_list_random):
            print(f"LOG: load MTC_FQN_list from {path_MTC_FQN_list_random}")
            MTC_FQN_list = json_processing.read(path_MTC_FQN_list_random)
        else:
            random.shuffle(MTC_FQN_list)
            print(f"LOG: shuffle MTC_FQN_list and store it to {path_MTC_FQN_list_random}")
            json_processing.write(MTC_FQN_list, path_MTC_FQN_list_random)
        if Setting.get("only2MI", False): # treats missing keys as False
            updated_MTC_FQN_list = []
            for MTC_FQN in MTC_FQN_list:
                invoked_methods_FQS = identified_MTCs_dict[MTC_FQN]["invoked_methods_FQS"]
                if len(invoked_methods_FQS) == 2:
                    updated_MTC_FQN_list.append(MTC_FQN)
            print("INFO: all MTC_FQN_list: ", len(MTC_FQN_list))
            MTC_FQN_list = updated_MTC_FQN_list
            print("INFO: only2MI MTC_FQN_list: ", len(updated_MTC_FQN_list), len(MTC_FQN_list))
        if Setting.get("afterCF", False): # treats missing keys as False   
            path_subjects_after_cf = "tasks_latestV_afterCF_MTC_FQN_list.json"
            subjects_after_cf = json_processing.read(path_subjects_after_cf)
            updated_MTC_FQN_list = [s["MTC_FQN"] for s in subjects_after_cf if s["MTC_FQN"] in MTC_FQN_list]
            print("INFO: before CF-filtering MTC_FQN_list: ", len(MTC_FQN_list))
            MTC_FQN_list = updated_MTC_FQN_list
            print("INFO: after CF-filtering MTC_FQN_list: ", len(MTC_FQN_list))

        # skip MTC_FQN_skip_list
        MTC_FQN_list = [MTC_FQN for MTC_FQN in MTC_FQN_list if MTC_FQN not in MTC_FQN_skip_list] # skip MTC_FQN_skip_list
        # in this way, the list is fixed.--- just the first 100 subjects 
        MTC_FQN_list = MTC_FQN_list[:100]
        
    elif Setting["targetCUTv"] == "BUGGY":
        # reproduced_bugs
        for MTC_FQN in reproduced_bugs_metainfo:
            if "target_methods_FQN" not in reproduced_bugs_metainfo[MTC_FQN]: 
                print(f"LOG: target_methods_FQN not in reproduced_bugs_metainfo[MTC_FQN]: {MTC_FQN}")
                continue
            # if MTC_FQN not in checkout_exe_results["detailed_lists"]["issuepass_but_issuepreFail"].keys(): 
            #     print(f"LOG: MTC_FQN not in checkout_exe_results['detailed_lists']['issuepass_but_issuepreFail'].keys(): {MTC_FQN}")
            #     continue
            MTC_FQN_list.append(MTC_FQN)
    
    print(f"LOG: MTC_FQN_list: {len(MTC_FQN_list)}")
    return MTC_FQN_list


class mrGenerator():
    @staticmethod
    def get_cache_dir(index_of_request):
        Setting['index_of_request'] = index_of_request
        # cache_dir_name_for_this_setting = f"{Setting['date']}_{Setting['targetCUTv']}V_{Setting['model']}_T{Setting['Prompt_template']}_Shot{Setting['number_of_shot']}_Temprature{Setting['temperature']}_Rev{Setting['number_of_revise']}_{Setting['index_of_request']}" 
        cache_dir_name_for_this_setting = f"{Setting['paired_method_info']}{Setting['pair_method_methodology']}{Setting['mutateMRs']}{Setting['code_refactoring']}{Setting['targetCUTv']}V_T{Setting['Prompt_template']}_{Setting['model']}_{Setting['date']}_Shot{Setting['number_of_shot']}_Temprature{Setting['temperature']}_Rev{Setting['number_of_revise']}_{Setting['index_of_request']}" 
        if Setting.get("afterCF", False):
            cache_dir_name_for_this_setting += "_afterCF"
        return cache_dir_name_for_this_setting

    def __init__(self, index_of_request, MTC_FQN, commitID, fixed_version_commitID=None):
        Setting['index_of_request'] = index_of_request
        cache_dir_name_for_this_setting = mrGenerator.get_cache_dir(index_of_request)
        cache_dir_for_this_setting = f"{CACHE_GENERATED_CONTENT_DIR}{cache_dir_name_for_this_setting}/"
        Crafted_prompts_dir = f"{cache_dir_for_this_setting}prompts/"

        """ metainfo """
        # self.MTC_item = MTC_item
        # get general metainfo from: each version's testClass_compilation.json
         # MTC_item = collected_MTCs_dict[MTC_FQN]
        dir_MTCFQN_VERSION_BUGREV = DIR_MTCFQN_VERSION_BUGREV % (MTC_FQN, commitID)
        path_version_testClass_compilation_info = PATH_MTCFQN_VERSION_TESTCLASS_COMPILATION % (MTC_FQN, commitID)
        version_testClass_compilation_info = json_processing.read(path_version_testClass_compilation_info)
        MTC_item_forVerionCheckout = version_testClass_compilation_info["MTC"]
        path_MTC_version_testclass_file = version_testClass_compilation_info["path_test_file"]

        # get checkout results (different reprodcued results) from: 
        # checkout_exe_result = checkout_exe_results["detailed_lists"]["issuepass_but_issuepreFail"][MTC_FQN] # old version: when running produced bug MTCs
        if MTC_FQN in taskset.sccpu4_but_not_sccpu7_reproduced_bugs_MTC.keys(): # for sccpu4's cases
            checkout_exe_result = taskset.sccpu4_but_not_sccpu7_reproduced_bugs_MTC[MTC_FQN]["checkout_exe_result"]
            if MTC_FQN in taskset.sccpu4_but_not_sccpu7_reproduced_bugs_MTC:
                MTC_commit_issue_dict[MTC_FQN] = taskset.sccpu4_but_not_sccpu7_reproduced_bugs_MTC[MTC_FQN]["Commit&issueIDs"]
        else:
            checkout_exe_result = checkout_exe_results["detailed_lists"]["latest_runable"][MTC_FQN]
        commit_hash = checkout_exe_result["commit_hash"]
        commit_hash_pre = checkout_exe_result["commit_hash_pre"]
        if fixed_version_commitID is None: # buggy or fixed version commitID
            fixed_version_commitID = commit_hash
            buggy_versoin_commitID = commit_hash_pre
        
        fix_version_testClass_compilation_info = json_processing.read(PATH_MTCFQN_VERSION_TESTCLASS_COMPILATION % (MTC_FQN, commitID))
        path_MTC_fix_version_testclass_file = fix_version_testClass_compilation_info["path_test_file"]
        
        # get target_methods_FQN and invoked_methods_FQS
        target_methods_FQN = None; invoked_methods_FQS = None; target_methods_FQS = None
        if MTC_FQN in reproduced_bugs_metainfo: # manually crafted
            target_methods_FQN = reproduced_bugs_metainfo[MTC_FQN]["target_methods_FQN"]
            invoked_methods_FQS = reproduced_bugs_metainfo[MTC_FQN]["invoked_methods_FQS"]
            target_methods_FQS = reproduced_bugs_metainfo[MTC_FQN]["target_methods_FQS"] # TODO: after updating the meta.json
        else:                                   # automatically identified        
            invoked_methods_FQS = identified_MTCs_dict[MTC_FQN]["invoked_methods_FQS"]  
            # read the commit info of this commit, and take the overlap of related_methods_FQN and invoked_methods_FQS as target methods
            related_methods_FQN = []
            issue_related_commits = list(all_MTC_checkout_exe_items_info[MTC_FQN]["issue_related_commitsANDpreCommit"].keys())
            for issue_related_commit in issue_related_commits:
                if not file_processing.pathExist(f"{BUGREV_CACHE_COMMIT_INFO_DIR}{issue_related_commit}.json"): continue
                commit_info = json_processing.read(f"{BUGREV_CACHE_COMMIT_INFO_DIR}{issue_related_commit}.json")
                if issue_related_commit not in commit_info: continue
                for modified_method in ["added_functions", "updated_functions"]:
                    for method_item in commit_info[issue_related_commit][modified_method]:
                        related_methods_FQN.append(method_item["fully_qualified_method_name"])
            target_methods_FQS = [method for method in invoked_methods_FQS if method.split("(")[0] in related_methods_FQN] # remove duplicate
            # target_methods_FQS = sorted( list(set(target_methods_FQS)) )
            target_methods_FQN = [ ele.split("(")[0] for ele in target_methods_FQS ] # target_methods_FQN may be not so necessary
            # reminder: sometimes, all invoked methods are related methods; if so, paired method info will be meaningless
            print(f"LOG: target_methods_FQN: {target_methods_FQN}")
        if target_methods_FQN==None or len(target_methods_FQN) == 0: # BACKUP
            target_methods_FQN = [invoked_methods_FQS[0]] # 2025-0722, 先暂取第一个。。。为target
            target_methods_FQS = [invoked_methods_FQS[0]]
        
        # get issue 
        issueID = None
        # print(f"LOG: MTC_FQN: {MTC_FQN}")
        # print(f"LOG: MTC_commit_issue_dict[MTC_FQN]: {MTC_commit_issue_dict[MTC_FQN]}")
        # print(f"LOG: commitID: {commitID}")
        if commitID in MTC_commit_issue_dict[MTC_FQN]:
            issueID = MTC_commit_issue_dict[MTC_FQN][commitID][0].replace("(","").replace(")","").replace("#","")
        else:
            issue_related_commits = list(all_MTC_checkout_exe_items_info[MTC_FQN]["issue_related_commitsANDpreCommit"].keys())
            for issue_related_commit in issue_related_commits:
                if issue_related_commit not in MTC_commit_issue_dict[MTC_FQN]: continue
                issueID = MTC_commit_issue_dict[MTC_FQN][issue_related_commit][0].replace("(","").replace(")","").replace("#","")
                break # only take the first one
        # get owner name and poj name
        # owner_name = None; poj_name = None
        example_poj_name = MTC_item_forVerionCheckout["poj_dir"].split("/")[-2]
        owner_name = example_poj_name.split("__example__")[0]
        poj_name = example_poj_name.split("__example__")[1]
        
        prompt_results_content_dir = f"{cache_dir_for_this_setting}prompts_results_content/"
        prompts_results_raw_dir = f"{cache_dir_for_this_setting}prompts_results_raw/"
        prompt_generated_MRs_dir = f"{cache_dir_for_this_setting}generated_MRs/"
        prompt_code_refactoring_dir = f"{cache_dir_for_this_setting}code_refactoring/"

        evaluation_execution_log_dir = f"{cache_dir_for_this_setting}exe_result/"
        evaluation_result_of_generated_MRs_function_path = f"{cache_dir_for_this_setting}evaluation_generated_MRs.json"
        compilation_log_dir = f"{cache_dir_for_this_setting}compilation_log/"

        # poj_build_tool
        poj_compilation_info = json_processing.read( dir_MTCFQN_VERSION_BUGREV.removesuffix("BugRev/") + "/AutoMR/compile_info.json")
        # print(f"poj_compilation_info: {poj_compilation_info}")
        # print(f"LOG: poj_compilation_info: {poj_compilation_info}") 
        poj_build_tool = poj_compilation_info["build_tool"][0]
        jdk_version = poj_compilation_info[f"{poj_build_tool}_java_version_success"][0]

        file_processing.creatFolder_IfExistPass(cache_dir_for_this_setting)
        file_processing.creatFolder_IfExistPass(Crafted_prompts_dir)
        file_processing.creatFolder_IfExistPass(prompt_generated_MRs_dir)
        file_processing.creatFolder_IfExistPass(prompt_results_content_dir)
        file_processing.creatFolder_IfExistPass(prompts_results_raw_dir)
        file_processing.creatFolder_IfExistPass(compilation_log_dir)
        file_processing.creatFolder_IfExistPass(evaluation_execution_log_dir)
        file_processing.creatFolder_IfExistPass(prompt_code_refactoring_dir)

        self.success_init = True
        self.Setting = Setting
        self.prompt_template = Templates[Setting["Prompt_template"]]
        self.index_of_request = index_of_request
        self.cache_dir_name_for_this_setting = cache_dir_name_for_this_setting
        self.cache_dir_for_this_setting = cache_dir_for_this_setting
        self.Crafted_prompts_dir = Crafted_prompts_dir
        self.prompt_generated_MRs_dir = prompt_generated_MRs_dir
        # self.cache_generated_valid_inputs_testing_MRs_dir = cache_generated_valid_inputs_testing_MRs_dir
        self.prompt_results_content_dir = prompt_results_content_dir
        self.prompt_code_refactoring_dir = prompt_code_refactoring_dir
        self.prompts_results_raw_dir = prompts_results_raw_dir

        self.evaluation_result_of_generated_MRs_function_path = evaluation_result_of_generated_MRs_function_path
        self.compilation_log_dir = compilation_log_dir
        self.evaluation_execution_log_dir = evaluation_execution_log_dir

        self.few_shot_info = []
        self.few_shot_info_path = ""

        # some metainfo
        self.MTC_item = MTC_item_forVerionCheckout
        self.checkout_exe_result = checkout_exe_result
        # self.target_methods_FQN = target_methods_FQN
        # self.target_methods_FQS = target_methods_FQS
        # only take the last one (each time target one method is also fine.); PIT can target all related/modified/invoked methods
        self.target_methods_FQN = [target_methods_FQN[0]] # just take the first one
        self.target_methods_FQS = [target_methods_FQS[0]] # just take the first one
        self.invoked_methods_FQS = invoked_methods_FQS
        self.genreated_test_class_name = None
        self.dir_MTCFQN_VERSION_BUGREV = dir_MTCFQN_VERSION_BUGREV
        self.dir_MTCFQN_VERSION_BUGREV_generated_tests = f"{dir_MTCFQN_VERSION_BUGREV}/generated_tests/"
        self.dir_MTCFQN_VERSION_BUGREV_generated_Major_mutants = f"{dir_MTCFQN_VERSION_BUGREV}/Major_generated_mutants/"
        self.MTC_version_poj_dir = dir_MTCFQN_VERSION_BUGREV.removesuffix("BugRev/")
        self.MTC_FQN = MTC_FQN
        self.commitID = commitID
        self.fixed_version_commitID = fixed_version_commitID
        self.path_version_testClass_compilation_info = path_version_testClass_compilation_info
        self.path_MTC_version_testclass_file = path_MTC_version_testclass_file
        self.path_MTC_fix_version_testclass_file = path_MTC_fix_version_testclass_file
        if not file_processing.pathExist(self.path_MTC_fix_version_testclass_file):
            print(f"LOG: path_MTC_fix_version_testclass_file does not exist: {self.path_MTC_fix_version_testclass_file}", MTC_FQN, fixed_version_commitID)

        self.pre_revision_evaluation_result = None
        self.pre_revision_evaluation_result_summary = None
        self.prompt_messages_path = None
        self.prompt_system_message = None; self.promt_id = None; self.prompt_path = None; self.promt_content = None; 
        self.OriginalNames_newNames_dict = None
        self.response_content_path = None
        self.chat_history = []
        self.flag_include_chat_history = False
        self.compilation_log_content = None
        self.execution_log_content = None
        self.poj_build_tool = poj_build_tool
        self.jdk_version = jdk_version
        
        self.owner_name = owner_name
        self.poj_name = poj_name
        self.issueID = issueID

        if file_processing.pathExist(path_MTC_version_testclass_file):
            test_file = file_processing.read_TXTfile(path_MTC_version_testclass_file)
        else:
            print(f"LOG: NOTE-ERROR: path_MTC_version_testclass_file does not exist: {path_MTC_version_testclass_file}", MTC_FQN, commitID)
            self.success_init = False
            return None
        package_line = test_file.split("\n")[:0]
        for line in test_file.split("\n"):
            if line.startswith("package "): package_line = line; break
            if line.strip().startswith("package "): package_line = line; break
        invoked_package_FQN = package_line.replace('package ','').replace(';','').strip() # 最准确啦
        self.invoked_package_FQN = invoked_package_FQN
        self.genreated_test_class_FQN = None
        # self.genreated_test_class_FQN = f"{invoked_package_FQN}.{genreated_test_class_name}" # genreated_test_class_name is not prepared now
        
        
        self.context_data = None
        methodsFQS_classPath = {}
        methodsFQS_returnType = {}
        for methodsFQS in invoked_methods_FQS + target_methods_FQS:
            poj_dir = self.MTC_version_poj_dir
            # class_path = java_file_processing.find_class_file_path_by_methodFQS(poj_dir, methodsFQS)
            class_path, MUT_code, return_type = java_file_processing.get_classPath_methodCode_returnType(methodsFQS, poj_dir)
            if class_path == None: # 绥靖政策。。。。
                class_path = java_file_processing.find_class_file_path_by_methodFQS(MTC_item_forVerionCheckout["poj_dir"], methodsFQS)
            if methodsFQS not in methodsFQS_classPath:
                methodsFQS_classPath[methodsFQS] = class_path
            if methodsFQS not in methodsFQS_returnType:
                methodsFQS_returnType[methodsFQS] = return_type
        self.methodsFQS_classPath = methodsFQS_classPath
        self.methodsFQS_returnType = methodsFQS_returnType
        
        self.task_symbol = None
        self.task_symbol_index = 0
        self.task_symbol_prefix = None
        self.context_data_for_current_task_symbol = None

        pass


class contextData:
    def __init__(self, MUTa_signature, MTCa_FQN):
        self.MUTa_signature = MUTa_signature
        self.MTCa_FQN = MTCa_FQN
        
        self.similar_MUTsB = None
        self.pattern_suggested_MUTbs = None
        self.pattern_suggested_pairMethods = None
        self.ordered_similar_MUTsB_and_patterns = None
        
        self.ordered_pattern_suggested_methods_MUTsB = None
        self.ordered_similar_MUTsB_and_pattern_suggested_methods = None
        self.ordered_pattern_suggested_methods_w_featureDes = None
        

def context_preparation(MR_generator):
    """
    TODO: 
    MUT: MUTa
    similar MUT in DB: MUTb
    
    # (previous) design
    1. get diverse and relevant MUTb's MTCb
    2. analyze the MR metadata of MTCb
    3. generate candidate MR metadata for MUTa
    4. generate MTCs for MUTa (based on each candidate MR metadata) 
    
    # implementation
    * get a lot of (1k) similar MUTs <MUTb, method pattern>
    * for each pattern, get the first 1 MUTb as example
    * for each pattern, get all satisfied methods as suggested methods
    
    
    we have:
    context_data.pattern_suggested_MUTbs = pattern_suggested_MUTbs
    context_data.pattern_suggested_pairMethods = pattern_suggested_pairMethods
    context_data.feature_suggested_pairMethods = feature_suggested_pairMethods
    context_data.ordered_similar_MUTsB_and_patterns = ordered_similar_MUTsB_and_patterns
    
    
    # option1 [pattern/feature driven]
    1 MUTa -> k * pattern/feature (+similar MTC as example) -> n* suggested methods (for pair)
    {MUTa: pattern_type: [ {MUTb, MUTb's MUT_info , suggested_methods: [MUTd, MUTe, MUTf]} ] }
    


    # option2 [similar MUTsB driven] [discarded]
    1 MUTa -> 5 * similar MUTsB (with pattern) -> n* suggested methods (for pair)
    (previous setting: 5 similar MUTsB, 5 all suggested methods)
    
    for similar_MUTb in ordered_similar_MUTsB_and_patterns:
        pattent = xxx 
        suggested_methods.extend(pattern_suggested_pairMethods[pattedn])
    return suggested_methods
    
    
    """
    if MR_generator.Setting["paired_method_info"] == "" or MR_generator.Setting["pair_method_methodology"] == "": return # baseline: do not need to pair methods
    Setting = MR_generator.Setting
    MUTa_signature = MR_generator.target_methods_FQS[0] # actually, only one inside
    MTCa_FQN = MR_generator.MTC_FQN
    class_under_test_path = MR_generator.methodsFQS_classPath[MUTa_signature] # MUTa_signature's file path
    methodsFQS_returnType = MR_generator.methodsFQS_returnType
    strong_pattern_only_flag = MR_generator.Setting["strong_pattern_only_flag"]
    strong_pattern_index = MR_method_pattern.strong_pattern_index

    context_data = contextData(MUTa_signature, MTCa_FQN)    
    MUTa_signature_returnType = methodsFQS_returnType[MUTa_signature]
    MUTa_signature_w_returnType = f"{MUTa_signature_returnType} {MUTa_signature}"
    method_name, simple_method_name_tokens, simple_parameter_types, return_type = MR_method_pattern.parse_method_signature(MUTa_signature_w_returnType, consider_empty_para_as_str=False)
    simple_method_name = method_name.split(".")[-1]
    simple_MUTa_signature_w_returnType = f"{return_type} {simple_method_name}({','.join(simple_parameter_types)})"
    
    # k = 1
    # k_patterns = MR_method_pattern.defined_pattern_index[:k]
    
    # 1. Query similar MUTs from database
    # similar_MUTsB_with_scores = query_DB.query_instance.query(MUTa_signature, MTCa_FQN, 100)
    # if running_config.Setting["paired_method_info"] == "similarMTC":
    similar_MUTsB_with_scores = [] # TODO: 
    if Setting["pair_method_methodology"] in ["S","2"]: # similar MTC driven
        from bugrevealingmrgen import MTCDB
        import bugrevealingmrgen.MTCDB.query_DB as query_DB
        similar_MUTsB_with_scores = query_DB.query_instance.query(simple_MUTa_signature_w_returnType, MTCa_FQN, 20)
    
    # 2. each pattern, get all satisfied methods as suggested methods
    # 2. each feature, get all satisfied methods as suggested methods
    pattern_suggested_pairMethods = {}
    pattern_suggested_pairMethods_metadata = {}
    feature_suggested_pairMethods = {}
    if class_under_test_path != None: 
        pattern_suggested_pairMethods_metadata, pattern_suggested_pairMethods = MR_method_pattern.suggest_paired_methods_by_pattern(MUTa_signature_w_returnType, class_under_test_path)
        feature_methods_dict_metadata, feature_methods_dict = MR_method_feature.suggest_paired_methods_by_feature(MUTa_signature_w_returnType, class_under_test_path)
        feature_suggested_pairMethods = feature_methods_dict 
        pattern_suggested_pairMethods.update(feature_suggested_pairMethods) # add feature methods to pattern methods
        pattern_suggested_pairMethods_metadata.update(feature_methods_dict_metadata)
    else:
        print(f"NOTE: MTCa_FQN '{MTCa_FQN}' MUTa_signature '{MUTa_signature}' no class_under_test_path `{class_under_test_path}`")
    
    # 2. identify pattern of similar MUTs
    pattern_suggested_MUTbs = {}
    ordered_similar_MUTsB_and_patterns = []
    for similar_MUTb, similarity_distance in similar_MUTsB_with_scores:
        # Get the other MUTs that were paired with this MUT in its test
        # print(f"similar_MUTb: {similar_MUTb.similar_MUTb.page_content}")
        other_muts_signatures = similar_MUTb.metadata["other_MUTs"].split("__split__")
        # fix: when other_MUTs is empty, it's the same as MUT
        if not similar_MUTb.metadata["other_MUTs"] or similar_MUTb.metadata["other_MUTs"] == "": 
            simple_signature_MUTb = similar_MUTb.page_content
            similar_MUTb.metadata["other_MUTs"] = simple_signature_MUTb
            other_muts_signatures = [simple_signature_MUTb]
        
        # Add the pattern information
        # 3. Study the pattern of paired methods in MTCs-B
        mut_signature = similar_MUTb.page_content
        pattern = MR_method_pattern.identify_pattens(mut_signature, other_muts_signatures)
        # feature = MR_method_pattern.identify_pattens(mut_signature, other_muts_signatures) # TODO, identify feature, added here
        # print(f"identify_pattens({mut_signature}, {other_muts_signatures}): {pattern}")
        if pattern["paired_patterns"][0]["pattern_type"] not in pattern_suggested_MUTbs:
            pattern_suggested_MUTbs[pattern["paired_patterns"][0]["pattern_type"]] = [similar_MUTb]
        else:
            pattern_suggested_MUTbs[pattern["paired_patterns"][0]["pattern_type"]].append(similar_MUTb)
        
        # add the code of similar_MUTb's MTC
        code_of_MUTb_MTC = similar_MUTb.page_content
        # similar_MUTb.metadata["MTC_code"] = similar_MUTb.page_content
        MTC_FQN = similar_MUTb.metadata["MTC_FQN"]
        MTC_FQN_name = MTC_FQN.replace("()","").split(".")[-1]
        MTC_code = java_parser.get_method_body_or_related_class_field(file_path=similar_MUTb.metadata["MTC_test_file_path"], method_name=MTC_FQN_name, function="getMethod")
        similar_MUTb.metadata["MTC_code"] = MTC_code # to check 
        
        ordered_similar_MUTsB_and_patterns.append({"similar_MUTb": similar_MUTb, "pattern": pattern, "similarity_score": similarity_distance})
        
    
    context_data.pattern_suggested_MUTbs = pattern_suggested_MUTbs
    context_data.pattern_suggested_pairMethods = pattern_suggested_pairMethods
    # context_data.feature_suggested_pairMethods = feature_suggested_pairMethods
    context_data.ordered_similar_MUTsB_and_patterns = ordered_similar_MUTsB_and_patterns
    context_data.similar_MUTsB = [doc for doc, score in similar_MUTsB_with_scores]

    """ format: pattern """
    ordered_pattern_suggested_methods_MUTsB = []
    # 
    strong_pattern_only_flag = False
    suggested_methods_w_featureDes_dict = {}
    for pattern_type in pattern_suggested_pairMethods:
        for method_signature in pattern_suggested_pairMethods[pattern_type]:
            if method_signature not in suggested_methods_w_featureDes_dict: suggested_methods_w_featureDes_dict[method_signature] = {}
            suggested_methods_w_featureDes_dict[method_signature][pattern_type] = pattern_suggested_pairMethods_metadata[pattern_type][method_signature]["description"]
        # Threshold: if one feature/pattern's result>10, clean this feature/pattern
        if len(pattern_suggested_pairMethods[pattern_type]) > 10: 
            methods = pattern_suggested_pairMethods[pattern_type].copy()
            if len(list(set(methods))) > 10: pattern_suggested_pairMethods[pattern_type] = []
    # Threshold: if < 15, all; if >15: strong only. and first top15 ...; 
    if suggested_methods_w_featureDes_dict.keys().__len__() > 15: strong_pattern_only_flag = True
    
    for pattern_type in pattern_suggested_pairMethods:
        similar_MUTbs_ = None
        if (strong_pattern_only_flag and pattern_type not in strong_pattern_index): continue # strong_pattern_index only works for "Sig"
        # if pattern_type in ["Sig4.3"]: continue # "Sig4.3" 直接排除
        if pattern_type in pattern_suggested_MUTbs: 
            similar_MUTbs_ = pattern_suggested_MUTbs[pattern_type]
        ordered_pattern_suggested_methods_MUTsB.append({
            "pattern": pattern_type,
            "suggested_methods": pattern_suggested_pairMethods[pattern_type],
            "similar_MUTb": similar_MUTbs_
        }) # note: similar_MUTb 里面可能会有很多个...同一个pattern的similar MTC
    context_data.ordered_pattern_suggested_methods_MUTsB = ordered_pattern_suggested_methods_MUTsB
    context_data.ordered_pattern_suggested_methods_w_featureDes = suggested_methods_w_featureDes_dict
    
    """ format: similar MUT """
    ordered_similar_MUTsB_and_pattern_suggested_methods = []
    for ordered_similar_MUTb_and_pattern in ordered_similar_MUTsB_and_patterns:
        pattern_type = ordered_similar_MUTb_and_pattern["pattern"]["paired_patterns"][0]["pattern_type"]
        suggested_methods_ = []
        if pattern_type not in pattern_suggested_pairMethods: continue
        suggested_methods_ = pattern_suggested_pairMethods[pattern_type]
        ordered_similar_MUTsB_and_pattern_suggested_methods.append({
            "similar_MUTb": ordered_similar_MUTb_and_pattern["similar_MUTb"],
            "pattern": ordered_similar_MUTb_and_pattern["pattern"],
            "suggested_methods": suggested_methods_
        })
    context_data.ordered_similar_MUTsB_and_pattern_suggested_methods = ordered_similar_MUTsB_and_pattern_suggested_methods
    MR_generator.context_data = context_data
    
    print("--------------------------------")
    print(f"MTCa_FQN: {MTCa_FQN}")
    print(f"MUTa_signature: {MUTa_signature}")
    print(f"simple_MUTa_signature_w_returnType: {simple_MUTa_signature_w_returnType}")
    print("+++++")
    for similar_MUTb, similarity_distance in similar_MUTsB_with_scores[:5]:
        print(f"similar_MUTb: {similar_MUTb.page_content} (similarity_distance: {similarity_distance:.4f})")
        print(f"similar_MUTb.metadata['other_MUTs']: {similar_MUTb.metadata['other_MUTs']}")
    print("+++++")
    # print(f"pattern_suggested_MUTbs[:10]: { pattern_suggested_MUTbs[") # to json reader-friendly
    print(f"pattern_suggested_pairMethods: {json.dumps(pattern_suggested_pairMethods, indent=2)}") # to json reader-friendly
    # print(f"feature_suggested_pairMethods: {feature_suggested_pairMethods}") # to json reader-friendly
    print("+++++")
    for ordered_similar_MUTb_and_pattern in ordered_similar_MUTsB_and_patterns[:5]:
        print(f"ordered_similar_MUTb_and_pattern: {ordered_similar_MUTb_and_pattern['similar_MUTb'].page_content}", f"pattern: {ordered_similar_MUTb_and_pattern['pattern']}")
    print("--------------------------------")
    return context_data


def generate_prompt_from_profile(MR_generator):
    """prompt info & system message """
    MR_generator = construct_prompt.generate_prompt_from_profile(MR_generator)

    """ few shot info """
    if MR_generator.Setting["number_of_shot"]>0:
        MR_generator = construct_prompt.generate_few_shot_info(MR_generator)

    return MR_generator


def generate_MRs_by_prompting(MR_generator):
    # # when self-revise, not overwrite previous prompt results, 已在后面处理
    # if MR_generator.pre_revision_evaluation_result_summary == "executable":
    #     print(f"Skip generate_MRs_by_prompting: pre_revision_evaluation_result_summary is executable")
    #     return MR_generator.pre_revision_evaluation_result_summary

    # prepare
    MTC_item = MR_generator.MTC_item
    Crafted_prompts_dir = MR_generator.Crafted_prompts_dir
    prompt_results_content_dir = MR_generator.prompt_results_content_dir
    prompts_results_raw_dir = MR_generator.prompts_results_raw_dir
    prompt_generated_MRs_dir = MR_generator.prompt_generated_MRs_dir
    system_message = MR_generator.prompt_system_message
    promt_id = MR_generator.promt_id
    prompt_path = MR_generator.prompt_path
    prompt = MR_generator.promt_content
    few_shot_info = MR_generator.few_shot_info
    pre_revision_evaluation_result_summary = MR_generator.pre_revision_evaluation_result_summary
    chat_history = MR_generator.chat_history
    flag_include_chat_history = MR_generator.flag_include_chat_history
    path_MTC_fix_version_testclass_file = MR_generator.path_MTC_fix_version_testclass_file
    OriginalNames_newNames_dict = MR_generator.OriginalNames_newNames_dict

    """ prompt: generate MRs """
    prompt_messages_path = f"{prompt_results_content_dir}{promt_id}_prompt_messages.md"
    response_content_path = f"{prompt_results_content_dir}{promt_id}_response_content.md"
    reasoning_content_path = f"{prompt_results_content_dir}{promt_id}_reasoning_content.md"
    
    # just for debugging: 20250602
    prompt = file_processing.read_TXTfile(prompt_path)
    system_message = file_processing.read_TXTfile(prompt_path.replace(".md",".system_message"))
    
    response_content = None
    reasoning_content = None
    # not overwrite previous prompt results
    if not Setting["overwritePreviousPromptResults"] and file_processing.pathExist(response_content_path) and len(file_processing.read_TXTfile(response_content_path).split(" ")) > 20: # at least 20 tokens
        response_content = file_processing.read_TXTfile(response_content_path)
        if file_processing.pathExist(reasoning_content_path): 
            reasoning_content = file_processing.read_TXTfile(reasoning_content_path)
        print(f"Skip prompting: {response_content_path} has been generated")
    # when self-revise, not overwrite previous prompt results
    elif Setting["number_of_revise"] > 0 and pre_revision_evaluation_result_summary == "executable" and file_processing.pathExist(response_content_path) and len(file_processing.read_TXTfile(response_content_path).split(" ")) > 20: # at least 20 tokens
        response_content = file_processing.read_TXTfile(response_content_path)
        print(f"Skip prompting: {response_content_path}, because pre_revision_evaluation_result_summary is executable, don't need to revise")
    elif Setting["UseGroundTruthMTCclass"] and file_processing.pathExist(path_MTC_fix_version_testclass_file):
        GroundTruthMTCclass = file_processing.read_TXTfile(path_MTC_fix_version_testclass_file)
        response_content = f"Just use GroundTruthMTCclass in {path_MTC_fix_version_testclass_file} as the generated MRs class.\n[TODO: should use `.java_updated` in the buggy version]\n```java\n{GroundTruthMTCclass}\n```"
        file_processing.write_TXTfile(path=response_content_path, content=response_content)
    else:
        response_content, reasoning_content = request_LLMs.request_LLMs_main(prompt, Setting["model"], promt_id, Setting["temperature"], prompt_results_content_dir, system_message, few_shot_info, chat_history, flag_include_chat_history, return_reasoning_content=True)
    print("LOG: path_MTC_fix_version_testclass_file: ", path_MTC_fix_version_testclass_file)
    # write: to play safe
    if reasoning_content: file_processing.write_TXTfile(path=reasoning_content_path, content=reasoning_content)
    
    """ prompt: mutate MRs """
    if Setting["mutateMRs"] == "mutateMRs" : 
        # response_content = None
        generated_class = parse_LLMs_response.extract_generated_class(response_content, generated_class_name=promt_id); 
        if not generated_class: generated_class = "empty"
        
        mutateMRs_prompt = construct_prompt.mutateMRs_template.replace("<GENERATED MTCs>", generated_class).replace("<EXISTING TESTS>", MR_generator.prompt_EXISTING_TESTS).replace("<METHOD CONTEXT>", MR_generator.prompt_CUT)
        mutateMRs_promt_id = MR_generator.promt_id + "_mutateMRs"
        mutateMRs_prompt_messages_path = f"{prompt_results_content_dir}{mutateMRs_promt_id}_prompt_messages.md"
        mutateMRs_response_content_path = f"{prompt_results_content_dir}{mutateMRs_promt_id}_response_content.md"
        mutateMRs_reasoning_content_path = f"{prompt_results_content_dir}{mutateMRs_promt_id}_reasoning_content.md"
        
        mutatedMRs_response_content = response_content # 初始状态
        if file_processing.pathExist(mutateMRs_response_content_path):
            mutatedMRs_response_content = file_processing.read_TXTfile(mutateMRs_response_content_path)
            if file_processing.pathExist(mutateMRs_reasoning_content_path):
                mutatedMRs_reasoning_content = file_processing.read_TXTfile(mutateMRs_reasoning_content_path)
            print(f"Skip mutateMRs: {mutateMRs_response_content_path} has been generated")
        else:
            if Setting["number_of_revise"] == 0: # 即：在非revision的状态下，才生成mutateMRs
                file_processing.write_TXTfile(path=mutateMRs_prompt_messages_path, content=mutateMRs_prompt)
                # mutatedMRs_response_content, mutatedMRs_reasoning_content = request_LLMs.request_LLMs_main(mutateMRs_prompt, Setting["model"], mutateMRs_promt_id, Setting["temperature"], prompt_results_content_dir, mutateMRs_system_message, few_shot_info, chat_history, flag_include_chat_history, return_reasoning_content=True)
                mutatedMRs_response_content, mutatedMRs_reasoning_content = request_LLMs.request_deepseekChat(
                    mutateMRs_prompt, 
                    model="deepseek-chat", 
                    temperature=0,
                    return_reasoning_content=True)
                # print(f"LOG: mutatedMRs_response_content: {mutatedMRs_response_content}")
                file_processing.write_TXTfile(path=mutateMRs_response_content_path, content=mutatedMRs_response_content)
            
        response_content = mutatedMRs_response_content
    
    """ prompt: apply generated MRs into more inputs """
    # 还有一个粗暴的办法就是：改MRGen的prompt，直接生成10个tests；就不需要再次生成了。。。这样可以省token，回头试试看效果悬殊大不大。
    inputGen_response_content = None
    inputGen_reasoning_content = None
    if Setting["number_of_tests_per_MR"] > 1:
        print(f"LOG: apply generated MRs into more inputs")
        
        # chat_history
        MRGen_prompt_messages = json_processing.read(prompt_messages_path)
        MRGen_response_content = file_processing.read_TXTfile(response_content_path)
        # chat_history = MRGen_prompt_messages[1:2] # the first one is the system message, so discarded; 只要第一次prompt吧。。。后面的interface就都不要了。。。
        chat_history = MRGen_prompt_messages[1:] # the first one is the system message, so discarded
        chat_history.append({"role": "assistant", "content": MRGen_response_content})
        flag_include_chat_history = True
        
        inputGen_prompt = MR_generator.prompt_apply_MRs_w_more_inputs
        inputGen_promt_id = MR_generator.promt_id + "_inputGen"
        inputGen_prompt_messages_path = f"{prompt_results_content_dir}{inputGen_promt_id}_prompt_messages.md"
        inputGen_response_content_path = f"{prompt_results_content_dir}{inputGen_promt_id}_response_content.md"
        inputGen_reasoning_content_path = f"{prompt_results_content_dir}{inputGen_promt_id}_reasoning_content.md"
        
         # not overwrite previous prompt results
        # if not Setting["overwritePreviousPromptResults"] and not Setting.get("overwritePreviousPromptInputGenResults",False) and file_processing.pathExist(inputGen_response_content_path) and len(file_processing.read_TXTfile(inputGen_response_content_path).split(" ")) > 20: # at least 20 tokens
        if not Setting["overwritePreviousPromptResults"] and file_processing.pathExist(inputGen_response_content_path) and len(file_processing.read_TXTfile(inputGen_response_content_path).split(" ")) > 20: # at least 20 tokens
            inputGen_response_content = file_processing.read_TXTfile(inputGen_response_content_path)
            if file_processing.pathExist(inputGen_reasoning_content_path): 
                inputGen_reasoning_content_path = file_processing.read_TXTfile(inputGen_reasoning_content_path)
            print(f"Skip prompting: {inputGen_response_content_path} has been generated")
        # when self-revise, not overwrite previous prompt results
        elif Setting["number_of_revise"] > 0 and pre_revision_evaluation_result_summary == "executable" and file_processing.pathExist(inputGen_response_content_path) and len(file_processing.read_TXTfile(inputGen_response_content_path).split(" ")) > 20: # at least 20 tokens
            inputGen_response_content = file_processing.read_TXTfile(inputGen_response_content_path)
            print(f"Skip prompting: {inputGen_response_content_path}, because pre_revision_evaluation_result_summary is executable, don't need to revise")
        else:
            inputGen_response_content, inputGen_reasoning_content = request_LLMs.request_LLMs_main(inputGen_prompt, Setting["model"], inputGen_promt_id, Setting["temperature"], prompt_results_content_dir, system_message, few_shot_info, chat_history, flag_include_chat_history, return_reasoning_content=True)
    
        if inputGen_response_content: # 如果inputGen_response_content生成成功，则当作最终结果;用于下一步的解析
            response_content = inputGen_response_content


        

    """ extract and post-process generated MRs class """
    path_prompt_cache_dir_genreated_class = f"{prompt_generated_MRs_dir}{promt_id}.java"
    path_prompt_cache_dir_genreated_class_raw = path_prompt_cache_dir_genreated_class.replace(".java","RAW.java")

    generated_class = parse_LLMs_response.extract_generated_class(response_content, generated_class_name=promt_id)
    if Setting["code_refactoring"] == "RefactorCode":# """ prompt: code refactoring: renaming back """
        # response_content: to do renaming back
        # change to reverse order of OriginalNames_newNames_dict
        for original_name, new_name in sorted(list(OriginalNames_newNames_dict.items()), reverse=True):
            generated_class = generated_class.replace(new_name, original_name)
    if not generated_class:
        print(f"LOG: generated_class is empty, promt_id: {promt_id}")
        file_processing.write_TXTfile(path=path_prompt_cache_dir_genreated_class, content="empty")
    else:
        file_processing.write_TXTfile(path=path_prompt_cache_dir_genreated_class_raw, content=generated_class)
        generated_class = post_process_MRs(MR_generator, generated_class,MTC_item, path_prompt_cache_dir_genreated_class)
        file_processing.write_TXTfile(path=path_prompt_cache_dir_genreated_class, content=generated_class)
        
        
    
    MR_generator.prompt_messages_path = prompt_messages_path
    MR_generator.response_content_path = response_content_path
    

def post_process_MRs(MR_generator,generated_class,MTC_item, path_prompt_cache_dir_genreated_class):
    # prepare
    genreated_test_class_name = MR_generator.genreated_test_class_name
    target_methods_FQN = MR_generator.target_methods_FQN
    MTC_class_test_file = MR_generator.path_MTC_version_testclass_file
    MTC_class_test_file_content = file_processing.read_TXTfile(MTC_class_test_file)
    poj_dir = MTC_item["poj_dir"] 

    """ check_generated_class: in case of LM change default class name """
    class_def_line =""
    for line in generated_class.split("\n"):
        if line.startswith("public class "): class_def_line = line; break 
        #  public final class MkGithubTest { 
        if line.startswith("public ") and " class " in line: class_def_line = line; break
        # class SkipListTest {
        if line.startswith("class ") and line.endswith("{"): class_def_line = line; break 
    if genreated_test_class_name not in class_def_line:
        correct_class_def_line = f"public class {genreated_test_class_name} {{"
        print(f"LOG: generated version: class_def_line: {class_def_line} is not correct, replace with {correct_class_def_line}")
        generated_class = generated_class.replace(class_def_line, correct_class_def_line)


    """ package_statement """
    package_line = MTC_class_test_file_content.split("\n")[:0]
    for line in MTC_class_test_file_content.split("\n"):
        if line.startswith("package "): package_line = line; break
        if line.strip().startswith("package "): package_line = line; break
    invoked_package_FQN = package_line.replace('package ','').replace(';','').strip() # 最准确啦

    package_statement = f"package {invoked_package_FQN};"
    # print("LOG:generated_class 1: ", generated_class)

    # using re to identify "package [a-zA-Z0-9.]*;" and replace it with "package [a-zA-Z0-9.]*.MRs;"
    pattern = r'package [a-zA-Z0-9.]*;'
    matches = re.findall(pattern, generated_class)
    if len( matches ) >1:
        print( "len( matches ) >1:", len(matches) )
    elif len( matches ) ==1:
        generated_class = generated_class.replace(matches[0], f"{package_statement}")
    elif len( matches ) ==0:
        generated_class = f"{package_statement}\n\n{generated_class}"
    # print("LOG:generated_class 2: ", generated_class)

    """ add junit """
    pattern = r'@Test'
    matches = re.findall(pattern, generated_class)
    if len( matches ) >0: # 说明有生成test
        # 说明没有import junit statement, 默认用Junit4
        if Junit4_STATEMENT.split("\n")[0] not in generated_class\
            and Junit5_STATEMENT.split("\n")[0] not in generated_class: 
            generated_class = generated_class.replace(f"{package_statement}", f"{package_statement}\n\n{Junit4_STATEMENT}")

    # print("LOG:generated_class 2.: ", generated_class)

    import_dependencies_CUT = []
    """ add CUT in import statements """
    # target_methods_FQN
    target_class_FQN = [ (".").join(ele.split("(")[0].split(".")[:-1]) for ele in target_methods_FQN] 
    import_dependencies_CUT = list(set(target_class_FQN))
    # import_dependencies_CUT = MTC_item["dependency"].split(";") # GT
    print("LOG: import_dependencies_CUT: ", import_dependencies_CUT)
    
    """ add generated class needed dependency """
    

    searched_involvded_dependencies = []
    searched_definedClassesORdependencies = []
    """ import involved depedency """
    try:
        """ get defined variables in inputMRsformation function """
        # tem store the file for javaparser
        tem_store_MR_file_path = path_prompt_cache_dir_genreated_class.replace(".java",".tmp")
        file_processing.write_TXTfile(path=tem_store_MR_file_path, content=generated_class)
        function = "getInvolvedClassInMethod" # getDeclaredVariablesInMethod getMethod getDeclaredVariablesInMethod

        # FQN_testMethos_name = FQN_testMethos.split(".")[-1].replace("()","")
        # method_name=f"inputMRsformation_{FQN_testMethos_name}"
        method_name = "testMR1" # TO UPDATE: there are more than one testMR

        involvedClasses = []
        involvedClass_str = java_parser.getInvolvedClassInMethod(tem_store_MR_file_path, method_name, function)
        # IntArrayList:a2;int:i;boolean:trimFlag2;List<Object>:MRsformed_inputs
        involvedClasses = involvedClass_str.replace(":"," ").replace("\n"," ").split(";")

        java_primitive_types = ['byte', 'short', 'int', 'long', 'float', 'double', 'boolean', 'char', 'String']
        defined_varible_Types = [ ele.split(" ")[0] for ele in involvedClasses if ele.split(" ")[0] not in java_primitive_types]
        defined_varible_Types = list(set(defined_varible_Types))
        """ add template needed dependency """
        # search the poj dir to find java file named as type
        poj_dir = MTC_class_test_file.split("src/")[0]
        files_path = file_processing.walk_FileDir(poj_dir)
        # and then, give me the fully-qualified name of this class
        if len(defined_varible_Types) > 0:
            for file in files_path:
                if file.endswith(".java"):
                    class_name = file.split("/")[-1].replace(".java", "")
                    if class_name in defined_varible_Types:
                        file_content = file_processing.read_TXTfile(file)
                        package_line_here = file_content.split("\n")[:0]

                        for line in file_content.split("\n"):
                            if line.startswith("package "): package_line_here = line; break
                        package_FQN = package_line_here.replace('package ','').replace(';','').strip() # 最准确啦
                        class_FQN = f"{package_FQN}.{class_name}"
                        searched_involvded_dependencies.append(class_FQN)   
                        searched_definedClassesORdependencies.append(class_FQN) 
    except Exception as e:
        print("LOG: import involved depedency error: ", e)
    
    if len(searched_definedClassesORdependencies) > 0:
        print("LOG: searched_definedClassesORdependencies>0: ", searched_definedClassesORdependencies)
        if switch: # refinement: add dependency
            for ele in searched_definedClassesORdependencies:
                if ele not in import_dependencies_CUT:
                    import_dependencies_CUT.append(ele)

    import_dependencies_template_need = [ "java.util.List", "java.util.Arrays"]
    import_dependencies = import_dependencies_CUT + import_dependencies_template_need
    import_statement = ("\n").join( [f"import {ele};" for ele in import_dependencies if f".{ele.split('.')[-1]};" not in generated_class ] ) # avoid duplicate import
    generated_class = generated_class.replace(f"{package_statement}", f"{package_statement}\n\n{import_statement}")
    # print("LOG:generated_class 3: ", generated_class)

    """ add original MTC class's dependency """
    # check if the dependency is in the generated class
    # get all import statements in MTC_class_test_file_content
    origianl_MTC_import_statements_list= []
    for line in MTC_class_test_file_content.split("\n"):
        if line.startswith("import "):
            origianl_MTC_import_statements_list.append(line)
    
    origianl_MTC_import_statements_block = ""
    for ele in origianl_MTC_import_statements_list:
        ele_class = ele.split('.')[-1]
        if f"{ele}" not in generated_class and f".{ele_class}" not in generated_class: # avoid duplicate import
            origianl_MTC_import_statements_block += f"{ele}\n"
    # origianl_MTC_import_statements_block = ("\n").join([ ele for ele in origianl_MTC_import_statements_list if f".{ele.split('.')[-1]}" not in generated_class]) # avoid duplicate import
    generated_class = generated_class.replace(f"{package_statement}", f"{package_statement}\n\n{origianl_MTC_import_statements_block}")
    # print("LOG:generated_class 4: ", generated_class)


    # """ exclude irrelevant code in input MRsformation function """ 
    # sourceInputsContent = MTC_item["sourceInput"]
    # followUpInputsContent = MTC_item["followUpInput"]
    # followUpInputs_TypeAndVariable = []
    # if len(followUpInputsContent) >1:
    #     followUpInputs_TypeAndVariable = ["List<Object> MRsformed_inputs"]
    # else:
    #     followUpInput = followUpInputsContent[0]
    #     followUpInputs_TypeAndVariable.append( f"{followUpInput['type']} {followUpInput['expression']}" )
    # # """ get all_relevant_variables   """
    # # tem store the file for javaparser
    # tem_store_MR_file_path = MTC_class_test_file.replace(".java",".tmp_IT")
    # file_processing.write_TXTfile(path=tem_store_MR_file_path, content=generated_class)
    # FQN_testMethos_name = FQN_testMethos.split(".")[-1].replace("()","")
    # function = "getMethod" # getDeclaredVariablesInMethod getMethod
    # method_name=f"inputMRsformation_{FQN_testMethos_name}"
    # defined_varible_TypeAndname = []
    # original_method_content = java_parser.get_method_body_or_related_class_field(tem_store_MR_file_path, method_name, function)
    
    # all_relevant_variables =  extract_code.variableDefExtractor(original_method_content, followUpInputs_TypeAndVariable).get_all_relevant_variables()
    # all_relevant_variables_str = ""
    # for var in all_relevant_variables:
    #     all_relevant_variables_str += f'{var["type"]}/{var["name"]}:'
    # all_relevant_variables_str = all_relevant_variables_str.rstrip(":")
    # # """ get udpated_function   """ # to be improved with more concise implementation
    # udpated_method_content = java_parser.getVaribleRelevantCode(tem_store_MR_file_path, method_name, all_relevant_variables_str.rstrip(":"), function)
    # if udpated_method_content != original_method_content:
    #     print("LOG: udpated_method_content != original_method_content ")
    #     print("LOG: original_method_content:\n ", original_method_content)
    #     print("LOG: udpated_method_content:\n ", udpated_method_content)
    #     if switch:
    #         generated_class = generated_class.replace(original_method_content, udpated_method_content)

    return generated_class


def post_process_comment_faulty_tests_and_imports(path_of_generated_MRs_in_cache, Path_compilation_log):
    # BACKUP
    file_processing.copyFile(source=path_of_generated_MRs_in_cache,target=path_of_generated_MRs_in_cache.replace(".java",".beforeComment.java")) 
    file_processing.copyFile(source=Path_compilation_log,target=Path_compilation_log.replace(".log",".beforeComment.log")) 

    source_code = file_processing.read_TXTfile(path_of_generated_MRs_in_cache)
    log = file_processing.read_TXTfile(Path_compilation_log)
    udpated_source_code = java_file_processing.comment_faulty_test_cases(source_code, log)
    file_processing.write_TXTfile(path_of_generated_MRs_in_cache, udpated_source_code)
    print(f"LOG: comment_faulty_test_cases: {path_of_generated_MRs_in_cache} has been updated")


# new: for testing in the original poj
def test_generated_MRs(MR_generator, skipCompileIfExist=True, commentFaultyCode=True, fixed_or_buggy_version="BUGGY"):
    """
    prepare: cp GT_MRs -> src/; and compile;if success: 
    cp generated_MTC_MRs -> src/; and compile > .log;
    if success: do testing > .log (refer to AutoMR的做法)
    复位: cp GT_MRs -> src/; and compile;
    """
    # prepare
    MTC_item = MR_generator.MTC_item
    MTC_FQN = MR_generator.MTC_FQN
    prompt_generated_MRs_dir = MR_generator.prompt_generated_MRs_dir
    evaluation_execution_log_dir = MR_generator.evaluation_execution_log_dir
    log_dir = MR_generator.compilation_log_dir
    genreated_test_class_name = MR_generator.genreated_test_class_name
    genreated_test_class_FQN = MR_generator.genreated_test_class_FQN
    invoked_package_FQN = MR_generator.invoked_package_FQN
    # processed_crafted_GT_MTC_test_class_name = genreated_test_class_name
    test_file_path = MR_generator.path_MTC_version_testclass_file
    dir_MTCFQN_VERSION_BUGREV_generated_tests = MR_generator.dir_MTCFQN_VERSION_BUGREV_generated_tests
    dir_MTCFQN_VERSION_BUGREV_generated_Major_mutants = MR_generator.dir_MTCFQN_VERSION_BUGREV_generated_Major_mutants
    task_type = MR_generator.Setting["task_type"]
    poj_dir = MR_generator.MTC_version_poj_dir
    prompt_messages_path = MR_generator.prompt_messages_path
    response_content_path = MR_generator.response_content_path
    target_CUTs_FQNs = MR_generator.target_CUTs_FQNs
    target_CUTs_pathes = MR_generator.target_CUTs_pathes
    poj_build_tool = MR_generator.poj_build_tool
    jdk_version = MR_generator.jdk_version
    target_methods_FQS = MR_generator.target_methods_FQN
    invoked_methods_FQS = MR_generator.invoked_methods_FQS
    suggested_methods_FQS = MR_generator.suggested_methods_FQS
    Setting = MR_generator.Setting
    task_symbol = MR_generator.task_symbol # task_symbol = f"{task_symbol_prefix}{index}"
    task_symbol_prefix = MR_generator.task_symbol_prefix
    task_symbol_index = MR_generator.task_symbol_index

    if fixed_or_buggy_version == "FIXED": # 更改路径 
        commitID = MR_generator.fixed_version_commitID
        dir_MTCFQN_VERSION_BUGREV = DIR_MTCFQN_VERSION_BUGREV % (MTC_FQN, commitID)
        poj_dir = dir_MTCFQN_VERSION_BUGREV.removesuffix("BugRev/")
        test_file_path = test_file_path.replace(MR_generator.commitID, MR_generator.fixed_version_commitID)
        dir_MTCFQN_VERSION_BUGREV_generated_tests = f"{dir_MTCFQN_VERSION_BUGREV}/generated_tests/"
        # log_dir
        # evaluation_execution_log_dir

    Test_result = {"MTC_item":MTC_item, 
                   "ES_result": None,
                   "LLM_direct_prompt_result": None, # LLMI: LLM generated new inputs
    }

    poj_name = poj_dir
    # test_file = file_processing.read_TXTfile(test_file_path)
    # package_line = test_file.split("\n")[:0]
    # for line in test_file.split("\n"):
    #     if line.startswith("package "): package_line = line; break
    #     if line.strip().startswith("package "): package_line = line; break
    # invoked_package_FQN = package_line.replace('package ','').replace(';','').strip() # 最准确啦
    

    print("test generated MRs: ", genreated_test_class_name)   
    """compile generated MRs class in original poj"""
    dir_of_generated_tests_in_original_poj = f"{dir_MTCFQN_VERSION_BUGREV_generated_tests}/{task_type}/"
    dir_of_generated_MRs_in_original_poj = f"{dir_of_generated_tests_in_original_poj}/{invoked_package_FQN.replace('.','/')}/"
    file_processing.creatFolder_recursively_IfExistPass(dir_of_generated_MRs_in_original_poj)
    path_of_generated_MRs_in_original_poj = f"{dir_of_generated_MRs_in_original_poj}{genreated_test_class_name}.java"
    # 复位: rm generated MRs in original poj
    file_processing.remove_file(path_of_generated_MRs_in_original_poj)
    file_processing.remove_file(path_of_generated_MRs_in_original_poj.replace(".java",".class"))
    if file_processing.pathExist(path_of_generated_MRs_in_original_poj+"/"): file_processing.remove_folder(path_of_generated_MRs_in_original_poj+"/") # 历史遗留错误。。20250720
    
    # copy: cache -> original poj
    path_of_generated_MRs_in_cache = f"{prompt_generated_MRs_dir}{genreated_test_class_name}.java"
    file_processing.copyFile(source=path_of_generated_MRs_in_cache,target=path_of_generated_MRs_in_original_poj)
    
    # compile
    Path_compilation_log = f"{log_dir}{genreated_test_class_name}_compile_{fixed_or_buggy_version}.log"
    if skipCompileIfExist and file_processing.pathExist(path_of_generated_MRs_in_cache.replace(".java",".class")):
        file_processing.copyFile(source=path_of_generated_MRs_in_cache.replace(".java",".class"),target=path_of_generated_MRs_in_original_poj.replace(".java",".class"))
        Test_result[f"generatedMR_compile_result_{fixed_or_buggy_version}"] = True
        print(f"Skip: {path_of_generated_MRs_in_cache} has been compiled")
    else:
        CMD_CD = f"cd {poj_dir};"
        PATH_JAVAC = compile_java_poj.get_jdkc_path(jdk_version)
        # path_of_generated_MRs_in_original_poj
        # generated_dot_class_path = path_of_generated_MRs_in_original_poj.replace(".java", ".class")
        cmd_result = java_test.compile_test_class_general(poj_build_tool, poj_name, CMD_CD, poj_dir, CP_jar_path="", extra_cp="", Path_TestFile_to_compile = path_of_generated_MRs_in_original_poj, PATH_JAVAC=PATH_JAVAC, log_dir=log_dir, log_file_suffix=f"{fixed_or_buggy_version}")

        if cmd_result != 0 and commentFaultyCode: # compile error, comment faulty code, and compile again
            post_process_comment_faulty_tests_and_imports(path_of_generated_MRs_in_cache, Path_compilation_log)
            file_processing.copyFile(source=path_of_generated_MRs_in_cache,target=path_of_generated_MRs_in_original_poj)
            # test_generated_MRs(MR_generator, skipCompileIfExist=skipCompileIfExist, commentFaultyCode=False, fixed_or_buggy_version="BUGGY") # 递归, 仅一次
            cmd_result = java_test.compile_test_class_general(poj_build_tool, poj_name, CMD_CD, poj_dir, CP_jar_path="", extra_cp="", Path_TestFile_to_compile = path_of_generated_MRs_in_original_poj, PATH_JAVAC=PATH_JAVAC, log_dir=log_dir, log_file_suffix=f"{fixed_or_buggy_version}")

        if cmd_result != 0:
            Test_result[f"generatedMR_compile_result_{fixed_or_buggy_version}"] = False
        else:
            Test_result[f"generatedMR_compile_result_{fixed_or_buggy_version}"] = True
            # 放回cache中，备份一下。
            file_processing.copyFile(source=path_of_generated_MRs_in_original_poj.replace(".java",".class") ,target=path_of_generated_MRs_in_cache.replace(".java",".class"))
            
            """option 2: prepare more test inputs for one MR"""
            # TODO: 
            # original java -> .java.OneTestPerMR
            # updated java
            
    # Test_result[f"generatedMR_compile_result_{fixed_or_buggy_version}"] = True
    """ validation: run on Major mutants """
    # generate mutants
    print(f"run_major")
    # 清楚历史遗留
    # file_processing.remove_folder(f"{dir_MTCFQN_VERSION_BUGREV_generated_Major_mutants}")
    # file_processing.creatFolder_recursively_IfExistPass(f"{dir_MTCFQN_VERSION_BUGREV_generated_Major_mutants}")
    exe_result = run_major.run_major(
        poj_dir=poj_dir,
        source_files=target_CUTs_pathes,
        output_dir=f"{dir_MTCFQN_VERSION_BUGREV_generated_Major_mutants}",
        java_home= compile_java_poj.get_jdk_home(jdk_version)
    )
    # second try:
    if not exe_result:
        print(f"run_major failed, second try")
        exe_result = run_major.run_major(
            poj_dir=poj_dir,
            source_files=target_CUTs_pathes,
            output_dir=f"{dir_MTCFQN_VERSION_BUGREV_generated_Major_mutants}",
            java_home= compile_java_poj.get_jdk_home(11)
        )
        print(f"run_major failed, second try: {exe_result}")
    EXE_RESULT_on_Major_mutants = None
    if exe_result:
        # run generated MRs genreated_test_class_FQN on mutants
        print(f"run generated MRs on Major mutants")
        Path_execution_log_on_Major_mutants = f"{evaluation_execution_log_dir}{genreated_test_class_name}{fixed_or_buggy_version}_on_Major_mutants.log"
        Path_execution_result_on_Major_mutants = f"{evaluation_execution_log_dir}{genreated_test_class_name}{fixed_or_buggy_version}_on_Major_mutants.json"
        
        major_jar_path = "/software/major/lib/major.jar:/software/major/lib/major-rt.jar"
        print(f"exe test on Major mutants: {MTC_FQN} {genreated_test_class_name} {genreated_test_class_FQN}")
        # EXE_RESULT_on_Major_mutants = java_test.test_runner(poj_dir=poj_dir, jdk_version=jdk_version, target_class_FQN=genreated_test_class_FQN, Path_execution_log=Path_execution_log_on_Major_mutants, Path_execution_result=Path_execution_result_on_Major_mutants, Path_test_file=path_of_generated_MRs_in_original_poj, poj_build_tool=poj_build_tool, high_priority_cp=f"{dir_of_generated_tests_in_original_poj}:{dir_MTCFQN_VERSION_BUGREV_generated_Major_mutants}/Major_generated_mutants/",ifExeResult_skip= not Setting["overwritePreviousEvaluationResults"]) # buggy?
        EXE_RESULT_on_Major_mutants = java_test.test_runner(poj_dir=poj_dir, jdk_version=jdk_version, target_class_FQN=genreated_test_class_FQN, Path_execution_log=Path_execution_log_on_Major_mutants, Path_execution_result=Path_execution_result_on_Major_mutants, Path_test_file=path_of_generated_MRs_in_original_poj, poj_build_tool=poj_build_tool, high_priority_cp=f"{dir_of_generated_tests_in_original_poj}:{dir_MTCFQN_VERSION_BUGREV_generated_Major_mutants}:{major_jar_path}",ifExeResult_skip= not Setting["overwritePreviousEvaluationResults"]) # fixed: 
    Test_result[f"generatedMR_exe_result_{fixed_or_buggy_version}_on_Major_mutants"] = EXE_RESULT_on_Major_mutants
    print(f"run generated MRs on Major mutants (result): {EXE_RESULT_on_Major_mutants}")
    

    """ evluation: generated MRs """
    # test generated MRs
    Path_execution_result = f"{evaluation_execution_log_dir}{genreated_test_class_name}{fixed_or_buggy_version}.json"
    Path_execution_log = f"{evaluation_execution_log_dir}{genreated_test_class_name}{fixed_or_buggy_version}.log"
    if not Setting["overwritePreviousEvaluationResults"] and file_processing.pathExist(Path_execution_result): pass
    else:
        # 清除历史遗留
        Path_test_file = path_of_generated_MRs_in_original_poj
        Path_test_class_file = Path_test_file.replace(".java", ".class")
        if file_processing.pathExist(Path_execution_result): file_processing.remove_file(Path_execution_result)
        if file_processing.pathExist(Path_execution_log): file_processing.remove_file(Path_execution_log)
        if file_processing.pathExist(Path_test_file+"/"): file_processing.remove_folder(Path_test_file+"/") # remove folder...

        print(f"exe test: {MTC_FQN} {genreated_test_class_name}")
        # test on the original verson
        EXE_RESULT = java_test.test_runner(poj_dir=poj_dir, jdk_version=jdk_version, target_class_FQN=genreated_test_class_FQN, Path_execution_log=Path_execution_log, Path_execution_result=Path_execution_result, Path_test_file=Path_test_file, poj_build_tool=poj_build_tool, extra_cp=dir_of_generated_tests_in_original_poj,
        ifExeResult_skip= not Setting["overwritePreviousEvaluationResults"])
        
        # TODO: test on the mutated verson
        # give different class pass, ignore/delete original test class OR, put the new pass at the beginning to overwrite the original class? TOCHEK: ask GPT, whether this can work?
        EXE_RESULT_MUTATED = None
    
    Test_result[f"generatedMR_exe_result_{fixed_or_buggy_version}"] = EXE_RESULT
    Test_result[f"generatedMR_exe_result_{fixed_or_buggy_version}MUTATED"] = EXE_RESULT_MUTATED
    # print(f"EXE_RESULT:  {EXE_RESULT}")

    """ run Pit """
    if fixed_or_buggy_version == "latest" and Setting.get("Pit", False): # 节省时间，latest 暂时也不用跑了。。。 # 需要时再跑
        # TODO, reminder: 20250824, 估计result collection时，还得处理一下。
        print("---run PITest---", genreated_test_class_name)
        genreated_green_test_class_name = f"{genreated_test_class_name}_green"
        genreated_green_test_class_FQN = f"{genreated_test_class_FQN}_green"
        path_of_generated_green_MRs_in_cache = path_of_generated_MRs_in_cache.replace(".java","_green.java")
        path_of_generated_green_MRs_in_original_poj = path_of_generated_MRs_in_original_poj.replace(".java","_green.java")

        # create green test suite
        # num_of_passed_test_cases = EXE_RESULT["num_of_passed_test_cases"]
        failure_info = EXE_RESULT[genreated_test_class_FQN]["failure_info"]
        non_passed_test_case_names = list( failure_info.keys() )
        # delete or comment non_passed_test_case_names in path_of_generated_MRs_in_original_poj
        green_generated_MRsTC_class = java_file_processing.remove_test_cases(path_of_generated_MRs_in_cache, non_passed_test_case_names)
        green_generated_MRsTC_class = green_generated_MRsTC_class.replace(f"public class {genreated_test_class_name}", f"public class {genreated_green_test_class_name}") # change class name to {class_name}_green
        file_processing.write_TXTfile(path=path_of_generated_green_MRs_in_cache, content=green_generated_MRsTC_class)
        file_processing.copyFile(source=path_of_generated_green_MRs_in_cache,target=path_of_generated_green_MRs_in_original_poj)
        
        # compile green test suite
        if skipCompileIfExist and file_processing.pathExist(path_of_generated_green_MRs_in_cache.replace(".java",".class")):
            # 20250717: previous version
            if file_processing.pathExist(path_of_generated_green_MRs_in_original_poj.replace(".java",".class")): file_processing.remove_file(path_of_generated_green_MRs_in_original_poj.replace(".java",".class"))# 清除历史遗留
            file_processing.copyFile(source=path_of_generated_green_MRs_in_cache.replace(".java",".class"),target=path_of_generated_green_MRs_in_original_poj.replace(".java",".class"))
            print(f"Skip: {path_of_generated_green_MRs_in_cache} has been compiled")
            
        else:
            cmd_result = java_test.compile_test_class_general(poj_build_tool, poj_name, CMD_CD, poj_dir, CP_jar_path="", extra_cp="", Path_TestFile_to_compile = path_of_generated_green_MRs_in_original_poj, PATH_JAVAC=PATH_JAVAC, log_dir=log_dir, log_file_suffix=f"{fixed_or_buggy_version}_green")
            
            
            if cmd_result != 0:
                Test_result[f"generatedMR_compile_result_{fixed_or_buggy_version}_green"] = False
            else:
                Test_result[f"generatedMR_compile_result_{fixed_or_buggy_version}_green"] = True
                # 放回cache中，备份一下。
                file_processing.copyFile(source=path_of_generated_green_MRs_in_original_poj.replace(".java",".class") ,target=path_of_generated_green_MRs_in_cache.replace(".java",".class"))
            print("compile for pit: ", Test_result[f"generatedMR_compile_result_{fixed_or_buggy_version}_green"])
            print("---path_of_generated_green_MRs_in_original_poj", path_of_generated_green_MRs_in_original_poj)
        
        # 20250717: (updated) copy all previously generated test suite here for pit
        # task_symbol="P1", task_symbol_prefix="P" , task_symbol_index=1
        path_of_generated_green_MRs_class_in_cache = path_of_generated_green_MRs_in_cache.replace(".java",".class")
        path_of_generated_green_MRs_class_in_original_poj = path_of_generated_green_MRs_in_original_poj.replace(".java",".class")
        previous_task_symbol_index = task_symbol_index-1 # start from the latest one
        all_genreated_green_test_class_FQNs = [genreated_green_test_class_FQN]
        # TODO: if want to include other requests. replace "generateMRs/..._Rev1_1/" with "generateMRs/..._Rev1_0/"
        while previous_task_symbol_index >= 0:
            previous_task_symbol = f"{task_symbol_prefix}{previous_task_symbol_index}"
            previous_path_of_generated_green_MRs_class_in_cache = path_of_generated_green_MRs_class_in_cache.replace(f"_{task_symbol}_", f"_{previous_task_symbol}_")
            previous_path_of_generated_green_MRs_class_in_original_poj = path_of_generated_green_MRs_class_in_original_poj.replace(f"_{task_symbol}_", f"_{previous_task_symbol}_")
            # 清除历史遗留
            file_processing.remove_file(previous_path_of_generated_green_MRs_class_in_original_poj)
            # copy
            file_processing.copyFile(source=previous_path_of_generated_green_MRs_class_in_cache,target=previous_path_of_generated_green_MRs_class_in_original_poj)
            print(f"copy all previously generated: {previous_path_of_generated_green_MRs_class_in_cache} has been compiled")
            previous_task_symbol_index -= 1
            
            all_genreated_green_test_class_FQNs.append( genreated_green_test_class_FQN.replace(f"_{task_symbol}_", f"_{previous_task_symbol}_") ) 
        
        # run PITest
        # target_methods_FQS invoked_methods_FQS =
        pit_target_methd_names = [ele.split(".")[-1].split("(")[0] for ele in invoked_methods_FQS] # take all invoked methods as targets
        pit_runner = PIT.pitRunner()
        # pit_runner.FullyQuilfiedName_TestForCUT = genreated_green_test_class_FQN # only the current test class 
        pit_runner.FullyQuilfiedName_TestForCUT = (",").join(all_genreated_green_test_class_FQNs) # all the test classes
        pit_runner.DIR_POJ = poj_dir
        pit_runner.poj = poj_name
        pit_runner.FQN_CUTs_formal = (",").join(target_CUTs_FQNs) 
        pit_runner.MTC_test_file_path = test_file_path
        pit_runner.poj_build_tool = poj_build_tool
        pit_runner.extra_cp = dir_of_generated_tests_in_original_poj #f"../generated_tests/direct_promt/"  
        pit_runner.keyname_id = genreated_green_test_class_name
        pit_runner.target_method_names = pit_target_methd_names
        pit_runner.path_pit_result = f"{evaluation_execution_log_dir}PIT_{genreated_green_test_class_name}.json"
        if "overwritePreviousPIT" in Setting and not Setting["overwritePreviousPIT"] and file_processing.pathExist(pit_runner.path_pit_result): 
            print(f"Skip: {pit_runner.path_pit_result} already exists")
        else:
            PIT.PIT_runner_general(pit_runner)
        # if not file_processing.pathExist(pit_runner.path_pit_result) or len(file_processing.read_TXTfile(pit_runner.path_pit_result))<30: time.sleep(60) # wait for the file to be written
        # PIT_result = PIT.analyze_pit_exe_result(pit_runner.path_pit_result)
        
            
        PIT_result = json_processing.read(pit_runner.path_pit_result)
        Test_result[f"PIT_{fixed_or_buggy_version}_green"] = PIT_result
        print("---end PITest: genreated_test_class_name ---", genreated_test_class_name)

        """ PIT: oMTC """
        # prepare oMTC only class
        """ 
            delete all other tests, replace class name as {class}_{MTC}_o.java
            cp to buReve/developer_written_tests/ 
            compile
        """
        dir_of_developer_written_tests_in_original_poj = dir_of_generated_tests_in_original_poj.replace("generated_tests","developer_written_tests")
        path_MTC_version_testclass_file = test_file_path # test_file_path = MR_generator.path_MTC_version_testclass_file
        MTC_name =  MTC_FQN.split(".")[-1]
        MTC_class_name = MTC_FQN.split(".")[-2]
        oMTC_class_name = f"{MTC_class_name}_{MTC_name}_o"
        oMTC_FQN = f"{invoked_package_FQN}.{oMTC_class_name}"
        oMTC_dir = f"{dir_of_developer_written_tests_in_original_poj}/{invoked_package_FQN.replace('.','/')}/"
        oMTC_path = f"{oMTC_dir}/{oMTC_class_name}.java"
        file_processing.creatFolder_recursively_IfExistPass(oMTC_dir)
        # updated_java_class
        MTC_class_content = file_processing.read_TXTfile(path_MTC_version_testclass_file)
        # updated_java_class = java_file_processing.comment_target_method(test_class_text=MTC_class_content, target_method_name=MTC_name, only_keep_target_method=True, keep_helper_methods=True)
        updated_java_class = java_file_processing.comment_target_test_method(test_class_text=MTC_class_content, target_method_name=MTC_name, only_keep_target_method=True, keep_helper_methods=True)
        # change class name 
        if f"public class {MTC_class_name}\n" in updated_java_class: # special case
            updated_java_class = updated_java_class.replace(f"public class {MTC_class_name}\n", f"public class {oMTC_class_name}\n")
        else:
            updated_java_class = updated_java_class.replace(f"public class {MTC_class_name} ", f"public class {oMTC_class_name} ")
        # post-process: add depdendencies, import
        # option1  target_methods_FQN
        # target_class_FQN = [ (".").join(ele.split(".")[:-1]) for ele in target_methods_FQN] 
        # import_dependencies_CUT = list(set(target_class_FQN))
        # option2  MTC_class_name基于MTC class的名字
        target_class_FQN = invoked_package_FQN + "." + MTC_class_name.replace("Test","")
        # updated_java_class = updated_java_class.replace(f"public class {oMTC_class_name}", f"import {target_class_FQN};\npublic class {oMTC_class_name}") # option1
        updated_java_class = updated_java_class.replace(f"package {invoked_package_FQN};", f"package {invoked_package_FQN};\nimport {target_class_FQN};") # option2
        # store 
        file_processing.write_TXTfile(path=oMTC_path, content=updated_java_class)
        print("---end prepare oMTC only class---", oMTC_path)

        # compile this class    
        cmd_result = java_test.compile_test_class_general(poj_build_tool, poj_name, CMD_CD, poj_dir, CP_jar_path="", extra_cp="", Path_TestFile_to_compile = oMTC_path, PATH_JAVAC=PATH_JAVAC, log_dir=log_dir, log_file_suffix=f"oMTC_only")

        if cmd_result != 0:
            Test_result[f"generatedMR_compile_result_oMTC_only"] = False
        else:
            Test_result[f"generatedMR_compile_result_oMTC_only"] = True
        print("compile for pit: ", Test_result[f"generatedMR_compile_result_oMTC_only"])
        print(f"log_path: cache/generateMRs/compilation_log/{oMTC_path.split('/')[-1].split('.')[0]}_compile_oMTC_only.log")
        print("---end compile oMTC only class---", oMTC_path)

        # run PITest, reuse previsou object pit_runner
        # add class path
        pit_runner_o = PIT.pitRunner()
        pit_runner_o.DIR_POJ = poj_dir
        pit_runner_o.poj = poj_name
        pit_runner_o.FQN_CUTs_formal = (",").join(target_CUTs_FQNs) 
        pit_runner_o.poj_build_tool = poj_build_tool
        pit_runner_o.FullyQuilfiedName_TestForCUT = oMTC_FQN # 
        pit_runner_o.MTC_test_file_path = oMTC_path   # 
        pit_runner_o.extra_cp = dir_of_developer_written_tests_in_original_poj #  
        pit_runner_o.keyname_id = oMTC_class_name # 
        pit_runner_o.path_pit_result = f"{evaluation_execution_log_dir}PIT_{oMTC_class_name}.json" # 
        pit_runner_o.target_method_names = pit_target_methd_names
        if "overwritePreviousPIT" in Setting and not Setting["overwritePreviousPIT"] and file_processing.pathExist(pit_runner_o.path_pit_result): 
            print(f"Skip: {pit_runner_o.path_pit_result} already exists")
        else:
            PIT.PIT_runner_general(pit_runner_o)
        # PIT.PIT_runner_general(pit_runner_o)
        # if not file_processing.pathExist(pit_runner_o.path_pit_result) or len(file_processing.read_TXTfile(pit_runner_o.path_pit_result))<30: time.sleep(60) # wait for the file to be written
        # PIT_result = PIT.analyze_pit_exe_result(pit_runner_o.path_pit_result)
        PIT_result = json_processing.read(pit_runner_o.path_pit_result)
        Test_result[f"PIT_oMTC_only"] = PIT_result
        print("---end PITest: oMTC_class_name ---", oMTC_class_name)


    """ 2. compile and execute on the fixed version  """
    if fixed_or_buggy_version == "BUGGY": # 不然，无限套娃了
        print("---test generated MRs on the fixed version---")
        Test_result_fixed_version = test_generated_MRs(MR_generator, skipCompileIfExist, commentFaultyCode, fixed_or_buggy_version="FIXED")
        Test_result[f"generatedMR_exe_result_FIXED"] = Test_result_fixed_version["generatedMR_exe_result_FIXED"]
        Test_result[f"generatedMR_compile_result_FIXED"] = Test_result_fixed_version["generatedMR_compile_result_FIXED"]
    if fixed_or_buggy_version == "FIXED": # already finish the compile and exe, can return the result 
        return Test_result

    # TODO
    Test_result["ES_result"] = None

    Test_result["generated_MR_testClass_FQN"] = genreated_test_class_FQN
    """ whether generated tests are MTCs? """
    if Setting["MRScout"]: # not elegent....
        print("---MRScout---")
        DIR_AUTOMR_DEMO_POJ = config.DIR_AUTOMR_DEMO_POJ
        cd_cmd = f"cd {DIR_AUTOMR_DEMO_POJ};" 
        env_dir = config.DIR_ENV
        java_path = config.PATH_JAVA_11
        argfile_path = config.AUTOMR_JAVA_DEMO_JAR_PATH
        Main_path = "com.example.Main"
        pojname = poj_dir.strip("/").split("/")[-1]
        # specifiedTestFile = path_of_generated_MRs_in_original_poj # why not used the original poj?
        specifiedTestFile = path_of_generated_MRs_in_cache
        exe_log_path = f"{evaluation_execution_log_dir}{genreated_test_class_name}_MRScout.output"
        print("file_processing.pathExist(specifiedTestFile)", file_processing.pathExist(specifiedTestFile), specifiedTestFile)
        cmd = f'{cd_cmd} nohup {env_dir} {java_path} -cp {argfile_path} {Main_path} "{pojname}" "{poj_dir}" "{specifiedTestFile}" > {exe_log_path} 2>&1 &'
        if file_processing.pathExist(exe_log_path) and not Setting.get("overwritePreviousMRScout", True): 
            print(f"Skip MRScout: {exe_log_path} already exists")
        else:
            exe_res = os.system( cmd )
            print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), f'{poj_dir}  cve_exe_cmd: {exe_res} cmd: {cmd}')
        # time.sleep(5) # 给点时间，让MRScout跑完
        budget = Setting["timeout"] # 给点时间，让MRScout跑完
        while budget>0:
            # PID_tool_main_end: finish
            if file_processing.pathExist(exe_log_path) and 'PID_tool_main_end:' in file_processing.read_TXTfile(exe_log_path): 
                print( "PID_tool_main_end:' in file_processing.read_TXTfile(exe_log_path)", exe_log_path ); break
            time.sleep(1); budget -= 1; print( f'to sleep {budget}s', exe_log_path)
        MTidentifier_result = MR_Scout_plus.parse_MRScout_output(pojname, exe_log_path)
        if Setting["MRScout_plus"]==True:
            MTidentifier_result = MR_Scout_plus.complement_MRScout(MTidentifier_result, path_of_generated_MRs_in_cache, target_methods_FQS+suggested_methods_FQS)
        Test_result["MTidentifier_result"] = MTidentifier_result
        
        print("MTidentifier_result: ", MTidentifier_result)



    """ measure the similarity of the generated MRs and the developer written tests """
    Test_result["similarity_to_developer_written_MTC"] = None
    Test_result["similarity_to_developer_written_MTC"] = MR_similarity.measure_similarity_of_generatedMR_and_developer_written_MTC(MR_generator)
    print("Test_result['similarity_to_developer_written_MTC']: ", Test_result["similarity_to_developer_written_MTC"])
    

    """ write validation result """
    # store sth
    Test_result[f"Path_compilation_log_{fixed_or_buggy_version}"] = Path_compilation_log
    Test_result[f"Path_execution_log_{fixed_or_buggy_version}"] = Path_execution_log
    Test_result[f"path_of_generated_MRs_in_cache"] = path_of_generated_MRs_in_cache
    Test_result[f"prompt_messages_path"] = prompt_messages_path
    Test_result[f"response_content_path"] = response_content_path
    
    MRs_validation_result = Test_result
    evaluation_result_of_generated_MRs = []
    evaluation_result_of_generated_MRs_function_path = MR_generator.evaluation_result_of_generated_MRs_function_path
    with file_lock:
        if file_processing.pathExist(evaluation_result_of_generated_MRs_function_path):
            with open (evaluation_result_of_generated_MRs_function_path, "r") as f: # 句柄打开，防止文件读写冲突。。
                print("evaluation_result_of_generated_MRs_function_path: ", evaluation_result_of_generated_MRs_function_path)
                print("MTC_item: ",  MTC_item["FQS"])
                evaluation_result_of_generated_MRs = json_processing.read(evaluation_result_of_generated_MRs_function_path)
                for ele in evaluation_result_of_generated_MRs:
                    if ele["MTC_item"]["FQS"] == MTC_item["FQS"] and ele["generated_MR_testClass_FQN"] == genreated_test_class_FQN:
                        evaluation_result_of_generated_MRs.remove(ele)
                evaluation_result_of_generated_MRs.append(MRs_validation_result)
                json_processing.write( json_content=evaluation_result_of_generated_MRs, path=evaluation_result_of_generated_MRs_function_path)
        else:
            evaluation_result_of_generated_MRs.append(MRs_validation_result)
            json_processing.write( json_content=evaluation_result_of_generated_MRs, path=evaluation_result_of_generated_MRs_function_path)

    """ 复位: rm generated MRs in original poj """
    file_processing.remove_file(path_of_generated_MRs_in_original_poj)
    file_processing.remove_file(path_of_generated_MRs_in_original_poj.replace(".java",".class"))
    return Test_result




def parallel():
    parallel_size = Setting["parallel_size"]
    tasks = []
    for index_of_request in range(Setting["number_of_request"]):
        for MTC_FQN in MTC_FQN_list:
            # """  a quick check: whether MTC_FQN exeuted before """
            # if file_processing.pathExist(evaluation_generated_MRs_path):
            #     executed_MRs_FQN = [item["MTC_item"]["FQS"] for item in json_processing.read(evaluation_generated_MRs_path)]
            #     if MTC_FQN+"()" in executed_MRs_FQN:
            #         print(f"Skip: {MTC_FQN} already executed")
            #         continue
            
            tasks.append({"index_of_request": index_of_request, "MTC_FQN": MTC_FQN})
        # break

    with multiprocessing.Pool(processes=parallel_size) as pool:
        # Use pool.imap or pool.map for ordered results
        pool.map(main_task, tasks)


def preparation_for_LLMSelfRevision(MR_generator):
    if MR_generator.Setting["number_of_revise"] == 0: 
        print("RETURN", f'{MR_generator.Setting["number_of_revise"]}')
        return
    
    revision_index = MR_generator.Setting["number_of_revise"]
    evaluation_result_of_generated_MRs_function_path = MR_generator.evaluation_result_of_generated_MRs_function_path
    evaluation_execution_log_dir = MR_generator.evaluation_execution_log_dir
    genreated_test_class_name = MR_generator.genreated_test_class_name
    # path_of_generated_MRs_in_original_poj = MR_generator.path_of_generated_MRs_in_original_poj

    pre_revision_index = revision_index - 1
    # get the evaluation result of the last revision
    pre_revision_evaluation_result_of_generated_MRs_function_path = evaluation_result_of_generated_MRs_function_path.replace(f"_Rev{revision_index}", f"_Rev{pre_revision_index}")
    pre_revision_evaluation_result_all = json_processing.read(pre_revision_evaluation_result_of_generated_MRs_function_path)
    pre_revision_evaluation_result = None
    for MTC_item_result in pre_revision_evaluation_result_all:
        if MTC_item_result["MTC_item"]["FQS"] == MR_generator.MTC_FQN + "()":
            pre_revision_evaluation_result = MTC_item_result
            break    
    
    generatedMR_compile_result = None
    generatedMR_exe_result = None
    Path_compilation_log = None
    Path_execution_log = None
    try:
        pre_revision_prompt_messages_path = pre_revision_evaluation_result["prompt_messages_path"]
    except:
        print("----------------!!!MARK!!!----------------")
        print("pre_revision_evaluation_result: ", pre_revision_evaluation_result)
        print("MR_generator.MTC_FQN: ", MR_generator.MTC_FQN)
        # raise Exception("pre_revision_evaluation_result is None")
        return
    pre_revision_response_content_path = pre_revision_evaluation_result["response_content_path"]
    if MR_generator.Setting["targetCUTv"] == "latest": 
        generatedMR_compile_result = pre_revision_evaluation_result["generatedMR_compile_result_latest"]
        generatedMR_exe_result = pre_revision_evaluation_result["generatedMR_exe_result_latest"]
        Path_compilation_log = pre_revision_evaluation_result[f"Path_compilation_log_latest"]
        Path_execution_log = pre_revision_evaluation_result[f"Path_execution_log_latest"]
        
        # TODO/TOTHINK: may we provide the compilation log of the beforeComment version?. IF so, the file content should be the beforeComment version. 
        Path_compilation_log = pre_revision_evaluation_result[f"Path_compilation_log_latest"].replace(".log", ".beforeComment.log")
        if not file_processing.pathExist(Path_compilation_log):
            Path_compilation_log = pre_revision_evaluation_result[f"Path_compilation_log_latest"]

    if MR_generator.Setting["targetCUTv"] == "BUGGY": 
        # print("pre_revision_evaluation_result_all: ", pre_revision_evaluation_result_all)
        generatedMR_compile_result_FIXED = pre_revision_evaluation_result["generatedMR_compile_result_FIXED"]
        generatedMR_exe_result_FIXED = pre_revision_evaluation_result["generatedMR_exe_result_FIXED"]
        
        generatedMR_compile_result = pre_revision_evaluation_result["generatedMR_compile_result_BUGGY"]
        generatedMR_exe_result = pre_revision_evaluation_result["generatedMR_exe_result_BUGGY"]
        Path_compilation_log = pre_revision_evaluation_result[f"Path_compilation_log_BUGGY"]
        Path_execution_log = pre_revision_evaluation_result[f"Path_execution_log_BUGGY"]
        # TODO/TOTHINK: may we provide the compilation log of the beforeComment version?.
        Path_compilation_log = pre_revision_evaluation_result[f"Path_compilation_log_BUGGY"].replace(".log", ".beforeComment.log")
        if not file_processing.pathExist(Path_compilation_log):
            Path_compilation_log = pre_revision_evaluation_result[f"Path_compilation_log_BUGGY"]
    print("Path_compilation_log: ", Path_compilation_log)

    pre_revision_evaluation_result_summary = "executable"
    if generatedMR_compile_result != True: # 说明上一轮编译失败
        pre_revision_evaluation_result_summary = "uncompiled"
 
    if generatedMR_compile_result:
        num_of_test_cases = 0
        for key in generatedMR_exe_result.keys():
            num_of_test_cases = generatedMR_exe_result[key]["num_of_test_cases"]
            break # 因为只有一个ele
        if num_of_test_cases == 0:              # 说明上一轮编译成功 但运行失败
            pre_revision_evaluation_result_summary = "non-executable"

    # print("pre_revision_evaluation_result_summary: ", pre_revision_evaluation_result_summary, MR_generator.MTC_FQN)
    if pre_revision_evaluation_result_summary == "executable": 
        # 搬运generated_MRs, 其他貌似都不重要。。。compilation_log, exe_result, 
        # 搬运了之后，就不会再request了。
        path_of_pre_revision_generated_MR_java_file = pre_revision_evaluation_result["path_of_generated_MRs_in_cache"]
        path_of_pre_revision_generated_MR_class_file = path_of_pre_revision_generated_MR_java_file.replace(".java", ".class")
        path_of_this_revision_generated_MR_java_file = path_of_pre_revision_generated_MR_java_file.replace(f"_Rev{pre_revision_index}", f"_Rev{revision_index}")
        path_of_pre_revision_generated_MR_class_file = path_of_pre_revision_generated_MR_java_file.replace(".java", ".class")
        path_of_this_revision_generated_MR_class_file = path_of_this_revision_generated_MR_java_file.replace(".java", ".class")

        file_processing.copyFile(source=path_of_pre_revision_generated_MR_java_file, target=path_of_this_revision_generated_MR_java_file)
        file_processing.copyFile(source=path_of_pre_revision_generated_MR_class_file, target=path_of_this_revision_generated_MR_class_file)
        
        # 搬运responses
        path_of_pre_revision_response_content_path = pre_revision_evaluation_result["response_content_path"]
        file_processing.copyFile(source=path_of_pre_revision_response_content_path, target=path_of_pre_revision_response_content_path.replace(f"_Rev{pre_revision_index}", f"_Rev{revision_index}"))
        # if exist _inputGen_response_content
        path_of_pre_revision_inputGen_response_content_path = path_of_pre_revision_response_content_path.replace("_response_content.md", "_inputGen_response_content.md")
        if file_processing.pathExist(path_of_pre_revision_inputGen_response_content_path):
            file_processing.copyFile(source=path_of_pre_revision_inputGen_response_content_path, target=path_of_pre_revision_inputGen_response_content_path.replace(f"_Rev{pre_revision_index}", f"_Rev{revision_index}"))
        
        # 搬运 prompt_messages
        path_of_pre_revision_prompt_messages_path = pre_revision_evaluation_result["prompt_messages_path"]
        file_processing.copyFile(source=path_of_pre_revision_prompt_messages_path, target=path_of_pre_revision_prompt_messages_path.replace(f"_Rev{pre_revision_index}", f"_Rev{revision_index}"))
        # if exist _inputGen_prompt_messages
        path_of_pre_revision_inputGen_prompt_messages_path = path_of_pre_revision_prompt_messages_path.replace("_prompt_messages.json", "_inputGen_prompt_messages.json")
        if file_processing.pathExist(path_of_pre_revision_inputGen_prompt_messages_path):
            file_processing.copyFile(source=path_of_pre_revision_inputGen_prompt_messages_path, target=path_of_pre_revision_inputGen_prompt_messages_path.replace(f"_Rev{pre_revision_index}", f"_Rev{revision_index}"))
        
        # 搬运_reasoning_content
        path_of_pre_revision_reasoning_content_path = path_of_pre_revision_response_content_path.replace("_response_content.md", "_reasoning_content.md")
        if file_processing.pathExist(path_of_pre_revision_reasoning_content_path):
            file_processing.copyFile(source=path_of_pre_revision_reasoning_content_path, target=path_of_pre_revision_reasoning_content_path.replace(f"_Rev{pre_revision_index}", f"_Rev{revision_index}"))
        # 搬运_inputGen_reasoning_content
        path_of_pre_revision_inputGen_reasoning_content_path = path_of_pre_revision_reasoning_content_path.replace("_reasoning_content.md", "_inputGen_reasoning_content.md")
        if file_processing.pathExist(path_of_pre_revision_inputGen_reasoning_content_path):
            file_processing.copyFile(source=path_of_pre_revision_inputGen_reasoning_content_path, target=path_of_pre_revision_inputGen_reasoning_content_path.replace(f"_Rev{pre_revision_index}", f"_Rev{revision_index}"))
        
        # 搬运 mutateMRs_prompt_messages
        if Setting["mutateMRs"] == "mutateMRs":
            path_of_pre_revision_mutateMRs_prompt_messages_path = path_of_pre_revision_response_content_path.replace("_response_content.md", "_mutateMRs_prompt_messages.md")
            if file_processing.pathExist(path_of_pre_revision_mutateMRs_prompt_messages_path):
                file_processing.copyFile(source=path_of_pre_revision_mutateMRs_prompt_messages_path, target=path_of_pre_revision_mutateMRs_prompt_messages_path.replace(f"_Rev{pre_revision_index}", f"_Rev{revision_index}"))
            # 搬运 mutateMRs_response_content
            path_of_pre_revision_mutateMRs_response_content_path = path_of_pre_revision_response_content_path.replace("_response_content.md", "_mutateMRs_response_content.md")
            if file_processing.pathExist(path_of_pre_revision_mutateMRs_response_content_path):
                file_processing.copyFile(source=path_of_pre_revision_mutateMRs_response_content_path, target=path_of_pre_revision_mutateMRs_response_content_path.replace(f"_Rev{pre_revision_index}", f"_Rev{revision_index}"))

        # 后面需要skip generate(),防止以后要开了覆盖模式时，被覆盖了。。。【done】
    else:
        # pre_revision_prompt_messages_path = pre_revision_evaluation_result["prompt_messages_path"]
        # pre_revision_response_content_path = pre_revision_evaluation_result["response_content_path"]
        
        pre_revision_prompt_messages = json_processing.read(pre_revision_prompt_messages_path)
        pre_revision_response_content = file_processing.read_TXTfile(pre_revision_response_content_path)
        chat_history = pre_revision_prompt_messages[1:2] # the first one is the system message; 只要第一次prompt吧。。。后面的interface就都不要了。。。
        chat_history.append({"role": "assistant", "content": pre_revision_response_content})
        if Setting["mutateMRs"] == "mutateMRs":
            mutateMRs_prompt_messages_path = pre_revision_response_content_path.replace("_response_content.md", "_mutateMRs_prompt_messages.md")
            mutateMRs_response_content_path = pre_revision_response_content_path.replace("_response_content.md", "_mutateMRs_response_content.md")
            if file_processing.pathExist(mutateMRs_response_content_path):
                mutateMRs_prompt_messages = file_processing.read_TXTfile(mutateMRs_prompt_messages_path)
                mutateMRs_response_content = file_processing.read_TXTfile(mutateMRs_response_content_path)
                chat_history.append({"role": "user", "content": mutateMRs_prompt_messages})
                chat_history.append({"role": "assistant", "content": mutateMRs_response_content})
        #     json_processing.write(chat_history, "chat_history.json")
        #     print("LOG: length of chat_history: ", len(chat_history))
        # print("LOG: length of chat_history2: ", len(chat_history))
        #  compilation / exectuion error content  
        compilation_log_content = file_processing.read_TXTfile(Path_compilation_log)
        if file_processing.pathExist(Path_execution_log):
            execution_log_content = file_processing.read_TXTfile(Path_execution_log)
        else:
            execution_log_content = ""
            print(f"LOG: NOTE-ERROR: execution_log_content not exist: {Path_execution_log}")
        MR_generator.chat_history = chat_history
        MR_generator.flag_include_chat_history = True
        MR_generator.compilation_log_content = compilation_log_content
        MR_generator.execution_log_content = execution_log_content
        # print("chat_history: ", chat_history)
        # print("compilation_log_content: ", compilation_log_content)
        # print("execution_log_content: ", execution_log_content)

    MR_generator.pre_revision_evaluation_result = pre_revision_evaluation_result
    MR_generator.pre_revision_evaluation_result_summary = pre_revision_evaluation_result_summary # uncompiled, non-executable, executable
    print("pre_revision_evaluation_result_summary: ", pre_revision_evaluation_result_summary)


special_list = [
    "com.github.davidmoten.rtree2.geometry.PointTest.testDoesNotContain",
    "com.github.davidmoten.rtree2.geometry.LineTest.testLineDoubleIntersectsWithHorizontalLine",
    "com.github.davidmoten.rtree2.geometry.LineTest.testLineFloatIntersectsWithHorizontalLine",
    "io.smallrye.config.PropertyNameTest.mappingNameEquals",
    "org.geolatte.geom.json.FeatureDeserializationTest.testDeSerializeWithNullGeometry",
    "fi.thl.covid19.exposurenotification.diagnosiskey.IntervalNumberTest.utcLocalDateWorks",
    "fi.thl.covid19.exposurenotification.diagnosiskey.IntervalNumberTest.dayLastIntervalWorks",
]


def main_task(task):
    index_of_request = task["index_of_request"]
    MTC_FQN = task["MTC_FQN"]

    # if "org.dyn4j.world.AbstractPhysicsWorldTest.addJoint" not in MTC_FQN: return # debug
    if Setting["targetCUTv"] == "BUGGY" or Setting["targetCUTv"] == "":
        buggy_version_commitID = reproduced_bugs_metainfo[MTC_FQN]["buggy"]
        fixed_version_commitID = reproduced_bugs_metainfo[MTC_FQN]["fixed"]
        MR_generator = mrGenerator(index_of_request, MTC_FQN, buggy_version_commitID, fixed_version_commitID)
    elif Setting["targetCUTv"] == "latest":
        commitID = "latest"
        MR_generator = mrGenerator(index_of_request, MTC_FQN, commitID)
    if MR_generator is None or MR_generator.success_init == False: print(f"LOG: NOTE-ERROR: MR_generator is failed initializtion and skipped: {MTC_FQN}, {index_of_request}");return
    print(f"Processing, index_of_request: {index_of_request}, MTC_item: {MTC_FQN}")
    print('+++ START: preparation_for_LLMSelfRevision ',MTC_FQN)
    preparation_for_LLMSelfRevision(MR_generator)
    
    
    """ baseline: do not need to pair methods """
    if MR_generator.Setting["paired_method_info"] == "" or MR_generator.Setting["pair_method_methodology"] == "": 
        print('+++ START: MR/MTC generation ',MTC_FQN)
        generate_prompt_from_profile(MR_generator)           
        generate_MRs_by_prompting(MR_generator)
                
        print('+++ START: validate_generated_MRs ', MTC_FQN)
        test_generated_MRs(MR_generator, skipCompileIfExist=Setting["skipCompileIfExist"], commentFaultyCode=Setting["commentFaultyCode"], fixed_or_buggy_version=Setting["targetCUTv"])
    else: 
        """ tool: pair methods + one-by-one MR """
        print("+++ START: context (similar MTC, pattern, paired methods) preparation ",MTC_FQN)
        context_preparation(MR_generator)
        task_symbol_prefix = ""
        ordered_suggestedMethodsMeta = []
        ordered_suggestedMethodsMeta_w_featureDes = []
        ordered_suggestedMethods_MUTbs = OrderedDict() # dict is 
        if Setting["pair_method_methodology"] in ["S","2"]: # similar MTC driven
            task_symbol_prefix = "M"
            ordered_suggestedMethodsMeta = MR_generator.context_data.ordered_similar_MUTsB_and_pattern_suggested_methods
        elif Setting["pair_method_methodology"] in ["P","2-1"]: # pattern driven driven
            task_symbol_prefix = "P"
            ordered_suggestedMethodsMeta = MR_generator.context_data.ordered_pattern_suggested_methods_MUTsB
            ordered_suggestedMethodsMeta_w_featureDes = MR_generator.context_data.ordered_pattern_suggested_methods_w_featureDes
        else: # take a default value
            raise Exception("pair_method_methodology not supported")
        
        for item in ordered_suggestedMethodsMeta:
            suggested_methods = item["suggested_methods"]
            similar_MUTb = item["similar_MUTb"]
            for method in suggested_methods:
                # if method not in ordered_suggestedMethods_MUTbs:
                #     ordered_suggestedMethods_MUTbs[method] = [similar_MUTb]
                # else:
                #     ordered_suggestedMethods_MUTbs[method].append(similar_MUTb)
                if method not in ordered_suggestedMethods_MUTbs:
                    ordered_suggestedMethods_MUTbs[method] = {}
                    ordered_suggestedMethods_MUTbs[method]["similar_MUTb"] = [similar_MUTb]
                else:
                    ordered_suggestedMethods_MUTbs[method]["similar_MUTb"].append(similar_MUTb)
                ordered_suggestedMethods_MUTbs[method]["pattern_info"] = ordered_suggestedMethodsMeta_w_featureDes[method]

        index=0   
        if len(ordered_suggestedMethods_MUTbs) == 0 or ordered_suggestedMethods_MUTbs.__sizeof__() == 0:
            for i in range(5):
                ordered_suggestedMethods_MUTbs[f"itself{i}"] = {"similar_MUTb": ["itself"], "pattern_info": {"pattern_type": ["NA"], "description": ["NA"]}}
        print("ordered_suggestedMethods_MUTbs: " , len(ordered_suggestedMethods_MUTbs))
        print("ordered_suggestedMethods_MUTbs: " , ordered_suggestedMethods_MUTbs.keys())
        for method in ordered_suggestedMethods_MUTbs: 
            if index >= 15: break # 暂取前15个吧 # TO UPDATE: switch
            task_symbol = f"{task_symbol_prefix}{index}"
            MR_generator.task_symbol_prefix = task_symbol_prefix
            MR_generator.task_symbol_index = index
            MR_generator.task_symbol = task_symbol
            MR_generator.context_data_for_current_task_symbol = {
                "suggested_methods": [method],
                "similar_MUTb": ordered_suggestedMethods_MUTbs[method]["similar_MUTb"],
                "pattern_info": ordered_suggestedMethods_MUTbs[method]["pattern_info"]
            }
            index += 1
            
            print('+++ START: prompt generation ',MTC_FQN)
            generate_prompt_from_profile(MR_generator)   
            print('+++ START: MR/MTC generation ',MTC_FQN)        
            generate_MRs_by_prompting(MR_generator)
                    
            print('+++ START: validate_generated_MRs ', MTC_FQN)
            test_generated_MRs(MR_generator, skipCompileIfExist=Setting["skipCompileIfExist"], commentFaultyCode=Setting["commentFaultyCode"], fixed_or_buggy_version=Setting["targetCUTv"])
            # break
    

def one_by_one():
    count = 0
    for index_of_request in range(Setting["number_of_request"]):
        # index_of_request = 2 # debug
        for MTC_FQN in MTC_FQN_list:
            # if MTC_FQN not in special_list: continue # debug
            # if "RationalNumberTest.testMultiplication" not in MTC_FQN: continue # PreviousClearBitTest.level1Miss debug not failed, TestPoint.testPt failed, TestArguments.testBooleanType
            # if "ConstraintGraphTest.testRemoveBodyWithUnaryJoint" not in MTC_FQN: continue # debug
            # if "com.fasterxml.jackson.databind.PropertyNameTest.testMerging" not in MTC_FQN: continue # debug
            # if MTC_FQN not in taskset.sccpu4_but_not_sccpu7_reproduced_bugs_MTC_: continue
            task = { "index_of_request": index_of_request, "MTC_FQN": MTC_FQN }
            main_task(task)
            break
        break




def main():
    # # time.sleep 1.5h, print sth every 10 min, with timestamp
    # for i in range(10):
    #     print(f"Sleeping for 10 minutes, {i*10} minutes passed, {time.strftime('%Y-%m-%d %H:%M:%S')}")
    #     time.sleep(600)

    init()
    if Setting["parallel"]:
        parallel()
    if Setting["one_by_one"]:
        one_by_one()
        
if __name__ == "__main__":
    main()
    