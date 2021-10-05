# start a server and accept requests
import flask 
import uuid
import os
import urllib
import json
from werkzeug.utils import secure_filename
from shutil import unpack_archive
from src.core.options import options
from src.core.opgen import OPGen
from src.core.logger import loggers, create_logger
from tinydb import TinyDB, Query

app = flask.Flask(__name__)
options.net_env_dir = None
app.showing_file = None
#db = TinyDB('./net_env_dir/tinydb.json')

def update_env():
    options.net_env_dir = os.path.join('./net_env_dir/', str(uuid.uuid4()))
    env_dir = options.net_env_dir
    if not os.path.exists(env_dir):
        os.makedirs(env_dir, exist_ok=True)
    # update the tmp logger location
    loggers.update_loggers(options.net_env_dir)
    options.input_file = None
    return env_dir

@app.route('/listdir', methods=['GET', 'POST'])
def dirlist():
    r=['<ul class="jqueryFileTree" style="display: none;">']
    try:
        r=['<ul class="jqueryFileTree" style="display: none;">']
        d = flask.request.form.get('dir')
        if d == '/':
            d = ""
        root_dir = options.net_env_dir
        full_dir = os.path.join(root_dir, d)
        print(options.net_env_dir, d, full_dir, options.babel)
        for filename in os.listdir(full_dir):
            full_path = os.path.join(full_dir,filename)
            relpath = os.path.relpath(full_path, root_dir)
            if os.path.isdir(full_path):
                r.append('<li class="directory collapsed"><a rel="%s/">%s</a></li>' % (relpath, filename))
            else:
                e = os.path.splitext(filename)[1][1:] # get .ext and remove dot
                if e == 'log' or e == 'zip':
                    continue
                r.append('<li class="file ext_%s"><a rel="%s">%s</a></li>' % (e,relpath ,filename))
        r.append('</ul>')
    except Exception as e:
        r.append('Could not load directory: %s' % str(e))
        r.append('</ul>')
    return ''.join(r)

@app.route('/')
@app.route('/imgs/<path:imgname>')
@app.route('/js/<path:jsname>')
@app.route('/css/<path:cssname>')
def index(jsname=None, cssname=None, imgname=None):
    if not jsname and not cssname and not imgname:
        return flask.send_from_directory(app.static_folder, 'index.html')
    elif jsname:
        return flask.send_from_directory(os.path.join(app.static_folder, 'js'), jsname)
    elif cssname:
        return flask.send_from_directory(os.path.join(app.static_folder, 'css'), cssname)
    elif imgname:
        return flask.send_from_directory(os.path.join(app.static_folder, 'imgs'), imgname)

@app.route('/getFile', methods=['POST'])
def get_file():
    data = flask.request.get_json()
    print("Get file {}".format(data['name']))
    file_name = os.path.abspath(os.path.join(options.run_env, data['name']))
    app.showing_file = file_name
    #TODO: vulnerable to path traversal
    return flask.send_file(file_name)

@app.route('/setEntrance', methods=['POST'])
def set_entrance_file():
    data = flask.request.get_json()
    full_path = os.path.join(options.run_env, data['file'])
    options.input_file = full_path
    file_name = os.path.abspath(full_path)
    return file_name


def generate_graph_json(render=True):
    """
    read the results form tmp results
    generate the json based graph
    Args:
        render (boolean): render as a js file or return nodes and edges
    Returns:
        str: the rendered template
    """
    env_dir = options.run_env

    with open(os.path.join(options.net_env_dir, "results_tmp.log"), 'r') as fp:
        res = fp.read()

    # handle the result
    if 'FilePath' not in res:
        return "Not detected"
    pathes = res.split("|checker|")[1:]

    # generate json for graph
    edges = []
    file_map = {}
    node_map = {}
    nodes = []
    node_blocks = []
    height = 0
    idx = 0
    for path in pathes:
        blocks = path.split("$FilePath$")
        cur_color = blocks[0].split("$color:")[1].split('$')[0]
        blocks = blocks[1:]
        pre_block = None
        for block in blocks:
            lines = block.split('\n')
            # if lines[0] is None, measn it's builtin
            if lines[0] == 'None':
                lines[0] = "Built-in Objects"
            else:
                lines[0] = os.path.relpath(lines[0], env_dir)
            max_len = max(len(line) for line in lines)

            title = lines[0]
            if title not in file_map:
                file_map[title] = idx
                node_map[title] = {"data": {"id": idx, "content": title}}
                idx += 1
            block = '\n'.join(block.split('\n')[1:])
            block = block.strip()
            block_height = len(lines) * 15

            if block not in node_map:
                node_map[block] = {
                    "data": {
                        "id": idx, 
                        "parent": file_map[title], 
                        "content": block,
                        "width": max_len * 8,
                        'height': block_height,
                        }}
                idx += 1

            if pre_block:
                source = node_map[pre_block]['data']['id']
                target = node_map[block]['data']['id'] 
                edges.append({
                    "data":{
                        "id": str(source) + "-" + str(target),
                        "source": source,
                        "target": target,
                        'color': cur_color
                        }
                    })

            pre_block = block

    nodes = json.dumps([v for k, v in node_map.items()])
    print(nodes)
    edges = json.dumps(edges)
    print(edges)
    if render:
        render_res = flask.render_template("graph.js", NODES=nodes, EDGES=edges)
        return render_res
    else:
        return nodes, edges

