from __future__ import with_statement
import requests
import json
import copy

# todo: redo everything using map, split and filter functions
"""StatServerList class downloads full list of devices from the Nx Stat Server
Its attributes represent lists of the unique multisensor cameras, encoders,
regular cameras and list of lists of original models intersections
"""


class StatServerData:
    def __init__(self):
        url = "https://cameras.networkoptix.com/api/v1/cacamerasorig/"
        multisensors = []
        encoders = []
        regulars = []
        full_json = requests.get(url).json()
        for data in full_json:
            vendor = data['origVendor']
            model = data['origModel']
            if (data['isMultiSensor'] and
                    not (vendor.startswith('Hanwha')
                    or vendor.startswith('Samsung')
                    or vendor.startswith('ArecontVision')
                    or vendor.startswith('PelcoOptera')
                    or vendor == 'Digital Watchdog')):
                multisensors.append([vendor, model])
            if ((data['hardwareType'] == 'Encoder') or
                    (data['hardwareType'] == 'DVR')):
                if not (data['hardwareType'] == 'DVR' and
                        vendor.startswith('Hanwha')):
                    encoders.append([vendor, model])
            if ((data['hardwareType'] == 'Camera') and
                    (not data['isMultiSensor'])):
                regulars.append([vendor, model])
        for lists in [multisensors, encoders, regulars]:
            fix_encoding(lists)
        encoders_copy = copy.deepcopy(encoders)
        encoders_regulars = compare_lists(encoders, regulars)
        encoders_multisensors = compare_lists(encoders_copy, multisensors)
        multisensors_regulars = compare_lists(multisensors, regulars)
        full_intresections_list = (encoders_regulars + encoders_multisensors +
            multisensors_regulars)
        self.intersections = list(set(tuple(i) for i
            in full_intresections_list))
        self.multisensors = multisensors
        self.encoders = (encoders)
        self.regulars = (regulars)


"""ResourceDataJsonList class downloads Nx json file with advanced options.
Its attributes represent lists of multisensor cameras and analog encoders.
"""


class ResourceDataJson:
    def __init__(self):
        url = "http://resources.vmsproxy.com/resource_data.json"
        multisensors_list_draft = []
        multisensors_list = []
        encoders_list_draft = []
        encoders_list = []
        full_json = requests.get(url).json()
        for data in full_json['data']:
            if 'canShareLicenseGroup' in data:
                for model in data['keys']:
                    if model not in multisensors_list_draft:
                        multisensors_list_draft.append(model)
            if 'analogEncoder' in data:
                for model in data['keys']:
                    if model not in encoders_list_draft:
                        encoders_list_draft.append(model)
        for name in multisensors_list_draft:
            if not (name.startswith('Hanwha') or name.startswith('Samsung')):
                for i in range(len(name)):
                    if name[i] == '|':
                        multisensors_list.append([name[:i], name[i+1:]])
        for name in encoders_list_draft:
            for i in range(len(name)):
                if name[i] == '|':
                    encoders_list.append([name[:i], name[i+1:]])
        fix_encoding(multisensors_list)
        fix_encoding(encoders_list)
        for _list in (encoders_list, multisensors_list):
            for device in _list:
                for i in range(len(device)):
                    if device[i].endswith('*'):
                        device[i] = device[i][:len(device[i])-1]
        self.multisensors = (multisensors_list)
        self.encoders = (encoders_list)


"""fix_encoding function cuts off weirdly encoded characters in the strings
and converts them from unicode to python lowercase strings
"""


def fix_encoding(input_list):
    for device in input_list:
        try:
            unicode(device[0], errors='strict')
            device[0].lower()
        except TypeError:
            device[0] = device[0].encode('ascii', 'ignore').lower()
        try:
            unicode(device[1], errors='ignore')
            device[1].lower()
        except TypeError:
            device[1] = device[1].encode('ascii', 'ignore').lower()


"""compare_lists function compares two lists, removes matched elements from
the initial lists and returns intersections for both input lists
"""


def compare_lists(input_list_1, input_list_2):
    bad_list = []
    check_list_1 = copy.deepcopy(input_list_1)
    check_list_2 = copy.deepcopy(input_list_2)
    for x in check_list_1:
        for y in check_list_2:
            if (((x[0] == y[0]) and (x[1] == y[1])) or
                    ((x[1] == y[0]) and (x[0] == y[1]))):
                bad_list.append(x)
                input_list_1.remove(x)
                input_list_2.remove(y)
    return bad_list

"""write_list_to_file function writes nested lists to the
file with output_file_name
"""


def write_list_to_file(input_list, output_file_name):
    with open(output_file_name, 'w') as _file:
        _file.write('Vendor|Model:\n')
        for item in input_list:
            _file.write(item[0]+'|'+item[1]+'\n')

"""function filter_exceptions takes list of lists as
an input and  filters out badly named devices
"""


def filter_exceptions(input_list):
    result = []
    exception_list = [
        'onvif',
        'networkcamera',
        'network camera',
        'network_camera',
        'h264',
        'ipc-model',
        'ip camera',
        'ipcamera',
        'ip_camera',
        'network video recorder',
        'embedded net dvr',
        'embedded_net_dvr',
        'group',
        'private',
        'general',
        'onvif_encoder'
        ]
    for device_name in reversed(input_list):
        isFiltered = 0
        for item in device_name:
            if not item:
                input_list.remove(device_name)
                continue
            for filter_str in exception_list:
                if filter_str == item:
                    isFiltered += 1
        if isFiltered == 2:
            print device_name
            input_list.remove(device_name)


def main():
    resource_data = ResourceDataJson()
    stat_data = StatServerData()
    stat_data_lists = [
        stat_data.encoders,
        stat_data.multisensors
    ]
    resource_data_lists = [
        resource_data.encoders,
        resource_data.multisensors
    ]

    def check_db_with_stat(resource_lists_input, stat_lists_input):
        result = [[], []]
        resource_lists = copy.deepcopy(resource_lists_input)
        stat_lists = copy.deepcopy(stat_lists_input)
        for i in range(0, 2):
            for stat_list in stat_lists[i]:
                for resource_list in resource_lists[i]:
                    if (stat_list[0].startswith(resource_list[0]) and
                            stat_list[1].startswith(resource_list[1])):
                        result[i].append(stat_list)
        for i in range(0, 2):
            for x in result[i]:
                if x in stat_lists[i]:
                    stat_lists[i].remove(x)
        return stat_lists

    result = check_db_with_stat(resource_data_lists, stat_data_lists)
    for data_list in result:
        filter_exceptions(data_list)
    write_list_to_file(result[0], 'encoders_diff.txt')
    write_list_to_file(result[1], 'multisensors_diff.txt')
    write_list_to_file(stat_data.intersections, 'manual_check.txt')


if __name__ == '__main__':
    main()
