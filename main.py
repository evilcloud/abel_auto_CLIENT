import requests
import subprocess
import logging
import socket
import xml.etree.ElementTree as ET

# Constants
API_URL = "https://abel-auto.onrender.com/api/report"
GENERAL_INFO = "systemctl status abel.service | grep ' m ' | tail -1"


def run_command(command):
    try:
        output = subprocess.check_output(command, shell=True)
        return output.decode("utf-8")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error running command {command}: {e}")
        return None


def capture_hostname():
    return socket.gethostname()


def capture_gpu_info():
    output = run_command("nvidia-smi -q -x")
    if output is None:
        return None, None

    root = ET.fromstring(output)
    total_power = 0.0
    gpus = []
    for gpu in root.iter('gpu'):
        gpu_name = gpu.find('product_name').text
        power_draw = float(gpu.find('power_readings/power_draw').text.split()[0])
        total_power += power_draw
        gpus.append(gpu_name)
    return gpus, total_power


def extract_hashrate(output):
    words = output.split()
    if "abelminer" in words and "m" in words:
        try:
            hashrate_value, hashrate_unit = words[10], words[11]
            hashrate_value = float(hashrate_value)

            if hashrate_unit == "Kh":
                hashrate_value /= 1000
            elif hashrate_unit == "h":
                hashrate_value /= 1_000_000

            return round(hashrate_value, 2)
        except (IndexError, ValueError):
            return None
    else:
        return None


def gather_data():
    output = run_command(GENERAL_INFO)
    hashrate_mh = extract_hashrate(output) if output else None
    server_name = capture_hostname()
    gpus, power_w = capture_gpu_info()

    hashrate_mh = int(hashrate_mh)
    power_w = int(power_w)

    data = {
        "server_name": server_name,
        "hashrate_mh": hashrate_mh,
        "gpus": gpus,
        "power_w": power_w
    }

    return data


def send_data():
    data = gather_data()
    try:
        response = requests.post(API_URL, json=data)
        print(f"Data sent: {data}. Server responded with status code {response.status_code}")
    except Exception as e:
        print(f"Error sending data to server: {e}")


if __name__ == "__main__":
    send_data()
