#!/usr/bin/env python3
"""
Test script to verify the modular refactoring works correctly.

This script tests the basic functionality of each module to ensure
the refactoring was successful.
"""

import sys
import os

# Add the voice_to_midi package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'voice_to_midi'))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing module imports...")
    
    try:
        # Test core imports
        from voice_to_midi import VoiceToMidiApp
        from voice_to_midi.config import ConfigManager, Settings
        print("✓ Core modules imported successfully")
        
        # Test device management
        from voice_to_midi.devices import AudioDeviceManager, MidiDeviceManager
        print("✓ Device management modules imported successfully")
        
        # Test audio processing
        from voice_to_midi.audio import AudioCapture, AudioProcessor
        print("✓ Audio processing modules imported successfully")
        
        # Test pitch detection
        from voice_to_midi.pitch import PitchDetector, PitchAnalyzer
        print("✓ Pitch detection modules imported successfully")
        
        # Test MIDI handling
        from voice_to_midi.midi import MidiOutput, MidiMessageHandler
        print("✓ MIDI handling modules imported successfully")
        
        # Test CLI
        from voice_to_midi.cli import cli
        print("✓ CLI modules imported successfully")
        
        # Test utilities
        from voice_to_midi.utils import setup_logging, frequency_to_midi_note
        print("✓ Utility modules imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def test_configuration():
    """Test configuration management."""
    print("\nTesting configuration management...")
    
    try:
        from voice_to_midi.config import ConfigManager, Settings
        
        # Test settings creation
        settings = Settings()
        settings.validate()
        print("✓ Settings validation passed")
        
        # Test configuration manager
        config_manager = ConfigManager("/tmp/test_config.json")
        config_manager.reset_to_defaults()
        
        # Test serialization
        settings_dict = settings.to_dict()
        restored_settings = Settings.from_dict(settings_dict)
        print("✓ Settings serialization/deserialization works")
        
        return True
        
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False

def test_device_management():
    """Test device management."""
    print("\nTesting device management...")
    
    try:
        from voice_to_midi.devices import AudioDeviceManager, MidiDeviceManager
        
        # Test audio device manager
        audio_mgr = AudioDeviceManager()
        audio_devices = audio_mgr.list_input_devices()
        print(f"✓ Found {len(audio_devices)} audio input devices")
        
        # Test MIDI device manager
        midi_mgr = MidiDeviceManager()
        midi_ports = midi_mgr.list_output_ports()
        print(f"✓ Found {len(midi_ports)} MIDI output ports")
        
        # Clean up
        audio_mgr.close()
        midi_mgr.close()
        
        return True
        
    except Exception as e:
        print(f"✗ Device management test failed: {e}")
        return False

def test_audio_processing():
    """Test audio processing."""
    print("\nTesting audio processing...")
    
    try:
        from voice_to_midi.audio import AudioProcessor
        import numpy as np
        
        # Test audio processor
        processor = AudioProcessor()
        processor.configure(sample_rate=44100)
        
        # Test with dummy audio data
        dummy_audio = np.random.randn(1024).astype(np.float32) * 0.1
        processed = processor.process(dummy_audio)
        
        print("✓ Audio processing works")
        
        return True
        
    except Exception as e:
        print(f"✗ Audio processing test failed: {e}")
        return False

def test_pitch_detection():
    """Test pitch detection."""
    print("\nTesting pitch detection...")
    
    try:
        from voice_to_midi.pitch import PitchDetector
        import numpy as np
        
        # Test pitch detector
        detector = PitchDetector()
        detector.configure(sample_rate=44100)
        
        # Test with dummy audio data
        dummy_audio = np.random.randn(1024).astype(np.float32) * 0.1
        frequency, confidence = detector.detect_pitch(dummy_audio)
        
        print(f"✓ Pitch detection works (freq: {frequency}, confidence: {confidence})")
        
        return True
        
    except Exception as e:
        print(f"✗ Pitch detection test failed: {e}")
        return False

def test_midi_handling():
    """Test MIDI handling."""
    print("\nTesting MIDI handling...")
    
    try:
        from voice_to_midi.midi import MidiMessageHandler
        
        # Test MIDI message handler
        handler = MidiMessageHandler()
        
        # Test message creation
        note_on = handler.create_note_on(60, 64, 0)
        note_off = handler.create_note_off(60, 0, 0)
        
        # Test message validation
        handler.validate_message(note_on)
        handler.validate_message(note_off)
        
        print("✓ MIDI message handling works")
        
        return True
        
    except Exception as e:
        print(f"✗ MIDI handling test failed: {e}")
        return False

def test_application():
    """Test main application."""
    print("\nTesting main application...")
    
    try:
        from voice_to_midi import VoiceToMidiApp
        
        # Test application creation
        app = VoiceToMidiApp()
        
        # Test configuration loading
        settings = app.load_config()
        print("✓ Application configuration loading works")
        
        return True
        
    except Exception as e:
        print(f"✗ Application test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Voice to MIDI Modular Refactoring Test")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_configuration,
        test_device_management,
        test_audio_processing,
        test_pitch_detection,
        test_midi_handling,
        test_application,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("🎉 All tests passed! The modular refactoring is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())