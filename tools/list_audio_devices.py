import sounddevice as sd

def main():
    print("=== LANY Audio Device Listing Tool ===\n")
    devices = sd.query_devices()
    hostapis = sd.query_hostapis()

    print("Available Input Devices (Microphones / Virtual Outputs):")
    print("-" * 65)
    for i, dev in enumerate(devices):
        if dev['max_input_channels'] > 0:
            print(f"[{i}] {dev['name']} (Channels: {dev['max_input_channels']}, Host API: {hostapis[dev['hostapi']]['name']})")

    print("\nAvailable Output Devices (Speakers / Virtual Inputs):")
    print("-" * 65)
    for i, dev in enumerate(devices):
        if dev['max_output_channels'] > 0:
            print(f"[{i}] {dev['name']} (Channels: {dev['max_output_channels']}, Host API: {hostapis[dev['hostapi']]['name']})")

    print("\nDefault Devices:")
    try:
        default_in = sd.query_devices(kind='input')
        default_out = sd.query_devices(kind='output')
        print(f"Default Input : {default_in['name']}")
        print(f"Default Output: {default_out['name']}")
    except Exception as e:
        print(f"Error querying default devices: {e}")

    print("\nPetunjuk:")
    print("Isikan nama device di file `.env` pada AUDIO_INPUT_DEVICE dan AUDIO_OUTPUT_DEVICE.")

if __name__ == '__main__':
    main()
