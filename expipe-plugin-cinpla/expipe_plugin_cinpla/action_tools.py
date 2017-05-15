import quantities as pq
from datetime import timedelta, datetime
import expipe.io
from distutils.util import strtobool
import sys
from ._version import get_versions

sys.path.append(expipe.config.config_dir)
if not op.exists(op.join(expipe.config.config_dir, 'expipe_params.py')):
    print('No config params file found, use "expipe' +
          'copy-to-config expipe_params.py"')
else:
    from expipe_params import user_params

DTIME_FORMAT = expipe.io.core.datetime_format

GIT_NOTE = {
    'registered': datetime.strftime(datetime.now(), DTIME_FORMAT),
    'note': 'Registered with the expipe cinpla plugin',
    'expipe-plugin-cinpla-version': get_versions()['version'],
    'expipe-version': expipe.__version__
}


def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [[Y]/n] "
    elif default == "no":
        prompt = " [y/[N]] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")


def deltadate(adjustdate, regdate):
    delta = regdate - adjustdate if regdate > adjustdate else timedelta.max
    return delta


def register_depth(project, action, left=None, right=None):
    regdate = datetime.strptime(action.datetime, DTIME_FORMAT)
    if left is None or right is None:
        ratnr = action.id.split('-')[0]
        try:
            adjustments = project.get_action(name=ratnr + '-adjustment')
        except IOError as e:
            raise IOError(
                str(e) + ', depth parameters left and right must be given')
        adjusts = {}
        for adjust in adjustments.modules:
            values = adjust.to_dict()
            adjusts[datetime.strptime(values['date'], DTIME_FORMAT)] = adjust

        adjustdates = adjusts.keys()
        adjustdate = min(adjustdates, key=lambda x: deltadate(x, regdate))
        adjustment = adjusts[adjustdate].to_dict()
        adleft = adjustment['depth'][0]
        adright = adjustment['depth'][1]
        assert adjustment['location'].lower() == 'left, right'
    left = left or adleft
    right = right or adright
    answer = query_yes_no(
        'Are the following values correct:' +
        ' left = {}, right = {}, '. format(left, right) +
        'adjust date time = {}'.format(adjustdate))
    if answer == False:
        print('Aborting depth registration')
        return
    L = action.require_module('electrophysiology_L').to_dict()
    L['depth'] = pq.Quantity(left, 'mm')
    print('Registering depth left = ', L['depth'])
    action.require_module('electrophysiology_L', contents=L,
                          overwrite=True)
    R = action.require_module('electrophysiology_R').to_dict()
    R['depth'] = pq.Quantity(right, 'mm')
    print('Registering depth right = ', R['depth'])
    action.require_module('electrophysiology_R', contents=R,
                          overwrite=True)


def _get_temp_path(file_record):
    '''

    :param file_record:
    :return:
    '''
    import platform
    folder_name = 'expipe_temp_storage'
    path = op.join(*file_record.local_path.split('/')[-2:])
    if platform.system() == "Linux":
        tmp_path = op.join(os.path.expanduser('~'), folder_name, path)
    elif platform.system() == "Windows":
        # tmp_path = op.join('C:' + os.sep + folder_name, path)
        tmp_path = op.join(os.path.expanduser('~'), folder_name, path)
    else:
        raise NotImplementedError("OS not supported")
    directory = op.split(tmp_path)[0]
    if not op.exists(directory):
        os.makedirs(directory)
    return tmp_path


def generate_templates(action, action_templates, overwrite, git_note=None):
    '''

    :param action:
    :param action_templates:
    :param overwrite:
    :param git_note:
    :return:
    '''
    if git_note is not None:
        action.require_module(name='git-note', contents=git_note,
                              overwrite=overwrite)
    for template in action_templates:
        try:
            if name.startswith('_inherit'):
                name = '_'.join(name.split('_')[1:])
                contents = {'_inherits': '/project_modules/' +
                                         user_params['project_id'] + '/' +
                                         name}
                action.require_module(name=name, contents=contents,
                                      overwrite=overwrite)
            else:
                action.require_module(template=template, name=name,
                                      overwrite=overwrite)
            print('Adding module ' + name)
        except Exception as e:
            print(template)
            raise e


def create_notebook(exdir_path, channel_group=0):
    import exdir
    exob = exdir.File(exdir_path)
    analysis_path = exob.require_group('analysis').directory
    import json
    from pprint import pprint
    currdir = op.dirname(op.abspath(__file__))
    fname = op.join(currdir, 'template_notebook.ipynb')
    with open(fname, 'r') as infile:
        notebook = json.load(infile)
    notebook['cells'][0]['source'] = ['exdir_path = r"{}"\n'.format(exdir_path),
                                      'channel_group = {}'.format(channel_group)]
    fnameout = op.join(analysis_path, 'analysis_notebook.ipynb')
    print('Generating notebook "' + fnameout + '"')
    with open(fnameout, 'w') as outfile:
            json.dump(notebook, outfile,
                      sort_keys=True, indent=4)
    return fnameout