#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
-----------------------------------------
@Author: 
@Created: 2022/11/22
------------------------------------------
@Modify: 2022/11/22
------------------------------------------
@Description:

parallel MRgenerator_main
"""
import json, os, sys
_PROJECT_NAME = "CyUtil"
_CURRENT_ABSPATH = os.path.abspath(__file__)
sys.path.insert(0, _CURRENT_ABSPATH[:_CURRENT_ABSPATH.find(_PROJECT_NAME) + len(_PROJECT_NAME) + 1])
import file_processing

def List_of_dictItems_to_csv(key_list, list_item_dict_content, path_to_store):
    file_content = ""

    title_row = ""
    for key in key_list:
        title_row += key +","

    data_rows = ""
    for item in list_item_dict_content:
        data_row = ""
        for key in key_list:
            if isinstance (item[key],(float) )  :
                data_row += str( round(item[key],2) ) + ","
            else:
                data_row += str(item[key]) + ","
        data_rows += data_row + '\n'

    file_content += title_row + '\n'
    file_content += data_rows

    file_processing.write_TXTfile(path=path_to_store, content=file_content)
    
    