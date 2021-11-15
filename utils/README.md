# Example
Read in a .WAV file (`music.wav`) and send a portion of one channel to the ARB.

## Create a `.raf` file from the audio
```python
import numpy as np
from scipy.io import wavfile
from raf_tools import *


samplerate, data = wavfile.read('music.wav')
samples = data[0:samplerate*10, 0]  # grab the first audio channel
peak = 1.05 * np.max(np.abs(samples))
samps = samples/peak
write_raf('music.raf', samples=samples, fs_Hz=samplerate, low_v=-1., high_v=1.)
```
## Send the `.raf` file to the ARB and turn on the output

```bash
python raf_tools.py -f music.raf -c 1 --vpp 2 -r 0 -o 1
```