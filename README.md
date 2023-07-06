# ODGen
ODGen is a JavaScript static analysis tool to detect vulnerabilities in Node.js packages. This project is written in Python and JavaScript and the source code is included in the repository. 

## Hello Reviewers
If you are the AE reviewer, please come here first! [README\_for\_AE\_reviewers.md](./README_for_AE_reviewers.md)

## Installation
Please check out [INSTALL.md](./INSTALL.md) for the detailed instruction of the installation.

## Usage
Use the following arugments to run the tool:

```bash
python3 odgen.py	[-h] [-p] [-m] [-q] [-s] [-a] [--timeout TIMEOUT] [-l LIST] [--install] 
		[--max-rep MAX_REP] [--nodejs] [--pre-timeout PRE_TIMEOUT]
		[--max-file-stack MAX_FILE_STACK] [--skip-func SKIP_FUNC] [--run-env RUN_ENV] 
		[--no-file-based] [--parallel PARALLEL] [input_file]
```

| Argument | Description |
| -------- | ----------- |
| `input_file` | The path to the input file. It can be a Node.js package directory or a JavaScript file |
| `-t VUL_TYPE, --vul-type VUL_TYPE` | Set the vulneralbility type, for now, it can be "os\_command", "code\_exec", "proto\_pollution", "ipt", "xss" and "path\_traversal"|
| `-p, --print` | Print logs to console, instead of files. |
| `-m, --module` | Module mode. Indicate the input is a module, instead of a script. |
| `-q, --exit` | Exit the analysis immediately when vulnerability is found. Do not use this if you need a complete graph. |
| `-s, --single-branch` | Single branch mode (or single execution). If set, ODGen will disable the branch-sensitive mode. |
| `-a, --run-all` | Run all exported functions in module.exports of **all** analyzed files even if the file is not the entrance file.|
| `--timeout TIMEOUT`| The timeout(in seconds) of running a single module for one time. (Optimizations may run a module multiple times. This is the timeout for a single run.)|
| `-l, --list LIST`| Run a list of files/packages. Each line of the file contains the path to a file/package. |
| `--install`| Download the source code of a list of packages to the --run-env location. |
| `--max-rep MAX_REP`| If set, every function can only exsits in the call stack for at most MAX_REP times. (To prevent too many levels of recursive calls)| 
| `--nodejs`| Node.js mode. Indicate the input is a Node.js package. |
| `--pre-timeout PRE_TIMEOUT`| The timeout(in seconds) for preparing the environment before running the prioritized functions. Defaults to 30.|
| `--max-file-stack MAX_FILE_STACK`| The max depth of the required file stack. |
| `--skip-func SKIP_FUNC`| Skip a list of functions, separated by "," .|
| `--run-env ENV_DIR` | Set the running environment location.|
| `--add-sinks SINK_FUNCS` | If set, ODGen will treat the added function names as sink functions, separated by ","|
| `--no-file-based`| Only detect the vulnerabilities that can be directly accessed from the main entrance of the package. |
| `--parallel PARALLEL`| Run a list of packages parallelly in PARALLEL threads. Only works together with --list argument. |

Once the command is finished, the tool will output the detecting result, and if any vulnerability is found, it will also output the location of the vulnerability and the attack path. 

### Command-line example
Here is an example to show how to use our command-line based tool:

```shell
$ python3 ./odgen.py ./tests/packages/command_injection/os_command.js -m -a -q -t os_command
```

Or to analyze a Node.js package, you can run a command like:

```shell
$ python3 ./odgen.py ./tests/packages/prototype_pollution/confucious@0.0.12 -maq -t proto_pollution
```

We also create a sample module with a prototype pollution vulnerability. You can test it by running:

```shell
$ python3 ./odgen.py ./tests/packages/prototype_pollution/pp.js -m -a -q -t proto_pollution
```

In this example, the output of the command-line based interface will be like:

```bash
Prototype pollution detected at node 49 (Line 4)
|Checker| Dataflow of Object Property:
Attack Path:
==========================
$FilePath$ODGen/tests/packages/pp.js
Line 11	function pp(key1, key2, value) {
$FilePath$ODGen/tests/packages/pp.js
Line 7	  var mid = val + " ";
$FilePath$ODGen/tests/packages/pp.js
Line 4	  proto[key2] = value;


|Checker| Dataflow of Assigned Value:
Attack Path:
==========================
$FilePath$ODGen/tests/packages/pp.js
Line 11	function pp(key1, key2, value) {
$FilePath$ODGen/tests/packages/pp.js
Line 4	  proto[key2] = value;


|Checker| Polluted Built-in Prototype:
Attack Path:
==========================
$FilePath$None
Object.prototype
$FilePath$ODGen/tests/packages/pp.js
Line 4	  proto[key2] = value;
```

Note that **ODGen** only outputs data-flows, which means that a statement is included in the path only when a new **object** is created and the created object will influence the result. For example, line 7 is included in the result because at line 7, *val + " "* creates a new object. While at line 12, even *tmp* is a new variable, it points to the created object at line 7, and no new object is created at line 12, **ODGen** will not include this statement in the result. 
