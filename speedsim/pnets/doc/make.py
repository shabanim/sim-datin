import os
import shutil
import subprocess

SPHINX = 'C:/work/tools/sphinx'

build_dir = '_build'


def add_python_path(path):
    if 'PYTHONPATH' in os.environ:
        os.environ['PYTHONPATH'] = os.environ['PYTHONPATH'] + os.pathsep + path
    else:
        os.environ['PYTHONPATH'] = path


script_path = os.path.realpath(__file__)
doc_dir = os.path.dirname(script_path)
os.chdir(doc_dir)

proj_dir = os.path.dirname(os.path.dirname(script_path))

add_python_path(SPHINX)
add_python_path(os.path.join(proj_dir, 'src'))

# ==============================
# Clean old files
# ==============================
shutil.rmtree(build_dir, ignore_errors=True)
shutil.rmtree('modules', ignore_errors=True)


def autogen(*files, output=None):
    """
    Run sphinx-autogen recursively on the specified file.

    :param file: input .rst file
    :param output: output directory to inspect
    """
    print("-D- Running", 'sphinx-autogen', '-t', os.path.join(doc_dir, '_templates'), *files, '...')
    subprocess.check_call([
        'python', 'C:/work/tools/sphinx/sphinx/ext/autosummary/generate.py', '-i',  '-t',
        os.path.join(doc_dir, '_templates'), *files
    ])


# ================================
# Build new documentation
# ================================
autogen('index.rst')

subprocess.check_call([
    'sphinx-build', '-M', 'html', '.',  build_dir
])

# copy to PROJ_DIR/public for publishing to GitLab pages
shutil.rmtree(os.path.join(proj_dir, 'public'), ignore_errors=True)
shutil.move(os.path.join(build_dir, 'html'), os.path.join(proj_dir, 'public'))
