# MR-Coupler Prototype

**MR-Coupler** is an automated approach to automatically generate metamorphic test case via functional coupling analysis.


## Environment Configuration 

* Java: 11.0.18
* Python: 3.10, the required depdencies can be found in `requirements.txt`

#### Subjects preparation
* Download the projects from [dataset1](https://github.com/MR-Coupler/MR-Coupler.github.io/blob/main/data/Human-written-MTCs.json) or [dataset2](https://github.com/MR-Coupler/MR-Coupler.github.io/blob/main/data/Bug-Revealing-MTCs.json) into the `inputs/experiemental_projects` directory.


#### Setting API key for LLMs
* Edit file `MR-Coupler/request_LLMs.py` and update the following fields.

``` python 
client = openai.AzureOpenAI(
    api_key="TODO",         # change to your OpenAI API key
    api_version="TODO",     # choose the api version
    azure_endpoint="TODO"   # set the endpoint
)
```

## Quick Start: Metamorphic test case generation
    
Navigate to MR-Coupler's directory and execute the following command:

```cmd
$ cd MR-Coupler; python generate_MTCs.py 
```

   Output:
   * generate input pairs and the validation results can be found at `validation_generated_MRs_$LLM_name$.json` 


#### Update

If you have any questions or issues, please feel free to report an issue. We will continue to maintain this project. Thanks for your feedback😄. 