from expipe_plugin_cinpla.imports import *
from expipe_plugin_cinpla.tools.action import generate_templates, get_git_info, query_yes_no
from expipe_plugin_cinpla.tools import config


def attach_to_cli(cli):
    @cli.command('register-subject',
                 short_help=('Register a subject to the "subjects-registry" ' +
                             'project.'))
    @click.argument('subject-id')
    @click.option('--overwrite',
                  is_flag=True,
                  help='Overwrite modules or not.',
                  )
    @click.option('-u', '--user',
                  type=click.STRING,
                  help='The experimenter performing the registration.',
                  )
    @click.option('--location',
                  required=True,
                  type=click.STRING,
                  help='The location of the animal.',
                  )
    @click.option('--birthday',
                  required=True,
                  type=click.STRING,
                  help='The birthday of the subject, format: "dd.mm.yyyy".',
                  )
    @click.option('--cell_line',
                  type=click.STRING,
                  callback=config.optional_choice,
                  envvar=PAR.POSSIBLE_CELL_LINES,
                  help='Add tags to action.',
                  )
    @click.option('--developmental_stage',
                  type=click.STRING,
                  help="The developemtal stage of the subject. E.g. 'embroyonal', 'adult', 'larval' etc.",
                  )
    @click.option('--gender',
                  type=click.STRING,
                  help='Male or female?',
                  )
    @click.option('--genus',
                  type=click.STRING,
                  help='The Genus of the studied subject. E.g "rattus"',
                  )
    @click.option('--health_status',
                  type=click.STRING,
                  help='Information about the health status of this subject.',
                  )
    @click.option('--label',
                  type=click.STRING,
                  help='If the subject has been labled in a specific way. The lable can be described here.',
                  )
    @click.option('--population',
                  type=click.STRING,
                  help='The population this subject is offspring of. This may be the bee hive, the ant colony, etc.',
                  )
    @click.option('--species',
                  type=click.STRING,
                  help='The scientific name of the species e.g. Apis mellifera, Homo sapiens.',
                  )
    @click.option('--strain',
                  type=click.STRING,
                  help='The strain the subject was taken from. E.g. a specific genetic variation etc.',
                  )
    @click.option('--trivial_name',
                  type=click.STRING,
                  help='The trivial name of the species like Honeybee, Human.',
                  )
    @click.option('--weight',
                  nargs=2,
                  type=(click.FLOAT, click.STRING),
                  default=(None, None),
                  help='The weight of the animal.',
                  )
    @click.option('--message', '-m',
                  multiple=True,
                  type=click.STRING,
                  help='Add message, use "text here" for sentences.',
                  )
    @click.option('-t', '--tag',
                  multiple=True,
                  type=click.STRING,
                  callback=config.optional_choice,
                  envvar=PAR.POSSIBLE_TAGS,
                  help='Add tags to action.',
                  )
    def generate_subject(subject_id, overwrite, user, message, location, tag,
                         **kwargs):
        DTIME_FORMAT = expipe.io.core.datetime_format
        project = expipe.require_project('subjects-registry')
        action = project.require_action(subject_id)
        kwargs['birthday'] = datetime.strftime(
            datetime.strptime(kwargs['birthday'], '%d.%m.%Y'), DTIME_FORMAT)
        action.datetime = datetime.now()
        action.type = 'Info'
        action.tags.extend(list(tag))
        action.location = location
        action.subjects = [subject_id]
        user = user or PAR.USER_PARAMS['user_name']
        user = user or []
        if len(user) == 0:
            raise ValueError('Please add user name')
        print('Registering user ' + user)
        action.users = [user]
        action.messages.extend([{'message': m,
                                 'user': user,
                                 'datetime': datetime.now()}
                               for m in message])
        subject_template_name = PAR.MODULES.get('subject') or 'subject_subject'
        subject = action.require_module(template=subject_template_name,
                                        overwrite=overwrite).to_dict()
        for key, val in kwargs.items():
            if isinstance(val, (str, float, int)):
                subject[key]['value'] = val
            elif isinstance(val, tuple):
                if not None in val:
                    subject[key] = pq.Quantity(val[0], val[1])
            elif isinstance(val, type(None)):
                pass
            else:
                raise TypeError('Not recognized type ' + str(type(val)))
        not_reg_keys = []
        for key, val in subject.items():
            if isinstance(val, dict):
                if val.get('value') is None:
                    not_reg_keys.append(key)
                elif len(val.get('value')) == 0:
                    not_reg_keys.append(key)
        if len(not_reg_keys) > 0:
            warnings.warn('No value registered for {}'.format(not_reg_keys))
        action.require_module(name=subject_template_name, contents=subject,
                              overwrite=True)