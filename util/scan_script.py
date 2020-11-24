import requests
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
        weirdos = []
        full_json = requests.get(url).json()
        for data in full_json:
            vendor = data['origVendor']
            if vendor.lower().startswith("hangzhou hikvision digital technology co., ltd"):
                vendor = "hikvision"
            elif vendor.lower().startswith("hanwha"):
                vendor = "hanwha"
            elif vendor.lower().startswith("samsung"):
                vendor = "samsung"
            elif (vendor.lower().startswith("digital watchdog")
                  or vendor.lower().startswith("digital_watchdog")
                  or vendor.lower().startswith("digitalwatchdog")):
                vendor = "dw"
            else:
                vendor = vendor.lower()
            model = data['origModel'].lower()
            # if vendor == 'general' and model.startswith('hen162'):
            #    data_except = data
            if '*' in vendor or '*' in model:
                weirdos.append([vendor, model])
                continue
            if data['isMultiSensor']:
                multisensors.append([vendor, model])
            if ((data['hardwareType'] == 'Encoder') or
                    (data['hardwareType'] == 'DVR')):
                if not (data['hardwareType'] == 'DVR' and
                        vendor == 'hanwha'):
                    encoders.append([vendor, model])
            if ((data['hardwareType'] == 'Camera') and
                    (not data['isMultiSensor'])):
                regulars.append([vendor, model])
        #todo: revise usage of the deepcopies
        encoders_copy = copy.deepcopy(encoders)
        encoders_regulars = compare_lists(encoders, regulars)
        encoders_multisensors = compare_lists(encoders_copy, multisensors)
        multisensors_regulars = compare_lists(multisensors, regulars)
        full_intresections_list = (encoders_regulars + encoders_multisensors +
                                   multisensors_regulars + weirdos)
        self.intersections = list(set(tuple(i) for i
                                      in full_intresections_list))
        self.multisensors = multisensors
        self.encoders = encoders
        self.regulars = regulars
        # self.test = data_except


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
            if ('canShareLicenseGroup' in data) and (data['canShareLicenseGroup']):
                for model in data['keys']:
                    if model not in multisensors_list_draft:
                        multisensors_list_draft.append(model.lower())
            if ('analogEncoder' in data) and (data['analogEncoder']):
                for model in data['keys']:
                    if model not in encoders_list_draft:
                        encoders_list_draft.append(model.lower())
        for name in multisensors_list_draft:
            name = name.split('|')
            multisensors_list.append([name[0], name[1]])
        for name in encoders_list_draft:
            name = name.split('|')
            encoders_list.append([name[0], name[1]])
        for _list in (encoders_list, multisensors_list):
            for device in _list:
                for i in range(len(device)):
                    if device[i].endswith('*'):
                        device[i] = device[i][:len(device[i]) - 1]
        self.multisensors = multisensors_list
        self.encoders = encoders_list


"""compare_lists function compares two lists, removes matched elements from
the initial lists and returns intersections for both input lists
"""

#todo: refactore compare_lists function
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
file with output_file_name in a format dictated by resource_data.json file.
"""


def write_list_to_file(input_list, output_file_name):
    with open(output_file_name, 'w') as _file:
        _file.write('Vendor|Model:\n')
        for item in input_list:
            _file.write('"' + item[0] + '|' + item[1] + '",\n')


"""function filter_exceptions takes list of lists as
an input and  filters out badly named devices
"""


def filter_exceptions(input_list):
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
        'onvif_encoder',
        'n/a'
    ]
    for device_name in reversed(input_list):
        isfiltered = 0
        for item in device_name:
            if not item:
                input_list.remove(device_name)
                continue
            for filter_str in exception_list:
                if filter_str == item:
                    isfiltered += 1
        if isfiltered == 2:
            print(("too generic model is filtered: " + str(device_name)))
            input_list.remove(device_name)

#todo: refactor main function
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
        check_result = [[], []]
        resource_lists = copy.deepcopy(resource_lists_input)
        stat_lists = copy.deepcopy(stat_lists_input)
        #todo: revise the loop, simplify the condition
        for i in range(0, 2):
            for stat_list in stat_lists[i]:
                for resource_list in resource_lists[i]:
                    if (not (not stat_list[0].startswith(resource_list[0]) or not stat_list[1].startswith(
                            resource_list[1]))):
                        check_result[i].append(stat_list)
        for i in range(0, 2):
            for x in check_result[i]:
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
