import numpy as np
import threading
import time
import itertools
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

class RingBuffer:
    def __init__(self, size):
        """Initialize the ring buffer with a fixed size."""
        self.size = size
        self.buffer = np.zeros(size, dtype=float)
        self.write_ptr = 0
        self.lock = threading.Lock()
       

    def write(self, data):
        """Write an array of data into the ring buffer, 
        overwriting older data if necessary."""
        with self.lock:
            n = len(data)
            if n >= self.size:
                # If the data is larger than the buffer, just keep the last part.
                self.buffer[:] = data[-self.size:]
                self.write_ptr = 0
            else:
                end_ptr = (self.write_ptr + n) % self.size
                if end_ptr < self.write_ptr:
                    # Wrap around
                    first_part = self.size - self.write_ptr
                    self.buffer[self.write_ptr:] = data[:first_part]
                    self.buffer[0:end_ptr] = data[first_part:]
                else:
                    # No wrap
                    self.buffer[self.write_ptr:end_ptr] = data
                self.write_ptr = end_ptr

    def read_latest(self, num_samples):
        """Read the most recent `num_samples` data points from the buffer."""
        with self.lock:
            if num_samples > self.size:
                raise ValueError("num_samples larger than buffer size")
            start = (self.write_ptr - num_samples) % self.size
            if start + num_samples <= self.size:
                return self.buffer[start:start+num_samples].copy()
            else:
                # Wrap around read
                end_len = (start + num_samples) - self.size
                return np.concatenate((self.buffer[start:], self.buffer[:end_len]))
            


class LivePlotter:
    """
    Plots the raw 'memory layout' of a ring buffer (x-axis = buffer indices).
    
    This means:
      - x=0 in the plot is index 0 of the buffer array,
      - x=1 in the plot is index 1 of the buffer array,
      ...
      - x=(size-1) in the plot is index (size-1) of the buffer array.
      
    As the ring buffer's write pointer wraps around in memory, you'll see 
    new data appear at the corresponding index in the plot. If the pointer 
    goes from (size-1) to 0, the newest sample will 'jump' from right edge 
    to left edge on the plot.
    
    Args:
        buffer (RingBuffer): 
            A ring buffer instance having 'buffer' (the numpy array of data) 
            and 'write_ptr' (the current write index).
        interval (int): 
            Interval in ms for updating the plot. Defaults to 50.
    """
    def __init__(self, buffer, interval=50):
        self.buffer = buffer
        self.size = buffer.size  # e.g. 16000
        self.interval = interval

        self.fig, self.ax = plt.subplots()
        self.line, = self.ax.plot([], [], lw=2, label='Buffer Data')
        
        # Optional: a marker/line to highlight the write pointer
        self.ptr_marker, = self.ax.plot([], [], 'ro', label='Write Pointer')

        self.ax.set_xlim(0, self.size)
        # Adjust the vertical range to your data
        self.ax.set_ylim(-0.2, 2.2)
        
        self.ax.set_xlabel('Buffer Index')
        self.ax.set_ylabel('Amplitude')
        self.ax.set_title('Raw Ring Buffer Memory Layout')
        self.ax.legend()

    def init_animation(self):
        """Initialize the animation with no data."""
        self.line.set_data([], [])
        self.ptr_marker.set_data([], [])
        return self.line, self.ptr_marker

    def update_animation(self, frame):
        """
        Update the plot with the ring buffer's raw memory layout.
        
        The newest data is wherever the ring buffer's write_ptr is pointing.
        If write_ptr wraps from size-1 back to 0, you'll see the data 
        'jump' from the rightmost index to x=0.
        """
        # 1) Just read the entire buffer array as is (no reordering)
        data = self.buffer.buffer  # shape = (size,)
        
        # 2) x-values = direct indices [0..size-1]
        x_vals = np.arange(self.size)
        self.line.set_data(x_vals, data)
        
        # (Optional) Show the pointer position in red
        ptr_x = self.buffer.write_ptr
        ptr_y = data[ptr_x]  # the current sample at that pointer
        self.ptr_marker.set_data([ptr_x], [ptr_y])

        return self.line, self.ptr_marker

    def start(self):
        """Start the animation."""
        self.ani = FuncAnimation(
            self.fig,
            self.update_animation,
            frames=itertools.count(),
            init_func=self.init_animation,
            interval=self.interval,
            blit=True
        )
        plt.show()


class SignalGenerator:
    def __init__(self, buffer, sample_rate=1000.0, func=None):
        """A class that continuously generates samples using a given function and writes it to a ring buffer.
        
        Parameters:
        -----------
        buffer : RingBuffer
            The ring buffer to write samples into.
        amplitude : float
            Amplitude scaling factor used by the default sine function. Ignored if func doesn't use amplitude.
        frequency : float
            Frequency parameter for the default sine function. Ignored if func doesn't use frequency.
        sample_rate : float
            Samples per second.
        func : callable or None
            The function used to generate samples. Must accept an array of time values (t) and return an array of samples.
            If None, defaults to a sine function: amplitude * sin(2*pi*frequency*t).
        """
        self.buffer = buffer
        self.sample_rate = sample_rate
        self.running = False
        self.time_offset = 0.0  # Tracks the continuous time offset

        if func is None:
            # Default to a sine function
            self.func = lambda t: 1.0 * np.sin(2 * np.pi * 1.0 * t)
        else:
            self.func = func

    def _generate_samples(self, duration=0.01):
        """Generate samples from the user-defined function for the given duration."""
        t = np.arange(0, duration, 1/self.sample_rate) + self.time_offset
        samples = self.func(t)
        # Update time offset for continuity
        self.time_offset += duration
        return samples

    def start(self, duration=0.01, interval=0.01):
        """Continuously generate and write data to the buffer.
        
        duration: length of each chunk generated per iteration
        interval: time between writes (simulates continuous feed)
        """
        self.running = True

        def run():
            while self.running:
                samples = self._generate_samples(duration)
                self.buffer.write(samples)
                time.sleep(interval)

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if hasattr(self, 'thread'):
            self.thread.join()

