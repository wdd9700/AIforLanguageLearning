import wave
import math
import struct

def generate_sine_wave(filename, duration=5, frequency=440, sample_rate=16000):
    """Generates a sine wave WAV file."""
    n_samples = int(sample_rate * duration)
    
    with wave.open(filename, 'w') as wav_file:
        # Set parameters: 1 channel, 2 bytes per sample, sample rate, number of samples, no compression
        wav_file.setparams((1, 2, sample_rate, n_samples, 'NONE', 'not compressed'))
        
        for i in range(n_samples):
            # Generate sine wave value
            value = int(32767.0 * math.sin(2.0 * math.pi * frequency * i / sample_rate))
            # Pack value as 16-bit little-endian integer
            data = struct.pack('<h', value)
            wav_file.writeframes(data)
            
    print(f"Generated {filename} ({duration}s, {frequency}Hz)")

if __name__ == "__main__":
    import sys
    import os
    
    # Default output path
    output_path = "test_audio.wav"
    if len(sys.argv) > 1:
        output_path = sys.argv[1]
        
    generate_sine_wave(output_path)
