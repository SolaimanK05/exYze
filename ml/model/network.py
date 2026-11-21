"""Hourglass floor plan network from CubiCasa5K.

Adapted from https://github.com/CubiCasa/CubiCasa5k (hg_furukawa_original.py),
which is licensed CC BY-NC 4.0. Changes: ported to current PyTorch, no
dependency on the pose-estimation init file (we always load full weights),
and the heatmap sigmoid no longer writes into the output tensor in place.

Attribute names are kept as in the original so the published checkpoint
loads without renaming any keys.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

N_HEATMAPS = 21
N_ROOM_CLASSES = 12
N_ICON_CLASSES = 11
N_CLASSES = N_HEATMAPS + N_ROOM_CLASSES + N_ICON_CLASSES


class Residual(nn.Module):
    def __init__(self, n_in, n_out):
        super().__init__()
        self.n_in = n_in
        self.n_out = n_out
        mid = n_out // 2
        self.bn = nn.BatchNorm2d(n_in)
        self.relu = nn.ReLU(inplace=True)
        self.conv1 = nn.Conv2d(n_in, mid, kernel_size=1)
        self.bn1 = nn.BatchNorm2d(mid)
        self.conv2 = nn.Conv2d(mid, mid, kernel_size=3, stride=1, padding=1)
        self.bn2 = nn.BatchNorm2d(mid)
        self.conv3 = nn.Conv2d(mid, n_out, kernel_size=1)
        if n_in != n_out:
            self.conv4 = nn.Conv2d(n_in, n_out, kernel_size=1)

    def forward(self, x):
        out = self.relu(self.bn(x))
        out = self.relu(self.bn1(self.conv1(out)))
        out = self.relu(self.bn2(self.conv2(out)))
        out = self.conv3(out)
        skip = self.conv4(x) if self.n_in != self.n_out else x
        return out + skip


def _upsample_add(top, lateral):
    # odd input sizes make the upsampled map one pixel off the lateral one
    if top.shape != lateral.shape:
        top = F.interpolate(
            top, size=lateral.shape[2:], mode="bilinear", align_corners=False
        )
    return top + lateral


class HourglassFloorPlan(nn.Module):
    def __init__(self, n_classes=N_CLASSES):
        super().__init__()
        self.conv1_ = nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3)
        self.bn1 = nn.BatchNorm2d(64)
        self.relu1 = nn.ReLU(inplace=True)
        self.r01 = Residual(64, 128)
        self.maxpool = nn.MaxPool2d(kernel_size=2, stride=2)
        self.r02 = Residual(128, 128)
        self.r03 = Residual(128, 128)
        self.r04 = Residual(128, 256)

        self.maxpool1 = nn.MaxPool2d(kernel_size=2, stride=2)
        self.r11_a = Residual(256, 256)
        self.r12_a = Residual(256, 256)
        self.r13_a = Residual(256, 256)

        self.maxpool2 = nn.MaxPool2d(kernel_size=2, stride=2)
        self.r21_a = Residual(256, 256)
        self.r22_a = Residual(256, 256)
        self.r23_a = Residual(256, 256)

        self.maxpool3 = nn.MaxPool2d(kernel_size=2, stride=2)
        self.r31_a = Residual(256, 256)
        self.r32_a = Residual(256, 256)
        self.r33_a = Residual(256, 256)

        self.maxpool4 = nn.MaxPool2d(kernel_size=2, stride=2)
        self.r41_a = Residual(256, 256)
        self.r42_a = Residual(256, 256)
        self.r43_a = Residual(256, 256)
        self.r44_a = Residual(256, 512)
        self.r45_a = Residual(512, 512)
        self.upsample4 = nn.ConvTranspose2d(512, 512, kernel_size=2, stride=2)

        self.r41_b = Residual(256, 256)
        self.r42_b = Residual(256, 256)
        self.r43_b = Residual(256, 512)
        self.r4_ = Residual(512, 512)
        self.upsample3 = nn.ConvTranspose2d(512, 512, kernel_size=2, stride=2)

        self.r31_b = Residual(256, 256)
        self.r32_b = Residual(256, 256)
        self.r33_b = Residual(256, 512)
        self.r3_ = Residual(512, 512)
        self.upsample2 = nn.ConvTranspose2d(512, 512, kernel_size=2, stride=2)

        self.r21_b = Residual(256, 256)
        self.r22_b = Residual(256, 256)
        self.r23_b = Residual(256, 512)
        self.r2_ = Residual(512, 512)
        self.upsample1 = nn.ConvTranspose2d(512, 512, kernel_size=2, stride=2)

        self.r11_b = Residual(256, 256)
        self.r12_b = Residual(256, 256)
        self.r13_b = Residual(256, 512)

        self.conv2_ = nn.Conv2d(512, 512, kernel_size=1)
        self.bn2 = nn.BatchNorm2d(512)
        self.relu2 = nn.ReLU(inplace=True)
        self.conv3_ = nn.Conv2d(512, 256, kernel_size=1)
        self.bn3 = nn.BatchNorm2d(256)
        self.relu3 = nn.ReLU(inplace=True)
        self.conv4_ = nn.Conv2d(256, n_classes, kernel_size=1)
        self.upsample = nn.ConvTranspose2d(
            n_classes, n_classes, kernel_size=4, stride=4
        )

    def forward(self, x):
        out = self.relu1(self.bn1(self.conv1_(x)))
        out = self.maxpool(out)
        out = self.r04(self.r03(self.r02(self.r01(out))))

        out1a = self.r13_a(self.r12_a(self.r11_a(self.maxpool1(out))))
        out1b = self.r13_b(self.r12_b(self.r11_b(out)))

        out2a = self.r23_a(self.r22_a(self.r21_a(self.maxpool2(out1a))))
        out2b = self.r23_b(self.r22_b(self.r21_b(out1a)))

        out3a = self.r33_a(self.r32_a(self.r31_a(self.maxpool3(out2a))))
        out3b = self.r33_b(self.r32_b(self.r31_b(out2a)))

        out4a = self.maxpool4(out3a)
        out4a = self.r45_a(self.r44_a(self.r43_a(self.r42_a(self.r41_a(out4a)))))
        out4b = self.r43_b(self.r42_b(self.r41_b(out3a)))

        out4 = self.r4_(_upsample_add(self.upsample4(out4a), out4b))
        out3 = self.r3_(_upsample_add(self.upsample3(out4), out3b))
        out2 = self.r2_(_upsample_add(self.upsample2(out3), out2b))
        out = _upsample_add(self.upsample1(out2), out1b)

        out = self.relu2(self.bn2(self.conv2_(out)))
        out = self.relu3(self.bn3(self.conv3_(out)))
        out = self.upsample(self.conv4_(out))

        # only the junction heatmaps go through a sigmoid, room and icon
        # channels stay as logits
        heat = torch.sigmoid(out[:, :N_HEATMAPS])
        return torch.cat([heat, out[:, N_HEATMAPS:]], dim=1)
