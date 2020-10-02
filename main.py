import os
import subprocess
import sys
import re
from shutil import which

SYSTEM_PACKAGES_REQUIRED = ['adb', 'aapt']


def parse_device_list(str_item):
    raw_list = filter(None, str_item.splitlines()[1:])

    devices = []
    for raw_device in raw_list:
        parts = raw_device.split()
        extra_parts = [it.decode("utf-8") for it in parts[1:]]
        devices.append((parts[0].decode("utf-8"), " ".join(extra_parts)))
    return devices


def parse_app_list(str_item):
    raw_list = filter(None, str_item.splitlines()[1:])

    apps = []
    for raw_app in raw_list:
        app = raw_app.decode("utf-8")
        base_app = app.split(':')[1]
        app_name = base_app.split('=')[-1]
        app_location = base_app.replace("="+app_name, "")
        apps.append((app_name, app_location))
    return apps


def get_devices():
    p = subprocess.Popen(
        ["adb", 'devices', '-l'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    out, err = p.communicate()
    if len(err) == 0:
        return parse_device_list(out)
    else:
        return []


def select_device(devices):
    for i in range(len(devices)):
        id, name = devices[i]
        print("(%d) - %s [%s]" % (i+1, id, name))

    def num(s):
        try:
            return int(s)
        except ValueError:
            return
    choosen = None
    while True:
        choosen = num(sys.stdin.readline())
        if (choosen is not None and choosen > 0 and choosen <= len(devices)):
            break
    return devices[choosen - 1][0]


def get_apps():
    command = "pm list packages -f -3"
    p = subprocess.Popen(
        "adb shell {0}".format(command),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    try:
        out, err = p.communicate()
        if len(err) == 0:
            return parse_app_list(out)
        else:
            return []
    except KeyboardInterrupt:
        return []


def download_apk(app_location, apk_name):
    p = subprocess.Popen(
        "adb pull {0} {1}".format(app_location, apk_name),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    out, err = p.communicate()
    if len(err) == 0:
        return True
    else:
        return False


def parse_permissions_from_apk(str_item):
    raw_list = filter(None, str_item.splitlines()[1:])
    base_text = "uses-permission:"

    permissions = []
    for item in raw_list:
        str_item = item.decode('utf-8')
        if base_text in str_item:
            text_arr = re.findall(r"'(.*?)'", str_item)
            if text_arr:
                permissions.append(text_arr[0])

    return permissions


def get_permissions_from_apk(apk_location):
    p = subprocess.Popen(
        "aapt d permissions {0}".format(apk_location),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    out, err = p.communicate()
    if len(err) == 0:
        return parse_permissions_from_apk(out)
    else:
        return False


def grant_permissions(app_name, permissions):
    for permission in permissions:
        command = f"pm grant {app_name} {permission}"
        p = subprocess.Popen(
            "adb shell {0}".format(command),
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        try:
            p.communicate()
        except KeyboardInterrupt:
            break


def _check_required_packages(packages):
    is_valid = all(which(it) is not None for it in packages)
    if not is_valid:
        print("required packages not found.")
        print(", ".join(packages))
        sys.exit(1)


def progress(count, total, suffix=''):
    bar_len = 60
    filled_len = int(round(bar_len * count / float(total)))

    percents = round(100.0 * count / float(total), 1)
    bar = '=' * filled_len + '-' * (bar_len - filled_len)

    sys.stdout.write('[%s] %s%s ...%s\r' % (bar, percents, '%', suffix))
    sys.stdout.flush()


def main():
    _check_required_packages(SYSTEM_PACKAGES_REQUIRED)
    devices = get_devices()
    if not devices:
        print("Could not find any device")
        sys.exit(1)
    device_selected = select_device(devices)
    os.environ['ANDROID_SERIAL'] = device_selected
    print("Device selected", device_selected)
    print("Getting apps")
    apps = get_apps()
    total = len(apps)
    count = 0
    for app_name, app_location in apps:
        count = count + 1
        apk_name = f"{app_name}.apk"
        is_apk = download_apk(app_location, apk_name)
        if is_apk:
            permissions = get_permissions_from_apk(apk_name)
            os.remove(apk_name)
            grant_permissions(app_name, permissions)
            print(app_name, "permissions grant")
            progress(count, total)


if __name__ == "__main__":
    main()
