import argparse

def parse_args():
    # Parse arguments
    parser = argparse.ArgumentParser(
        description='Object graph generator for JavaScript.')
    parser.add_argument('-p', '--print', action='store_true',
                        help='Print logs to console, instead of file.')
    parser.add_argument('-t', '--vul-type', default='os_command',
                        help="Set the vulnerability type to be checked.")
    parser.add_argument('-P', '--prototype-pollution', '--pp',
                        action='store_true',
                        help="Check prototype pollution.")
    parser.add_argument('-m', '--module', action='store_true',
                        help="Module mode. Regard the input file as a module "
                        "required by some other modules.")
    parser.add_argument('-q', '--exit', action='store_true', default=False,
                        help="Exit the program when vulnerability is found.")
    parser.add_argument('-s', '--single-branch', action='store_true',
                        help="Single branch. Do not create multiple "
                        "possibilities when meet a branching point.")
    parser.add_argument('-a', '--run-all', action='store_true', default=False,
                        help="Run all exported functions in module.exports. "
                        "By default, only main functions will be run.")
    parser.add_argument('-f', '--function-timeout', type=float,
                        help="Time limit when running all exported function, "
                        "in seconds. (Defaults to no limit.)")
    parser.add_argument('--timeout', type=int, help="Time limit for testing an entrance. (Defaults to None)")
    parser.add_argument('--package-timeout', type=int, help="Time limit for testing a package. (Defaults to None)")
    parser.add_argument('-c', '--call-limit', default=3, type=int,
                        help="Set the limit of a call statement. "
                        "(Defaults to 3.)")
    parser.add_argument('-e', '--entry-func')
    parser.add_argument('-l', '--list', action='store')
    parser.add_argument('--install', action='store_true', default=False, help="If set, we will install the packages to the run env")
    parser.add_argument('--max-rep', type=int, default=4, help="If set, OPGen will limit of the max time of calls of each function in the call stack to max-rep")
    parser.add_argument('--run-all-files', action='store_true', default=False, help="If set, OPGen will run all files of a package")
    parser.add_argument('--no-prioritized-funcs', action='store_true', default=False, help="If set, OPGen will not try to run prioritized functions before everything")
    parser.add_argument('--entrance-func', type=str, help="If set, OPGen will start from a specified function")
    parser.add_argument('--pre-timeout', type=int, default=30, help="timeout for pre-processing file (for entrance func set only)")
    parser.add_argument('--exported-func-timeout', type=int, default=None, help="timeout for single exported function")
    parser.add_argument('--no-exports', action='store_true', default=False, help="if set, OPGen will never run exported functions")
    parser.add_argument('--max-file-stack', type=int, help="If set, OPGen will limit the max size of file stack to max-file-stack")
    parser.add_argument('--skip-func', type=str, help="If set, OPGen will skip a list of functions, separated by ,")
    parser.add_argument('--add-sinks', type=str, help="If set, OPGen will treat the added function names as sink functions, separated by ,")
    parser.add_argument('--print-all-pathes', action='store_true', default=False, help="If set, OPGen will print all pathes even if the path is not a valid expolitable path")
    parser.add_argument('--run-env', default='./tmp_env/', help="set the running env location")
    parser.add_argument('--no-file-based', action='store_true', default=False, help="No file based detection")
    parser.add_argument('--parallel', help="run multiple package parallelly")
    parser.add_argument('--auto-type', action='store_true', default=False, help="Auto change the type of wildcard obj based on the called method")
    parser.add_argument('--export', help="export the graph to csv files, can be light or all")
    parser.add_argument('--nodejs', action='store_true', default=False, help="run a nodejs package")
    parser.add_argument('--gc', action='store_true', default=False, help="run a garbage collection after every function run")
    parser.add_argument('--more-output', action='store_true', default=False, help="output a more detailed version of result")
    parser.add_argument('--run-test', action='store_true', default=False, help="Run the pre-defined tests to make sure the installation finished")
    parser.add_argument('--babel', help="use babel to convert the files first, need to input the path to the files to be converted")
    parser.add_argument('input_file', action='store', nargs='?',
        help="Source code file (or directory) to generate object graph for. "
        "Use '-' to get source code from stdin. Ignore this argument to "
        "analyze ./nodes.csv and ./rels.csv.")
    args = parser.parse_args()
    if args.vul_type == 'prototype_pollution':
        args.vul_type = 'proto_pollution'

    return args

class Options:
    class __Options:
        def __init__(self):
            args = parse_args()
            for arg in vars(args):
                setattr(self,arg,getattr(args,arg))
    instance = None
    def __init__(self):
        if not Options.instance:
            Options.instance = Options.__Options()
    def __getattr__(self, name):
        return getattr(self.instance, name)
    def __setattr__(self, name, val):
        return setattr(self.instance, name, val)

options = Options()
