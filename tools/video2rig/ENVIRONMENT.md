These files record the separate local test environment. Upstream remains unmodified at commit 55d51b3b9685125a8ea27841d6af9523f6352aa1; its Blender 4.x compatibility is already part of that commit.

Dot-source Enter-Video2Rig.ps1 with -ExperimentRoot pointing to the prepared workspace/experiments/video2rig directory. The workspace must provide tools/blender-4.5.15-windows-x64/blender.exe and video-mocap/tools/ffmpeg.exe, or adjust those two environment paths.

The package lock contains no private filesystem dependencies or credentials. CUDA PyTorch wheels require the official cu128 index; install torch 2.10.0+cu128 and torchvision 0.25.0+cu128 from https://download.pytorch.org/whl/cu128 before applying the remaining locked packages. No existing environment needs to be modified.
