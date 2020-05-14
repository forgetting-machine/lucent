import torch
import torch.nn.functional as F
import numpy as np
import kornia
from kornia.geometry.transform import translate


device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")


def jitter(d):
    assert d > 1, "Jitter parameter d must be more than 1, currently {}".format(d)
    def inner(t_image):
        dx = np.random.choice(d)
        dy = np.random.choice(d)
        return translate(t_image, torch.tensor([[dx, dy]]).float().to(device))
    return inner

def pad(w, mode="reflect", constant_value=0.5):
    if mode != "constant":
        constant_value = 0
    def inner(t_image):
        return F.pad(
            t_image,
            [w]*4,
            mode=mode,
            value=constant_value,
        )
    return inner

def random_scale(scales):
    def inner(t_image):
        scale = np.random.choice(scales)
        shp = t_image.shape[2:]
        scale_shape = [_roundup(scale * d) for d in shp]
        pad_x = max(0, _roundup((shp[1] - scale_shape[1])/2))
        pad_y = max(0, _roundup((shp[0] - scale_shape[0])/2))
        upsample = torch.nn.Upsample(size=scale_shape, mode='bilinear', align_corners=True)
        return F.pad(upsample(t_image), [pad_y, pad_x]*2)
    return inner

def random_rotate(angles, units="degrees"):
    def inner(t_image):
        # kornia takes degrees
        alpha = _rads2angle(np.random.choice(angles), units)
        angle = torch.ones(1) * alpha
        scale = torch.ones(1)
        center = torch.ones(1, 2)
        center[..., 0] = (t_image.shape[3] - 1) / 2
        center[..., 1] = (t_image.shape[2] - 1) / 2
        print(center)
        M = kornia.get_rotation_matrix2d(center, angle, scale).to(device)
        _, _, h, w = t_image.shape
        rotated_image = kornia.warp_affine(t_image.float(), M, dsize=(h, w))
        return rotated_image
    return inner

def compose(transforms):
    def inner(x):
        for transform in transforms:
            x = transform(x)
        return x
    return inner

def _roundup(value):
    return np.ceil(value).astype(int)

def _rads2angle(angle, units):
    if units.lower() == "degrees":
        angle = angle
    elif units.lower() in ["radians", "rads", "rad"]:
        angle = angle * 180. / np.pi
    return angle
