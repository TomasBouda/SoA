"""A Real-ESRGAN upscaler with no dependency on basicsr.

The RRDBNet architecture is written out here directly, because the basicsr
package often fights with newer versions of PyTorch and numpy. The weights are
the official RealESRGAN_x2plus.pth.

The model does not handle the alpha channel - only RGB goes through it and the
transparency is enlarged with Lanczos and put back. That way the vegetation and
effect textures do not lose their mask.
"""
import os

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image

MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'models')

# Two models for two different jobs:
#   photo - RealESRGAN_x2plus, trained on photographs. Good for the game
#           textures (terrain, buildings, vehicles).
#   anime - RealESRGAN_x4plus_anime_6B, trained on drawn content. On small
#           stylised images such as the GUI portraits (every face is only about
#           32x32 px) the photographic model invents detail and deforms the
#           features. This one keeps the shapes.
MODELS = {
    'photo': ('RealESRGAN_x2plus.pth', 2, 23,
              'https://github.com/xinntao/Real-ESRGAN/releases/download/'
              'v0.2.1/RealESRGAN_x2plus.pth'),
    'anime': ('RealESRGAN_x4plus_anime_6B.pth', 4, 6,
              'https://github.com/xinntao/Real-ESRGAN/releases/download/'
              'v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth'),
}


class ResidualDenseBlock(nn.Module):
    def __init__(self, nf=64, gc=32):
        super().__init__()
        self.conv1 = nn.Conv2d(nf, gc, 3, 1, 1)
        self.conv2 = nn.Conv2d(nf + gc, gc, 3, 1, 1)
        self.conv3 = nn.Conv2d(nf + 2 * gc, gc, 3, 1, 1)
        self.conv4 = nn.Conv2d(nf + 3 * gc, gc, 3, 1, 1)
        self.conv5 = nn.Conv2d(nf + 4 * gc, nf, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(0.2, inplace=True)

    def forward(self, x):
        x1 = self.lrelu(self.conv1(x))
        x2 = self.lrelu(self.conv2(torch.cat((x, x1), 1)))
        x3 = self.lrelu(self.conv3(torch.cat((x, x1, x2), 1)))
        x4 = self.lrelu(self.conv4(torch.cat((x, x1, x2, x3), 1)))
        x5 = self.conv5(torch.cat((x, x1, x2, x3, x4), 1))
        return x5 * 0.2 + x


class RRDB(nn.Module):
    def __init__(self, nf, gc=32):
        super().__init__()
        self.rdb1 = ResidualDenseBlock(nf, gc)
        self.rdb2 = ResidualDenseBlock(nf, gc)
        self.rdb3 = ResidualDenseBlock(nf, gc)

    def forward(self, x):
        return self.rdb3(self.rdb2(self.rdb1(x))) * 0.2 + x


class RRDBNet(nn.Module):
    """Watch out for scale=2: the network shrinks the input to half with
    pixel_unshuffle and then doubles it twice, which yields the final factor
    of two."""

    def __init__(self, in_ch=3, out_ch=3, scale=2, nf=64, nb=23, gc=32):
        super().__init__()
        self.scale = scale
        if scale == 2:
            in_ch *= 4
        elif scale == 1:
            in_ch *= 16
        self.conv_first = nn.Conv2d(in_ch, nf, 3, 1, 1)
        self.body = nn.Sequential(*[RRDB(nf, gc) for _ in range(nb)])
        self.conv_body = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_up1 = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_up2 = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_hr = nn.Conv2d(nf, nf, 3, 1, 1)
        self.conv_last = nn.Conv2d(nf, out_ch, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(0.2, inplace=True)

    def forward(self, x):
        if self.scale == 2:
            feat = F.pixel_unshuffle(x, downscale_factor=2)
        elif self.scale == 1:
            feat = F.pixel_unshuffle(x, downscale_factor=4)
        else:
            feat = x
        feat = self.conv_first(feat)
        feat = feat + self.conv_body(self.body(feat))
        feat = self.lrelu(self.conv_up1(F.interpolate(feat, scale_factor=2, mode='nearest')))
        feat = self.lrelu(self.conv_up2(F.interpolate(feat, scale_factor=2, mode='nearest')))
        return self.conv_last(self.lrelu(self.conv_hr(feat)))


_cache = {}
_device = None


def load(model='photo', device=None):
    """Load and cache the network. Returns (network, device, native factor)."""
    global _device
    if model in _cache:
        return _cache[model], _device, MODELS[model][1]
    if model not in MODELS:
        raise ValueError('unknown model %r, available: %s' % (model, list(MODELS)))
    fname, native, blocks, url = MODELS[model]
    path = os.path.join(MODELS_DIR, fname)
    if not os.path.exists(path):
        raise FileNotFoundError('the model %s is missing, download it from %s' % (path, url))
    _device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
    sd = torch.load(path, map_location='cpu', weights_only=True)
    sd = sd.get('params_ema', sd.get('params', sd))
    net = RRDBNet(scale=native, nb=blocks)
    net.load_state_dict(sd, strict=True)
    net.eval().to(_device)
    _cache[model] = net
    return net, _device, native


@torch.no_grad()
def upscale_rgb(arr, model='photo'):
    """arr: HxWx3 uint8 -> enlarged by the native factor of the model"""
    net, dev, _ = load(model)
    t = torch.from_numpy(arr).float().div(255).permute(2, 0, 1).unsqueeze(0).to(dev)
    out = net(t).clamp(0, 1).squeeze(0).permute(1, 2, 0).cpu().numpy()
    return (out * 255).round().astype(np.uint8)


def upscale_image(src, dest, scale=2, model='photo'):
    im = Image.open(src)
    if im.mode == 'P':
        im = im.convert('RGBA' if 'transparency' in im.info else 'RGB')
    elif im.mode not in ('RGB', 'RGBA', 'L', 'LA'):
        im = im.convert('RGBA')

    alpha = None
    if im.mode in ('RGBA', 'LA'):
        alpha = im.getchannel('A')
        im = im.convert('RGB')
    elif im.mode == 'L':
        im = im.convert('RGB')

    out = Image.fromarray(upscale_rgb(np.array(im), model))
    want = (im.width * scale, im.height * scale)
    if out.size != want:                 # the model has a different native factor
        out = out.resize(want, Image.LANCZOS)

    if alpha is not None:
        a = alpha.resize(out.size, Image.LANCZOS)
        out = out.convert('RGBA')
        out.putalpha(a)

    os.makedirs(os.path.dirname(dest), exist_ok=True)
    out.save(dest)
