"""
Audio processing module for preprocessing audio data.

This module handles audio preprocessing including windowing, filtering,
and silence detection before pitch analysis.
"""

import logging
from typing import Optional, Tuple
import numpy as np
from scipy import signal

from ..core.exceptions import AudioError


logger = logging.getLogger(__name__)


class AudioProcessor:
    """
    Processes audio data for pitch detection.
    
    This class handles audio preprocessing including windowing, filtering,
    and silence detection to prepare audio data for pitch analysis.
    
    Example:
        >>> processor = AudioProcessor()
        >>> processor.configure(sample_rate=44100, silence_threshold=0.01)
        >>> processed_data = processor.process(audio_data)
        >>> is_silent = processor.is_silent(processed_data)
    """
    
    def __init__(self):
        """Initialize the audio processor."""
        self.sample_rate = 44100
        self.silence_threshold = 0.01
        self.window_type = 'hann'
        self.apply_high_pass = True
        self.high_pass_freq = 50.0
        
        # Filter coefficients (computed when configured)
        self._filter_b = None
        self._filter_a = None
        
        # State for filtering
        self._filter_state = None
        
        logger.debug("Audio processor initialized")
    
    def configure(self, sample_rate: int = 44100, silence_threshold: float = 0.01,
                  window_type: str = 'hann', apply_high_pass: bool = True,
                  high_pass_freq: float = 50.0) -> None:
        """
        Configure audio processing parameters.
        
        Args:
            sample_rate: Sample rate in Hz
            silence_threshold: Threshold for silence detection
            window_type: Window function type ('hann', 'hamming', 'blackman')
            apply_high_pass: Whether to apply high-pass filtering
            high_pass_freq: High-pass filter cutoff frequency
            
        Raises:
            AudioError: If configuration is invalid
        """
        if sample_rate <= 0:
            raise AudioError("Sample rate must be positive")
        if silence_threshold < 0:
            raise AudioError("Silence threshold must be non-negative")
        if high_pass_freq <= 0 or high_pass_freq >= sample_rate / 2:
            raise AudioError("High-pass frequency must be between 0 and Nyquist frequency")
        
        self.sample_rate = sample_rate
        self.silence_threshold = silence_threshold
        self.window_type = window_type
        self.apply_high_pass = apply_high_pass
        self.high_pass_freq = high_pass_freq
        
        # Design high-pass filter if needed
        if self.apply_high_pass:
            self._design_high_pass_filter()
        
        logger.info(f"Audio processor configured: {sample_rate}Hz, threshold={silence_threshold}")
    
    def process(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Process audio data.
        
        Args:
            audio_data: Input audio data
            
        Returns:
            Processed audio data
            
        Raises:
            AudioError: If processing fails
        """
        if audio_data is None or len(audio_data) == 0:
            raise AudioError("Invalid audio data")
        
        try:
            processed_data = audio_data.copy()
            
            # Apply high-pass filter if configured
            if self.apply_high_pass and self._filter_b is not None:
                processed_data = self._apply_high_pass_filter(processed_data)
            
            # Apply windowing
            processed_data = self._apply_window(processed_data)
            
            return processed_data
            
        except Exception as e:
            raise AudioError(f"Audio processing failed: {e}")
    
    def is_silent(self, audio_data: np.ndarray) -> bool:
        """
        Check if audio data is silent.
        
        Args:
            audio_data: Audio data to check
            
        Returns:
            True if audio is silent
        """
        if audio_data is None or len(audio_data) == 0:
            return True
        
        # Calculate RMS level
        rms = np.sqrt(np.mean(audio_data ** 2))
        return rms < self.silence_threshold
    
    def get_audio_level(self, audio_data: np.ndarray) -> float:
        """
        Get the audio level (RMS).
        
        Args:
            audio_data: Audio data
            
        Returns:
            RMS level of the audio
        """
        if audio_data is None or len(audio_data) == 0:
            return 0.0
        
        return np.sqrt(np.mean(audio_data ** 2))
    
    def get_peak_level(self, audio_data: np.ndarray) -> float:
        """
        Get the peak audio level.
        
        Args:
            audio_data: Audio data
            
        Returns:
            Peak level of the audio
        """
        if audio_data is None or len(audio_data) == 0:
            return 0.0
        
        return np.max(np.abs(audio_data))
    
    def normalize_audio(self, audio_data: np.ndarray, target_level: float = 0.5) -> np.ndarray:
        """
        Normalize audio to target level.
        
        Args:
            audio_data: Audio data to normalize
            target_level: Target RMS level
            
        Returns:
            Normalized audio data
        """
        if audio_data is None or len(audio_data) == 0:
            return audio_data
        
        current_level = self.get_audio_level(audio_data)
        if current_level == 0:
            return audio_data
        
        gain = target_level / current_level
        return audio_data * gain
    
    def _design_high_pass_filter(self) -> None:
        """Design high-pass filter coefficients."""
        try:
            # Design a 2nd order Butterworth high-pass filter
            nyquist = self.sample_rate / 2
            normalized_freq = self.high_pass_freq / nyquist
            
            self._filter_b, self._filter_a = signal.butter(
                2, normalized_freq, btype='high', analog=False
            )
            
            # Initialize filter state
            self._filter_state = signal.lfilter_zi(self._filter_b, self._filter_a)
            
            logger.debug(f"High-pass filter designed: {self.high_pass_freq}Hz")
            
        except Exception as e:
            logger.error(f"Failed to design high-pass filter: {e}")
            self._filter_b = None
            self._filter_a = None
    
    def _apply_high_pass_filter(self, audio_data: np.ndarray) -> np.ndarray:
        """Apply high-pass filter to audio data."""
        if self._filter_b is None or self._filter_a is None:
            return audio_data
        
        try:
            # Apply filter with state to maintain continuity
            filtered_data, self._filter_state = signal.lfilter(
                self._filter_b, self._filter_a, audio_data, zi=self._filter_state
            )
            
            return filtered_data
            
        except Exception as e:
            logger.error(f"High-pass filtering failed: {e}")
            return audio_data
    
    def _apply_window(self, audio_data: np.ndarray) -> np.ndarray:
        """Apply windowing to audio data."""
        try:
            if self.window_type == 'hann':
                window = np.hanning(len(audio_data))
            elif self.window_type == 'hamming':
                window = np.hamming(len(audio_data))
            elif self.window_type == 'blackman':
                window = np.blackman(len(audio_data))
            else:
                # No windowing
                return audio_data
            
            return audio_data * window
            
        except Exception as e:
            logger.error(f"Windowing failed: {e}")
            return audio_data
    
    def get_frequency_spectrum(self, audio_data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Get frequency spectrum of audio data.
        
        Args:
            audio_data: Audio data
            
        Returns:
            Tuple of (frequencies, magnitudes)
        """
        if audio_data is None or len(audio_data) == 0:
            return np.array([]), np.array([])
        
        try:
            # Compute FFT
            fft = np.fft.rfft(audio_data)
            magnitudes = np.abs(fft)
            frequencies = np.fft.rfftfreq(len(audio_data), 1.0 / self.sample_rate)
            
            return frequencies, magnitudes
            
        except Exception as e:
            logger.error(f"FFT computation failed: {e}")
            return np.array([]), np.array([])
    
    def detect_clipping(self, audio_data: np.ndarray, threshold: float = 0.95) -> bool:
        """
        Detect audio clipping.
        
        Args:
            audio_data: Audio data to check
            threshold: Clipping threshold (0-1)
            
        Returns:
            True if clipping is detected
        """
        if audio_data is None or len(audio_data) == 0:
            return False
        
        peak_level = self.get_peak_level(audio_data)
        return peak_level > threshold
    
    def get_processing_info(self) -> dict:
        """
        Get information about current processing settings.
        
        Returns:
            Dictionary with processing information
        """
        return {
            'sample_rate': self.sample_rate,
            'silence_threshold': self.silence_threshold,
            'window_type': self.window_type,
            'apply_high_pass': self.apply_high_pass,
            'high_pass_freq': self.high_pass_freq,
            'filter_enabled': self._filter_b is not None,
        }