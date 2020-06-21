import base64
import hashlib
import os
from datetime import datetime
from typing import List

import requests


class RC4:
    def initKey(self, paramString: str):
        arrayOfByte2 = paramString.encode()
        arrayOfByte1 = []
        for i in range(256):
            if i <= 127:
                arrayOfByte1.append(i)
            else:
                arrayOfByte1.append(-128 + i - 128)
        j = k = 0
        if arrayOfByte2 is None or len(arrayOfByte2) == 0:
            return None
        i = 0
        while True:
            arrayOfByte = arrayOfByte1
            if (i < 256):
                k = (arrayOfByte2[j] & 0xFF) + (arrayOfByte1[i] & 0xFF) + k & 0xFF
                arrayOfByte1[i], arrayOfByte1[k] = arrayOfByte1[k], arrayOfByte1[i]
                j = (j + 1) % len(arrayOfByte2)
                i += 1
                continue

            return arrayOfByte

    def RC4Base(self, paramArrayOfByte: List[int], paramString: str) -> List[int]:
        k = j = 0
        arrayOfByte1 = self.initKey(paramString)
        arrayOfByte2 = [0] * len(paramArrayOfByte)
        for i in range(len(paramArrayOfByte)):
            k = k + 1 & 0xFF
            j = (arrayOfByte1[k] & 0xFF) + j & 0xFF
            arrayOfByte1[j], arrayOfByte1[k] = arrayOfByte1[k], arrayOfByte1[j]
            b2 = arrayOfByte1[k]
            b3 = arrayOfByte1[j]
            arrayOfByte2[i] = (paramArrayOfByte[i] ^ arrayOfByte1[(b2 & 0xFF) + (b3 & 0xFF) & 0xFF])
            i += 1
        return arrayOfByte2


def get_md5(text):
    md5 = hashlib.md5()
    md5.update(text.encode('utf-8'))
    result = md5.hexdigest()
    return result


def get_sha1(text):
    sha1 = hashlib.sha1()
    sha1.update(text.encode('utf-8'))
    result = sha1.hexdigest()
    return result


def decode(ciphertext: str, param: str) -> str:
    key = get_md5(f'aibang{param}')
    step1 = [byte if byte <= 127 else byte - 256 for byte in base64.b64decode(ciphertext.encode())]
    step2 = [byte if byte > 0 else byte + 256 for byte in rc4.RC4Base(step1, key)]
    result = bytes(step2).decode('utf-8')
    return result


def get_abtoken(timestamp, path):
    text = f'bjjw_jtcxandroid67a88ec31de7a589a2344cc5d0469074{timestamp}{path}'
    abtoken = get_md5(get_sha1(text))
    return abtoken


def read_headers(headers_path):
    if not os.path.isfile(headers_path):
        raise RuntimeError("headers文件不存在！")

    headers = {}
    with open(headers_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines:
            line = line.strip()
            if len(line) == 0:
                continue

            split_index = line.find(':')
            headers[line[:split_index]] = line[split_index + 1:]
        return headers


def get_path(url):
    try:
        path = '/'.join(url.split('?')[0].split('/')[3:])
        return f'/{path}'
    except Exception as e:
        print(e)


def do_get(url):
    try:
        path = get_path(url)
        timestamp = str(int(datetime.now().timestamp()))
        headers['TIME'] = timestamp
        headers['ABTOKEN'] = get_abtoken(timestamp, path)
        resp = rsession.get(url, headers=headers)
        if resp.status_code == 200:
            result = resp.json()
            return result
        else:
            print(f'Wrong status_code: {resp.status_code}!')

    except Exception as e:
        print(e)
    finally:
        print(f'[GET] {url}')


def get_all_lines():
    url = base_url + '/ssgj/v1.0.0/checkupdate?version=0'
    result = do_get(url)
    if result is None or result.get('errcode', '-1') != '200':
        raise RuntimeError('返回数据错误！')
    lines = result.get('lines', {}).get('line')

    datas = []
    for line in lines:
        line_id = line.get('id')
        line_name = line.get('linename')
        # classify = line.get('classify')
        data = f'{int(line_id):4d} {line_name}\n'
        datas.append(data)

    with open('lines.txt', 'w', encoding='utf-8') as f:
        f.writelines(datas)


def get_line_detail(line_id):
    line_id = str(line_id)
    url = base_url + f'/ssgj/v1.0.0/update?id={line_id}'
    result = do_get(url)
    if result is None or result.get('errcode', '-1') != '200':
        raise RuntimeError('返回数据错误！')
    busline = result.get('busline')[0]
    line_name = decode(busline.get('linename'), line_id)
    runtime = busline.get('time')

    datas = []
    datas.append(f'{line_name} {runtime}\n')
    stations = busline.get('stations', {}).get('station')
    for station in stations:
        station_name = decode(station.get('name'), line_id)
        station_id = decode(station.get('no'), line_id)
        datas.append(f'{int(station_id):2d} {station_name}\n')

    with open(f'line_{line_id}.txt', 'w', encoding='utf-8') as f:
        f.writelines(datas)


def get_realtime_bus(line_id, station_id):
    url = base_url + f'/ssgj/bus.php?no={station_id}&versionid=6&city=%E5%8C%97%E4%BA%AC&datatype=json&encrypt=1&id={line_id}&type=1 '
    result = do_get(url)
    if result is None or result.get('root', {}).get('status', '-1') != '200':
        raise RuntimeError('获取数据错误')

    buses = result.get('root', {}).get('data', {}).get('bus')

    for bus in buses:
        gps_update_time = bus.get('gt')
        bus_id = bus.get('id')
        next_station = decode(bus.get('ns'), gps_update_time)
        next_station_no = decode(bus.get('nsn'), gps_update_time)
        distance = decode(bus.get('sd'), gps_update_time)
        remain_seconds = decode(bus.get('srt'), gps_update_time)
        arriving_time = decode(bus.get('st'), gps_update_time)
        if arriving_time == '-1':
            continue
        arriving_time = datetime.fromtimestamp(int(arriving_time))

        print(
            f'车辆No.{bus_id}下一站{next_station_no}-{next_station}，距离目的站点还有{int(station_id) - int(next_station_no) + 1}站、{distance}米，预计{arriving_time}到达，还有{remain_seconds}s'
        )


if __name__ == '__main__':
    base_url = 'http://transapp.btic.org.cn:8512'

    rc4 = RC4()

    headers = read_headers('bus.headers')
    headers['IMSI'] = os.getenv('IMSI')

    rsession = requests.Session()
    rsession.headers.update(headers)

    if not os.path.exists('lines.txt'):
        get_all_lines()

    line_id = 2361
    station_id = 22

    if not os.path.exists(f'line_{line_id}.txt'):
        get_line_detail(line_id)

    get_realtime_bus(line_id, station_id)
