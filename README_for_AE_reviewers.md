# README FOR REVIEWERS
Thank you for reviewing our artifact! We are applying for the **Artifacts Available, Artifacts Functional** and **Results Reproduced** badges.

## Estimated Time
- Environment setup: 10 mins
- Play with the examples: 10 mins
- Reproduce the result: 35 mins


## Access our Artifact

We provide three methods for testing: 

- A customized virtual machine

```
Address: 128.220.247.60
Port: 40022
Username: guest
Password: **included in the reviewer's page**

ssh guest@128.220.247.60 -p 40022
```
- A docker image --

We uploaded our docker to Docker Hub. You can pull it by running 

```
docker pull iamthesong/odgen:latest
```
Then you can attach to this docker by running

```
docker run -it iamthesong/odgen bash
```

After loading it, you should be able to see the same environment with the virtual machine

- A repository for the source code

If you are not able to access the virtual machine and can not load the docker image, you can also try to clone our source code from the [repository](https://github.com/Song-Li/ODGen) and follow the instructions in the README.md to set up the environment.

 
## File Organization of Our Virtual Machine

Once you log into the virtual machine, all the files and folders are organized as follows: 

```
.
|--projs: the source code and libs of our tool. 
|--packages: all the zero-day vulnerable packages detected by our tool.
  |--code_exec: packages with zero-day arbitrary code execution vulnerabilities 
    |--XX: package-name@version
      |--cve.txt: if it exists, it indicates the CVE identifier
      |--run.sh: a script to detect the zero-day vulnerability
  |--ipt: packages with zero-day internal property tampering vulnerabilities 
  |--os_command: packages with zero-day OS command injection vulnerabilities 
  |--path_traversal: packages with zero-day path traversal vulnerabilities
  |--proto_pollution: packages with zero-day prototype pollution vulnerabilities
  |--xss: packages with zero-day XSS vulnerabilities
|--examples: a few simple vulnerable examples 
  |--pp_example.js: the prototype pollution example 
  |--run_proto_pollution.sh: detect prototype pollution of pp_example.js
  |--motivating_example.js: the motivating example mentioned in the paper
  |--run_ipt.sh: detect internal property tampering of motivating_example.js
  |--run_os_command.sh: detect taint-style vulnerability of motivating_example.js      
  |--clean.sh: clean up log files 
|--back_up: recovery files (do not touch)
```

## Play With the Examples
In the **~/examples** folder, we have a few simple vulnerable examples for you to get familiar with our tool. You can try the **run\_ipt.sh,  run\_os\_command.sh** or **run\_proto\_pollution.sh** to run our tool on top of the **pp\_example.js**(a prototype pollution) example and the **motivating_example.js**(the motivating example introduced in our paper). You can also write your modules, use a similar command and test them out. 

## Artifacts Available
Our tool is been made permanently available for retrieval. The source code will be stored and maintained in the [repository](https://github.com/Song-Li/ODGen). The license of the source code is GPL-2.0.


## Artifacts Functional
### Documentation: are the artifacts sufficiently documented to enable them to be exercised by readers of the paper?
Our tool is well documented. Including a detailed README.md file and detailed comments of each function in the source code. We believe that the source code is well structured and well-written.

### Completeness: do the submitted artifacts include all of the key components described in the paper?
Our tool is an implementation of the paper, it's directly related to the paper and provides multiple configurable arguments for different levels of users. The tool is also complete, the documentations are ready and every function mentioned in the paper is implemented and functional.


### Exercisability: do the submitted artifacts include the scripts and data needed to run the experiments described in the paper, and can the software be successfully executed?
Our tool is exercisable. We provide the main entrance of the package together with a list of scripts that can install the requirements and run the verifications. We also kindly include the motivating example of the paper and the related scripts in the **~/example** directory for you to test it out. 

## Results Reproduced
As we claimed in the **Abstract** section and the **Contributions** part of section 1, our main claim that needed to be evaluated is that we found 43 application-level and 137 package-level zero-day vulnerabilities. We prepared the dataset and the related scripts to run our tool on top of the packages. 

### Dataset

- Dataset: The 174 zero-day vulnerable packages that found by our tool. (Note that after our reporting, there are eight packages that are unpublished from NPM.  Currently, we only have source code for 173 packages + one package, which is unpublished but cached on our server.)
- Location: ~/packages
- the CVEs they got: ~/packages/xx/package-name@version/cve.txt (if exists)
- a script that runs the analysis on each of these folders/projects and detects the vulnerabilities: ~/packages/xx/package-name@version/run.sh

where xx = code\_exec, ipt, os\_command, path\_trasversal,   proto\_pollution, and xss.

Note that considering the large size of the dataset, we are not able to upload the dataset to the GitHub repository. We uploaded the zipped dataset to [Google Drive](https://drive.google.com/file/d/1IiuQoMV4a2QAzwswEq9fSKXcZpNuGYP0/view?usp=sharing) and if you are testing it by the source code, please download it, unzip it, and put it in the root directory of your machine. 

### Group Testing
Totally we have six different types of vulnerabilities, they are command injection, code execution, prototype pollution, path traversal, cross-site scripting, and internal property tampering. Each of them can be tested by running one command **in the root directory of the source code**:

- Command injection: ``./scripts/os_command.sh``
- Code execution: ``./scripts/code_exec.sh``
- Prototype pollution: ``./scripts/prototype_pollution.sh``
- Path traversal: ``./scripts/path_traversal.sh``
- Cross-site scripting: ``./scripts/xss.sh``
- Internal property tampering: ``./scripts/ipt.sh``

To reproduce the results, you can pick a vulnerability type and run the corresponding script. 

Note that the scripts will try to run our tool parallelly, so you will not see the progress. Once you run a script, you should be able to see a message that says "new instance". You can check how many processes are still running by the command: ``screen -ls``. You can also attach to a specific process by running: ``screen -r XXX``(XXX means the name of the screen). Once all the processes are finished, you can check the result and run another script. 

### Expected Results
The testing results are located in the "**logs**" folder of the running directory. All the detected vulnerable packages will be output to the "**succ.log**" file; All the un-detected packages will be output to the "**results.log**" file. You can get the number of the successfully detected packages by running ``cat ./logs/succ.log | wc -l``, during or after the running process.

If you finished checking one vulnerability type, please run ``./clean.sh`` to remove the logs and temporary files before checking another one.

Note that since the order of the testing functions is randomized, you may encounter some un-detected packages. For the un-detected packages, you may run them independently follow the instructions in README.md, or, go to "~/packages/vulneralbility-type/package-name@version/" and run the "run.sh"

The number of all the packages, unpublished packages, expected detected packages and the estimated running time are listed below:

|             | Command Injection | Code Execution | Prototype Pollution | Path Traversal | Cross-site Scripting | IPT   |
|-------------|-------------------|----------------|---------------------|----------------|----------------------|-------|
| Total       | 80                | 14             | 19                  | 30             | 13                   | 24    |
| Unpublished | 2                 | 4              | 0                   | 0              | 0                    | 0     |
| Expected    | 76~78             | 9~10           | 17~19               | 30             | 12~13                | 23~24 |
| Time/mins   | ~10               | ~6             | ~10                 | ~5             | ~1                   | ~3    |