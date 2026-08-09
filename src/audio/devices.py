import logging
import sounddevice as sd

logger = logging.getLogger("LANY.AudioDevices")

def find_device_index(device_name_query: str, is_input: bool = True) -> int | None:
    if not device_name_query:
        return None

    devices = sd.query_devices()
    device_name_query = device_name_query.lower()

    for idx, dev in enumerate(devices):
        dev_name = dev['name'].lower()
        has_channels = dev['max_input_channels'] > 0 if is_input else dev['max_output_channels'] > 0
        if has_channels and device_name_query in dev_name:
            logger.info(f"Matched device '{dev['name']}' at index {idx} (is_input={is_input})")
            return idx

    logger.warning(f"Device matching '{device_name_query}' not found. Using default {'input' if is_input else 'output'} device.")
    return None

def get_audio_config():
    return {
        "sample_rate": 48000,
        "channels": 1,
        "dtype": "int16"
    }
