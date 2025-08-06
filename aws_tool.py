import boto3
import json
import traceback
from datetime import datetime, timezone, timedelta
import config_in

def get_client(service_name: str, aws: int, region: str = "ap-southeast-1") -> boto3.client:
    '''

    :param service_name: iot or iot-data
    :param aws: 1: softgrid aws 2: chevalier aws
    :param region: default: ap-southeast-1
    :return: boto3.client or None
    '''
    if aws == 1:
        # softgrid aws
        aws_access_key_id = config_in.AWS_ACCESS_KEY_ID
        aws_secret_access_key = config_in.AWS_SECRET_ACCESS_KEY
    else:
        print(f"please input correct aws number")
        return None
    iot_client = boto3.client(
        service_name,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region
    )
    return iot_client

def update_thing_shadow(thing_name, shadow: str, aws: int):
    # 创建IoT客户端
    iot_client = get_client('iot-data', aws)
    try:
        desired_state = json.loads(shadow)
        response = iot_client.update_thing_shadow(
            thingName=thing_name,
            payload=json.dumps({
                    'state': {
                        'desired': desired_state
                    }
            })
        )
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            print(f"{thing_name}: shadow更新为{shadow}成功")
        else:
            print(f"{thing_name}: 更新shadow失败，错误信息：{response['ResponseMetadata']['HTTPErrorMessage']}")
    except Exception as e:
        print(f"update {thing_name} shadow {shadow} failed")
        print(traceback.format_exc())

def get_thing_shadow(thing_name, aws: int) -> str:
    # 创建IoT客户端
    iot_client = get_client('iot-data', aws)
    try:
        shadow = iot_client.get_thing_shadow(thingName=thing_name)
        #print(f"{shadow}")
        content = shadow['payload'].read().decode('utf-8')
        #print(f"{type(content)}")
        # 解析内容为JSON格式
        # data = json.loads(content)
        # 打印解析后的数据
        # print(f'the_device_{thing_name}_shaodw_is:{content}')
        #print(json.dumps(data, indent=4))
        #print(f"{shadow['payload'].read()}")
        return content
    except Exception as e:
        print(traceback.format_exc())
        return None

def get_thing_version(thing_name, aws: int) -> str:
    # 创建IoT客户端
    iot_client = get_client('iot-data', aws)
    try:
        shadow = iot_client.get_thing_shadow(thingName=thing_name)
        content = shadow['payload'].read().decode('utf-8')
        jdata = json.loads(content)
        value = jdata.get("state").get("reported")
        v = value.get("CurrentVersion") or value.get("app_version")
        py = value.get("PythonVersion")
        # print(f'the_device_{thing_name}_version_is:  {v}')
        return content, v, py
    except Exception as e:
        print(traceback.format_exc())
        return None

def get_key_word(thing_name, aws: int, key: str) -> str:
    # 创建IoT客户端
    iot_client = get_client('iot-data', aws)
    try:
        shadow = iot_client.get_thing_shadow(thingName=thing_name)
        content = shadow['payload'].read().decode('utf-8')
        jdata = json.loads(content)
        value = jdata.get("state").get("reported")
        v = value.get(key)
        print(f'the_device_{thing_name}_{key}_is:  {v}')
        return content
    except Exception as e:
        print(traceback.format_exc())
        return None

def get_latest_metadata_timestamp(metadata):
    """递归提取 metadata 中所有时间戳，返回最大值（秒级）"""
    timestamps = []

    def _extract_timestamps(data):
        if isinstance(data, dict):
            for key, value in data.items():
                if key == 'timestamp' and isinstance(value, int):
                    timestamps.append(value)
                    # print(value)
                else:
                    _extract_timestamps(value)
        elif isinstance(data, list):
            for item in data:
                _extract_timestamps(item)

    _extract_timestamps(metadata)
    return max(timestamps) if timestamps else None

