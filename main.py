import numpy as np

from ring_buffer import RingBuffer, LivePlotter, SignalGenerator



class SignalFunctions:
    
    class MySin:
        def __init__(self, frequency = 1, offset = 0):
            self.offset = offset
            self.frequency = frequency
         
            
        def __call__(self, t):
            #print(self.data[self.current_read_out[0]: self.current_read_out[1]])
            #self.current_read_out = [x +  self.interval_steps for x in self.current_read_out]
            return np.sin(2 * np.pi * t * self.frequency) + self.offset

            
 
        
    class DeltaUpDown:
       def __init__(self, amplitude=1.0, frequency=1.0, offset=0, edge_time = 0.05):
            self.amplitude = amplitude
            self.frequency = frequency
            self.offset = offset
            self.edge_time = edge_time
            
            
       def __call__(self, t):
            data = []
            T = 1/self.frequency
            edge0 = 0.1*T
            edge1 = (0.1+self.edge_time)*T
            
            edge2 = 0.6*T
            edge3 = (0.6+self.edge_time)*T
            
            
            t_mod = [t_val%T for t_val in t]
            for x in t_mod[:int(len(t_mod)/2)]:
                if x <= edge0:
                    data.append(0.0 + self.offset) 
                elif x >= edge0 and x <= edge1:
                   # Scale/shift x into [0, 1]
                   t = (x - edge0) / (edge1 - edge0)
                   data.append( self.amplitude* ( t**2 * (3 - 2*t)) + self.offset)
                elif x >= edge1 and x <= edge2:
                    data.append(self.amplitude * 1.0 + self.offset)
                elif x >= edge2 and x <= edge3:
                   t = (x - edge2) / (edge3 - edge2)
                   data.append(self.amplitude* (1-(t**2 * (3 - 2*t))) + self.offset)
                else: 
                    data.append(self.amplitude * 0. + self.offset)
            return data
                    
              
                    
              
# Example usage:
if __name__ == "__main__":

    # Example ring buffer as in redpitaya
    rb = RingBuffer(size=16000)
   
    # function needs to be a callable object, see examples above 
    func = SignalFunctions.DeltaUpDown(offset= 0, amplitude = 2, frequency=0.2,edge_time = 0.2)

    gen = SignalGenerator(rb,  sample_rate=16000.0, func=func)
    gen.start(duration=0.01, interval=0.01) 

     
    try:
        plotter = LivePlotter(rb, interval=10)
        plotter.start()
    except KeyboardInterrupt:
        print('exiting')
    finally:
        gen.stop()
