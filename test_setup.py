#!/usr/bin/env python3
"""
Test script to verify that all dependencies are properly installed
and the voice-to-MIDI application can run.
"""

import sys
import importlib

def test_imports():
    """Test that all required modules can be imported"""
    required_modules = [
        'pyaudio',
        'numpy', 
        'librosa',
        'mido',
        'scipy',
        'tkinter'
    ]
    
    print("Testing imports...")
    failed_imports = []
    
    for module in required_modules:
        try:
            importlib.import_module(module)
            print(f"✓ {module}")
        except ImportError as e:
            print(f"✗ {module}: {e}")
            failed_imports.append(module)
    
    if failed_imports:
        print(f"\nFailed to import: {', '.join(failed_imports)}")
        print("Please install missing dependencies:")
        print("  uv sync")
        print("  or")
        print("  pip install -r requirements.txt")
        return False
    else:
        print("\n✓ All imports successful!")
        return True

def test_audio():
    """Test audio system"""
    try:
        import pyaudio
        audio = pyaudio.PyAudio()
        
        # Get input devices
        input_devices = []
        for i in range(audio.get_device_count()):
            device_info = audio.get_device_info_by_index(i)
            if device_info['maxInputChannels'] > 0:
                input_devices.append(device_info['name'])
        
        print(f"\nAudio input devices found: {len(input_devices)}")
        for device in input_devices:
            print(f"  - {device}")
            
        audio.terminate()
        return True
    except Exception as e:
        print(f"✗ Audio test failed: {e}")
        return False

def test_midi():
    """Test MIDI system"""
    try:
        import mido
        ports = mido.get_output_names()
        
        print(f"\nMIDI output ports found: {len(ports)}")
        for port in ports:
            print(f"  - {port}")
            
        if not ports:
            print("  No MIDI ports available. You may need to install a virtual MIDI driver.")
            
        return True
    except Exception as e:
        print(f"✗ MIDI test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Voice to MIDI - Setup Test")
    print("=" * 30)
    
    # Test imports
    imports_ok = test_imports()
    
    if imports_ok:
        # Test audio
        audio_ok = test_audio()
        
        # Test MIDI
        midi_ok = test_midi()
        
        print("\n" + "=" * 30)
        if imports_ok and audio_ok:
            print("✓ Setup looks good! You can run the application with:")
            print("  python voice_to_midi.py")
        else:
            print("✗ Some tests failed. Please check the errors above.")
    else:
        print("\n✗ Import tests failed. Please install dependencies first.")

if __name__ == "__main__":
    main() 