def get_thing_shadow_update_time(thing_name, aws):
    # 创建IoT Data客户端
    client = get_client('iot-data', aws)

    try:
        # 获取设备影子
        response = client.get_thing_shadow(thingName=thing_name)
        # 读取并解析Payload
        payload = json.loads(response['payload'].read())
        # 提取时间戳（单位：毫秒）
        # print(json.dumps(payload, indent=4))
        # print(type(payload))
        # timestamp_sec = payload.get('timestamp')
        # print(timestamp_sec)
        actual_latest_ts = get_latest_metadata_timestamp(payload.get('metadata', {}))
        if actual_latest_ts:
            # 1. 获取UTC时间并附加时区
            utc_time = datetime.utcfromtimestamp(actual_latest_ts).replace(tzinfo=timezone.utc)
            # 2. 转换为北京时间（东八区）
            beijing_time = utc_time.astimezone(timezone(timedelta(hours=8)))

            # 3. 格式化为目标字符串（去掉时区偏移）
            beijing_str = beijing_time.strftime("%Y-%m-%dT%H:%M:%S")
            # print(beijing_str)

        actual_latest_ts2 = get_latest_metadata_timestamp(payload['metadata'].get('reported', {}))
        if actual_latest_ts2:
            # 1. 获取UTC时间并附加时区
            utc_time = datetime.utcfromtimestamp(actual_latest_ts2).replace(tzinfo=timezone.utc)
            # 2. 转换为北京时间（东八区）
            beijing_time = utc_time.astimezone(timezone(timedelta(hours=8)))

            # 3. 格式化为目标字符串（去掉时区偏移）
            beijing_str2 = beijing_time.strftime("%Y-%m-%dT%H:%M:%S")
            # print(beijing_str)
        if beijing_str and beijing_str2:
            return [beijing_str, beijing_str2]
        else:
            return None
    except client.exceptions.ResourceNotFoundException:
        return f"Thing '{thing_name}'不存在"
    except Exception as e:
        return f"发生错误: {str(e)}"

def list_thing(aws: int):
    # 创建IoT客户端
    iot_client = get_client('iot', aws)
    next_token = None
    all_things = []
    try:
        while True:
            if next_token:
                response = iot_client.list_things(nextToken=next_token)
            else:
                response = iot_client.list_things()
            #all_things.extend(response['things'])
            for item in response['things']:
                #print(item)
                if 'thingName' and 'thingTypeName' in item:
                    all_things.append([item['thingName'], item['thingTypeName']])
            #print(type(response['things']))
            #all_things.extend([response['things']['thingName'], response['things']['thingTypeName']])
            # 检查是否还有更多页面
            if 'nextToken' in response:
                next_token = response['nextToken']
            else:
                break
        for thing in all_things:
            print(thing)

        for thing in all_things:
            print(thing[0])

    except Exception as e:
        #print(f"{e}")
        print(traceback.format_exc())


