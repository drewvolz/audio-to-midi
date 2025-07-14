"""
Audio capture module for real-time microphone input.

This module handles audio capture from microphone input using PyAudio
with configurable parameters and error handling.
"""

import logging
import threading
import queue
from typing import Optional, Callable
import numpy as np
import pyaudio

from ..core.exceptions import AudioError


logger = logging.getLogger(__name__)


class AudioCapture:
    """
    Handles real-time audio capture from microphone input.
    
    This class manages PyAudio streams for continuous audio capture with
    configurable sample rates, chunk sizes, and input devices.
    
    Example:
        >>> capture = AudioCapture()
        >>> capture.configure(sample_rate=44100, chunk_size=1024)
        >>> capture.start()
        >>> while True:
        ...     audio_data = capture.get_audio_data()
        ...     if audio_data is not None:
        ...         # Process audio data
        ...         pass
        >>> capture.stop()
    """
    
    def __init__(self):
        """Initialize the audio capture."""
        self._audio = None
        self._stream = None
        self._is_capturing = False
        self._capture_thread = None
        self._audio_queue = queue.Queue()
        
        # Configuration
        self.sample_rate = 44100
        self.chunk_size = 1024
        self.channels = 1
        self.device_index = None
        self.format = pyaudio.paFloat32
        
        # Callbacks
        self.on_audio_data: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        self._initialize_audio()
    
    def _initialize_audio(self) -> None:
        """Initialize PyAudio."""
        try:
            self._audio = pyaudio.PyAudio()
            logger.debug("PyAudio initialized for audio capture")
        except Exception as e:
            raise AudioError(f"Failed to initialize PyAudio: {e}")
    
    def configure(self, sample_rate: int = 44100, chunk_size: int = 1024,
                  channels: int = 1, device_index: Optional[int] = None) -> None:
        """
        Configure audio capture parameters.
        
        Args:
            sample_rate: Sample rate in Hz
            chunk_size: Audio chunk size in samples
            channels: Number of audio channels
            device_index: Input device index (None for default)
            
        Raises:
            AudioError: If configuration is invalid
        """
        if self._is_capturing:
            raise AudioError("Cannot configure while capturing")
        
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.channels = channels
        self.device_index = device_index
        
        # Validate configuration
        if sample_rate <= 0:
            raise AudioError("Sample rate must be positive")
        if chunk_size <= 0:
            raise AudioError("Chunk size must be positive")
        if channels <= 0:
            raise AudioError("Channels must be positive")
        
        logger.info(f"Audio capture configured: {sample_rate}Hz, {chunk_size} samples, {channels} channels")
    
    def start(self) -> None:
        """
        Start audio capture.
        
        Raises:
            AudioError: If capture cannot be started
        """
        if self._is_capturing:
            logger.warning("Audio capture already started")
            return
        
        try:
            # Open audio stream
            self._stream = self._audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._stream_callback,
                start=False
            )
            
            # Start the stream
            self._stream.start_stream()
            self._is_capturing = True
            
            logger.info("Audio capture started")
            
        except Exception as e:
            raise AudioError(f"Failed to start audio capture: {e}")
    
    def stop(self) -> None:
        """Stop audio capture."""
        if not self._is_capturing:
            logger.warning("Audio capture not started")
            return
        
        self._is_capturing = False
        
        # Stop and close stream
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
                self._stream = None
                logger.debug("Audio stream stopped and closed")
            except Exception as e:
                logger.error(f"Error stopping audio stream: {e}")
        
        # Clear the queue
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break
        
        logger.info("Audio capture stopped")
    
    def get_audio_data(self, timeout: Optional[float] = None) -> Optional[np.ndarray]:
        """
        Get the next audio data chunk.
        
        Args:
            timeout: Timeout in seconds (None for blocking)
            
        Returns:
            Audio data as numpy array, or None if no data available
        """
        try:
            if timeout is None:
                audio_data = self._audio_queue.get()
            else:
                audio_data = self._audio_queue.get(timeout=timeout)
            
            return audio_data
            
        except queue.Empty:
            return None
        except Exception as e:
            logger.error(f"Error getting audio data: {e}")
            if self.on_error:
                self.on_error(AudioError(f"Error getting audio data: {e}"))
            return None
    
    def _stream_callback(self, in_data, frame_count, time_info, status):
        """PyAudio stream callback."""
        try:
            # Convert audio data to numpy array
            audio_data = np.frombuffer(in_data, dtype=np.float32)
            
            # Put in queue for processing
            if not self._audio_queue.full():
                self._audio_queue.put(audio_data)
            
            # Call callback if provided
            if self.on_audio_data:
                self.on_audio_data(audio_data)
            
            return (None, pyaudio.paContinue)
            
        except Exception as e:
            logger.error(f"Stream callback error: {e}")
            if self.on_error:
                self.on_error(AudioError(f"Stream callback error: {e}"))
            return (None, pyaudio.paAbort)
    
    def get_stream_info(self) -> dict:
        """
        Get information about the current audio stream.
        
        Returns:
            Dictionary with stream information
        """
        if not self._stream:
            return {}
        
        try:
            return {
                'sample_rate': self.sample_rate,
                'chunk_size': self.chunk_size,
                'channels': self.channels,
                'device_index': self.device_index,
                'is_active': self._stream.is_active(),
                'is_stopped': self._stream.is_stopped(),
                'input_latency': self._stream.get_input_latency(),
                'cpu_load': self._stream.get_cpu_load(),
            }
        except Exception as e:
            logger.error(f"Error getting stream info: {e}")
            return {}
    
    def close(self) -> None:
        """Clean up resources."""
        self.stop()
        
        if self._audio:
            self._audio.terminate()
            self._audio = None
            logger.debug("PyAudio terminated")
    
    @property
    def is_capturing(self) -> bool:
        """Check if currently capturing audio."""
        return self._is_capturing
    
    @property
    def queue_size(self) -> int:
        """Get current audio queue size."""
        return self._audio_queue.qsize()
    
    def __del__(self):
        """Destructor to clean up resources."""
        self.close()