#!/bin/env python

import os.path
import logging
import sys
import argparse
import yaml
import pprint
from utils import setup_logging
from command import CommandRegistry, register_all_commands
from state import InputState
from project_ci import CiProject

log = logging.getLogger(__name__)


all_projects = [
    CiProject,
    ]



def pprint_state_dict(name, state_dict):
    for line in pprint.pformat(state_dict).splitlines():
        log.debug('%s: %s', name, line)

def create_project_by_id(project_id, in_assist_mode):
    for project in all_projects:
        if project.project_id == project_id:
            return project(in_assist_mode)
    assert False, 'Unknown project id: %r; known are: %r' % (
        project_id, [project.project_id for project in all_projects])


def run_project_stage(input_file_path, output_file_path):
    command_registry = CommandRegistry()
    register_all_commands(command_registry)

    with open(input_file_path) as f:
        input = yaml.load(f)
    input_state = InputState.from_dict(input, command_registry)

    project_id = input_state.current_command.project_id
    stage_id = input_state.current_command.stage_id
    in_assist_mode = input_state.current_command.in_assist_mode

    setup_logging(logging.DEBUG if in_assist_mode else logging.INFO)

    pprint_state_dict('input', input)
    log.info('%s %r stage %r on node %r',
                 'Assist' if in_assist_mode else 'Project', project_id, stage_id, input_state.current_node)

    project = create_project_by_id(project_id, in_assist_mode)
    output_state = project.run(stage_id, input_state)

    output = output_state.to_dict()
    pprint_state_dict('output', output)
    with open(output_file_path, 'w') as f:
        yaml.dump(output, f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', help='Input state, yaml')
    parser.add_argument('--output', help='Output state, yaml')
    args = parser.parse_args()
    if not os.path.isfile(args.input):
        println >>sys.stderr, 'Input file is missing: %r' % args.input
        sys.exit(1)

    run_project_stage(args.input, args.output)


if __name__ == '__main__':
    main()