if __name__ == '__main__':
    import argparse
    argpaser = argparse.ArgumentParser()
    argpaser.add_argument("-t", "--thing", action="store", dest="thing", help="the thing's name u want to operate")
    argpaser.add_argument("-f", "--file", action="store", dest="file", help="the file with all the things' name in it;"
                                                                            " import: one thing in one line")
    argpaser.add_argument("-a", "--aws", action="store", dest="aws", help="the aws platform u want to operate; 1: softgrid 2: chevalier")
    argpaser.add_argument("-m", "--mode", action="store", dest="mode", help="1: get the device's shadow and show out."
                                                                            "    exam: -m 1 -t S0001234 or -m 1 -f haha.txt;"
                                                                            "1.1: get app_version"
                                                                            "    2: update the device's shadow."
                                                                            "    exam: -m 2 -t S0001234 -v 2.3.5 or -m 2 -v 2.3.5 -f haha.txt;"
                                                                            "    3: list all the devices on aws."
                                                                            "    exam: -m 3"
                                                                            "4: get the key words from reported"
                                                                            "5: get the latest shadow update time")
    argpaser.add_argument("-k", "--key", action="store", dest="key", help='''the thing's desired shadow's key word, '''
                                                                                '''such as: DesiredVersion''')
    argpaser.add_argument("-v", "--value", action="store", dest="value", help='''the thing's desired shadow's value, '''
                                                                          '''such as: 2.1.0''')
    argpaser.add_argument("-p", "--type", action="store", dest="type", help='''the thing's desired shadow's value's type, '''
                                                                              '''such as: int or str, default is str''')
    args = argpaser.parse_args()

    if int(args.aws) != 1 and int(args.aws) != 2:
        print(f"please input correct aws platform, default is softgrid aws")
        args.aws = 1
    things = []
    if args.mode == '1' or args.mode == "1.1":
        #get the device's shadow and show out
        if args.thing:
            things.append(args.thing)
        elif args.file:
            with open(args.file, 'r') as f:
                for line in f:
                    things.append(line.strip())
        else:
            print(f'please input a thing name or the file of thing names')
            exit()
        for i in things:
            print(i)
        print(f"will get these devices' shadow, if ok, please input yes or no")
        str = input()
        if str.upper() == "YES" or str.upper() == "Y":
            for thing in things:
                if args.mode == '1':
                    get_thing_shadow(thing, int(args.aws))
                elif args.mode == '1.1':
                    get_thing_version(thing, int(args.aws))
        else:
            print('restart')
            exit()
    elif args.mode == '2':
        #update the device's shadow
        if args.thing:
            things.append(args.thing)
        elif args.file:
            with open(args.file, 'r') as f:
                for line in f:
                    things.append(line.strip())
        else:
            print(f'please input a thing name or the file of thing names')
            exit()
        desired_state = {}
        if args.key and args.value:
            if args.type == "int":
                desired_state = json.dumps({args.key: int(args.value)})
            elif args.type == "str":
                desired_state = json.dumps({args.key: str(args.value)})
            else:
                desired_state = json.dumps({args.key: args.value})
        else:
            print(f'please input the desired version')
            exit()
        for i in things:
            print(i)
        print(f'will update the desired version number of these devices, if ok,please input yes or no')
        str = input()
        if str.upper() == "YES" or str.upper() == "Y":
            for thing in things:
                update_thing_shadow(thing, desired_state, int(args.aws))
        else:
            print('restart')
            exit()
    elif args.mode == '3':
        #list all the devices on aws
        list_thing(int(args.aws))
    elif args.mode == '4':
        #get the key words from reported shadow
        if args.thing:
            things.append(args.thing)
        elif args.file:
            with open(args.file, 'r') as f:
                for line in f:
                    things.append(line.strip())
        else:
            print(f'please input a thing name or the file of thing names')
            exit()
        for i in things:
            print(i)
        print(f"will get these devices' shadow, if ok, please input yes or no")
        str = input()
        if str.upper() == "YES" or str.upper() == "Y":
            for thing in things:
                get_key_word(thing, int(args.aws), args.key)
    elif args.mode == '5':
        if args.thing:
            things.append(args.thing)
        elif args.file:
            with open(args.file, 'r') as f:
                for line in f:
                    things.append(line.strip())
        else:
            print(f'please input a thing name or the file of thing names')
            exit()
        for i in things:
            print(i)
        print(f"will get these devices' shadow, if ok, please input yes or no")
        str = input()
        if str.upper() == "YES" or str.upper() == "Y":
            for thing in things:
                update_time = get_thing_shadow_update_time(thing, 1)
                if update_time:
                    print(f"设备 {thing} 影子的最后更新时间: {update_time[0]}, 影子最后上报时间： {update_time[1]}")
                else:
                    print(f"设备 {thing} 影子的最后更新时间: none")

    else:
        print(f'please input the correct parameter')