def validate_zip(package_path):
    """
    validate a unzipped package
    """
    from src.core.multi_run_helper import get_entrance_files_of_package, \
            validate_package
    # here we assume that web user can not use options.run_all_files
    if not validate_package(package_path):
        return 1 
    if len(get_entrance_files_of_package(package_path)) == 0:
        return 2 
    return 0

@app.route('/check', methods=['POST'])
def check():
    env_dir = options.net_env_dir
    form = flask.request.form
    options.vul_type = form['vul_type']
    if 'module' in form:
        options.module = True
    else:
        options.module = False

    if 'no_file_based' in form:
        options.no_file_based = True
    else:
        options.no_file_based = False
        
    if 'exit_when_found' in form:
        options.exit = True
    else:
        options.exit = False

    if 'run_all' in form:
        options.run_all = True
    else:
        options.run_all = False

    if 'print_all' in form:
        options.print_all_pathes = True
    else:
        options.print_all_pathes = False

    if "sink_funcs" in form:
        options.add_sinks = form['sink_funcs']
        print(options.add_sinks)

    if "timeout" in form:
        try:
            options.timeout = int(form['timeout'])
        except:
            options.timeout = None

    if options.input_file is None:
        # entrance file is not set
        options.input_file = os.path.join(os.path.abspath(env_dir))

    if 'babel' in form:
        options.babel = os.path.abspath(env_dir)
        options.run_env = os.path.join('./net_env_dir/', str(uuid.uuid4()))
    else:
        options.babel = None
        options.run_env = options.net_env_dir

    # we need to clear the results tmp
    with open(os.path.join(options.net_env_dir, "results_tmp.log"), 'w') as fp:
        fp.write("")
    with open(os.path.join(options.net_env_dir, "progress.log"), 'w') as fp:
        fp.write("0\n")

    opg = OPGen()
    try:
        opg.run()
    except Exception as e:
        print(e)

    render_res = generate_graph_json()
    # if use babel, change net env dir to babel run env
    if options.babel is not None:
        options.net_env_dir = options.run_env
    return render_res

@app.route('/progress', methods=['GET', 'POST'])
def get_progress():
    with open(os.path.join(options.net_env_dir, "progress.log"), 'r') as fp:
        lines = fp.readlines()
    if len(lines) != 0:
        return lines[-1]
    else:
        return 'Exploits detecting failed'

@app.route('/upload', methods=['POST'])
def upload():
    options.mark_tainted = []
    options.entrance_func_location = []
    options.net_env_dir = update_env()
    options.run_env = options.net_env_dir
    env_dir = options.net_env_dir
    file_cnt = 0
    file_path = None
    try:
        uploaded = flask.request.files
        for file_values in uploaded.listvalues():
            # we only have one key here
            for f in file_values:
                file_path = os.path.join(env_dir, secure_filename(f.filename))
                f.save(file_path)
                file_cnt += 1
    except Exception as e:
        print(e)
        return "File uploading failed"

    try:
        # unzip the file
        unpack_archive(file_path, env_dir)
    except Exception as e:
        return "File unzipping failed"

    package_path = os.path.join(os.path.abspath(env_dir))
    validate_res = validate_zip(package_path)

    if validate_res == 1:
        return "Cannot find package.json or index.js"
    elif validate_res == 2:
        return "Cannot find the entrance of the package"

    return f"success"

@app.route('/setEntranceFunc', methods=['GET', 'POST'])
def set_entrance_func():
    """
    set a function as entrance function
    """
    data = flask.request.get_json()
    if 'func' not in data:
        return 'Function not set'
    
    options.entrance_func = data['func']
    print(options.entrance_func)
    
    if not hasattr(options, 'entrance_func_location'):
        options.entrance_func_location = []
    options.entrance_func_location.append((app.showing_file, data['funcLoc']))
    
    return "success"

@app.route('/markTainted', methods=['GET', 'POST'])
def mark_tainted():
    """
    mark a variable as tainted
    """
    data = flask.request.get_json()
    if 'var' not in data:
        return 'Function not set'
    
    tainted_var = data['var']
    if not hasattr(options, 'mark_tainted'):
        options.mark_tainted = []

    options.mark_tainted.append((app.showing_file, tainted_var))
    print(options.mark_tainted)
    return tainted_var


@app.route('/getTainteds', methods=['GET'])
def getTainteds(): 
    """
    Response all tained variables of the file; 
    """
    if not hasattr(options, 'mark_tainted'): options.mark_tainted = []
    tainted_list = options.mark_tainted
    tainted_files = {}
    for file_path, tained_range in tainted_list: 
        file_head = os.path.abspath(options.run_env)
        file_name = file_path[len(file_head)+1:]
        if file_name not in tainted_files: tainted_files[file_name] = set()
        range_str = json.dumps(tained_range).partition(', "text": ')[0] + '}'
        tainted_files[file_name].add(range_str)
    return json.dumps({name : list(tainted_files[name]) for name in tainted_files})

@app.route('/getEntrance', methods=['GET'])
def getEntrance():
    """
    Respond to all set entrance of the file;
    """
    if not hasattr(options, 'entrance_func_location'):
        options.entrance_func_location = []
    entrance_list = options.entrance_func_location
    entrance_files = {}
    print(entrance_list)
    for file_path, entrance_range in entrance_list:
        file_head = os.path.abspath(options.run_env)
        file_name = file_path[len(file_head)+1:]
        if file_name not in entrance_files: entrance_files[file_name] = set()
        range_str = json.dumps(entrance_range).partition(', "text": ')[0] + '}'
        entrance_files[file_name].add(range_str)
    return json.dumps({name : list(entrance_files[name]) for name in entrance_files})
